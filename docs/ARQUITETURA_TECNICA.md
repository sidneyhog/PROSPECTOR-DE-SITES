# ARQUITETURA_TECNICA.md — Arquitetura Técnica (Etapa 3 de 7)

**Depende de:** `docs/PRD.md` (Etapa 1, aprovado) e `docs/AGENTES.md`
(Etapa 2, aprovado). Este documento traduz o desenho de agentes em módulos,
dados, integrações e operação concretos — sempre dentro dos limites já
confirmados: **arquitetura nativa ao Claude Code, sem backend HTTP próprio,
sem banco externo, deploy em VPS própria**. Nenhum código foi alterado para
produzir este documento.

Status: **aprovado**.

**Nota de nomenclatura (Fase 9):** cada agente citado aqui pela função
técnica também tem um nome próprio humanizado (ex.: Orquestrador = Atlas,
CRM = Carmem) — glossário completo em `docs/AGENTES.md`.

---

## 1. Princípios que restringem toda decisão técnica abaixo

1. Tudo roda **local ao operador**, dentro do Claude Code/Cowork; não há
   servidor sempre-ligado próprio além do dashboard local opcional já
   existente (porta 8765).
2. Persistência é **SQLite + arquivos**, nunca um banco externo gerenciado.
3. "Filas" e "agendamento" usam os mecanismos **já nativos ao ambiente**
   (Routines/triggers do Claude Code), não um message broker externo.
4. Todo agente é um **subagent/skill do Claude Code** com contexto isolado;
   a "API" entre eles é o contrato JSON já definido em `AGENTES.md` §0.4,
   não uma API HTTP.
5. Migração de schema é sempre **aditiva** (RF-19) — nunca `DROP`/recriação
   destrutiva.
6. Deploy é **VPS própria via SSH/SCP**, servindo o conteúdo publicado por
   uma pilha Docker (Traefik + Portainer + imagem própria
   `prospector-sites`, `docs/PLANO_IMPLEMENTACAO.md` §14/Fase 10) que
   emite e renova HTTPS automaticamente; o caminho HostGator/cPanel/FTP da
   v2 foi descontinuado e removido (Fase 9).

## 2. Módulos (estrutura de arquivos proposta)

```
prospector-de-sites/
├── .claude-plugin/
│   └── plugin.json                  # manifesto do plugin (versão, nome)
├── agents/                          # NOVO — um .md por agente (Etapa 6: PROMPTS.md)
│   ├── orquestrador.md
│   ├── prospeccao.md
│   ├── qualificacao-leads.md
│   ├── auditoria-tecnica.md
│   ├── seo.md
│   ├── seo-local.md
│   ├── performance.md
│   ├── core-web-vitals.md
│   ├── acessibilidade.md
│   ├── inteligencia-competitiva.md
│   ├── google-business-profile.md
│   ├── ux-ui.md
│   ├── branding.md
│   ├── copywriting.md
│   ├── cro.md
│   ├── front-end.md
│   ├── qa.md
│   ├── precificacao-proposta.md
│   ├── deploy-vps.md
│   ├── crm.md
│   ├── follow-up.md
│   ├── analytics.md
│   ├── lgpd.md
│   ├── geracao-relatorios.md
│   ├── governanca-prompts.md
│   └── onboarding.md
├── commands/                        # pontos de entrada do operador (evoluem, não somem)
│   ├── setup.md                     # aciona agente Onboarding
│   ├── prospectar.md                # aciona Orquestrador (Prospecção → Qualificação)
│   ├── redesenhar.md                # aciona Orquestrador (Grupo B + Grupo C)
│   ├── editor.md
│   ├── publicar.md                  # aciona Orquestrador → Deploy
│   ├── proposta.md                  # aciona Orquestrador → Precificação + Copywriting + LGPD
│   ├── respostas.md                 # aciona Orquestrador → Follow-up/Analytics
│   ├── followup.md
│   └── contrato.md
├── skills/                          # procedimentos ricos em ferramenta, reusados por agentes
│   ├── prospeccao-maps/             # usado pelo agente Prospecção
│   ├── redesign-premium/            # usado por UX/UI, Branding, Front-end
│   ├── deploy-vps/                  # NOVO — substitui deploy-hostgator
│   ├── proposta-email/              # usado por Copywriting/Precificação
│   ├── dashboard-leads/             # usado pelo agente CRM (servidor + template)
│   └── contrato-servico/            # usado por Copywriting (parte textual) + CRM
├── lib/                             # NOVO — código compartilhado, stdlib-first
│   ├── db.py                        # acesso único ao SQLite (só o agente CRM chama)
│   ├── migrations.py                # runner de migração idempotente (ver §4.4)
│   ├── fila.py                      # fila local (ver §5)
│   ├── ssh_deploy.py                # publicação VPS via SSH/SCP (destino: volume do container prospector-sites)
│   └── auditlog.py                  # gravação do log de execuções (ver §10)
├── dashboard-server.py              # evoluído: novos endpoints (§8.3)
├── dashboard-template.html
├── manual.html
└── docs/                            # este PRD e demais documentos de etapa
```

**Nota de risco de implementação (a validar na Etapa 7):** o suporte do
mecanismo de plugins do Claude Code a uma pasta `agents/` própria (análoga a
`commands/`/`skills/`) precisa ser confirmado experimentalmente antes da
implementação; se não for suportado nativamente pelo empacotamento de
plugin, os agentes serão distribuídos como `skills/` com frontmatter de
agente, sem mudança de responsabilidades.

## 3. Serviços

Não há serviço HTTP externo. Os únicos processos de longa duração são:

| Serviço | Natureza | Substitui |
|---|---|---|
| `dashboard-server.py` | Servidor HTTP **localhost-only**, porta 8765, opcional (só roda quando o operador abre o dashboard) | Já existe na v2, evoluído com novos endpoints |
| Poller de fila local (`lib/fila.py`) | Processo/tarefa curta disparada por Routine do Claude Code, não um daemon 24/7 | Generaliza o poller de publicação (Task Scheduler/launchd) já usado no `deploy-hostgator` da v2 |
| Routines/triggers (Claude Code) | Agendamento nativo do ambiente (cron gerenciado pela plataforma) | Substitui o polling manual do `/respostas` e o agendador local do deploy |

## 4. Banco de dados

### 4.1 Tabela `leads` (evolução aditiva da v2)

Mantém todas as colunas atuais (`slug, nome, nicho, cidade, nota,
avaliacoes, email, telefone, whatsapp, siteAntigo, motivo, status, urlNova,
dataProposta, valor, obs, contratoStatus, contratoEm, manutencao, pago,
docCliente, endCliente, atualizado`). Novas colunas (via `ALTER TABLE ...
ADD COLUMN`, mesmo padrão já usado em `dashboard-server.py`):

```sql
ALTER TABLE leads ADD COLUMN lgpd_status TEXT DEFAULT 'pendente';   -- pendente|aprovado|bloqueado
ALTER TABLE leads ADD COLUMN valor_setup REAL;                      -- separa setup de manutenção
ALTER TABLE leads ADD COLUMN vps_host TEXT;                         -- alvo de deploy desta instalação/lead
ALTER TABLE leads ADD COLUMN vps_dominio TEXT;
ALTER TABLE leads ADD COLUMN https_validado_em TEXT;
```

O `status` passa a assumir os valores do pipeline do PRD §8.1: `encontrado,
qualificado, em_analise, site_auditado, pagina_gerada, pagina_revisada,
contato_realizado, negociacao, fechado, perdido, follow_up`.

### 4.2 Tabelas novas

```sql
-- Dossiês de diagnóstico (Grupo B), reaproveitáveis entre agentes (RF-06)
CREATE TABLE IF NOT EXISTS auditorias (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  lead_slug TEXT NOT NULL REFERENCES leads(slug),
  tipo TEXT NOT NULL,        -- tecnica|seo|seo_local|performance|cwv|acessibilidade|inteligencia_competitiva|gbp
  dados_json TEXT NOT NULL,  -- payload estruturado do agente (ver AGENTES.md §0.4)
  criado_em TEXT NOT NULL
);

-- Histórico de transições de estado (auditabilidade — RNF-04/RNF-10)
CREATE TABLE IF NOT EXISTS interacoes (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  lead_slug TEXT NOT NULL REFERENCES leads(slug),
  de_status TEXT,
  para_status TEXT NOT NULL,
  agente TEXT NOT NULL,
  motivo TEXT,
  criado_em TEXT NOT NULL
);

-- Log de toda execução de agente (observabilidade — RNF-10)
CREATE TABLE IF NOT EXISTS execucoes_agentes (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  lead_slug TEXT REFERENCES leads(slug),   -- NULL quando não associado a um lead específico
  agente TEXT NOT NULL,
  status TEXT NOT NULL,                    -- concluido|bloqueado|erro|precisa_input_humano
  resumo TEXT,
  criterios_pendentes TEXT,                -- JSON array
  referencias TEXT,                        -- JSON array (paths/URLs consultados)
  iniciado_em TEXT NOT NULL,
  concluido_em TEXT
);

-- Fila local de jobs (ver §5)
CREATE TABLE IF NOT EXISTS fila_jobs (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  tipo TEXT NOT NULL,        -- deploy|followup|gbp_monitor|respostas_email
  lead_slug TEXT REFERENCES leads(slug),
  payload_json TEXT,
  status TEXT NOT NULL DEFAULT 'pendente',  -- pendente|em_execucao|concluido|erro
  tentativas INTEGER NOT NULL DEFAULT 0,
  agendado_para TEXT,
  criado_em TEXT NOT NULL,
  atualizado_em TEXT
);

-- Propostas comerciais (separando preço de copy — agente Precificação vs Copywriting)
CREATE TABLE IF NOT EXISTS propostas (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  lead_slug TEXT NOT NULL REFERENCES leads(slug),
  valor_setup REAL,
  valor_manutencao REAL,
  justificativa TEXT,
  enviado_em TEXT,
  respondido_em TEXT
);

-- Tentativas de follow-up
CREATE TABLE IF NOT EXISTS followups (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  lead_slug TEXT NOT NULL REFERENCES leads(slug),
  tentativa_numero INTEGER NOT NULL,
  enviado_em TEXT NOT NULL,
  respondido INTEGER NOT NULL DEFAULT 0
);

-- Snapshots de Google Business Profile (comparação antes/depois — RF-08)
CREATE TABLE IF NOT EXISTS gbp_snapshots (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  lead_slug TEXT NOT NULL REFERENCES leads(slug),
  nota REAL,
  num_avaliacoes INTEGER,
  completude_percentual REAL,
  capturado_em TEXT NOT NULL
);

-- Histórico de estética usada (Branding não pode repetir paleta/tipografia — regra já vigente na v2)
CREATE TABLE IF NOT EXISTS estetica_historico (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  lead_slug TEXT NOT NULL REFERENCES leads(slug),
  paleta TEXT,
  tipografia TEXT,
  gerado_em TEXT NOT NULL
);

-- Checklist de conformidade LGPD por lead (gate de bloqueio — RF-16)
CREATE TABLE IF NOT EXISTS lgpd_checklist (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  lead_slug TEXT NOT NULL REFERENCES leads(slug),
  campo TEXT NOT NULL,       -- ex.: email, telefone, cpf
  finalidade TEXT,
  retencao TEXT,
  aprovado INTEGER NOT NULL DEFAULT 0,
  verificado_em TEXT NOT NULL
);

-- Versionamento de prompts (governança — §26 de AGENTES.md)
CREATE TABLE IF NOT EXISTS prompts_versionamento (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  agente TEXT NOT NULL,
  versao TEXT NOT NULL,
  hash TEXT NOT NULL,
  aprovado_em TEXT,
  observacoes TEXT
);

-- Versão de schema (para o migration runner — §4.4)
CREATE TABLE IF NOT EXISTS schema_version (
  versao INTEGER NOT NULL
);
```

### 4.3 Armazenamento de configuração

`prospector-config.json` é mantido como formato de arquivo (compatibilidade
com instalações existentes — RF-19), mas o campo de credencial de VPS
**deixa de aceitar senha em texto plano como única opção** (RNF-03):
passa a suportar (preferencialmente) uma chave SSH local, com senha como
fallback. É substituído por um bloco
`vps { host, porta, usuario, caminhoRemoto, dominio, pastaBase,
chaveSshPath, senha }`.

**Atualização (Fase 9, conclusão):** o campo legado `hostgator` foi
removido do código (`dashboard-server.py` não lê nem grava mais esse
bloco) — `bloco vps{}` é agora o único formato reconhecido para deploy.
Instalações antigas que ainda tenham um bloco `hostgator{}` no próprio
`prospector-config.json` local não quebram (o arquivo JSON pode ter campos
extras não lidos), mas precisam preencher `vps{}` via `/setup` para
publicar.

### 4.4 Migração de schema

Hoje `dashboard-server.py` faz `ALTER TABLE` com `try/except` ad hoc a cada
subida do servidor. Isso é substituído por um **migration runner idempotente**
(`lib/migrations.py`): lê `schema_version`, aplica em ordem só as migrações
ainda não aplicadas, grava a nova versão. Continua sendo SQLite puro
(stdlib `sqlite3`), sem framework de ORM/migração externo — só disciplina
sobre o padrão que já existia.

## 5. Filas

Não há message broker. "Fila" é a tabela `fila_jobs` (§4.2) mais dois
mecanismos de disparo:

1. **Disparo imediato**: o Orquestrador insere um job e o processa na mesma
   execução quando possível (ex.: Deploy logo após aprovação do QA).
2. **Disparo agendado**: para jobs que dependem de tempo (Follow-up após N
   dias, monitoramento periódico de GBP), o Orquestrador usa uma
   **Routine/trigger do Claude Code** (mecanismo já disponível no ambiente)
   que, ao disparar, retoma a sessão/agente e processa os itens
   `pendente`/`agendado_para <= agora` da fila.

Isso substitui diretamente o mecanismo frágil da v2 (Task Scheduler/launchd
+ arquivo `fila-publicacao.txt` de texto simples) por uma fila com estado
consistente (SQLite) e reentrância (campo `tentativas`), mantendo a mesma
ideia (fila local, sem infraestrutura externa).

## 6. Cache

- **Dossiê de auditoria** (`auditorias`): funciona como cache — um agente
  do Grupo B não reprocessa o site do zero se já existe um dossiê recente
  (janela configurável, ex.: 30 dias) para o mesmo `lead_slug`.
- **Histórico de estética** (`estetica_historico`): cache de "o que já foi
  usado", consultado por Branding para garantir variedade (já é a lógica da
  v2 com `ui-ux-pro-max`, agora com estado persistido em vez de heurística
  apenas na sessão).
- **Prompt caching nativo do modelo**: quando o Orquestrador aciona um
  agente repetidamente com o mesmo prompt de sistema, o cache de prompt do
  próprio Claude reduz custo — não requer implementação própria, só
  organização do prompt (system prompt estável + operacional variável),
  tratado em detalhe na Etapa 6 (`PROMPTS.md`).

## 7. Memória

Detalhamento completo é objeto da Etapa 5 (`MEMORIA.md`); aqui fica o
mapeamento técnico de onde cada tipo de memória vive:

| Tipo de memória (PRD/Etapa 5) | Onde vive tecnicamente |
|---|---|
| Temporária (durante uma execução) | Contexto do subagent, descartado ao final |
| Por execução (log) | `execucoes_agentes` |
| Do lead | `leads` + `auditorias` + `interacoes` + `followups` + `gbp_snapshots` + `estetica_historico` + `lgpd_checklist` |
| Compartilhada (entre leads) | Consultas agregadas sobre as mesmas tabelas (ex.: preços já praticados, estéticas recentes, concorrentes já mapeados por nicho/cidade) |
| Do projeto | `docs/*.md`, `agents/*.md`, `prompts_versionamento` |
| Histórico | `interacoes` (transições) + logs append-only (§10) |
| Embeddings/RAG | Tabela adicional a especificar na Etapa 5 (ex.: `embeddings(lead_slug, tipo, vetor_json)`), consultada por similaridade simples (cosseno em Python puro, sem serviço de vetor externo) |
| Versionamento de contexto | `prompts_versionamento` + `schema_version` |

## 8. Armazenamento, integrações e APIs

### 8.1 Armazenamento de arquivos

```
<pasta-conectada-do-operador>/
├── prospector.db
├── prospector-config.json
├── leads/
│   └── <slug>/
│       ├── auditoria.json          # espelho legível do dossiê (auditorias)
│       ├── pagina.html             # saída do Front-end
│       ├── pagina-editor.html
│       ├── comparar.html
│       ├── proposta.html
│       └── contrato.docx
└── logs/
    └── AAAA-MM-DD.jsonl            # log append-only diário (§10)
```

Google Sheets/Drive continuam sendo o destino de exportação de leads
(conector Drive, sem mudança de responsabilidade).

### 8.2 Integrações externas

| Integração | Uso | Agente(s) |
|---|---|---|
| Claude in Chrome (navegador) | Google Maps, inspeção de sites concorrentes, Google Business Profile | Prospecção, Qualificação, Auditoria Técnica, SEO/SEO Local/Performance/CWV/Acessibilidade, Inteligência Competitiva, GBP, Branding (extração de ativos) |
| Conector Gmail (MCP) | Envio de proposta/follow-up, detecção de resposta | Copywriting, Follow-up, Analytics |
| Conector Google Drive (MCP) | Exportação de planilha de leads | Prospecção, CRM |
| SSH (VPS do operador/cliente) | Publicação (SCP para o volume do container `prospector-sites`); Traefik cuida do certificado Let's Encrypt automaticamente | Deploy |
| `ui-ux-pro-max-cli` (npx, third-party) | Geração de variedade de paleta/tipografia | Branding |
| `python-docx` (pip) | Geração de contrato bloqueado | Copywriting (conteúdo) / CRM (persistência do estado do contrato) |

**Nenhuma API oficial do Google Maps/Business Profile é usada** (decisão
mantida da v2, já sinalizada como risco no PRD §17 — dependência de
navegador em vez de API paga/autenticada).

**Nome exato da ferramenta no `tools:` frontmatter do agente:**
`mcp__claude-in-chrome` (MCP server reservado, exposto quando a extensão
Claude in Chrome está conectada — `mcp__<server>` concede acesso a todas
as ferramentas daquele servidor; ver referência de sub-agents do Claude
Code). **Bug real encontrado em produção (05/08/2026):** os 11 agentes
listados acima na linha "Claude in Chrome" foram implementados com
`tools: Bash, Read` (ou só `Read`), sem essa entrada — o procedimento
escrito no `.md` do agente exigia navegador, mas o `tools:` não concedia.
Corrigido em todos os 11 (`iris`, `justo`, `vitor`, `gael`, `nando`,
`ravi`, `vitalina`, `clara`, `sofia`, `gabi`, `bruna`). Ao criar ou editar
qualquer agente que dependa de navegador, **confira que `tools:` inclui
`mcp__claude-in-chrome`** — essa tabela é a fonte de verdade de quem
precisa.

### 8.3 "APIs" internas do sistema

Como não há backend HTTP próprio além do dashboard local, a "API" real do
sistema é o **contrato de invocação de agente** já definido em
`AGENTES.md` §0.4 (JSON de entrada/saída), mais duas superfícies concretas:

**(a) Módulo `lib/db.py`** — único ponto de acesso ao SQLite, chamado
apenas pelo agente CRM (nunca diretamente por outro agente):

```python
def obter_lead(slug: str) -> dict: ...
def atualizar_estado(slug: str, novo_estado: str, dados: dict, agente: str, motivo: str | None) -> dict: ...
def registrar_execucao(agente: str, lead_slug: str | None, status: str, resumo: str, referencias: list) -> None: ...
def registrar_auditoria(lead_slug: str, tipo: str, dados: dict) -> None: ...
```

**(b) `dashboard-server.py` (REST local, porta 8765, já existente)** —
evoluído com novos endpoints somando-se aos já existentes
(`/api/leads`, `/api/config`):

| Endpoint novo | Método | Uso |
|---|---|---|
| `/api/execucoes` | GET | Lista `execucoes_agentes` (observabilidade — nova aba no dashboard) |
| `/api/auditorias/<slug>` | GET | Dossiê consolidado de um lead |
| `/api/fila` | GET | Estado da fila de jobs |
| `/api/lgpd/<slug>` | GET | Checklist de conformidade do lead |

## 9. Modelos de IA (defaults por agente — calibráveis na Etapa 7)

| Agente | Modelo default | Racional |
|---|---|---|
| Orquestrador | Sonnet | Decisão dinâmica exige raciocínio, mas não a criatividade de Opus |
| Onboarding | Haiku | Coleta estruturada de dados |
| Prospecção | Sonnet | Navegação e julgamento visual do Maps |
| Qualificação de Leads | Haiku | Checklist objetivo |
| Auditoria Técnica | Sonnet | Estruturação de dossiê técnico |
| SEO / SEO Local / Performance / CWV / Acessibilidade | Haiku (default), Sonnet (opcional) | Análise sobre dossiê já coletado; Haiku reduz custo, Sonnet disponível se qualidade exigir |
| Inteligência Competitiva | Sonnet | Comparação qualitativa |
| Google Business Profile | Haiku | Captura de dados estruturados |
| UX/UI | Sonnet | Decisões estruturais |
| Branding | Sonnet | Uso de ferramenta + julgamento visual |
| Copywriting | Sonnet (Opus opcional para contas/propostas de maior ticket) | Qualidade de texto é crítica para conversão |
| CRO | Sonnet | Julgamento de conversão |
| Front-end | Sonnet | Geração de código HTML/CSS/JS |
| QA | Sonnet | Precisa pegar regressões sutis |
| Precificação/Proposta Comercial | Haiku | Cálculo + regras |
| Deploy | Sonnet | Troubleshooting de SSH/Docker/Traefik exige raciocínio |
| CRM | Haiku | Validação/persistência determinística |
| Follow-up | Haiku | Regras de agendamento |
| Analytics | Haiku | Consolidação de eventos |
| LGPD | Sonnet | Julgamento de conformidade é sensível/alto risco |
| Geração de Relatórios | Sonnet | Consolidação apresentável |
| Governança de Prompts | Sonnet | Revisão de consistência entre 25 prompts |

Esses defaults ficam registrados em configuração (não hard-coded), para que
o operador possa recalibrar por custo/qualidade — detalhamento de como isso
se aplica a cada prompt é da Etapa 6.

## 10. Observabilidade e logs

- **`execucoes_agentes`** (SQLite) é a fonte primária de observabilidade:
  todo acionamento de agente grava uma linha (RNF-10).
- **Log append-only diário** (`logs/AAAA-MM-DD.jsonl`): espelho em arquivo
  simples do que foi gravado em `execucoes_agentes`, para durabilidade e
  inspeção manual mesmo sem abrir o dashboard.
- **Retenção**: logs em arquivo mantidos por um período configurável (ex.:
  90 dias) e depois compactados/removidos; `execucoes_agentes` mantido
  indefinidamente (é volume baixo — texto estruturado por execução).
- **Dashboard**: nova aba "Execuções" (via `/api/execucoes`) permite ao
  operador ver, por lead, quais agentes rodaram, em que ordem e com qual
  resultado — atende RF-20/RNF-10 sem exigir ferramenta de observability
  externa (Datadog/Sentry etc., fora de escopo desta v3).

## 11. Versionamento

- **Do plugin**: mantém o padrão semver já usado (`v2.1.0` etc.), registrado
  em `.claude-plugin/plugin.json` e `marketplace.json`.
- **Do schema de dados**: tabela `schema_version` + `lib/migrations.py`
  (§4.4), substituindo o `try/except ALTER TABLE` ad hoc atual por um
  runner determinístico e idempotente.
- **Dos prompts de agente**: tabela `prompts_versionamento` + agente de
  Governança de Prompts (`AGENTES.md` §26) — toda mudança de prompt gera uma
  nova versão revisada antes de entrar em uso.
- **Do código/commits**: Git no repositório do plugin, mantendo o hábito já
  existente de mensagens de commit descritivas; recomenda-se (não
  obrigatório nesta etapa) adotar `CHANGELOG.md` explícito a partir da v3,
  já que o histórico de versões hoje só é rastreável via `git log`.

---

## Próximos passos

Mediante aprovação deste documento, a Etapa 4 (`CRM.md`) detalha a
modelagem completa do ciclo comercial (estados, transições válidas, campos
por estado, relacionamentos) com base no schema já introduzido aqui em
§4.
