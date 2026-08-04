# agents/

Pasta reservada para as definições dos agentes especialistas (Orquestrador +
25 agentes) especificadas em `docs/AGENTES.md` e `docs/PROMPTS.md`.

Fica vazia (só este README) até a Fase 1 do plano de implementação
(`docs/PLANO_IMPLEMENTACAO.md` §4), quando os primeiros três agentes
(Orquestrador, CRM, Onboarding) são adicionados aqui.

**Nota em aberto (`ARQUITETURA_TECNICA.md` §2):** o suporte do mecanismo de
plugins do Claude Code a uma pasta `agents/` própria (análoga a
`commands/`/`skills/`) precisa ser confirmado experimentalmente na Fase 1;
se não for suportado nativamente, os agentes serão distribuídos como
`skills/` com frontmatter de agente, sem mudança de responsabilidades.
