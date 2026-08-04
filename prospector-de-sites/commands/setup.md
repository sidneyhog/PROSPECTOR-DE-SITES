---
description: Configura o plugin — assinatura, preferências e conexão com a VPS própria (roda uma vez)
---

Acione o Orquestrador (`agents/orquestrador.md`) para processar este
comando.

O Orquestrador deve delegar integralmente ao agente `onboarding`
(`agents/onboarding.md`), que executa o procedimento completo de
configuração (pasta de trabalho, dados do operador, conexão com a VPS,
dashboard inicial, manual e o gerador de variedade estética).

Depois que o agente `onboarding` retornar (formato padrão,
`docs/AGENTES.md` §0.4), o Orquestrador registra a execução via
`lib/auditlog.py` (`docs/ARQUITETURA_TECNICA.md` §10) e reporta ao
operador um resumo do que foi configurado — ou, se o agente retornar
`bloqueado`/`precisa_input_humano`, reporta o motivo específico em vez de
prosseguir.
