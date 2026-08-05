---
description: Verifica respostas e envia o próximo follow-up (dentro do limite configurado) para propostas paradas
argument-hint: "[nome do cliente] — opcional, padrão: todos os elegíveis"
---

Acione o Orquestrador (`agents/orquestrador.md`) para processar este
comando, seguindo a seção "Follow-up e Analytics" de
`agents/orquestrador.md`.

## Passos

1. Acionar `follow-up` (`agents/follow-up.md`) por completo: verificar
   respostas primeiro (quem respondeu sai da lista de elegíveis e vai
   para `negociacao`), depois `db.listar_leads_para_followup` para achar
   quem está parado há `diasSemResposta` (config, padrão 3) e ainda não
   atingiu `limiteTentativas` (config, padrão 1 — mesmo comportamento da
   v2 de não repetir indefinidamente).
2. Para cada elegível: `follow-up` escreve o texto (máximo 4 linhas, tom
   gentil, sem preço, checklist anti-spam da skill `proposta-email`) e
   **passa pelo gate de LGPD (`agents/lgpd.md`, obrigatório e bloqueante
   — mesma regra do `/proposta`, RF-16)** antes de criar o rascunho/
   enviar via Gmail. Só se `lgpd` aprovar, o `crm` persiste
   `contato_realizado -> follow_up` ou `follow_up -> follow_up`. Se
   bloquear, pule aquele lead nesta rodada e reporte o motivo.
3. Para quem já atingiu o limite sem resposta: `crm` persiste
   `follow_up -> perdido` com `motivo: "sem_resposta"`.

## Saída

Liste: follow-ups criados, leads que responderam nesse meio-tempo
(celebre!), e leads movidos para `perdido` por esgotar o limite. Ofereça
automatizar via Routine agendada (ver `agents/follow-up.md`, seção
"Automação") se ainda não tiver sido configurada.
