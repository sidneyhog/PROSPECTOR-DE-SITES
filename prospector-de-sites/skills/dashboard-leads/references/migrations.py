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
