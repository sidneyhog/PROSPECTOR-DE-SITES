#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Memória compartilhada via embeddings/RAG (docs/MEMORIA.md §9).

Sem dependências externas: só stdlib. Implementa o "MVP de menor custo"
descrito em MEMORIA.md §9.2 — similaridade lexical (vetor de frequência de
termos, bag-of-words) em vez de um modelo de embeddings dedicado (ex.
Voyage AI). O `modelo` fica registrado por linha para permitir trocar a
implementação depois sem migrar dados antigos (docs/MEMORIA.md §10,
versionamento de contexto): basta registrar novas linhas com
`modelo='voyage-...'` e o código de consulta já as trata igual.

Ver docs/PLANO_IMPLEMENTACAO.md §11 (Fase 8).

REGRA OBRIGATÓRIA (docs/MEMORIA.md §9.4): `texto_fonte` nunca contém
e-mail, telefone, WhatsApp, CPF/CNPJ ou nome completo do titular. Este
módulo aplica uma checagem de segurança (best-effort, por regex) e
RECUSA indexar texto que pareça conter esses dados — não é só política,
é reforçada em código.

LIMITAÇÃO CONHECIDA: sem stemming/lemmatização, a similaridade só conta
sobreposição literal de token (ex.: "nutricionista" e "nutrição" não
casam). Para o volume esperado (um operador solo, textos curtos e
específicos de nicho) isso já é útil o suficiente; se não for, é o
primeiro ponto a melhorar antes de trocar para um modelo de embeddings
real.
"""
import json
import math
import re
import sqlite3
from collections import Counter
from datetime import datetime

import migrations

MODELO_PADRAO = 'bow-tf-v1'  # bag-of-words, frequência de termo, cosseno

_RE_EMAIL = re.compile(r'[a-zA-Z0-9._%+\-]+@[a-zA-Z0-9.\-]+\.[a-zA-Z]{2,}')
_RE_CPF = re.compile(r'\d{3}\.?\d{3}\.?\d{3}-?\d{2}')
_RE_TELEFONE = re.compile(r'(?:\+?55\s?)?\(?\d{2}\)?\s?9?\d{4}-?\d{4}')

_STOPWORDS_PT = {
    'a', 'o', 'as', 'os', 'de', 'da', 'do', 'das', 'dos', 'e', 'em', 'para',
    'por', 'com', 'um', 'uma', 'uns', 'umas', 'no', 'na', 'nos', 'nas', 'que',
    'se', 'ao', 'aos', 'à', 'às', 'é', 'foi', 'ser', 'sua', 'seu', 'suas',
    'seus', 'mais', 'muito', 'ja', 'já',
}


def _agora():
    return datetime.now().strftime('%Y-%m-%d %H:%M:%S')


def contem_pii_provavel(texto):
    """Checagem best-effort de PII (e-mail, telefone, CPF) no texto. Não é
    exaustiva (não pega nome completo, por exemplo — isso continua sendo
    responsabilidade de quem chama `indexar`), mas pega os padrões mais
    comuns e objetivamente detectáveis por regex."""
    return bool(_RE_EMAIL.search(texto) or _RE_CPF.search(texto) or _RE_TELEFONE.search(texto))


def _tokenizar(texto):
    palavras = re.findall(r'[a-zA-ZÀ-ÿ0-9]+', texto.lower())
    return [p for p in palavras if p not in _STOPWORDS_PT and len(p) > 1]


def _vetor_tf(texto):
    """Vetor de frequência de termo normalizado (soma dos pesos = 1)."""
    tokens = _tokenizar(texto)
    if not tokens:
        return {}
    contagem = Counter(tokens)
    total = sum(contagem.values())
    return {termo: n / total for termo, n in contagem.items()}


def _cosseno(v1, v2):
    termos_comuns = set(v1) & set(v2)
    if not termos_comuns:
        return 0.0
    produto = sum(v1[t] * v2[t] for t in termos_comuns)
    norma1 = math.sqrt(sum(p * p for p in v1.values()))
    norma2 = math.sqrt(sum(p * p for p in v2.values()))
    if norma1 == 0 or norma2 == 0:
        return 0.0
    return produto / (norma1 * norma2)


def indexar(caminho_db, ref_tipo, ref_id, texto_fonte, nicho=None, modelo=MODELO_PADRAO):
    """Indexa `texto_fonte` para consulta por similaridade depois. RECUSA
    indexar se o texto parecer conter PII (docs/MEMORIA.md §9.4) — retorna
    {'ok': False, 'motivo': '...'} nesse caso, sem gravar nada.

    `ref_tipo`: 'proposta' | 'objecao_perda' | 'comparativo_competitivo' |
    'auditoria_resumo' (docs/MEMORIA.md §9.2). `ref_id`: slug do lead ou id
    da linha de origem."""
    if contem_pii_provavel(texto_fonte):
        return {'ok': False, 'motivo': 'texto_fonte parece conter e-mail/telefone/CPF - recusado (docs/MEMORIA.md §9.4)'}
    vetor = _vetor_tf(texto_fonte)
    c = sqlite3.connect(caminho_db)
    migrations.aplicar(c)
    c.execute(
        'INSERT INTO embeddings (ref_tipo, ref_id, nicho, texto_fonte, vetor_json, modelo, criado_em) '
        'VALUES (?,?,?,?,?,?,?)',
        (ref_tipo, ref_id, nicho, texto_fonte, json.dumps(vetor, ensure_ascii=False), modelo, _agora()),
    )
    c.commit()
    c.close()
    return {'ok': True}


def consultar(caminho_db, texto_consulta, ref_tipo=None, nicho=None, top_k=3):
    """Retorna os `top_k` textos mais similares a `texto_consulta`
    (filtrando por `ref_tipo`/`nicho` quando informados), cada um com
    `texto_fonte`, `ref_tipo`, `ref_id`, `similaridade` (0-1). Nunca
    retorna o registro bruto do lead de origem — só o texto já sanitizado
    indexado (docs/MEMORIA.md §9.3)."""
    c = sqlite3.connect(caminho_db)
    migrations.aplicar(c)
    c.row_factory = sqlite3.Row
    condicoes, valores = [], []
    if ref_tipo:
        condicoes.append('ref_tipo = ?')
        valores.append(ref_tipo)
    if nicho:
        condicoes.append('nicho = ?')
        valores.append(nicho)
    sql = 'SELECT ref_tipo, ref_id, texto_fonte, vetor_json FROM embeddings'
    if condicoes:
        sql += ' WHERE ' + ' AND '.join(condicoes)
    rows = c.execute(sql, valores).fetchall()
    c.close()

    vetor_consulta = _vetor_tf(texto_consulta)
    resultados = []
    for row in rows:
        vetor_armazenado = json.loads(row['vetor_json'])
        sim = _cosseno(vetor_consulta, vetor_armazenado)
        if sim > 0:
            resultados.append({
                'ref_tipo': row['ref_tipo'], 'ref_id': row['ref_id'],
                'texto_fonte': row['texto_fonte'], 'similaridade': round(sim, 4),
            })
    resultados.sort(key=lambda r: r['similaridade'], reverse=True)
    return resultados[:top_k]
