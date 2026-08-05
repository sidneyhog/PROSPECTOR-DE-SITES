# MEMORIA.md — Sistema de Memória (Etapa 5 de 7)

**Depende de:** `docs/PRD.md` (Etapa 1), `docs/AGENTES.md` (Etapa 2),
`docs/ARQUITETURA_TECNICA.md` (Etapa 3) e `docs/CRM.md` (Etapa 4) — todos
aprovados. Este documento detalha os oito tipos de memória exigidos,
aprofundando o mapeamento já esboçado em `ARQUITETURA_TECNICA.md` §7, com
ciclo de vida, regras de acesso, o desenho concreto de embeddings/RAG e a
política de retenção alinhada a LGPD. Nenhum código foi alterado para
produzir este documento.

Status: **aprovado**.

**Nota de nomenclatura (Fase 9):** cada agente citado aqui pela função
técnica também tem um nome próprio humanizado (ex.: Prospecção = Íris,
Inteligência Competitiva = Sofia) — glossário completo em
`docs/AGENTES.md`.

---

## 1. Princípio geral

Memória existe para dois objetivos, nunca um terceiro: **(a)** evitar que
um agente repita trabalho já feito (contexto mínimo, RNF-01) e **(b)**
permitir que a plataforma aprenda entre leads (ex.: quais propostas
convertem melhor, quais estéticas já foram usadas). Memória **não** é um
histórico de conversa — nenhum agente acumula "lembranças" de sessões
anteriores fora das estruturas explícitas descritas aqui. Isso é reforço
direto do requisito de LGPD/minimização (RNF-02): o que não está em uma das
oito categorias abaixo, não persiste.

## 2. Taxonomia (visão geral)

| # | Tipo | Pergunta que responde | Onde vive |
|---|---|---|---|
| 1 | Temporária | "O que o agente precisou saber só durante esta execução?" | Contexto do subagent (efêmero) |
| 2 | Por execução | "O que um agente específico fez, quando, com que resultado?" | `execucoes_agentes` |
| 3 | Do lead | "Tudo sobre este lead específico" | `leads` + tabelas satélite (`CRM.md` §5) |
| 4 | Compartilhada | "O que aprendemos entre leads?" | Consultas agregadas + `embeddings` |
| 5 | Do projeto | "Como o sistema é especificado e deve se comportar?" | `docs/*.md`, `agents/*.md`, `prompts_versionamento` |
| 6 | Histórico | "Como o lead chegou até aqui?" | `interacoes` + logs append-only |
| 7 | Embeddings/RAG | "Que casos passados são parecidos com este?" | Tabela `embeddings` (§6) |
| 8 | Versionamento de contexto | "Este registro antigo ainda é interpretável pela versão atual do sistema?" | `schema_version` + campos de versão por registro (§7) |

## 3. Memória temporária (execução)

**O que é.** O raciocínio, rascunhos e ferramentas intermediárias que um
agente usa durante uma única invocação (ex.: o agente Front-end gerando e
descartando três variações de layout antes de decidir a final).

**Ciclo de vida.** Nasce quando o Orquestrador aciona o agente; morre
integralmente quando o agente devolve o payload de saída padrão
(`AGENTES.md` §0.4). Nada disso é persistido — é exatamente o mecanismo de
isolamento de contexto por subagent que já sustenta o objetivo de reduzir
consumo de tokens (PRD §2/§7).

**Regra de acesso.** Não acessível a nenhum outro agente nem ao operador —
por definição, não existe mais após a execução.

## 4. Memória por execução (log)

**O que é.** O registro de que um agente rodou: quando, com qual lead
(ou nenhum), com qual resultado. Já especificada como tabela
`execucoes_agentes` em `ARQUITETURA_TECNICA.md` §4.2/§10.

**Ciclo de vida.** Escrita uma vez ao final de cada execução de agente;
nunca alterada depois (é log, não estado mutável). Espelhada em arquivo
append-only diário (`logs/AAAA-MM-DD.jsonl`) para durabilidade.

**Regra de acesso.** Escrita exclusiva do próprio mecanismo de execução
(via `lib/auditlog.py`, chamado pelo Orquestrador após cada retorno de
agente — não pelo agente CRM, para não acoplar observabilidade a regras de
negócio do CRM). Leitura por qualquer agente/operador que precise auditar
(dashboard, aba "Execuções" de `CRM.md` §8).

## 5. Memória do lead

**O que é.** Tudo o que é específico de um lead: os campos de `leads`, os
dossiês (`auditorias`), a linha do tempo (`interacoes`), propostas
(`propostas`), tentativas de follow-up (`followups`), snapshots de GBP
(`gbp_snapshots`), estética usada (`estetica_historico`) e checklist de
LGPD (`lgpd_checklist`) — todas já schematizadas em
`ARQUITETURA_TECNICA.md` §4.2 e relacionadas em `CRM.md` §5.

**Ciclo de vida.** Nasce quando o lead é `encontrado`; é atualizada ao
longo de todo o pipeline; não é apagada quando o lead vira `perdido`
(mantém-se para análise de padrões de perda — catálogo de motivos,
`CRM.md` §6) nem quando vira `fechado` (vira histórico de cliente).

**Regra de acesso.** Escrita exclusiva do agente CRM (`CRM.md` §7, regra
1). Leitura por qualquer agente que precise de contexto do lead — mas
**só os campos que o Orquestrador decidir repassar** (RNF-01): por exemplo,
o agente Copywriting recebe o dossiê e o comparativo competitivo, não o
histórico de tentativas de follow-up de outro lead.

## 6. Memória compartilhada

**O que é.** Conhecimento que atravessa leads: preços já praticados por
nicho (para calibrar Precificação — `AGENTES.md` §19), estéticas recentes
(para Branding não repetir — `estetica_historico`), concorrentes já
mapeados por nicho/cidade (para Inteligência Competitiva não reprospectar
do zero — `AGENTES.md` §11), e os casos recuperáveis por similaridade via
RAG (§7 abaixo).

**Ciclo de vida.** É construída incrementalmente a cada lead processado;
nunca pertence a um único lead — é a agregação de vários.

**Regra de acesso.** Somente leitura por agentes especialistas (consultas
agregadas sobre as tabelas de memória do lead, ou consulta ao índice de
embeddings); a escrita de origem continua sendo, sempre, uma escrita de
memória do lead individual feita pelo CRM — a "memória compartilhada" é uma
*visão*, não uma tabela própria com escrita direta (exceto `embeddings`,
que tem pipeline de indexação próprio, §7).

## 7. Memória do projeto

**O que é.** A especificação viva do próprio sistema: os documentos desta
série (`docs/PRD.md`, `AGENTES.md`, `ARQUITETURA_TECNICA.md`, `CRM.md`,
este `MEMORIA.md`, e os que vêm a seguir), as definições de agente
(`agents/*.md`) e o registro de versões de prompt (`prompts_versionamento`,
`ARQUITETURA_TECNICA.md` §11).

**Ciclo de vida.** Muda por decisão humana (aprovação de uma nova etapa do
PRD, aprovação de um novo prompt pelo agente de Governança — `AGENTES.md`
§26) — nunca é modificada autonomamente por um agente especialista durante
o processamento de um lead.

**Regra de acesso.** Leitura por todos os agentes (é o que define seu
próprio comportamento); escrita apenas via processo de governança
(Etapa 6/7), nunca em runtime de processamento de lead.

## 8. Histórico

**O que é.** A trilha de auditoria de como cada lead evoluiu:
`interacoes` (transições de estado, já detalhada em `CRM.md` §2.3) mais os
logs append-only (§4). É a base direta de RNF-04 e RNF-10.

**Ciclo de vida.** Só cresce (append-only); nunca é reescrito.

**Regra de acesso.** Escrita exclusiva no momento da transição (CRM,
`interacoes`) e no momento da execução (log de agente, §4). Leitura livre
para auditoria.

## 9. Embeddings / RAG

### 9.1 Objetivo

Permitir que um agente pergunte "já vi algo parecido com isto?" sem
precisar reprocessar leads antigos inteiros — ex.: Copywriting recuperando
propostas anteriores que converteram bem para o mesmo nicho; Inteligência
Competitiva recuperando comparativos já feitos na mesma cidade; Follow-up
identificando objeções recorrentes.

### 9.2 Desenho (proporcional à escala real: um operador, centenas a poucos
milhares de leads — não justifica um banco vetorial dedicado)

```sql
CREATE TABLE IF NOT EXISTS embeddings (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  ref_tipo TEXT NOT NULL,     -- 'proposta' | 'objecao_perda' | 'comparativo_competitivo' | 'auditoria_resumo'
  ref_id TEXT NOT NULL,       -- slug do lead ou id da linha de origem (propostas.id, etc.)
  nicho TEXT,                 -- filtro rápido antes de calcular similaridade
  texto_fonte TEXT NOT NULL,  -- texto resumido e SANITIZADO (sem PII — ver §9.4)
  vetor_json TEXT NOT NULL,   -- embedding serializado (array de floats)
  modelo TEXT NOT NULL,       -- identifica o modelo/versão de embeddings usado
  criado_em TEXT NOT NULL
);
```

- **Indexação**: quando um agente produz um artefato elegível (proposta
  enviada, motivo de perda registrado, comparativo competitivo concluído),
  o Orquestrador chama uma rotina de indexação (`lib/embeddings.py`, a
  detalhar na implementação) que gera o vetor e grava a linha.
- **Consulta**: um agente que precisa de "casos parecidos" pede ao
  Orquestrador; o Orquestrador computa o embedding da consulta, filtra por
  `ref_tipo`/`nicho` quando aplicável, e calcula similaridade de cosseno
  em memória (Python puro, sem índice ANN — o volume não justifica) contra
  os vetores já armazenados, retornando os top-K `texto_fonte` (nunca o
  registro bruto do lead de origem, para não vazar contexto irrelevante).
- **Modelo de embeddings**: recomenda-se um modelo de embeddings dedicado
  (ex.: Voyage AI, parceiro recomendado pela Anthropic para RAG) chamado
  sob demanda — não é infraestrutura própria a manter, é uma chamada de API
  pontual, equivalente em natureza às já feitas hoje aos conectores
  Gmail/Drive. Alternativa de menor custo/complexidade para o MVP (a
  decidir na Etapa 7): similaridade lexical simples (ex.: TF-IDF em
  stdlib) enquanto o volume de dados por instalação for pequeno.

### 9.3 Casos de uso por agente

| Agente | Consulta por similaridade em... |
|---|---|
| Copywriting | Propostas anteriores (`ref_tipo='proposta'`) do mesmo nicho que resultaram em `fechado` |
| Precificação/Proposta Comercial | Propostas anteriores com valor e resultado (fechado/perdido por preço) |
| Follow-up | Motivos de perda (`ref_tipo='objecao_perda'`) recorrentes no nicho, para adaptar tom |
| Inteligência Competitiva | Comparativos competitivos (`ref_tipo='comparativo_competitivo'`) já feitos na mesma cidade |

### 9.4 Regra de sanitização (obrigatória, ligada a LGPD)

`texto_fonte` **nunca** contém e-mail, telefone, WhatsApp, CPF/CNPJ ou nome
completo do titular — apenas o conteúdo generalizável (texto da proposta,
motivo da perda, achados competitivos). Quem grava uma linha em
`embeddings` é responsável por sanitizar antes (o agente de LGPD pode ser
consultado para validar o padrão de sanitização na Etapa 6/7, mas a
responsabilidade operacional de não vazar PII é de quem indexa).

## 10. Versionamento de contexto

**O que é.** A garantia de que um registro de memória gravado numa versão
anterior do sistema continua interpretável (ou é migrado de forma
explícita) quando o schema evolui.

**Mecanismo.**
- `schema_version` (já introduzida em `ARQUITETURA_TECNICA.md` §4.2/§4.4)
  controla a versão física das tabelas.
- `prompts_versionamento` controla qual versão de prompt gerou um dado
  registro de `execucoes_agentes` — permite, ao investigar um resultado
  antigo, saber exatamente qual prompt estava em vigor (adiciona-se, na
  implementação, uma referência opcional `prompt_versao` em
  `execucoes_agentes`).
- Migrações de memória seguem a mesma regra de `RF-19`: sempre aditivas.
  Se um novo tipo de memória compartilhada for introduzido (ex.: um novo
  `ref_tipo` em `embeddings`), registros antigos continuam válidos sem
  necessidade de reprocessamento retroativo.

## 11. Ciclo de vida e regras de acesso — resumo consolidado

| Tipo | Quem escreve | Quem lê | Mutável depois de escrito? |
|---|---|---|---|
| Temporária | O próprio agente (efêmero) | Ninguém (não persiste) | N/A |
| Por execução | Orquestrador (`lib/auditlog.py`) | Qualquer agente/operador | Não (log) |
| Do lead | Agente CRM | Agentes autorizados pelo Orquestrador (contexto mínimo) | Sim (estado evolui) |
| Compartilhada | Derivada (leitura agregada) + `embeddings` (pipeline próprio) | Agentes especialistas | Vetores: não; agregações: sempre recalculadas |
| Do projeto | Processo de governança humana | Todos os agentes | Sim, via aprovação explícita |
| Histórico | CRM (`interacoes`) + log de execução | Qualquer agente/operador | Não (append-only) |
| Embeddings/RAG | Pipeline de indexação (`lib/embeddings.py`) | Agentes especialistas (consulta por similaridade) | Não (nova versão = nova linha) |
| Versionamento de contexto | Processo de migração/governança | Todo o sistema (implícito) | Só avança, nunca retrocede silenciosamente |

## 12. Riscos específicos de memória

| Risco | Mitigação |
|---|---|
| Vazamento de PII em `embeddings.texto_fonte` | Regra de sanitização obrigatória (§9.4); nenhum campo de contato bruto é elegível para indexação |
| Contaminação entre leads (um agente usar contexto de outro lead por engano) | Contrato de contexto mínimo do Orquestrador (RNF-01) + `embeddings` retorna apenas texto resumido, nunca o registro completo do lead de origem |
| Viés por poucos exemplos (RAG sugerindo padrão de 1-2 casos como se fosse regra geral) | Consulta por similaridade sempre reporta quantos casos similares foram encontrados; agente consumidor trata isso como sinal fraco, não determinístico |
| Memória do projeto desalinhada com o comportamento real dos agentes (docs desatualizados) | Papel do agente de Governança de Prompts (`AGENTES.md` §26) inclui checar essa consistência antes de aprovar mudanças |
| Crescimento não controlado de logs/embeddings ao longo do tempo | Política de retenção (logs em arquivo expiram, `execucoes_agentes` mantido mas de baixo volume por natureza) |

---

## Próximos passos

Mediante aprovação deste documento, a Etapa 6 (`PROMPTS.md`) especifica,
para cada um dos 26 agentes, o prompt de sistema, o prompt operacional, as
ferramentas autorizadas, as restrições e os critérios de qualidade, revisão
e aprovação — consumindo diretamente a taxonomia de memória definida aqui
para decidir o que cada prompt pode e deve acessar.
