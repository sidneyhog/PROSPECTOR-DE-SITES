#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Migration runner idempotente para o schema do prospector.db.

Sem dependências externas: só sqlite3 (stdlib). Ver docs/ARQUITETURA_TECNICA.md
§4.4 e docs/PLANO_IMPLEMENTACAO.md §3 (Fase 0).

Substitui o padrão anterior de `ALTER TABLE ... ; except OperationalError: pass`
por uma lista ordenada de migrações, cada uma aplicada no máximo uma vez,
controlada pela tabela `schema_version`.

Uso:
    import sqlite3, migrations
    c = sqlite3.connect('prospector.db')
    migrations.aplicar(c)

NOTA DE MANUTENÇÃO: este arquivo tem uma cópia idêntica em
skills/dashboard-leads/references/migrations.py, copiada junto de
dashboard-server.py para a pasta conectada do usuário na configuração
(mesmo padrão de distribuição já usado para os demais arquivos da skill,
que são todos autocontidos). Este repositório não tem build/empacotamento
próprio ainda — mantenha as duas cópias em sincronia ao editar.
"""

MIGRACOES = []


def _migracao(numero):
    def registrar(fn):
        MIGRACOES.append((numero, fn))
        return fn
    return registrar


def _tem_coluna(c, tabela, coluna):
    return coluna in [r[1] for r in c.execute("PRAGMA table_info(%s)" % tabela).fetchall()]


def _add_coluna_se_faltando(c, tabela, coluna, tipo):
    if not _tem_coluna(c, tabela, coluna):
        c.execute('ALTER TABLE %s ADD COLUMN %s %s' % (tabela, coluna, tipo))


@_migracao(1)
def _m1_schema_leads_base(c):
    """Formaliza o schema já existente da v2 (nenhuma tabela/coluna nova)."""
    c.execute('''CREATE TABLE IF NOT EXISTS leads(
        slug TEXT PRIMARY KEY, nome TEXT, nicho TEXT, cidade TEXT, nota REAL, avaliacoes INTEGER,
        email TEXT, telefone TEXT, whatsapp TEXT, siteAntigo TEXT, motivo TEXT,
        status TEXT DEFAULT 'novo', urlNova TEXT, dataProposta TEXT, valor REAL, obs TEXT,
        atualizado TEXT DEFAULT (datetime('now','localtime')))''')
    for col, tipo in [
        ('contratoStatus', "TEXT DEFAULT 'pendente'"),
        ('contratoEm', 'TEXT'),
        ('manutencao', 'REAL'),
        ('pago', 'INTEGER DEFAULT 0'),
        ('docCliente', 'TEXT'),
        ('endCliente', 'TEXT'),
    ]:
        _add_coluna_se_faltando(c, 'leads', col, tipo)


@_migracao(2)
def _m2_interacoes_e_execucoes(c):
    """Fase 1 (docs/PLANO_IMPLEMENTACAO.md §4): histórico de transições de
    estado do lead (auditabilidade — RNF-04/RNF-10) e log de execução de
    agentes (observabilidade — RNF-10). Ver docs/ARQUITETURA_TECNICA.md §4.2."""
    c.execute('''CREATE TABLE IF NOT EXISTS interacoes(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        lead_slug TEXT NOT NULL REFERENCES leads(slug),
        de_status TEXT,
        para_status TEXT NOT NULL,
        agente TEXT NOT NULL,
        motivo TEXT,
        criado_em TEXT NOT NULL)''')
    c.execute('''CREATE TABLE IF NOT EXISTS execucoes_agentes(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        lead_slug TEXT REFERENCES leads(slug),
        agente TEXT NOT NULL,
        status TEXT NOT NULL,
        resumo TEXT,
        criterios_pendentes TEXT,
        referencias TEXT,
        iniciado_em TEXT NOT NULL,
        concluido_em TEXT)''')


@_migracao(3)
def _m3_auditorias_e_gbp(c):
    """Fase 3 (docs/PLANO_IMPLEMENTACAO.md §6): dossiês de diagnóstico do
    Grupo B (RF-06) e snapshots de Google Business Profile (RF-08). Ver
    docs/ARQUITETURA_TECNICA.md §4.2."""
    c.execute('''CREATE TABLE IF NOT EXISTS auditorias(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        lead_slug TEXT NOT NULL REFERENCES leads(slug),
        tipo TEXT NOT NULL,
        dados_json TEXT NOT NULL,
        criado_em TEXT NOT NULL)''')
    c.execute('''CREATE TABLE IF NOT EXISTS gbp_snapshots(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        lead_slug TEXT NOT NULL REFERENCES leads(slug),
        nota REAL,
        num_avaliacoes INTEGER,
        completude_percentual REAL,
        capturado_em TEXT NOT NULL)''')


@_migracao(4)
def _m4_estetica_historico(c):
    """Fase 4 (docs/PLANO_IMPLEMENTACAO.md §7): histórico de estética usada
    por lead (paleta, tipografia, layout de hero), para os agentes
    `nina` e `bruna` não repetirem a direção estética de clientes
    recentes. Ver docs/ARQUITETURA_TECNICA.md §4.2 (coluna `layout_hero`
    é uma extensão aditiva ao schema ali documentado, para cobrir também a
    regra de não repetir layout de hero, já vigente na v2)."""
    c.execute('''CREATE TABLE IF NOT EXISTS estetica_historico(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        lead_slug TEXT NOT NULL REFERENCES leads(slug),
        paleta TEXT,
        tipografia TEXT,
        layout_hero TEXT,
        gerado_em TEXT NOT NULL)''')


@_migracao(5)
def _m5_https_validado(c):
    """Fase 5 (docs/PLANO_IMPLEMENTACAO.md §8): marca quando o HTTPS de um
    lead publicado foi validado (RF-11) — condição para a transição
    `negociacao -> fechado` (docs/CRM.md §3). Não adicionamos `vps_host`/
    `vps_dominio` por lead (como o esboço inicial de
    docs/ARQUITETURA_TECNICA.md §4.1 cogitava): a VPS é uma só por
    instalação (config global `vps.dominio`), não por lead — cada lead só
    precisa saber QUANDO seu HTTPS foi validado."""
    _add_coluna_se_faltando(c, 'leads', 'https_validado_em', 'TEXT')


@_migracao(6)
def _m6_propostas_e_lgpd(c):
    """Fase 6 (docs/PLANO_IMPLEMENTACAO.md §9): separa preço (tabela
    `propostas`, agente `valentina`) de redação (agente
    `clarice`, Fase 4), e introduz o gate de conformidade LGPD
    obrigatório antes de qualquer envio externo (RF-16). Ver
    docs/ARQUITETURA_TECNICA.md §4.2. `leads.valor_setup` é um espelho
    denormalizado do valor da proposta mais recente, para leitura rápida
    no dashboard (mesmo padrão já usado por `manutencao`)."""
    _add_coluna_se_faltando(c, 'leads', 'valor_setup', 'REAL')
    c.execute('''CREATE TABLE IF NOT EXISTS propostas(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        lead_slug TEXT NOT NULL REFERENCES leads(slug),
        valor_setup REAL,
        valor_manutencao REAL,
        justificativa TEXT,
        criado_em TEXT NOT NULL,
        enviado_em TEXT,
        respondido_em TEXT)''')
    c.execute('''CREATE TABLE IF NOT EXISTS lgpd_checklist(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        lead_slug TEXT NOT NULL REFERENCES leads(slug),
        campo TEXT NOT NULL,
        finalidade TEXT,
        retencao TEXT,
        aprovado INTEGER NOT NULL DEFAULT 0,
        verificado_em TEXT NOT NULL)''')


@_migracao(7)
def _m7_followups(c):
    """Fase 7 (docs/PLANO_IMPLEMENTACAO.md §10): tentativas de follow-up
    por lead (RF-13), para não depender de o operador rodar /respostas e
    /followup manualmente todo dia. Ver docs/ARQUITETURA_TECNICA.md §4.2."""
    c.execute('''CREATE TABLE IF NOT EXISTS followups(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        lead_slug TEXT NOT NULL REFERENCES leads(slug),
        tentativa_numero INTEGER NOT NULL,
        enviado_em TEXT NOT NULL,
        respondido INTEGER NOT NULL DEFAULT 0)''')


@_migracao(8)
def _m8_prompts_versionamento_e_embeddings(c):
    """Fase 8 (docs/PLANO_IMPLEMENTACAO.md §11): versionamento de prompts
    (agente `gustavo`) e memória compartilhada via embeddings/
    RAG (docs/MEMORIA.md §9). Ver docs/ARQUITETURA_TECNICA.md §4.2."""
    c.execute('''CREATE TABLE IF NOT EXISTS prompts_versionamento(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        agente TEXT NOT NULL,
        versao TEXT NOT NULL,
        hash TEXT NOT NULL,
        aprovado_em TEXT,
        observacoes TEXT)''')
    c.execute('''CREATE TABLE IF NOT EXISTS embeddings(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        ref_tipo TEXT NOT NULL,
        ref_id TEXT NOT NULL,
        nicho TEXT,
        texto_fonte TEXT NOT NULL,
        vetor_json TEXT NOT NULL,
        modelo TEXT NOT NULL,
        criado_em TEXT NOT NULL)''')


@_migracao(9)
def _m9_canal_whatsapp(c):
    """Decisão do operador (05/08/2026): WhatsApp passa a ser o canal
    primário de contato com o lead, no lugar do e-mail — taxa de resposta
    observada por e-mail frio é baixa. `canal` registra qual canal essa
    proposta usa ('whatsapp' ou 'email', `whatsapp` é o padrão a partir de
    agora); `mensagem` guarda o texto pronto (gerado por `clarice`,
    aprovado pelo gate de `lia`) que o operador envia clicando no botão
    "Enviar mensagem" do dashboard (abre `wa.me/<numero>?text=<mensagem>`
    — o operador clica enviar no próprio WhatsApp, sem automação/API
    envolvida, RNF de anti-banimento). `enviado_em` aqui é preenchido
    manualmente pelo dashboard quando o operador confirma que enviou (não
    dá pra detectar clique no link `wa.me`, diferente do rascunho do
    Gmail)."""
    _add_coluna_se_faltando(c, 'propostas', 'canal', "TEXT NOT NULL DEFAULT 'whatsapp'")
    _add_coluna_se_faltando(c, 'propostas', 'mensagem', 'TEXT')


def versao_atual(c):
    c.execute("CREATE TABLE IF NOT EXISTS schema_version (versao INTEGER NOT NULL)")
    row = c.execute("SELECT versao FROM schema_version").fetchone()
    if row is None:
        c.execute("INSERT INTO schema_version (versao) VALUES (0)")
        return 0
    return row[0]


def aplicar(c):
    """Aplica, em ordem, só as migrações com número maior que a versão atual.
    Idempotente: rodar de novo sobre um banco já atualizado não faz nada."""
    atual = versao_atual(c)
    for numero, fn in sorted(MIGRACOES, key=lambda par: par[0]):
        if numero > atual:
            fn(c)
            c.execute("UPDATE schema_version SET versao=?", (numero,))
            atual = numero
    c.commit()
    return atual
