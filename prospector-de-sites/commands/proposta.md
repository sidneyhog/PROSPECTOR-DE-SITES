---
description: Define o valor, escreve e envia (ou cria rascunho de) a proposta por e-mail, com gate de conformidade LGPD obrigatório
argument-hint: "[nome do cliente ou todos]"
---

Acione o Orquestrador (`agents/orquestrador.md`) para processar este
comando, seguindo a seção "Comercial: Precificação + gate de LGPD" de
`agents/orquestrador.md`.

## Passos

1. Ler `prospector-config.json` (assinatura e modo de envio).
2. Determinar os destinatários: `$ARGUMENTS`, ou todos os leads
   `pagina_revisada` já publicados (`urlNova`/`https_validado_em`
   preenchidos) que ainda não receberam proposta. Somente leads com
   e-mail confirmado — para os demais, informar que a abordagem fica
   manual via WhatsApp (oferecer o texto adaptado), sem passar pelo gate
   de LGPD automatizado nesta fase.
3. Para cada lead, na ordem: `precificacao-proposta` (define e registra
   valor internamente — nunca aparece no e-mail) → `copywriting` (redige
   o e-mail seguindo a skill `proposta-email` na íntegra: elogio
   específico, defeito objetivo, ÚNICO link a página-capa
   `.../proposta.html`, zero preço) → **checklist anti-spam da skill
   `proposta-email` (bloqueante)**, reescrever até passar em todos os
   itens → **`lgpd` (gate obrigatório e bloqueante)**.
4. **Se `lgpd` bloquear**: não envie nada para aquele lead. Reporte ao
   operador o motivo específico por campo e siga para o próximo lead do
   lote — um bloqueio não interrompe o lote inteiro.
5. **Se `lgpd` aprovar**: envio conforme o modo do config:
   - **rascunho** (padrão): crie o rascunho pelo conector do Gmail.
   - **enviar direto**: se o conector não oferecer envio direto, use o
     Claude in Chrome no Gmail web, ou crie o rascunho e avise o usuário.
   Depois do envio, peça ao `crm` para persistir
   `pagina_revisada -> contato_realizado` e para marcar a proposta como
   enviada (`marcar_proposta_enviada`).

## Saída

Resuma, por lead: valor definido (interno, não citado no e-mail), veredito
do gate de LGPD (aprovado/bloqueado com motivo), e status do envio
(rascunho criado / enviado / bloqueado). Lembre o usuário: `/respostas`
verifica quem respondeu (dá pra agendar diário) e `/followup` cuida de
quem está 3+ dias sem responder (ambos ainda no fluxo pré-v3 — agentes
`follow-up`/`analytics` chegam na Fase 7).
