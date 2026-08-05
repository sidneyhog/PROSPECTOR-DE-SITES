# Changelog

Formato inspirado em [Keep a Changelog](https://keepachangelog.com/pt-BR/1.0.0/).
Datas no formato AAAA-MM-DD. Histórico consolidado a partir do `git log`
(não havia `CHANGELOG.md` antes da v3 — ver
`docs/ARQUITETURA_TECNICA.md` §11).

## [Não lançado] — v3 (plataforma multi-agente)

Evolução do plugin de chat monolítico para uma plataforma orquestrador +
26 agentes especialistas nativos ao Claude Code. Documentação completa em
`docs/` (PRD, arquitetura de agentes, arquitetura técnica, CRM, memória,
prompts, plano de implementação). Todas as mudanças de schema são
aditivas; nenhum comando ou skill da v2 foi removido.

### Adicionado
- Orquestrador + 25 agentes especialistas (`agents/`): prospecção,
  qualificação de leads, auditoria técnica, SEO, SEO local, performance,
  Core Web Vitals, acessibilidade, inteligência competitiva, Google
  Business Profile, UX/UI, branding, copywriting, CRO, front-end, QA,
  precificação/proposta comercial, deploy, CRM, follow-up, analytics,
  LGPD, geração de relatórios, governança de prompts, onboarding.
- `lib/`: `migrations.py` (runner idempotente), `db.py` (acesso único ao
  SQLite com máquina de estados validada), `auditlog.py` (log de
  execução), `ssh_deploy.py` (publicação em VPS), `embeddings.py`
  (memória compartilhada via RAG).
- `skills/deploy-vps/`: publicação em VPS própria via SSH/nginx/Let's
  Encrypt, substituindo o HostGator como caminho principal (mantido como
  fallback).
- Schema do banco: tabelas `interacoes`, `execucoes_agentes`,
  `auditorias`, `gbp_snapshots`, `estetica_historico`, `propostas`,
  `lgpd_checklist`, `followups`, `prompts_versionamento`, `embeddings`,
  `schema_version`; coluna `leads.https_validado_em`/`valor_setup`.
- Dashboard: painel "Conexão VPS" e abas Execuções, Auditoria, LGPD;
  Kanban/funil estendido para o vocabulário de 11 estados do pipeline v3
  (`docs/CRM.md` §2), convivendo com o vocabulário legado da v2.
- Gate de conformidade LGPD obrigatório antes de qualquer envio externo.
- Follow-up automatizado com limite de tentativas configurável.

### Corrigido
- Drift entre `commands/setup.md` (já referenciava uma skill "deploy-vps"
  desde antes desta evolução) e o código real (só existia
  `deploy-hostgator`) — resolvido com a implementação de `deploy-vps`.
- `SKILL.md` de `dashboard-leads` desatualizado (não listava todos os
  módulos `lib/` para cópia).
- Ordenação por timestamp de precisão de segundo em consultas de
  "mais recente por tipo" (`obter_auditorias`, `ultimo_gbp_snapshot`,
  `listar_estetica_recente`) — corrigido para ordenar por `id`.
- Edição manual do dashboard (drag-and-drop/formulário) não gravava
  trilha de auditoria (`interacoes`) — corrigido (ver Fase 9,
  `docs/PLANO_IMPLEMENTACAO.md`).

## [2.1.0] — 2026-07-14
- Numeração alinhada com a série de vídeos do produto; manual e READMEs
  atualizados.

## [0.14.0] — 2026-07-11
- Suporte a Mac (publicador via `.command`/launchd, dashboard, setup por
  sistema operacional).

## [2.0 / 0.13.5] — 2026-07-10
- Reescrita completa do plugin: skills `prospeccao-maps`,
  `redesign-premium`, `deploy-hostgator`, `proposta-email`,
  `dashboard-leads`, `contrato-servico`; dashboard local (SQLite + 9
  vistas); geração de contrato (HTML + DOCX travado); comando `/followup`.

## [0.4.2] — 2026-07-07
- Hotfix: corrige arquivos truncados nos comandos e skills; primeira
  versão minimamente completa do plugin.
