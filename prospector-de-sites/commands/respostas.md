---
description: Verifica no Gmail se os clientes responderam as propostas, atualiza o CRM e reporta o panorama do funil
argument-hint: "[nome do cliente] — opcional, padrão verifica todos em contato_realizado/follow_up"
---

Acione o Orquestrador (`agents/atlas.md`) para processar este
comando, seguindo a seção "Follow-up e Analytics" de
`agents/atlas.md`.

## Passos

1. Acionar `fabi` (`agents/fabi.md`) só para o passo "Verificar
   respostas" (sem enviar novo follow-up): para cada lead
   `contato_realizado`/`follow_up` (ou o de `$ARGUMENTS`), buscar no Gmail
   e classificar resposta/sem resposta.
2. Para quem respondeu: `carmem` persiste a transição para `negociacao`.
3. Acionar `ana` (`agents/ana.md`) para reportar o panorama
   geral do funil (taxa de resposta, tempo médio, etc.).

## Automação (sugerir na primeira execução)

Ofereça deixar isso automático via Routine agendada do ambiente Claude
Code (ver a seção "Automação" de `agents/fabi.md`) — se aceitar,
crie a Routine para rodar este fluxo diariamente. Se recusar, ou a
ferramenta não estiver disponível, siga com a execução manual.

## Regras

- NUNCA marque `fechado` sozinho — fechamento envolve contrato assinado
  (Fase 8+); apenas o operador confirma.
- Não responda e-mails automaticamente: leitura e classificação apenas.
  Se o operador quiser, ofereça rascunho de resposta.

## Saída

Resuma: quem respondeu (com a essência de cada resposta), quem segue sem
resposta e há quantos dias, e o panorama do funil (`ana`). Sugira
`/followup` para quem está elegível a um novo follow-up.
