---
description: Redesenha os sites dos leads auditados com estética premium, via a cadeia de agentes do Grupo C (lote de 5 ou mais)
argument-hint: "[URLs ou nomes dos leads] — opcional, usa os 5+ melhores leads site_auditado"
---

Acione o Orquestrador (`agents/atlas.md`) para processar este
comando, seguindo a seção "Grupo C de produção da página" de
`agents/atlas.md`.

## Seleção dos clientes

1. Ler `prospector-config.json` na pasta conectada.
2. Se `$ARGUMENTS` trouxer URLs ou nomes, usar esses leads (devem estar
   com status `site_auditado`; se algum não estiver, oriente a rodar
   `/prospectar` até completar o diagnóstico dele antes de incluí-lo
   aqui). Senão, selecionar os leads `site_auditado` mais bem ranqueados
   via o agente `carmem` — mínimo de 5 clientes por lote (se houver menos de
   5, use todos e avise que rodar `/prospectar` de novo aumenta o lote).
3. Confirmar a lista com o usuário antes de começar.

## Para cada cliente do lote

Rodar a cadeia completa do Grupo C (`agents/atlas.md`, seção
correspondente): `nina` → `bruna` → `clarice` → `cris` →
`fe` → `quel` (com loop de reprovação). Registrar cada execução via
`lib/auditlog.py` e persistir as transições de estado
(`site_auditado -> pagina_gerada -> pagina_revisada`) e a direção
estética via o agente `carmem`, conforme descrito em `agents/atlas.md`.

Se `quel` reprovar mais de 2 vezes seguidas para o mesmo lead, pare o loop
automático, reporte ao operador os motivos das reprovações e peça decisão
manual (seguir mesmo assim, ou revisar manualmente antes de continuar) —
não insista indefinidamente sem visibilidade do operador.

## Checklist de saída (bloqueante)

Antes de apresentar qualquer resultado ao usuário, confirme que TODOS
estes arquivos existem para cada cliente aprovado por `quel` — se faltar
algum, isso é um bug da cadeia (reporte, não gere manualmente por fora
dela):

- [ ] `sites/[slug]/[slug].html`
- [ ] `sites/[slug]/[slug]-editor.html`
- [ ] `comparar.html` na raiz, com abas para TODOS os clientes do lote
      (antigos e novos)

## Saída (TRAVADA — siga exatamente este formato)

A entrega final ao usuário DEVE conter, nesta ordem, sem exceção:

1. **Cards de arquivo apresentados no chat** (via ferramenta de
   apresentação de arquivos): o `comparar.html` PRIMEIRO, depois a página
   e o editor de cada cliente aprovado.
2. **Resumo de 1 linha por cliente** (o que melhorou) + status de `quel`
   (aprovado direto, ou aprovado após N reprovações, ou pendente de
   decisão manual).
3. **Confirmação do dashboard**: "Dashboard atualizado: [N] leads em
   pagina_revisada" — o dashboard reflete o `prospector.db` via
   `dashboard-server.py`/`dashboard-leads`.
4. Orientação curta: `comparar.html` = antes/depois lado a lado ·
   `[slug]-editor.html` = editar textos/imagens · próximo passo:
   `/publicar` (o agente `diego` publica em VPS própria via SSH/nginx).

É PROIBIDO encerrar a resposta sem os itens 1 e 3.

## Reversibilidade (Fase 4)

O skill `redesign-premium` da v2 permanece disponível e inalterado. Se a
cadeia de agentes do Grupo C apresentar problema para um cliente
específico, o operador pode pedir explicitamente para redesenhar aquele
cliente seguindo a skill `redesign-premium` diretamente (fluxo monolítico
da v2), sem passar pelo Grupo C — nesse caso, avise que a página resultante
não terá passado pelo `quel` nem pelo dossiê do Grupo B, e ofereça rodar o
`quel` manualmente sobre o resultado depois.
