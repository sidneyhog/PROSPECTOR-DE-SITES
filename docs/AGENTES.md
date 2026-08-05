# AGENTES.md — Arquitetura Multi-Agente (Etapa 2 de 7)

**Depende de:** `docs/PRD.md` (Etapa 1, aprovado). Este documento detalha o
Orquestrador e cada agente especialista mínimo exigido, mais os agentes
adicionais propostos e já justificados no PRD (§10). Nenhum código foi
alterado para produzir este documento — é especificação, não implementação.

Status: **aprovado**.

**Nota de nomenclatura (Fase 9 de `docs/PLANO_IMPLEMENTACAO.md`):** todos os
26 agentes têm, além da função técnica, um nome próprio humanizado — mais
fácil de lembrar e referenciar em conversa do que o identificador técnico.
O nome aparece sempre ao lado da função (ex.: "Atlas — Orquestrador"), e o
identificador técnico (`name:` no frontmatter, nome do arquivo em
`agents/`) é a versão em minúsculas sem acento do nome. Glossário completo:

| Nome | Função | Arquivo |
|---|---|---|
| Atlas | Orquestrador | `agents/atlas.md` |
| Bia | Onboarding/Configuração | `agents/bia.md` |
| Íris | Prospecção | `agents/iris.md` |
| Justo | Qualificação de Leads | `agents/justo.md` |
| Vitor | Auditoria Técnica de Sites | `agents/vitor.md` |
| Gael | SEO | `agents/gael.md` |
| Nando | SEO Local | `agents/nando.md` |
| Ravi | Performance | `agents/ravi.md` |
| Vitalina | Core Web Vitals | `agents/vitalina.md` |
| Clara | Acessibilidade | `agents/clara.md` |
| Sofia | Inteligência Competitiva | `agents/sofia.md` |
| Gabi | Google Business Profile | `agents/gabi.md` |
| Nina | UX/UI | `agents/nina.md` |
| Bruna | Branding | `agents/bruna.md` |
| Clarice | Copywriting | `agents/clarice.md` |
| Cris | CRO | `agents/cris.md` |
| Fê | Front-end | `agents/fe.md` |
| Quel | QA | `agents/quel.md` |
| Valentina | Precificação/Proposta Comercial | `agents/valentina.md` |
| Diego | Deploy | `agents/diego.md` |
| Carmem | CRM | `agents/carmem.md` |
| Fabi | Follow-up | `agents/fabi.md` |
| Ana | Analytics | `agents/ana.md` |
| Lia | LGPD | `agents/lia.md` |
| Renata | Geração de Relatórios | `agents/renata.md` |
| Gustavo | Governança de Prompts/Qualidade | `agents/gustavo.md` |

---

## 0. Regras arquiteturais válidas para todos os agentes

1. **Nenhum agente conversa diretamente com outro.** Toda entrada que um
   agente recebe vem do Orquestrador; toda saída que produz volta para o
   Orquestrador. Um agente nunca invoca outro agente, nunca lê a saída bruta
   de outro agente sem o Orquestrador mediar.
2. **Nenhum agente escreve diretamente no CRM.** Todo agente devolve um
   payload de "dados sugeridos para o CRM"; só o Orquestrador (via agente
   CRM, ver §5) confirma e persiste a mudança de estado.
3. **Contexto mínimo por execução.** O Orquestrador só repassa a um agente os
   campos do lead/CRM e artefatos estritamente necessários para aquela
   tarefa — nunca o histórico completo da sessão (requisito RNF-01 do PRD).
4. **Contrato de saída padrão.** Todo agente devolve ao Orquestrador uma
   estrutura com os mesmos campos-base, para que o Orquestrador consiga
   agregar resultados de agentes diferentes de forma previsível:

   ```json
   {
     "agente": "nome-do-agente",
     "lead_id": "slug-do-lead ou null se não aplicável",
     "status": "concluido | bloqueado | erro | precisa_input_humano",
     "resumo": "1-3 frases do que foi feito/encontrado",
     "dados_para_crm": { "campo": "valor" },
     "criterios_atendidos": ["..."],
     "criterios_pendentes": ["..."],
     "proxima_acao_sugerida": "texto curto ou null",
     "confianca": "alta | media | baixa",
     "referencias": ["paths/URLs consultados, para auditabilidade (RNF-04/RNF-10)"]
   }
   ```
5. **Encerramento nunca é "silencioso".** Um agente sempre termina em um dos
   quatro `status` acima — nunca some ou retorna vazio; se não conseguiu
   concluir, reporta `bloqueado`/`erro`/`precisa_input_humano` com o motivo.
6. **Modelo/ferramentas concretas ficam para a Etapa 3/6.** Aqui a coluna
   "Ferramentas" descreve *categorias* de capacidade (ex.: "navegador",
   "conector Gmail"); o mapeamento exato para tools do Claude Code
   (`WebFetch`, conectores MCP, `Bash`, etc.) é objeto de
   `ARQUITETURA_TECNICA.md` e `PROMPTS.md`.

Convenção de leitura de cada ficha: **Objetivo · Responsabilidades ·
Limites (o que NÃO faz) · Entradas · Saídas · Ferramentas · Memória ·
Critérios de qualidade · Critérios de encerramento.**

---

## 1. Atlas — Orquestrador

**Objetivo.** Ser o único ponto de decisão sobre *quais* agentes acionar,
*em que ordem*, e o único ponto que fala tanto com o operador humano quanto
com o CRM.

**Responsabilidades.**
- Interpretar o comando/intenção do operador (ex.: "processar lead X",
  "prospectar em Curitiba", "reenviar follow-up dos leads travados").
- Consultar o estado atual do lead (ou conjunto de leads) no CRM antes de
  decidir o que acionar (evita reprocessar etapas já concluídas).
- Selecionar dinamicamente o subconjunto de agentes necessário para avançar
  o estado (nunca aciona os 26 agentes de uma vez; ver mapa de gatilhos §8).
- Agregar as saídas dos agentes acionados, resolver conflitos (ex.: SEO e
  CRO sugerindo mudanças incompatíveis no mesmo elemento) e decidir a ação
  final.
- Confirmar a persistência do resultado no CRM (via agente CRM).
- Reportar ao operador um resumo consolidado, nunca o output bruto de cada
  agente.

**Limites (o que NÃO faz).**
- Não realiza trabalho especialista (não escreve copy, não julga
  acessibilidade, não decide preço) — sempre delega.
- Não altera os prompts/critérios de um agente em tempo de execução (isso é
  responsabilidade do agente de Governança de Prompts, §26, fora do
  runtime).
- Não publica nada em produção diretamente — sempre delega ao agente Deploy.

**Entradas.** Comando do operador (texto) + estado atual do(s) lead(s) no
CRM + configuração da instalação (nicho/cidade default, credenciais de VPS,
preferências definidas no Onboarding).

**Saídas.** Plano de execução (quais agentes, em que ordem), resumo
consolidado para o operador, conjunto de atualizações confirmadas no CRM.

**Ferramentas.** Mecanismo de subagents do Claude Code (para acionar cada
agente com contexto isolado); leitura/escrita mediada no CRM; acesso a
Routines/triggers para agendamentos (delegunderlying ao Follow-up/GBP).

**Memória utilizada.** Estado completo do CRM do(s) lead(s) em jogo; log de
execuções anteriores (para não repetir agentes já concluídos com sucesso);
configuração do operador. Não mantém memória de "conversa" entre execuções
não relacionadas.

**Critérios de qualidade.** Nunca aciona um agente cujas pré-condições no
CRM não estão satisfeitas (ex.: não aciona Copywriting antes de Auditoria
Técnica existir); nunca pula uma validação obrigatória (QA antes de Deploy;
LGPD antes de qualquer envio externo); nunca deixa o operador sem uma
resposta final clara.

**Critérios de encerramento.** Todos os agentes necessários para a transição
de estado solicitada retornaram com `status` definido e o CRM foi
atualizado (ou o Orquestrador reporta explicitamente ao operador o bloqueio
e o motivo, quando algum agente retornou `bloqueado`/`erro`/
`precisa_input_humano`).

---

## Grupo A — Aquisição de Leads

### 2. Bia — Onboarding/Configuração

**Objetivo.** Capturar e manter os parâmetros globais que todos os outros
agentes consomem (substitui o `/setup` atual).

**Responsabilidades.** Coletar/atualizar nicho(s)-alvo, cidade(s), dados de
assinatura/identidade do operador, credenciais de VPS (host, usuário, chave
SSH — nunca senha em texto plano, ver RNF-03), preferências de tom/marca
para propostas.

**Limites.** Não decide estratégia comercial nem toca em dados de leads
específicos — só configuração global da instalação.

**Entradas.** Respostas do operador a um checklist de configuração.

**Saídas.** Um objeto de configuração validado (`config` no CRM/armazenamento
local).

**Ferramentas.** Leitura/escrita de arquivo de configuração local;
validação de conectividade SSH com a VPS informada.

**Memória utilizada.** Configuração da instalação (persistente, não expira).

**Critérios de qualidade.** Nunca aceita credencial de VPS sem testar
conectividade; nunca aceita configuração incompleta que bloquearia agentes
downstream (ex.: Deploy sem VPS configurada).

**Critérios de encerramento.** Configuração completa e validada, ou lista
explícita de pendências reportada ao operador.

### 3. Íris — Prospecção

**Objetivo.** Encontrar candidatos a lead em um nicho/cidade a partir de
fontes públicas (hoje: Google Maps via Claude in Chrome).

**Responsabilidades.** Buscar negócios que atendam a critérios *configuráveis*
de entrada (nota mínima, nº de avaliações mínimo — defaults herdados da v2,
não fixos); coletar dados públicos básicos (nome, nicho, cidade, nota,
nº avaliações, site atual se existir, telefone/WhatsApp público).

**Limites.** **Não julga qualidade do site** nem qualifica o lead — isso é
exclusividade do agente de Qualificação (§4). Não decide se um lead deve
avançar no funil.

**Entradas.** Nicho + cidade (do comando do operador ou config default) +
critérios de filtro.

**Saídas.** Lista de candidatos brutos com dados públicos coletados.

**Ferramentas.** Navegador (Claude in Chrome) para Google Maps; extração de
dados de página.

**Memória utilizada.** Nenhuma memória de longo prazo própria; escreve
candidatos brutos que o Orquestrador registra no CRM como `Encontrado`.

**Critérios de qualidade.** Não duplica leads já existentes no CRM para o
mesmo nicho/cidade (checagem contra CRM antes de finalizar a lista); não
inclui negócios sem meio de contato público.

**Critérios de encerramento.** Lista de candidatos entregue (mesmo que
vazia, com o motivo — ex.: "nenhum resultado abaixo do critério de nota").

### 4. Justo — Qualificação de Leads

**Objetivo.** Decidir, para cada candidato trazido pela Prospecção, se ele
entra oficialmente no funil como lead `Qualificado`.

**Responsabilidades.** Julgar a qualidade do site atual do candidato (layout
datado, ausência de CTA, hospedagem gratuita, não responsivo, ausência de
prova social — critérios herdados da v2); confirmar existência de um
contato de WhatsApp válido (canal primário de contato desde 05/08/2026 —
`docs/PRD.md` §20; e-mail deixou de ser critério de desqualificação);
produzir um veredito com justificativa.

**Limites.** Não busca novos candidatos (isso é Prospecção); não realiza
auditoria técnica aprofundada (isso é o agente de Auditoria Técnica, que
roda depois, só para quem já foi qualificado — evita gastar contexto em
candidatos que nem passam no primeiro filtro).

**Entradas.** Dados públicos do candidato (da Prospecção) + URL do site
atual, se existir.

**Saídas.** Veredito `qualificado` / `desqualificado` + motivo + campos para
o CRM.

**Ferramentas.** Navegador (inspeção visual/estrutural do site atual).

**Memória utilizada.** Critérios de qualificação vigentes (configuráveis);
nenhuma memória de execuções passadas além do histórico do próprio lead.

**Critérios de qualidade.** Todo veredito vem com justificativa auditável
(RNF-04); critérios aplicados de forma consistente entre leads do mesmo
lote.

**Critérios de encerramento.** Veredito emitido para 100% dos candidatos
recebidos.

---

## Grupo B — Diagnóstico

### 5. Vitor — Auditoria Técnica de Sites

**Objetivo.** Produzir o dossiê técnico estruturado do site atual do lead
qualificado, consumido pelos demais agentes de diagnóstico (SEO, Performance,
CWV, Acessibilidade) em vez de cada um re-inspecionar o site do zero.

**Responsabilidades.** Levantar estrutura HTML, stack aparente (CMS,
hospedagem), presença/ausência de elementos-chave (meta tags, sitemap,
robots.txt, HTTPS, responsividade), e organizar tudo em um relatório
estruturado único.

**Limites.** Não emite julgamento de SEO, performance ou acessibilidade —
apenas coleta e estrutura os fatos que esses agentes vão interpretar.

**Entradas.** URL do site atual do lead.

**Saídas.** Relatório técnico estruturado (dossiê) reutilizável.

**Ferramentas.** Navegador/inspeção de página; leitura de HTML/headers.

**Memória utilizada.** Nenhuma própria; o dossiê é anexado ao registro do
lead (memória do lead — ver `MEMORIA.md`, Etapa 5).

**Critérios de qualidade.** Dossiê deve ser reaproveitável sem re-visita ao
site pelos agentes seguintes (RF-06).

**Critérios de encerramento.** Dossiê completo entregue, ou `bloqueado` com
motivo (ex.: site fora do ar).

### 6. Gael — SEO

**Objetivo.** Avaliar SEO on-page/técnico geral do site atual e recomendar
melhorias a aplicar no redesign.

**Responsabilidades.** Analisar hierarquia de headings, meta description/
title, densidade e relevância de conteúdo, presença de sitemap/robots,
estrutura de URLs, uso de schema.org genérico.

**Limites.** Não trata de SEO local/GBP (agente próprio, §8); não decide
copy final (entrega recomendações, Copywriting decide a redação).

**Entradas.** Dossiê da Auditoria Técnica.

**Saídas.** Lista priorizada de recomendações de SEO + achados.

**Ferramentas.** Análise do dossiê (sem nova navegação, reuso de dados já
coletados).

**Memória utilizada.** Dossiê técnico do lead (leitura); nenhuma memória
própria de longo prazo.

**Critérios de qualidade.** Recomendações acionáveis (não genéricas),
priorizadas por impacto.

**Critérios de encerramento.** Recomendações entregues ou `bloqueado` se o
dossiê de entrada estiver incompleto.

### 7. Nando — SEO Local

**Objetivo.** Avaliar sinais de SEO local — NAP consistency (Nome/Endereço/
Telefone), presença/qualidade do Google Business Profile, schema
`LocalBusiness`.

**Responsabilidades.** Comparar dados do site com o GBP (via agente GBP,
§9), identificar inconsistências de NAP, avaliar presença de schema local.

**Limites.** Não gerencia o GBP diretamente (isso é o agente GBP); não trata
SEO técnico geral (agente SEO, §6).

**Entradas.** Dossiê técnico + snapshot do GBP (do agente GBP).

**Saídas.** Achados de SEO local + recomendações.

**Ferramentas.** Análise de dados já coletados por Auditoria Técnica e GBP.

**Memória utilizada.** Dossiê do lead; snapshot de GBP.

**Critérios de qualidade.** Toda inconsistência de NAP citada deve apontar a
fonte divergente (site vs. GBP vs. diretórios).

**Critérios de encerramento.** Achados entregues, ou `precisa_input_humano`
se o GBP do lead não existir/não puder ser localizado.

### 8. Ravi — Performance

**Objetivo.** Avaliar velocidade e eficiência técnica do site atual (peso de
página, nº de requisições, uso de cache/compressão).

**Responsabilidades.** Medir/estimar tempo de carregamento e principais
gargalos técnicos.

**Limites.** Não avalia Core Web Vitals (métricas de UX de carregamento —
agente próprio, §9, mais específico e centrado em campo/laboratório Google);
Performance aqui é o diagnóstico técnico geral (peso de assets, requests).

**Entradas.** URL do site + dossiê técnico.

**Saídas.** Achados de performance + recomendações técnicas.

**Ferramentas.** Inspeção de rede/página via navegador.

**Memória utilizada.** Dossiê do lead.

**Critérios de qualidade.** Achados quantificados sempre que possível (não
apenas "está lento").

**Critérios de encerramento.** Achados entregues ou `bloqueado` (site
inacessível).

### 9. Vitalina — Core Web Vitals

**Objetivo.** Avaliar LCP, INP/FID e CLS do site atual conforme critérios do
Google.

**Responsabilidades.** Estimar/checar as três métricas centrais de CWV e
classificá-las (bom/precisa melhorar/ruim).

**Limites.** Não sobrepõe Performance (§8) — CWV é especificamente as
métricas de experiência do usuário definidas pelo Google, usadas depois por
SEO/Relatórios como critério formal.

**Entradas.** URL do site.

**Saídas.** Classificação das 3 métricas + recomendações específicas.

**Ferramentas.** Navegador/inspeção de carregamento real.

**Memória utilizada.** Dossiê do lead.

**Critérios de qualidade.** Classificação alinhada aos thresholds oficiais
do Google (não critério subjetivo do agente).

**Critérios de encerramento.** Classificação completa das 3 métricas
entregue.

### 10. Clara — Acessibilidade

**Objetivo.** Avaliar conformidade do site atual com critérios básicos de
acessibilidade (contraste, alt text, navegação por teclado, semântica HTML).

**Responsabilidades.** Checklist de acessibilidade sobre o dossiê técnico +
inspeção visual/estrutural.

**Limites.** Não decide o redesign (entrega achados; Front-end/UX-UI
aplicam).

**Entradas.** Dossiê técnico + URL do site.

**Saídas.** Lista de violações de acessibilidade + severidade.

**Ferramentas.** Inspeção de página (contraste, atributos HTML).

**Memória utilizada.** Dossiê do lead.

**Critérios de qualidade.** Cada violação referenciada a um critério
reconhecível (ex.: contraste insuficiente, ausência de `alt`).

**Critérios de encerramento.** Checklist completo entregue.

### 11. Sofia — Inteligência Competitiva

**Objetivo.** Comparar o lead com concorrentes diretos do mesmo nicho/cidade.

**Responsabilidades.** Identificar 2-3 concorrentes (via Prospecção/Maps),
comparar presença online (site, avaliações, GBP) e apontar diferenciais
exploráveis na proposta.

**Limites.** Não re-executa prospecção completa — usa o que a Prospecção já
levantou no mesmo nicho/cidade quando disponível; não decide copy (entrega
insumos para Copywriting/CRO/Precificação).

**Entradas.** Nicho/cidade do lead + (quando existente) leads já
prospectados no mesmo recorte.

**Saídas.** Comparativo estruturado + diferenciais sugeridos.

**Ferramentas.** Navegador (Maps, sites concorrentes).

**Memória utilizada.** Histórico de leads do mesmo nicho/cidade (memória
compartilhada — ver `MEMORIA.md`).

**Critérios de qualidade.** Comparação baseada em dados verificáveis, não
suposição.

**Critérios de encerramento.** Comparativo entregue com pelo menos 1
concorrente identificado, ou `precisa_input_humano` se nenhum concorrente
for encontrado.

### 12. Gabi — Google Business Profile

**Objetivo.** Monitorar e reportar o estado do GBP do lead/cliente
(avaliações, posição, completude do perfil), antes e depois do redesign.

**Responsabilidades.** Capturar snapshot do GBP (nota, nº avaliações,
categorias, completude de informações); disponibilizar esse snapshot para
SEO Local e Inteligência Competitiva; poder rodar de forma independente do
fluxo de redesign (monitoramento pós-venda, RF-08).

**Limites.** Não realiza SEO local propriamente dito (entrega dados brutos
para o agente SEO Local interpretar); não decide se o GBP precisa de
otimização — reporta os fatos.

**Entradas.** Nome/localização do negócio.

**Saídas.** Snapshot estruturado do GBP.

**Ferramentas.** Navegador (Google Business/Maps).

**Memória utilizada.** Histórico de snapshots do GBP por lead (memória do
lead — permite comparar antes/depois).

**Critérios de qualidade.** Snapshot com timestamp e fonte, comparável a
snapshots anteriores do mesmo lead.

**Critérios de encerramento.** Snapshot capturado, ou `bloqueado` se o
perfil não for localizável.

---

## Grupo C — Produção da Página

### 13. Nina — UX/UI

**Objetivo.** Definir a estrutura de experiência/interface da nova página
(hierarquia de informação, fluxo de navegação, wireframe conceitual).

**Responsabilidades.** Traduzir achados de Auditoria/Acessibilidade/CWV em
decisões de estrutura de página (o que vai acima da dobra, quantas seções,
onde ficam CTAs).

**Limites.** Não escreve copy (Copywriting) nem decide paleta/identidade
visual (Branding) — define estrutura e fluxo, não conteúdo final nem estilo
visual.

**Entradas.** Dossiê técnico + achados de Acessibilidade/CWV + briefing do
Onboarding (preferências do operador).

**Saídas.** Estrutura de página (wireframe conceitual em texto/spec).

**Ferramentas.** Nenhuma externa; raciocínio sobre os dossiês recebidos.

**Memória utilizada.** Dossiê do lead; padrões de variedade visual já usados
em outros clientes (memória compartilhada, para não repetir estrutura
idêntica — ver `MEMORIA.md`).

**Critérios de qualidade.** Estrutura coerente com achados de acessibilidade
e CWV (ex.: não propõe carrossel pesado se CWV já apontou LCP ruim).

**Critérios de encerramento.** Estrutura entregue e consumível por Branding/
Copywriting/Front-end sem ambiguidade.

### 14. Bruna — Branding

**Objetivo.** Definir identidade visual da nova página (paleta, tipografia,
tom visual), preservando ativos reais do cliente (logo, fotos) quando
existentes.

**Responsabilidades.** Extrair ativos reais do site atual (logo, fotos —
prática já usada na v2); decidir paleta/tipografia via ferramenta de
variedade visual (`ui-ux-pro-max`, herdada da v2) garantindo que o resultado
não repita a estética de outro cliente recente.

**Limites.** Não define estrutura de página (UX/UI) nem redige texto
(Copywriting).

**Entradas.** Estrutura de UX/UI + ativos extraídos do site atual + memória
de estéticas usadas recentemente.

**Saídas.** Especificação de identidade visual (paleta, tipografia, uso dos
ativos).

**Ferramentas.** Navegador (extração de ativos); ferramenta de geração de
variedade visual (`ui-ux-pro-max-cli`).

**Memória utilizada.** Memória compartilhada de estéticas recentes (evitar
repetição entre clientes — já era requisito da v2, preservado aqui).

**Critérios de qualidade.** Não repete paleta/tipografia idêntica a um
cliente processado recentemente (mesmo critério já vigente na v2);
preserva ativos reais do cliente sem invenção.

**Critérios de encerramento.** Especificação visual entregue e distinta das
últimas N estéticas usadas.

### 15. Clarice — Copywriting

**Objetivo.** Redigir todo o texto voltado ao cliente final: página,
mensagem de proposta (WhatsApp, canal primário desde 05/08/2026 — e-mail
como alternativa), follow-up, contrato (partes textuais).

**Responsabilidades.** Redigir copy da página com base na estrutura (UX/UI)
e nos diferenciais levantados (Inteligência Competitiva); redigir
mensagens de proposta/follow-up sem preço (preço é do agente de
Precificação, §19).

**Limites.** Não define preço/condições comerciais; não decide layout/
estrutura (UX/UI) nem identidade visual (Branding); não implementa HTML
(Front-end).

**Entradas.** Estrutura de UX/UI + achados de Inteligência Competitiva +
tom de voz definido no Onboarding.

**Saídas.** Textos finais (página, mensagem de proposta, follow-up)
prontos para revisão de CRO.

**Ferramentas.** Nenhuma externa além de leitura dos insumos recebidos.

**Memória utilizada.** Dossiê do lead; diretrizes de tom de voz do
Onboarding.

**Critérios de qualidade.** Copy livre de alegações não verificáveis; sem
gatilhos que soem spam (mensagem curta e pessoal para WhatsApp; checklist
completo já usado na v2 quando o canal for e-mail).

**Critérios de encerramento.** Todos os textos necessários entregues e
prontos para avaliação de CRO.

### 16. Cris — CRO

**Objetivo.** Otimizar a copy e a estrutura para conversão (CTAs, prova
social, redução de fricção), sem reescrever do zero o trabalho de
Copywriting/UX-UI.

**Responsabilidades.** Revisar o texto e a estrutura entregues e sugerir
ajustes pontuais de conversão (posição de CTA, uso de prova social,
clareza de proposta de valor).

**Limites.** Não define preço; não redige do zero (ajusta o que já existe);
não implementa (Front-end aplica).

**Entradas.** Textos de Copywriting + estrutura de UX/UI.

**Saídas.** Lista de ajustes de conversão aplicáveis.

**Ferramentas.** Nenhuma externa.

**Memória utilizada.** Padrões de conversão que funcionaram em propostas
anteriores (memória compartilhada — taxa de resposta por variação, quando
disponível via Analytics).

**Critérios de qualidade.** Sugestões específicas e testáveis, não
genéricas ("melhorar CTA" não basta — deve dizer qual CTA e por quê).

**Critérios de encerramento.** Lista de ajustes entregue (mesmo que vazia,
se nada precisar mudar).

### 17. Fê — Front-end

**Objetivo.** Implementar a página final (HTML/CSS/JS autocontido,
responsivo), incorporando estrutura (UX/UI), identidade (Branding) e texto
final (Copywriting + ajustes de CRO).

**Responsabilidades.** Gerar a página estática autocontida (mantendo o
padrão já usado na v2: CSS inline, fontes Google, sem dependências
externas pesadas); gerar também a versão de editor visual e página de
comparação (funcionalidades já existentes, preservadas).

**Limites.** Não decide conteúdo, estrutura ou identidade — só implementa o
que os demais agentes do Grupo C definiram; não aprova a própria qualidade
(QA faz isso, nunca o próprio Front-end).

**Entradas.** Estrutura (UX/UI) + identidade (Branding) + textos finais
(Copywriting/CRO).

**Saídas.** Página HTML final + editor visual + página de comparação
(antes/depois).

**Ferramentas.** Geração/escrita de arquivos HTML/CSS/JS.

**Memória utilizada.** Nenhuma de longo prazo própria; consome as
especificações recebidas.

**Critérios de qualidade.** Página responsiva, autocontida, sem quebrar os
achados de Acessibilidade/CWV já levantados no Grupo B.

**Critérios de encerramento.** Página gerada e pronta para QA (transição
`PaginaGerada` no CRM).

### 18. Quel — QA

**Objetivo.** Ser o único agente com autoridade para aprovar a transição
`PaginaGerada → PaginaRevisada` (RF-10).

**Responsabilidades.** Validar a página final contra os achados de
Acessibilidade, CWV, Performance e SEO (regressão), checar responsividade,
checar que todos os textos de Copywriting foram incorporados corretamente,
checar ausência de erros óbvios (links quebrados, imagens faltando).

**Limites.** Não corrige — reprova e devolve ao Orquestrador com motivo
específico para reacionamento do agente responsável (Front-end, Copywriting
etc.); nunca aprova o próprio trabalho de um agente que também é QA (não
aplicável aqui, mas vale como princípio: QA nunca é o mesmo agente que
produziu o artefato).

**Entradas.** Página final (Front-end) + todos os achados do Grupo B
(referência de regressão).

**Saídas.** Veredito aprovado/reprovado + lista de motivos se reprovado.

**Ferramentas.** Inspeção da página gerada (navegador/leitura de arquivo).

**Memória utilizada.** Achados de diagnóstico do lead (Grupo B), para
checagem de regressão.

**Critérios de qualidade.** Todo motivo de reprovação é específico e
acionável pelo agente que vai corrigir.

**Critérios de encerramento.** Veredito emitido; se reprovado, o
Orquestrador reaciona o(s) agente(s) responsável(is) e QA roda novamente
sobre a nova versão (loop até aprovação ou decisão humana de seguir mesmo
assim).

---

## Grupo D — Comercial e Publicação

### 19. Valentina — Precificação/Proposta Comercial

**Objetivo.** Decidir valor e condições comerciais (setup + manutenção)
com base no dossiê de auditoria e no comparativo competitivo — separado de
Copywriting (que só redige), conforme proposto no PRD §10.

**Responsabilidades.** Definir preço de setup e mensalidade de manutenção,
considerando complexidade identificada (Grupo B) e posicionamento
competitivo (Inteligência Competitiva).

**Limites.** Não redige a mensagem de proposta (Copywriting faz isso,
usando o valor definido aqui); não negocia diretamente com o cliente
final.

**Entradas.** Dossiê de auditoria + achados de Inteligência Competitiva +
tabela de referência de preços da instalação (config).

**Saídas.** Valor de setup + manutenção + justificativa.

**Ferramentas.** Nenhuma externa.

**Memória utilizada.** Histórico de propostas/valores fechados
anteriormente (memória compartilhada, para calibrar consistência de
precificação).

**Critérios de qualidade.** Preço justificado por complexidade real do
projeto, não arbitrário; consistente com o histórico de preços da
instalação.

**Critérios de encerramento.** Valor definido e entregue ao Orquestrador
para composição da proposta.

### 20. Diego — Deploy

**Objetivo.** Publicar a página aprovada em VPS própria via SSH/nginx/Let's
Encrypt (substituindo definitivamente o fluxo HostGator/cPanel da v2).

**Responsabilidades.** Transferir os arquivos para a VPS configurada,
configurar/atualizar o virtual host nginx, emitir/renovar certificado
Let's Encrypt, validar HTTPS antes de reportar sucesso (equivalente ao
check de AutoSSL da v2, portado para o novo alvo).

**Limites.** Só publica página já aprovada por QA — nunca publica direto a
partir do Front-end; não decide configuração de VPS (isso é Onboarding).

**Entradas.** Página aprovada (pós-QA) + configuração de VPS (do
Onboarding).

**Saídas.** URL publicada + confirmação de HTTPS válido.

**Ferramentas.** Conexão SSH; comandos de configuração nginx; validação de
certificado.

**Memória utilizada.** Configuração de VPS (Onboarding); histórico de
publicações do lead (para idempotência — RNF-05).

**Critérios de qualidade.** HTTPS válido confirmado antes de reportar
sucesso; nenhuma duplicação de virtual host em republicações do mesmo lead.

**Critérios de encerramento.** Publicação confirmada com HTTPS válido, ou
`bloqueado` com o erro específico (ex.: falha de conexão SSH, DNS não
apontado).

### 21. Carmem — CRM

**Objetivo.** Ser o único agente com permissão de escrita no armazenamento
de estado do ciclo comercial (SQLite `leads` evoluído), a pedido do
Orquestrador.

**Responsabilidades.** Validar e persistir transições de estado (§8 do
PRD), validar que uma transição é permitida antes de gravá-la (ex.: não
permite pular de `Encontrado` direto para `Fechado`), manter histórico de
transições.

**Limites.** Não decide *se* uma transição deve ocorrer (isso é decisão do
Orquestrador com base nos vereditos dos demais agentes) — só valida a
consistência e persiste.

**Entradas.** Pedido de atualização de estado + payload de dados (vindo do
Orquestrador, agregando saídas de outros agentes).

**Saídas.** Confirmação de persistência + estado atualizado do lead.

**Ferramentas.** Leitura/escrita no armazenamento SQLite (`ALTER TABLE`
aditivo, nunca destrutivo — RF-19).

**Memória utilizada.** É, ele próprio, a camada de memória compartilhada de
negócio (ver `MEMORIA.md`, Etapa 5).

**Critérios de qualidade.** Nunca persiste uma transição de estado inválida
(RF-03); todo histórico de transição é preservado (não sobrescrito).

**Critérios de encerramento.** Transição persistida com sucesso, ou
rejeitada com motivo (transição inválida para o estado atual).

### 22. Fabi — Follow-up

**Objetivo.** Gerenciar o acompanhamento pós-proposta sem depender de o
operador rodar comandos manualmente todo dia (RF-13).

**Responsabilidades.** Verificar resposta a propostas enviadas (via CRM +
sinal do conector Gmail), agendar e executar follow-ups espaçados (regra
herdada da v2: acompanhamento gentil após alguns dias, não repetitivo/
insistente), mover lead para `Perdido` quando o limite de tentativas se
esgota.

**Limites.** Não redige o conteúdo do follow-up do zero (usa texto de
Copywriting); não decide preço/condições novas (aciona Precificação via
Orquestrador se necessário).

**Entradas.** Estado do lead no CRM + sinal de resposta (conector Gmail).

**Saídas.** Ação de follow-up executada ou decisão de mover para
`Perdido`.

**Ferramentas.** Conector Gmail (leitura de resposta, envio); agendamento
via Routine/trigger do Claude Code (substitui o polling manual do
`/respostas` da v2).

**Memória utilizada.** Histórico de tentativas de follow-up por lead
(memória do lead).

**Critérios de qualidade.** Nunca envia follow-up além do limite
configurado (evita parecer spam); sempre verifica resposta antes de
insistir.

**Critérios de encerramento.** Follow-up executado e registrado, ou lead
movido para `Perdido` com o motivo (limite esgotado).

---

## Grupo E — Governança e Relacionamento com o Cliente Final

### 23. Ana — Analytics

**Objetivo.** Registrar eventos de funil (proposta enviada/aberta/
respondida) para alimentar métricas de sucesso do PRD (§15).

**Responsabilidades.** Capturar e consolidar eventos disponíveis pelos
conectores já usados (Gmail); disponibilizar séries históricas para CRO e
Relatórios.

**Limites.** Não interpreta os dados para decisão de negócio (entrega
dados; CRO/Precificação/Relatórios interpretam).

**Entradas.** Eventos de funil vindos de outros agentes (Copywriting/
Follow-up/CRM) via Orquestrador.

**Saídas.** Séries de métricas consolidadas.

**Ferramentas.** Leitura de eventos já capturados pelos conectores
existentes (sem nova infraestrutura, RF-17).

**Memória utilizada.** Histórico de eventos por lead e agregado (memória
compartilhada).

**Critérios de qualidade.** Nenhum evento duplicado ou perdido na
consolidação.

**Critérios de encerramento.** Métricas solicitadas entregues e
consistentes com o histórico do CRM.

### 24. Lia — LGPD

**Objetivo.** Ser o guardião de conformidade: validar, antes de qualquer
envio externo (proposta, contrato, follow-up), que os dados pessoais
tratados têm finalidade e retenção documentadas — com poder de **bloquear**
o envio (RF-16).

**Responsabilidades.** Checar que os dados coletados de um lead têm base
legal registrada; checar que não há dado sensível desnecessário sendo
enviado; manter um checklist mínimo de conformidade por lead.

**Limites.** Não é um agente jurídico completo — atua como gate técnico de
verificação, não substitui aconselhamento jurídico formal.

**Entradas.** Payload de dados pessoais que está prestes a ser enviado
externamente.

**Saídas.** Aprovação ou bloqueio + motivo.

**Ferramentas.** Nenhuma externa; checklist sobre os dados recebidos.

**Memória utilizada.** Checklist de conformidade por lead (memória do
lead).

**Critérios de qualidade.** Todo bloqueio vem com motivo específico e
acionável (qual dado, qual problema).

**Critérios de encerramento.** Veredito de aprovação/bloqueio emitido antes
de qualquer envio externo ser autorizado pelo Orquestrador.

### 25. Renata — Geração de Relatórios

**Objetivo.** Consolidar saídas de Performance, CWV, SEO, Acessibilidade e
Analytics em um relatório apresentável ao cliente final (RF-18).

**Responsabilidades.** Montar o artefato final de relatório (HTML/PDF),
sem duplicar a análise já feita por esses agentes — só consolida e
apresenta.

**Limites.** Não reanalisa dados — só formata e apresenta o que já foi
produzido pelos agentes de diagnóstico.

**Entradas.** Achados de Performance, CWV, SEO, Acessibilidade, Analytics
para um lead/cliente específico.

**Saídas.** Relatório final apresentável.

**Ferramentas.** Geração de arquivo HTML/PDF.

**Memória utilizada.** Nenhuma própria; consome dados já persistidos no CRM/
memória do lead.

**Critérios de qualidade.** Relatório fiel aos dados de origem (sem
extrapolar além do que os agentes de diagnóstico encontraram).

**Critérios de encerramento.** Relatório gerado e entregue.

### 26. Gustavo — Governança de Prompts/Qualidade

**Objetivo.** Ser o dono da consistência dos prompts de sistema/
operacionais dos demais 25 agentes (Etapa 6), evitando que cada agente
evolua seu prompt de forma isolada e incoerente — conforme proposto no
PRD §10.

**Responsabilidades.** Revisar mudanças propostas a qualquer prompt de
agente quanto a consistência de formato de saída (contrato §0.4),
sobreposição de responsabilidade com outro agente, e clareza dos critérios
de qualidade/encerramento.

**Limites.** Não opera em tempo real durante o processamento de leads — é
um agente de manutenção/governança da própria especificação, acionado
quando um prompt é criado ou alterado, não a cada lead.

**Entradas.** Proposta de prompt novo/alterado para um agente.

**Saídas.** Aprovação ou pedido de ajuste do prompt revisado.

**Ferramentas.** Leitura dos documentos de especificação (`AGENTES.md`,
`PROMPTS.md`).

**Memória utilizada.** Todo o conjunto de prompts vigente (para checar
sobreposição/inconsistência).

**Critérios de qualidade.** Nenhum prompt aprovado viola o contrato de
saída padrão (§0.4) ou invade responsabilidade de outro agente.

**Critérios de encerramento.** Prompt aprovado ou devolvido com pedido de
ajuste específico.

---

## 27. Mapa de gatilhos: estado do CRM → agentes acionados pelo Orquestrador

| Transição de estado (PRD §8.1) | Agentes acionados pelo Orquestrador |
|---|---|
| `Encontrado` → `Qualificado` | Qualificação de Leads |
| `Qualificado` → `EmAnalise` | Auditoria Técnica, SEO, SEO Local, Performance, Core Web Vitals, Acessibilidade, Inteligência Competitiva, Google Business Profile |
| `EmAnalise` → `SiteAuditado` | CRM (persistência do dossiê consolidado) |
| `SiteAuditado` → `PaginaGerada` | UX/UI, Branding, Copywriting, CRO, Front-end |
| `PaginaGerada` → `PaginaRevisada` | QA (loop com Front-end/Copywriting se reprovado) |
| `PaginaRevisada` → `ContatoRealizado` | Precificação/Proposta Comercial, Copywriting (mensagem WhatsApp/e-mail), LGPD (gate), CRM — envio confirmado manualmente pelo operador no dashboard |
| `ContatoRealizado` → `Negociacao` | Follow-up, Analytics |
| `Negociacao` → `Fechado` | Deploy, CRM |
| `Negociacao` / `ContatoRealizado` → `Perdido` | Follow-up, CRM |
| Qualquer estado → `FollowUp` (sem resposta) | Follow-up |
| Pós-`Fechado` (monitoramento contínuo) | Google Business Profile, Analytics, Geração de Relatórios |

Este mapa é a base operacional para o mecanismo de decisão dinâmica do
Orquestrador (RF-01) e será formalizado tecnicamente na Etapa 3.

---

## Próximos passos

Mediante aprovação deste documento, a Etapa 3 (`ARQUITETURA_TECNICA.md`)
detalha como este desenho mapeia para módulos, "banco de dados", filas,
cache, memória, armazenamento, integrações, APIs, modelos de IA,
observabilidade, logs e versionamento — tudo dentro dos limites já
confirmados (arquitetura nativa ao Claude Code, sem backend próprio).
