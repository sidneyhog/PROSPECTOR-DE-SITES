---
description: Busca no Google Maps negócios bem avaliados com sites ruins, qualifica cada candidato e grava o resultado no CRM
argument-hint: "[nicho] [cidade] — opcional, usa os padrões do config"
---

Acione o Orquestrador (`agents/atlas.md`) para processar este
comando.

## O que o Orquestrador deve fazer

1. Ler `prospector-config.json` na pasta conectada. Se não existir,
   oriente a rodar `/setup` primeiro.
2. Determinar nicho e cidade: usar os argumentos `$ARGUMENTS` se
   informados; senão, perguntar ao usuário qual dos nichos padrão do
   config usar (e confirmar a cidade). O usuário SEMPRE pode trocar nicho
   e cidade na hora — nunca travar nos padrões.
3. Perguntar ao agente `carmem` (`agents/carmem.md`) quais leads já existem no
   CRM para este nicho/cidade — usar essa lista para excluir duplicatas da
   nova busca (RF-04, `docs/AGENTES.md` §3).
4. Acionar o agente `iris` (`agents/iris.md`) passando nicho,
   cidade, meta de candidatos (config, padrão 10) e a lista de já
   conhecidos. Registrar a execução via `lib/auditlog.py`.
5. Para cada candidato retornado por `iris`:
   a. Acionar o agente `carmem` para persistir a criação do lead
      (`None -> encontrado`) com os dados coletados.
   b. Acionar o agente `justo` (`agents/justo.md`)
      com os dados do candidato. Registrar a execução via
      `lib/auditlog.py`.
   c. Acionar o agente `carmem` para persistir o veredito:
      `encontrado -> qualificado` (com o motivo e o e-mail encontrado) ou
      `encontrado -> perdido` (com `motivo=nao_qualificado: ...`).
6. Ao final da busca, se pelo menos um candidato ficou `qualificado`,
   pergunte ao operador se deseja rodar agora o diagnóstico técnico
   completo (Grupo B: auditoria técnica, SEO, SEO local, performance, Core
   Web Vitals, acessibilidade, inteligência competitiva, Google Business
   Profile) para os leads recém-qualificados deste lote — padrão sugerido:
   sim. Se confirmado, siga a seção "Grupo B de diagnóstico" de
   `agents/atlas.md` para cada lead qualificado, até
   `site_auditado` ou um bloqueio reportável. Se o operador preferir
   revisar a lista antes, pule esta etapa — o lead fica `qualificado` e
   pode ser levado a `em_analise` depois, reacionando o mesmo fluxo.
7. Gerar as saídas voltadas ao usuário descritas abaixo. A fonte de
   verdade do funil passa a ser o `prospector.db` (via CRM) — a planilha e
   o `dashboard.html` são espelhos para consumo humano, regenerados a
   partir do que está no banco.

Se qualquer agente retornar `bloqueado`/`erro`/`precisa_input_humano` para
um candidato específico, registre e siga para o próximo candidato — não
interrompa o lote inteiro por causa de um caso isolado; reporte os casos
não resolvidos no resumo final ao operador.

## Saída — Google Sheets + dashboard + cópia local

1. **Google Sheets**: salve os leads numa PLANILHA DO GOOGLE via conector
   do Google Drive — `create_file` com `contentMimeType: text/csv` e o CSV
   como `textContent` (a conversão automática cria uma planilha nativa do
   Sheets). Título: `Leads Prospector — [nicho] [cidade]`. Colunas: #,
   Nome, Nota, Avaliações, E-mail, Telefone, Site atual, Motivo, Situação
   (Qualificado/Perdido + motivo), Status (CRM), URL nova. Inclua TODOS os
   avaliados (qualificados e perdidos), ranqueados por potencial (melhor
   nota + pior site primeiro). Retorne o link da planilha ao usuário.
2. **Cópia local**: mantenha `leads.md` na pasta conectada como cópia de
   trabalho legível, gerada a partir do `prospector.db` (não é mais a
   fonte de verdade — só espelho). Em rodadas novas, some os leads novos
   aos antigos, nunca duplique cliente já avaliado (o CRM já garante isso
   no passo 3).
3. **Dashboard**: regenere `dashboard.html` na raiz da pasta conectada
   seguindo a skill `dashboard-leads` (o próprio `dashboard-server.py`, se
   estiver rodando, já reflete o banco em tempo real via `/api/leads`).

A entrega final DEVE incluir a confirmação explícita "Dashboard atualizado:
[N] leads (X qualificados, Y perdidos, Z auditados)". Mostre a tabela ao
usuário com o link da planilha e do `dashboard.html`, e sugira o próximo
passo: `/redesenhar` para os leads já `site_auditado` (a implementação do
Grupo C de produção da página é da Fase 4 — até lá, `/redesenhar` segue o
fluxo anterior à v3).
