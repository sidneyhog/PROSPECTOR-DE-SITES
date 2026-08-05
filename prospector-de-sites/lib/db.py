#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Acesso único ao SQLite do CRM (prospector.db).

Sem dependências externas: só sqlite3 (stdlib). Ver docs/ARQUITETURA_TECNICA.md
§8.3 e docs/PLANO_IMPLEMENTACAO.md §4 (Fase 1).

Por regra arquitetural (docs/AGENTES.md §0.2/§21, docs/CRM.md §7): só o
agente CRM chama estas funções para persistir dados de negócio. Qualquer
outro agente apenas devolve o payload `dados_para_crm` ao Orquestrador
(docs/AGENTES.md §0.4) — quem grava é sempre o CRM, através deste módulo.

NOTA DE MANUTENÇÃO: cópia idêntica em
skills/dashboard-leads/references/db.py (mesmo motivo de migrations.py —
ver nota no topo daquele arquivo). Mantenha as duas em sincronia.

LIMITAÇÃO CONHECIDA (Fase 1): `TRANSICOES_VALIDAS` só reconhece o
vocabulário de status novo (docs/CRM.md §2). Leads de instalações v2
existentes com status legado (`novo`, `redesenhado`, `publicado`,
`proposta`, `respondeu`, `descartado`) não têm transição de saída
reconhecida ainda — `atualizar_estado` vai bloquear qualquer tentativa
sobre eles até a Fase 2 definir o mapeamento de migração desses status
legados para o novo pipeline.

"""
import json
import sqlite3
from datetime import datetime

import migrations

CAMPOS_LEAD = ['slug', 'nome', 'nicho', 'cidade', 'nota', 'avaliacoes', 'email',
               'telefone', 'whatsapp', 'siteAntigo', 'motivo', 'status', 'urlNova',
               'dataProposta', 'valor', 'obs', 'contratoStatus', 'contratoEm',
               'manutencao', 'pago', 'docCliente', 'endCliente', 'https_validado_em',
               'valor_setup']

# Máquina de estados (docs/CRM.md §2.2/§2.3): de_status -> {para_status permitidos}.
# None = criação do lead (nenhum estado anterior ainda).
TRANSICOES_VALIDAS = {
    None: {'encontrado'},
    'encontrado': {'qualificado', 'perdido'},
    'qualificado': {'em_analise'},
    'em_analise': {'site_auditado'},
    'site_auditado': {'pagina_gerada'},
    'pagina_gerada': {'pagina_gerada', 'pagina_revisada'},  # loop de reprovação do QA
    'pagina_revisada': {'contato_realizado'},
    'contato_realizado': {'negociacao', 'follow_up'},
    'follow_up': {'follow_up', 'negociacao', 'perdido'},
    'negociacao': {'fechado', 'perdido', 'follow_up'},
    'perdido': {'qualificado'},  # reabertura manual (docs/CRM.md §2.3)
    'fechado': set(),
}


def _agora():
    return datetime.now().strftime('%Y-%m-%d %H:%M:%S')


def conectar(caminho_db):
    """Abre a conexão e garante que o schema está na versão mais recente."""
    c = sqlite3.connect(caminho_db)
    migrations.aplicar(c)
    return c


def obter_lead(caminho_db, slug):
    """Retorna o lead como dict, ou None se não existir."""
    c = conectar(caminho_db)
    c.row_factory = sqlite3.Row
    row = c.execute('SELECT * FROM leads WHERE slug=?', (slug,)).fetchone()
    c.close()
    return dict(row) if row else None


def listar_leads(caminho_db, nicho=None, cidade=None):
    """Lista leads (slug, nome) filtrando por nicho/cidade — usado pelo
    agente `iris`, via Orquestrador, para não duplicar leads já
    existentes no CRM na mesma busca (docs/AGENTES.md §3, RF-04)."""
    c = conectar(caminho_db)
    c.row_factory = sqlite3.Row
    condicoes, valores = [], []
    if nicho:
        condicoes.append('nicho = ?')
        valores.append(nicho)
    if cidade:
        condicoes.append('cidade = ?')
        valores.append(cidade)
    sql = 'SELECT slug, nome FROM leads'
    if condicoes:
        sql += ' WHERE ' + ' AND '.join(condicoes)
    rows = [dict(r) for r in c.execute(sql, valores).fetchall()]
    c.close()
    return rows


def atualizar_estado(caminho_db, slug, novo_estado, dados=None, agente='carmem', motivo=None):
    """Valida a transição de estado (docs/CRM.md §2.3) e persiste.

    `dados` é um dict com os demais campos de `leads` a gravar junto (ex.:
    nome, nicho, valor_setup...). Retorna:
        {'ok': True, 'lead': {...}}            em caso de sucesso
        {'ok': False, 'motivo': '...'}          se a transição não é permitida
    Nunca lança exceção por transição inválida — é o CRM reportando
    `status: bloqueado` ao Orquestrador (docs/AGENTES.md §0.4/§21).
    """
    c = conectar(caminho_db)
    c.row_factory = sqlite3.Row
    atual = c.execute('SELECT * FROM leads WHERE slug=?', (slug,)).fetchone()
    de_status = atual['status'] if atual else None

    permitidos = TRANSICOES_VALIDAS.get(de_status, set())
    if novo_estado not in permitidos:
        c.close()
        return {
            'ok': False,
            'motivo': 'transicao invalida: %s -> %s (permitidos a partir de %s: %s)'
                      % (de_status, novo_estado, de_status, sorted(permitidos)),
        }

    campos = dict(dados or {})
    campos['slug'] = slug
    campos['status'] = novo_estado
    colunas = [k for k in campos if k in CAMPOS_LEAD]
    if atual is None:
        c.execute(
            'INSERT INTO leads (%s) VALUES (%s)' % (','.join(colunas), ','.join('?' * len(colunas))),
            [campos[k] for k in colunas],
        )
    else:
        sets = [k for k in colunas if k != 'slug']
        c.execute(
            'UPDATE leads SET %s, atualizado=? WHERE slug=?' % ','.join('%s=?' % k for k in sets),
            [campos[k] for k in sets] + [_agora(), slug],
        )

    c.execute(
        'INSERT INTO interacoes (lead_slug, de_status, para_status, agente, motivo, criado_em) '
        'VALUES (?,?,?,?,?,?)',
        (slug, de_status, novo_estado, agente, motivo, _agora()),
    )
    c.commit()
    lead = dict(c.execute('SELECT * FROM leads WHERE slug=?', (slug,)).fetchone())
    c.close()
    return {'ok': True, 'lead': lead}


def registrar_interacao_manual(caminho_db, slug, de_status, para_status, motivo=None):
    """Registra em `interacoes` uma mudança de status feita por edição
    humana direta no dashboard (drag-and-drop/formulário), SEM validar
    contra `TRANSICOES_VALIDAS` — é um canal de override intencional do
    operador, não uma transição de agente (docs/PLANO_IMPLEMENTACAO.md
    §12, gap encontrado na Fase 8 e fechado na Fase 9: antes disso, edição
    manual não deixava rastro de auditoria). Chamado por
    `dashboard-server.py`, não pelos agentes."""
    if de_status == para_status:
        return
    c = conectar(caminho_db)
    c.execute(
        'INSERT INTO interacoes (lead_slug, de_status, para_status, agente, motivo, criado_em) '
        'VALUES (?,?,?,?,?,?)',
        (slug, de_status, para_status, 'operador (dashboard)', motivo, _agora()),
    )
    c.commit()
    c.close()


def registrar_execucao(caminho_db, agente, lead_slug, status, resumo,
                        criterios_pendentes=None, referencias=None, iniciado_em=None):
    """Grava uma linha em execucoes_agentes (log de execução — RNF-10).

    Em uso normal, chamado via `lib/auditlog.py` (que também espelha em
    arquivo) pelo Orquestrador, logo após cada retorno de agente — não pelo
    próprio agente nem pelo agente CRM (docs/ARQUITETURA_TECNICA.md §10).
    """
    c = conectar(caminho_db)
    agora = _agora()
    c.execute(
        'INSERT INTO execucoes_agentes '
        '(lead_slug, agente, status, resumo, criterios_pendentes, referencias, iniciado_em, concluido_em) '
        'VALUES (?,?,?,?,?,?,?,?)',
        (
            lead_slug, agente, status, resumo,
            json.dumps(criterios_pendentes or [], ensure_ascii=False),
            json.dumps(referencias or [], ensure_ascii=False),
            iniciado_em or agora, agora,
        ),
    )
    c.commit()
    c.close()


def listar_execucoes(caminho_db, lead_slug=None, limite=200):
    """Lista execuções de agente (mais recentes primeiro), opcionalmente
    filtrando por lead — usado pela aba "Execuções" do dashboard
    (docs/CRM.md §8, docs/ARQUITETURA_TECNICA.md §8.3)."""
    c = conectar(caminho_db)
    c.row_factory = sqlite3.Row
    sql = 'SELECT * FROM execucoes_agentes'
    valores = []
    if lead_slug:
        sql += ' WHERE lead_slug=?'
        valores.append(lead_slug)
    sql += ' ORDER BY id DESC LIMIT ?'
    valores.append(limite)
    rows = c.execute(sql, valores).fetchall()
    c.close()
    resultado = []
    for row in rows:
        item = dict(row)
        item['criterios_pendentes'] = json.loads(item['criterios_pendentes'] or '[]')
        item['referencias'] = json.loads(item['referencias'] or '[]')
        resultado.append(item)
    return resultado


def registrar_auditoria(caminho_db, lead_slug, tipo, dados):
    """Grava um dossiê de diagnóstico do Grupo B (docs/AGENTES.md §5-§12).
    `tipo` é um de: tecnica|seo|seo_local|performance|cwv|acessibilidade|
    inteligencia_competitiva|gbp. `dados` é um dict serializável em JSON.

    Cada chamada grava uma NOVA linha (histórico completo, nunca
    sobrescreve) — `obter_auditorias` devolve só a mais recente por tipo.
    A decisão de reaproveitar uma auditoria recente em vez de reprocessar
    (cache — docs/ARQUITETURA_TECNICA.md §6) é do Orquestrador, não desta
    função.
    """
    c = conectar(caminho_db)
    c.execute(
        'INSERT INTO auditorias (lead_slug, tipo, dados_json, criado_em) VALUES (?,?,?,?)',
        (lead_slug, tipo, json.dumps(dados, ensure_ascii=False), _agora()),
    )
    c.commit()
    c.close()


def obter_auditorias(caminho_db, lead_slug):
    """Retorna o dossiê consolidado do lead: {tipo: {'dados': {...},
    'criado_em': '...'}}, só a auditoria mais recente de cada tipo.

    Ordena por `id` (não por `criado_em`): o timestamp tem precisão de
    segundo e várias auditorias podem ser gravadas no mesmo segundo — `id`
    (autoincrement) é a única ordem estritamente confiável de inserção.
    """
    c = conectar(caminho_db)
    rows = c.execute(
        'SELECT tipo, dados_json, criado_em FROM auditorias WHERE lead_slug=? ORDER BY id',
        (lead_slug,),
    ).fetchall()
    c.close()
    dossie = {}
    for tipo, dados_json, criado_em in rows:
        dossie[tipo] = {'dados': json.loads(dados_json), 'criado_em': criado_em}
    return dossie


def registrar_gbp_snapshot(caminho_db, lead_slug, nota, num_avaliacoes, completude_percentual):
    """Grava um snapshot do Google Business Profile do lead (RF-08),
    comparável a snapshots anteriores do mesmo lead via
    `ultimo_gbp_snapshot`."""
    c = conectar(caminho_db)
    c.execute(
        'INSERT INTO gbp_snapshots (lead_slug, nota, num_avaliacoes, completude_percentual, capturado_em) '
        'VALUES (?,?,?,?,?)',
        (lead_slug, nota, num_avaliacoes, completude_percentual, _agora()),
    )
    c.commit()
    c.close()


def ultimo_gbp_snapshot(caminho_db, lead_slug):
    """Retorna o snapshot de GBP mais recente do lead, ou None se nunca
    capturado. Ordena por `id` (ver nota em `obter_auditorias` sobre
    precisão de timestamp)."""
    c = conectar(caminho_db)
    c.row_factory = sqlite3.Row
    row = c.execute(
        'SELECT * FROM gbp_snapshots WHERE lead_slug=? ORDER BY id DESC LIMIT 1',
        (lead_slug,),
    ).fetchone()
    c.close()
    return dict(row) if row else None


def registrar_estetica(caminho_db, lead_slug, paleta, tipografia, layout_hero):
    """Grava a direção estética usada num redesign (Grupo C, Fase 4) —
    consultada por `listar_estetica_recente` para os agentes `nina` e
    `bruna` não repetirem paleta/tipografia/layout de hero de clientes
    recentes (regra já vigente na v2 com `ui-ux-pro-max`)."""
    c = conectar(caminho_db)
    c.execute(
        'INSERT INTO estetica_historico (lead_slug, paleta, tipografia, layout_hero, gerado_em) '
        'VALUES (?,?,?,?,?)',
        (lead_slug, paleta, tipografia, layout_hero, _agora()),
    )
    c.commit()
    c.close()


def listar_estetica_recente(caminho_db, limite=5):
    """Retorna as últimas `limite` direções estéticas usadas (mais recente
    primeiro), para checagem de variedade antes de definir a de um novo
    lead. Ordena por `id` (ver nota em `obter_auditorias` sobre precisão
    de timestamp)."""
    c = conectar(caminho_db)
    c.row_factory = sqlite3.Row
    rows = c.execute(
        'SELECT lead_slug, paleta, tipografia, layout_hero, gerado_em '
        'FROM estetica_historico ORDER BY id DESC LIMIT ?',
        (limite,),
    ).fetchall()
    c.close()
    return [dict(r) for r in rows]


def atualizar_campos(caminho_db, slug, dados, agente):
    """Atualiza campos do lead SEM transição de estado — diferente de
    `atualizar_estado`: não valida contra `TRANSICOES_VALIDAS` nem grava
    em `interacoes` (não é uma mudança de estado do funil). Uso típico:
    o agente `diego` registrando `urlNova`/`https_validado_em` num lead
    que permanece `pagina_revisada` (a transição para `fechado` acontece
    depois, por assinatura de contrato — docs/CRM.md §3).

    Retorna {'ok': True, 'lead': {...}} ou {'ok': False, 'motivo': '...'}
    se o lead não existir.
    """
    c = conectar(caminho_db)
    c.row_factory = sqlite3.Row
    atual = c.execute('SELECT * FROM leads WHERE slug=?', (slug,)).fetchone()
    if atual is None:
        c.close()
        return {'ok': False, 'motivo': 'lead nao encontrado: %s' % slug}
    colunas = [k for k in dados if k in CAMPOS_LEAD and k != 'slug']
    if colunas:
        c.execute(
            'UPDATE leads SET %s, atualizado=? WHERE slug=?' % ','.join('%s=?' % k for k in colunas),
            [dados[k] for k in colunas] + [_agora(), slug],
        )
        c.commit()
    lead = dict(c.execute('SELECT * FROM leads WHERE slug=?', (slug,)).fetchone())
    c.close()
    return {'ok': True, 'lead': lead}


def registrar_proposta(caminho_db, lead_slug, valor_setup, valor_manutencao, justificativa):
    """Grava uma proposta comercial (agente `valentina`),
    ainda não enviada (`enviado_em` fica NULL até `marcar_proposta_enviada`).
    Também espelha `valor_setup` em `leads` (mesmo padrão já usado por
    `manutencao`, para leitura rápida no dashboard). Retorna o id da
    proposta criada."""
    c = conectar(caminho_db)
    c.execute(
        'INSERT INTO propostas (lead_slug, valor_setup, valor_manutencao, justificativa, criado_em) '
        'VALUES (?,?,?,?,?)',
        (lead_slug, valor_setup, valor_manutencao, justificativa, _agora()),
    )
    proposta_id = c.execute('SELECT last_insert_rowid()').fetchone()[0]
    c.execute('UPDATE leads SET valor_setup=?, manutencao=? WHERE slug=?',
              (valor_setup, valor_manutencao, lead_slug))
    c.commit()
    c.close()
    return proposta_id


def marcar_proposta_enviada(caminho_db, lead_slug):
    """Marca a proposta mais recente (ainda não enviada) do lead como
    enviada agora. Retorna {'ok': True} ou {'ok': False, 'motivo': '...'}
    se não houver proposta pendente de envio."""
    c = conectar(caminho_db)
    row = c.execute(
        'SELECT id FROM propostas WHERE lead_slug=? AND enviado_em IS NULL ORDER BY id DESC LIMIT 1',
        (lead_slug,),
    ).fetchone()
    if row is None:
        c.close()
        return {'ok': False, 'motivo': 'nenhuma proposta pendente de envio para %s' % lead_slug}
    c.execute('UPDATE propostas SET enviado_em=? WHERE id=?', (_agora(), row[0]))
    c.commit()
    c.close()
    return {'ok': True}


def registrar_lgpd_checklist(caminho_db, lead_slug, campo, finalidade, retencao, aprovado):
    """Grava o veredito de conformidade LGPD de um campo de dado pessoal
    (agente `lia`). Cada chamada grava uma NOVA linha (histórico); só a
    mais recente por campo conta (ver `lgpd_status`)."""
    c = conectar(caminho_db)
    c.execute(
        'INSERT INTO lgpd_checklist (lead_slug, campo, finalidade, retencao, aprovado, verificado_em) '
        'VALUES (?,?,?,?,?,?)',
        (lead_slug, campo, finalidade, retencao, 1 if aprovado else 0, _agora()),
    )
    c.commit()
    c.close()


def lgpd_status(caminho_db, lead_slug):
    """Retorna o checklist LGPD consolidado do lead: {'checklist':
    {campo: {finalidade, retencao, aprovado, verificado_em}}, 'aprovado':
    bool} — `aprovado` só é True se houver ao menos um campo verificado e
    TODOS estiverem aprovados. Ordena por `id` (ver nota em
    `obter_auditorias` sobre precisão de timestamp)."""
    c = conectar(caminho_db)
    rows = c.execute(
        'SELECT campo, finalidade, retencao, aprovado, verificado_em '
        'FROM lgpd_checklist WHERE lead_slug=? ORDER BY id',
        (lead_slug,),
    ).fetchall()
    c.close()
    checklist = {}
    for campo, finalidade, retencao, aprovado, verificado_em in rows:
        checklist[campo] = {
            'finalidade': finalidade, 'retencao': retencao,
            'aprovado': bool(aprovado), 'verificado_em': verificado_em,
        }
    aprovado_geral = len(checklist) > 0 and all(v['aprovado'] for v in checklist.values())
    return {'checklist': checklist, 'aprovado': aprovado_geral}


def registrar_resposta(caminho_db, lead_slug):
    """Marca a resposta mais recente esperada do lead como recebida — o
    follow-up ainda não respondido mais recente, ou (se não houver
    follow-up) a proposta mais recente ainda não respondida. Não persiste
    transição de estado (`contato_realizado`/`follow_up -> negociacao`
    fica a cargo de quem chamar, via `atualizar_estado`)."""
    c = conectar(caminho_db)
    row_fu = c.execute(
        'SELECT id FROM followups WHERE lead_slug=? AND respondido=0 ORDER BY id DESC LIMIT 1',
        (lead_slug,),
    ).fetchone()
    if row_fu:
        c.execute('UPDATE followups SET respondido=1 WHERE id=?', (row_fu[0],))
    else:
        row_prop = c.execute(
            'SELECT id FROM propostas WHERE lead_slug=? AND respondido_em IS NULL ORDER BY id DESC LIMIT 1',
            (lead_slug,),
        ).fetchone()
        if row_prop:
            c.execute('UPDATE propostas SET respondido_em=? WHERE id=?', (_agora(), row_prop[0]))
    c.commit()
    c.close()


def registrar_followup(caminho_db, lead_slug, tentativa_numero):
    """Grava uma tentativa de follow-up enviada agora."""
    c = conectar(caminho_db)
    c.execute(
        'INSERT INTO followups (lead_slug, tentativa_numero, enviado_em, respondido) VALUES (?,?,?,0)',
        (lead_slug, tentativa_numero, _agora()),
    )
    c.commit()
    c.close()


def listar_leads_para_followup(caminho_db, dias_sem_resposta=3, limite_tentativas=1):
    """Retorna leads elegíveis para (mais) um follow-up: em
    `contato_realizado` (proposta enviada, sem follow-up ainda) ou
    `follow_up` (já com tentativa(s) anterior(es)), sem resposta detectada
    há pelo menos `dias_sem_resposta` desde o último contato (proposta ou
    follow-up anterior), e com menos de `limite_tentativas` follow-ups já
    feitos. Cada item: {slug, status, tentativas_ja_feitas,
    dias_sem_resposta}. Não dispara nada — só identifica candidatos; quem
    chama decide se envia (agente `fabi`) e persiste o resultado.
    """
    c = conectar(caminho_db)
    c.row_factory = sqlite3.Row
    candidatos = c.execute(
        "SELECT * FROM leads WHERE status IN ('contato_realizado', 'follow_up')"
    ).fetchall()
    elegiveis = []
    for lead in candidatos:
        slug = lead['slug']
        n_followups = c.execute(
            'SELECT COUNT(*) FROM followups WHERE lead_slug=?', (slug,)
        ).fetchone()[0]
        if n_followups >= limite_tentativas:
            continue
        ultimo_followup = c.execute(
            'SELECT enviado_em, respondido FROM followups WHERE lead_slug=? ORDER BY id DESC LIMIT 1',
            (slug,),
        ).fetchone()
        if ultimo_followup:
            if ultimo_followup['respondido']:
                continue
            referencia = ultimo_followup['enviado_em']
        else:
            proposta = c.execute(
                'SELECT enviado_em, respondido_em FROM propostas WHERE lead_slug=? ORDER BY id DESC LIMIT 1',
                (slug,),
            ).fetchone()
            if proposta is None or proposta['enviado_em'] is None or proposta['respondido_em'] is not None:
                continue
            referencia = proposta['enviado_em']
        dias = c.execute(
            "SELECT julianday('now','localtime') - julianday(?)", (referencia,)
        ).fetchone()[0]
        if dias >= dias_sem_resposta:
            elegiveis.append({
                'slug': slug, 'status': lead['status'],
                'tentativas_ja_feitas': n_followups, 'dias_sem_resposta': round(dias, 1),
            })
    c.close()
    return elegiveis


def metricas_funil(caminho_db):
    """Consolida métricas de funil a partir de propostas/followups/leads
    (agente `ana`, docs/AGENTES.md §23) — não interpreta os dados,
    só consolida contagens/médias já existentes."""
    c = conectar(caminho_db)
    total_propostas = c.execute(
        "SELECT COUNT(*) FROM propostas WHERE enviado_em IS NOT NULL"
    ).fetchone()[0]
    total_respondidas = c.execute(
        "SELECT COUNT(*) FROM propostas WHERE respondido_em IS NOT NULL"
    ).fetchone()[0]
    tempo_medio_resposta_dias = c.execute(
        "SELECT AVG(julianday(respondido_em) - julianday(enviado_em)) FROM propostas "
        "WHERE enviado_em IS NOT NULL AND respondido_em IS NOT NULL"
    ).fetchone()[0]
    total_followups = c.execute('SELECT COUNT(*) FROM followups').fetchone()[0]
    total_perdidos_sem_resposta = c.execute(
        "SELECT COUNT(*) FROM leads WHERE status='perdido' AND motivo LIKE 'sem_resposta%'"
    ).fetchone()[0]
    total_fechados = c.execute("SELECT COUNT(*) FROM leads WHERE status='fechado'").fetchone()[0]
    c.close()
    taxa_resposta = (total_respondidas / total_propostas) if total_propostas else None
    return {
        'total_propostas_enviadas': total_propostas,
        'total_respondidas': total_respondidas,
        'taxa_resposta': taxa_resposta,
        'tempo_medio_resposta_dias': tempo_medio_resposta_dias,
        'total_followups_enviados': total_followups,
        'total_perdidos_sem_resposta': total_perdidos_sem_resposta,
        'total_fechados': total_fechados,
    }


def registrar_versao_prompt(caminho_db, agente, versao, hash_prompt, aprovado_em=None, observacoes=None):
    """Grava uma versão de prompt de agente (agente `gustavo`,
    docs/AGENTES.md §26). Cada mudança de prompt gera uma nova linha —
    histórico completo, nunca sobrescreve."""
    c = conectar(caminho_db)
    c.execute(
        'INSERT INTO prompts_versionamento (agente, versao, hash, aprovado_em, observacoes) VALUES (?,?,?,?,?)',
        (agente, versao, hash_prompt, aprovado_em, observacoes),
    )
    c.commit()
    c.close()


def obter_versoes_prompt(caminho_db, agente):
    """Retorna o histórico de versões de prompt de um agente, mais recente
    primeiro."""
    c = conectar(caminho_db)
    c.row_factory = sqlite3.Row
    rows = c.execute(
        'SELECT agente, versao, hash, aprovado_em, observacoes FROM prompts_versionamento '
        'WHERE agente=? ORDER BY id DESC',
        (agente,),
    ).fetchall()
    c.close()
    return [dict(r) for r in rows]
