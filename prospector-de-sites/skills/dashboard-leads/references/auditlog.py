#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Log de execução de agentes: grava em `execucoes_agentes` (SQLite, via
lib/db.py) e espelha em arquivo append-only diário (docs/ARQUITETURA_TECNICA.md
§10). Chamado pelo Orquestrador logo após cada retorno de agente — nunca
pelo próprio agente, nunca pelo agente CRM (observabilidade é
responsabilidade do Orquestrador, não regra de negócio do CRM).

Sem dependências externas: só stdlib. Ver docs/PLANO_IMPLEMENTACAO.md §4
(Fase 1).

NOTA DE MANUTENÇÃO: cópia idêntica em
skills/dashboard-leads/references/auditlog.py. Mantenha as duas em sincronia.
"""
import json
import os
from datetime import datetime

import db


def registrar(caminho_db, pasta_logs, agente, lead_slug, status, resumo,
              criterios_pendentes=None, referencias=None, iniciado_em=None):
    """Grava a execução no banco (execucoes_agentes) e no log diário (JSONL)."""
    db.registrar_execucao(
        caminho_db, agente, lead_slug, status, resumo,
        criterios_pendentes=criterios_pendentes, referencias=referencias, iniciado_em=iniciado_em,
    )
    _append_jsonl(pasta_logs, {
        'agente': agente,
        'lead_slug': lead_slug,
        'status': status,
        'resumo': resumo,
        'criterios_pendentes': criterios_pendentes or [],
        'referencias': referencias or [],
        'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
    })


def _append_jsonl(pasta_logs, evento):
    os.makedirs(pasta_logs, exist_ok=True)
    nome_arquivo = datetime.now().strftime('%Y-%m-%d') + '.jsonl'
    caminho = os.path.join(pasta_logs, nome_arquivo)
    with open(caminho, 'a', encoding='utf-8') as f:
        f.write(json.dumps(evento, ensure_ascii=False) + '\n')
