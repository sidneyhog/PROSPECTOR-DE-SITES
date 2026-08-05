# PLANO_IMPLEMENTACAO.md — Plano Incremental de Implementação (Etapa 7 de 7)

**Depende de:** `docs/PRD.md`, `docs/AGENTES.md`, `docs/ARQUITETURA_TECNICA.md`,
`docs/CRM.md`, `docs/MEMORIA.md` e `docs/PROMPTS.md` — todos aprovados.
Esta é a **última etapa de documentação**. Ela organiza tudo o que foi
especificado nas Etapas 1–6 em fases pequenas, testáveis e reversíveis.
**Nenhuma linha de código do plugin foi escrita até aqui** — a execução de
cada fase abaixo só começa mediante aprovação explícita, fase a fase, como
já ocorreu com cada etapa de documentação.

Status: **aprovado — Fases 0 a 9 implementadas** (deploy-hostgator removido; VPS própria é o único caminho de publicação)
(ver `docs/AGENTES.md` para o glossário de nomes próprios dos agentes,
adotado na Fase 9).

---

## 1. Regras de execução válidas para todas as fases

1. **Uma fase = uma entrega isolada.** Cada fase abaixo é implementada em
   sua própria sequência de commits sobre a branch de trabalho, com escopo
   fechado — nunca duas fases misturadas no mesmo conjunto de mudanças.
2. **Toda fase é aditiva por padrão.** Segue RF-19: `CREATE TABLE IF NOT
   EXISTS`, `ALTER TABLE ... ADD COLUMN`, novos arquivos — nunca remoção de
   funcionalidade existente sem uma fase de descomissionamento explícita e
   aprovada à parte (§10).
3. **Toda fase tem critério de aceite testável manualmente** (este projeto
   não tem suíte de testes automatizados hoje — ver §11 sobre o que se
   propõe adicionar, de forma opcional, sem bloquear as fases).
4. **Toda fase é reversível**: reverter o(s) commit(s) daquela fase deve
   devolver o sistema ao comportamento da fase anterior, sem perda de dados
   de leads já processados pelas fases anteriores.
5. **Aprovação explícita entre fases.** Ao final de cada fase, reporto o
   resultado e aguardo aprovação antes de iniciar a próxima — mesmo padrão
   já seguido nas Etapas 1–6.
6. **O legado da v2 nunca é removido antes de confirmado.** Comandos e
   skills atuais continuam funcionando durante toda a migração; a v2 só é
   descontinuada numa fase final explícita (§10), decidida pelo operador.

## 2. Mapa Fases → Ondas do Roadmap (PRD §16)

| Onda (PRD §16) | Fases desta etapa |
|---|---|
| Onda 1 — Fundação | Fase 0, Fase 1, Fase 2 |
| Onda 2 — Diagnóstico | Fase 3 |
| Onda 3 — Produção da página | Fase 4 |
| Onda 4 — Publicação | Fase 5 |
| Onda 5 — Relacionamento | Fase 6, Fase 7 |
| Onda 6 — Fechamento do ciclo | Fase 8 |
| (descomissionamento, fora do roadmap original) | Fase 9 |

## 3. Fase 0 — Fundação técnica sem mudança funcional

**Objetivo.** Introduzir a infraestrutura de suporte (migração de schema,
estrutura de pastas) sem alterar nenhum comportamento hoje existente.

**Entregas.**
- Pastas `agents/` e `lib/` criadas (vazias ou com placeholders).
- `lib/migrations.py` (runner idempotente) + tabela `schema_version`
  (`ARQUITETURA_TECNICA.md` §4.4), aplicada sobre o schema atual **sem**
  ainda criar as tabelas novas das fases seguintes.
- `dashboard-server.py` passa a chamar o migration runner na subida, no
  lugar do `try/except ALTER TABLE` ad hoc atual.

**Critério de aceite.** O dashboard sobe normalmente sobre um
`prospector.db` de uma instalação v2 existente, sem qualquer diferença de
comportamento visível ao operador; `schema_version` reflete a versão atual.

**Reversibilidade.** Reverter remove os arquivos novos e a tabela
`schema_version`; nenhum dado de lead é tocado.

## 4. Fase 1 — Fundação do Orquestrador, CRM e Onboarding

**Objetivo.** Ter o primeiro agente (CRM) com escrita exclusiva no banco, e
o Orquestrador acionando pelo menos Onboarding, antes de qualquer agente de
negócio.

**Entregas.**
- `lib/db.py` (funções `obter_lead`, `atualizar_estado`,
  `registrar_execucao`, `registrar_auditoria` — `ARQUITETURA_TECNICA.md` §8.3).
- Tabelas novas: `interacoes`, `execucoes_agentes` (aditivas).
- `agents/atlas.md`, `agents/carmem.md`, `agents/bia.md`
  (`PROMPTS.md` §1, §2, §21).
- `commands/setup.md` passa a acionar o Orquestrador → Onboarding, em vez
  de instrução direta ao operador.
- `lib/auditlog.py` grava em `execucoes_agentes` a cada execução de agente.

**Critério de aceite.** Rodar `/setup` grava configuração validada (teste
de SSH incluído); qualquer mudança manual de status de um lead de teste
gera uma linha em `interacoes`; toda execução do agente Onboarding aparece
em `execucoes_agentes`.

**Reversibilidade.** Tabelas novas sem dados de negócio ainda dependente
delas; reverter remove o mecanismo sem afetar `leads` existente.

## 5. Fase 2 — Prospecção e Qualificação como agentes distintos

**Objetivo.** Separar, pela primeira vez, "encontrar" (Prospecção) de
"julgar" (Qualificação de Leads) — hoje uma única etapa dentro do skill
`prospeccao-maps`.

**Entregas.**
- `agents/iris.md`, `agents/justo.md`
  (`PROMPTS.md` §3, §4).
- `commands/prospectar.md` atualizado: aciona Orquestrador → Prospecção →
  Qualificação de Leads → CRM (grava `encontrado`/`qualificado`/`perdido`
  com o campo `motivo`, `CRM.md` §2.3).
- Reuso do skill `prospeccao-maps` existente como a "ferramenta" que o
  agente Prospecção invoca (não é reescrito do zero — `ARQUITETURA_TECNICA.md`
  §2).

**Critério de aceite.** Rodar `/prospectar` em um nicho/cidade de teste
produz leads no CRM com status `encontrado` ou diretamente `perdido`
(`motivo=nao_qualificado`) quando reprovados na Qualificação, sem
duplicatas contra leads já existentes.

**Reversibilidade.** `commands/prospectar.md` da v2 fica preservado em
histórico de git; caso a nova cadeia apresente regressão de qualidade
perceptível, revert do commit restaura o comportamento anterior
imediatamente.

## 6. Fase 3 — Grupo B: Diagnóstico completo

**Objetivo.** Introduzir os 8 agentes de diagnóstico, hoje totalmente
inexistentes no produto (PRD §2.2).

**Entregas.**
- Tabelas `auditorias`, `gbp_snapshots` (aditivas).
- `agents/vitor.md`, `agents/gael.md`, `agents/nando.md`,
  `agents/ravi.md`, `agents/vitalina.md`,
  `agents/clara.md`, `agents/sofia.md`,
  `agents/gabi.md` (`PROMPTS.md` §5–§12).
- Orquestrador passa a acionar todo o Grupo B na transição
  `qualificado → em_analise → site_auditado` (`AGENTES.md` §27).

**Critério de aceite.** Para um lead qualificado de teste, rodar o
Orquestrador produz um dossiê completo (uma linha por tipo em
`auditorias`) e o lead avança para `site_auditado`; se qualquer agente do
Grupo B retornar `precisa_input_humano`, a transição não ocorre
(`CRM.md` §2.3).

**Reversibilidade.** Cada agente do Grupo B pode ser desativado
individualmente via configuração sem quebrar os demais (baixo acoplamento
por design — `AGENTES.md`, cada ficha é independente).

## 7. Fase 4 — Grupo C: Produção da página

**Objetivo.** Decompor o skill monolítico `redesign-premium` da v2 em
UX/UI, Branding, Copywriting, CRO, Front-end e QA.

**Entregas.**
- Tabela `estetica_historico` (aditiva).
- `agents/nina.md`, `agents/bruna.md`, `agents/clarice.md`,
  `agents/cris.md`, `agents/fe.md`, `agents/quel.md`
  (`PROMPTS.md` §13–§18).
- `commands/redesenhar.md` atualizado para acionar a cadeia do Grupo C via
  Orquestrador, com o loop de reprovação do QA (`CRM.md` §2.2).
- O skill `redesign-premium` da v2 **permanece disponível** durante esta
  fase como comparação de qualidade (não é removido).

**Critério de aceite.** Gerar a página de um lead de teste produz um
resultado revisado por QA (aprovado ou reprovado com motivo); comparação
lado a lado com o resultado do skill monolítico da v2 não mostra
regressão perceptível de qualidade visual/textual.

**Reversibilidade.** Skill antigo mantido em paralelo nesta fase
especificamente por segurança; `commands/redesenhar.md` pode reverter para
acionar o skill antigo diretamente se a nova cadeia apresentar problema.

## 8. Fase 5 — Deploy em VPS (substitui HostGator)

**Objetivo.** Entregar o novo alvo de publicação confirmado pelo usuário
(VPS própria via SSH/nginx/Let's Encrypt), resolvendo o drift identificado
no PRD §2.2/§17.1.

**Entregas.**
- `skills/deploy-vps/` (novo) + `lib/ssh_deploy.py`.
- `agents/diego.md` (`PROMPTS.md` §20).
- `commands/publicar.md` atualizado para acionar Deploy via Orquestrador.
- `prospector-config.json`: novo bloco `vps{host, usuario, chave_ssh_path,
  dominio_padrao}`; bloco `hostgator{}` legado mantido **somente leitura**
  (nunca mais escrito), para instalações que ainda não migraram.
- `skills/deploy-hostgator/` **não foi removido nesta fase** — permaneceu
  como caminho secundário/manual, documentado no manual do usuário como
  legado, até a remoção definitiva aprovada na Fase 9 (§12).

**Critério de aceite.** Publicar a página de um lead de teste em uma VPS
de teste real via SSH resulta em HTTPS válido confirmado e
`https_validado_em` registrado; executar o Deploy uma segunda vez sobre o
mesmo lead (republicação) não duplica configuração nginx (RNF-05).

**Reversibilidade.** `deploy-hostgator` continuou existindo e funcional
durante esta fase; reverter esta fase apenas removeria o novo caminho, sem
impacto em quem ainda publicasse via HostGator manualmente. (Nota: esse
caminho foi removido definitivamente na Fase 9, §12 — este parágrafo
descreve o estado da Fase 5 no momento em que foi implementada.)

## 9. Fase 6 — Comercial: Precificação, Proposta e gate de LGPD

**Objetivo.** Separar preço (Precificação) de redação (Copywriting, já
feito na Fase 4) e introduzir o gate de conformidade obrigatório antes de
qualquer envio externo (RF-16).

**Entregas.**
- Tabelas `propostas`, `lgpd_checklist` (aditivas).
- `agents/valentina.md`, `agents/lia.md`
  (`PROMPTS.md` §19, §24).
- `commands/proposta.md` atualizado: Orquestrador aciona Precificação →
  Copywriting (reaproveitando texto da Fase 4) → **LGPD (gate obrigatório,
  bloqueante)** → envio via conector Gmail → CRM.

**Critério de aceite.** Tentar enviar uma proposta com um campo de dado
pessoal sem finalidade/retenção documentada é **bloqueado** pelo agente de
LGPD, com motivo específico; com o checklist completo, o envio ocorre
normalmente e `propostas.enviado_em` é registrado.

**Reversibilidade.** Gate pode ser inspecionado/testado isoladamente antes
de entrar em uso; reverter a fase remove Precificação/LGPD do fluxo sem
afetar leads já em `contato_realizado`.

## 10. Fase 7 — Relacionamento: Follow-up automatizado e Analytics

**Objetivo.** Eliminar a dependência de o operador rodar `/respostas`
manualmente todo dia (RF-13).

**Entregas.**
- Tabela `followups` (aditiva).
- `agents/fabi.md`, `agents/ana.md` (`PROMPTS.md` §22, §23).
- Uma Routine/trigger do Claude Code configurada para verificar respostas
  e disparar follow-ups agendados (substitui o polling manual da v2).

**Critério de aceite.** Simular um lead em `contato_realizado` sem resposta
por N dias (valor de teste reduzido) resulta em follow-up disparado
automaticamente pela Routine; esgotar o limite de tentativas move o lead
para `perdido` com `motivo=sem_resposta`.

**Reversibilidade.** A Routine pode ser desabilitada (sem exclusão) a
qualquer momento sem afetar dados já processados; comando manual
`/respostas`/`/followup` continua disponível como fallback.

## 11. Fase 8 — Fechamento do ciclo: Relatórios, Governança e observabilidade completa

**Objetivo.** Completar as últimas peças: agente de Relatórios, agente de
Governança de Prompts, memória compartilhada via embeddings/RAG, e as
novas abas do dashboard.

**Entregas.**
- Tabelas `prompts_versionamento`, `embeddings` (aditivas).
- `agents/renata.md`, `agents/gustavo.md`
  (`PROMPTS.md` §25, §26).
- `lib/embeddings.py` (indexação/consulta por similaridade —
  `MEMORIA.md` §9).
- Dashboard: novas abas Execuções, Auditoria/Diagnóstico e LGPD
  (`CRM.md` §8, `ARQUITETURA_TECNICA.md` §8.3).

**Critério de aceite.** Gerar um relatório para um lead `fechado` de teste
produz um artefato fiel aos dados de diagnóstico já existentes; uma consulta
de "propostas similares" via RAG retorna resultados sem vazar dado pessoal
no texto indexado (`MEMORIA.md` §9.4).

**Reversibilidade.** Todas as adições são aditivas e desacopladas do
pipeline comercial principal — reverter não interrompe prospecção → deploy.

## 12. Fase 9 — Hardening e descomissionamento do legado (concluída)

**Objetivo.** Só depois de todas as fases anteriores validadas em uso real
por um período (a definir pelo operador, ex.: um ciclo comercial completo):
avaliar a remoção definitiva do caminho `deploy-hostgator` e consolidar
`CHANGELOG.md`.

**Esta fase exigiu aprovação explícita e separada do operador antes de
qualquer remoção** — nenhum caminho legado seria apagado por decisão
autônoma do sistema, conforme princípio de reversibilidade (§1.6). O
operador aprovou a remoção explicitamente (renomear os agentes primeiro,
depois remover o legado e preparar a hospedagem VPS Hostinger).

**Entregas — parte não-destrutiva (concluída).**
- `CHANGELOG.md` consolidando o histórico de versões (antes só rastreável
  via `git log` — `ARQUITETURA_TECNICA.md` §11).
- Revisão de segurança final: credenciais (RNF-03), conformidade LGPD
  ponta a ponta — encontrou e corrigiu 2 gaps reais (gate de LGPD ausente
  no follow-up; risco documentado de senha em argv no publicador Windows).
- **Gap encontrado na Fase 8, fechado nesta fase:**
  `dashboard-server.py`'s `PUT /api/leads/<slug>` (edição manual/drag-and-
  drop no Kanban) gravava direto na tabela `leads`, sem passar pela
  validação de `lib/db.py::atualizar_estado` nem gravar em `interacoes`.
  Decisão: esse é um canal de override humano intencional (o operador pode
  corrigir o Kanban livremente), mas agora sempre registra uma linha de
  auditoria em `interacoes` com `agente='operador (dashboard)'`
  (`docs/CRM.md` §7, regra 6).
- 26 agentes renomeados com identidade humanizada e criativa
  (`docs/AGENTES.md`, glossário no topo do documento).

**Entregas — parte destrutiva (concluída, aprovação recebida).**
- Remoção de `skills/deploy-hostgator/` (todos os arquivos: `SKILL.md` e
  scripts em `references/`).
- Remoção do bloco `hostgator{}` do `dashboard-server.py` (rotas
  GET/PUT de `/api/config` só conhecem `vps` agora) e do painel "Conexão
  HostGator" do `dashboard-template.html`.
- Referências a HostGator/cPanel atualizadas para VPS em
  `commands/publicar.md`, `commands/redesenhar.md`, `agents/atlas.md`,
  `skills/deploy-vps/SKILL.md`, `skills/proposta-email/SKILL.md`,
  `manual.html`, `README.md` (raiz e do plugin), `.claude-plugin/
  plugin.json` e `.claude-plugin/marketplace.json` (versão 3.0.0).
- Preparação para hospedagem na VPS Hostinger do operador (ver runbook em
  `docs/RUNBOOK_VPS.md`).

**Nota sobre `prospector-config.json`:** este arquivo é dado de execução
do operador (gitignored, nunca commitado neste repositório) — não existe
uma cópia dele para editar aqui. Instalações antigas que ainda tenham um
bloco `hostgator{}` no próprio arquivo local não são afetadas pela remoção
do código (o dashboard simplesmente para de ler/gravar esse bloco); o
runbook de VPS orienta preencher o bloco `vps{}` via `/setup`.

## 13. Sobre testes automatizados (recomendação, não bloqueante)

O repositório hoje não tem nenhuma suíte de testes nem CI (achado da
exploração inicial). Para não introduzir dependência de infraestrutura
nova (contra o princípio de "sem infraestrutura própria" do PRD §13),
propõe-se, **como melhoria opcional dentro da Fase 1**, um teste mínimo em
`unittest` da biblioteca stdlib (sem framework externo) cobrindo
`lib/db.py` e `lib/migrations.py` — os dois módulos mais críticos para não
corromper dados de instalações existentes. Testes de agente em si (que
dependem de navegador/LLM) permanecem validação manual por critério de
aceite, como descrito em cada fase acima; automação completa desses fica
fora do escopo desta v3.

---

## Conclusão da documentação

Com a aprovação deste documento, encerram-se as Etapas 1–7 exigidas antes
de qualquer implementação. A partir daqui, cada fase (§3 a §12) é executada
e reportada individualmente, com aprovação explícita entre uma fase e a
próxima — o mesmo padrão de gate já usado durante toda a produção destes
sete documentos.

**Pronto para iniciar a Fase 0 assim que você confirmar.**
