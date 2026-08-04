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
               'manutencao', 'pago', 'docCliente', 'endCliente']

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
    agente `prospeccao`, via Orquestrador, para não duplicar leads já
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


def atualizar_estado(caminho_db, slug, novo_estado, dados=None, agente='crm', motivo=None):
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
    'criado_em': '...'}}, só a auditoria mais recente de cada tipo."""
    c = conectar(caminho_db)
    rows = c.execute(
        'SELECT tipo, dados_json, criado_em FROM auditorias WHERE lead_slug=? ORDER BY criado_em',
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
    capturado."""
    c = conectar(caminho_db)
    c.row_factory = sqlite3.Row
    row = c.execute(
        'SELECT * FROM gbp_snapshots WHERE lead_slug=? ORDER BY capturado_em DESC LIMIT 1',
        (lead_slug,),
    ).fetchone()
    c.close()
    return dict(row) if row else None
