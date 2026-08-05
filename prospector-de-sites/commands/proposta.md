---
description: Define o valor e prepara a mensagem de proposta (WhatsApp, canal primário — e-mail como alternativa), com gate de conformidade LGPD obrigatório. O envio em si é manual, pelo botão "Enviar mensagem" do dashboard.
argument-hint: "[nome do cliente ou todos]"
---

Acione o Orquestrador (`agents/atlas.md`) para processar este
comando, seguindo a seção "Comercial: Precificação + gate de LGPD" de
`agents/atlas.md`.

## Passos

1. Ler `prospector-config.json` (assinatura).
2. Determinar os destinatários: `$ARGUMENTS`, ou todos os leads
   `pagina_revisada` já publicados (`urlNova`/`https_validado_em`
   preenchidos) que ainda não têm proposta pendente. WhatsApp é o canal
   padrão (exigido desde a qualificação por `justo`); se por algum motivo
   o lead só tiver e-mail, use a alternativa de e-mail (ver `clarice`).
3. Para cada lead, na ordem: `valentina` (define e registra
   valor internamente — nunca aparece na mensagem) → `clarice` (redige a
   mensagem de WhatsApp: elogio específico, defeito objetivo, ÚNICO link
   a página-capa `.../proposta.html`, zero preço, curta — ver seção
   "Mensagem de proposta" em `agents/clarice.md`) → **`lia` (gate
   obrigatório e bloqueante de LGPD)**.
4. **Se `lia` bloquear**: não prepare nada para aquele lead. Reporte ao
   operador o motivo específico por campo e siga para o próximo lead do
   lote — um bloqueio não interrompe o lote inteiro.
5. **Se `lia` aprovar**: peça ao `carmem` para persistir a mensagem
   (`registrar_proposta(..., canal='whatsapp', mensagem=...)`) — **isso
   NÃO envia nada e NÃO transiciona o estado do lead ainda.** O envio real
   é um clique do operador no botão "Enviar mensagem" do card do lead no
   dashboard (abre `wa.me/<numero>?text=<mensagem>` com o texto já
   pronto): só nesse clique é que `enviado_em` é gravado e o lead
   transiciona `pagina_revisada -> contato_realizado`
   (`docs/CRM.md` §7 regra 7 — decisão de 05/08/2026: sem automação/API
   de envio, risco de banimento do WhatsApp assumido conscientemente só
   para leitura manual, nunca para disparo em massa).

## Saída

Resuma, por lead: valor definido (interno, não citado na mensagem),
veredito do gate de LGPD (aprovado/bloqueado com motivo), e se a mensagem
ficou pronta para envio. Lembre o operador: abra o dashboard, aba
Pipeline, e clique "Enviar mensagem" em cada card pronto — isso abre o
WhatsApp com o texto preenchido, e o operador confirma o envio de lá.
Depois de enviar por WhatsApp, a detecção de resposta ainda é manual
(mova o card quando o lead responder) — `/respostas`/`/followup`
continuam existindo para quem usa e-mail como alternativa.
