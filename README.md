# 🎯 Prospector de Sites — v3.0.0

**Plataforma multi-agente para Claude (Cowork) que roda o ciclo completo de prospecção e venda de sites — com CRM local, LGPD de ponta a ponta e hospedagem em VPS própria.**

**Achou → Qualificou → Auditou → Redesenhou → Publicou → Ofertou → Acompanhou → Fechou.**

De graça, rodando no seu computador, sem mensalidade.

## O que mudou na v3

A v2 era um conjunto de comandos que o Claude seguia num único fluxo. A v3
reorganiza tudo em **1 orquestrador + 26 agentes especialistas**, cada um
com um nome próprio e uma responsabilidade só — do jeito que um estúdio de
verdade divide o trabalho (SEO não mexe em preço, quem publica não decide
copy). Três coisas novas de primeira classe:

- **LGPD obrigatória**: nenhuma proposta ou follow-up sai sem passar pelo
  gate de conformidade (agente **Lia**) — antes, o dado pessoal do lead
  simplesmente seguia direto pro e-mail.
- **Hospedagem em VPS própria**, containerizada (Docker + Traefik +
  Portainer) — chega de depender de cPanel/HostGator; ver
  `docs/RUNBOOK_VPS.md`.
- **CRM com trilha de auditoria completa**: toda transição de estado,
  automática ou manual, fica registrada — quem fez, quando e por quê.

Todo o desenho está documentado em `docs/` antes de qualquer linha de
código (veja [Documentação](#documentação) abaixo) — é assim que o projeto
foi construído, etapa por etapa, com aprovação explícita em cada uma.

## O ciclo completo

| Comando | O que acontece | Agente(s) principal(is) |
|---|---|---|
| `/setup` | Configura tudo uma vez (pasta, assinatura, nichos, conexão VPS) e entrega o manual + dashboard | Bia |
| `/prospectar` | Varre o Google Maps: negócios nota ≥ 4.7 com site fraco e e-mail público → CRM | Íris, Justo |
| `/redesenhar` | Audita o site atual (SEO, performance, acessibilidade, Core Web Vitals) e recria a página com estética premium, mantendo conteúdo/logo/fotos REAIS | Vitor, Gael, Nando, Ravi, Vitalina, Clara, Sofia, Gabi, Nina, Bruna, Clarice, Cris, Fê, Quel |
| `/editor` | Edita texto e imagem da página no navegador, sem código | Fê |
| `/publicar` | Sobe a página na sua VPS própria (Docker/Traefik, HTTPS automático) + página-capa da proposta | Diego |
| `/proposta` | Calcula o preço, escreve o e-mail, passa pelo gate de LGPD e cria o rascunho no Gmail | Valentina, Clarice, Lia |
| `/respostas` | Lê seu Gmail e move o card sozinho quando o cliente responde | Ana |
| `/followup` | Sem resposta em N dias? Gera o follow-up gentil automaticamente (via Routine agendada) | Fabi |
| `/contrato` | Fechou? Gera a minuta + Word travado e deixa o rascunho no Gmail | Carmem |

Um agente **Orquestrador (Atlas)** coordena tudo — os especialistas nunca
conversam entre si, só devolvem um resultado padronizado pra ele. O **CRM
(Carmem)** é o único que grava no banco; todos os outros passam por ela.
Lista completa dos 26 agentes:

<details>
<summary>Ver os 26 agentes e suas funções</summary>

| Nome | Função |
|---|---|
| Atlas | Orquestrador |
| Bia | Onboarding/Configuração |
| Íris | Prospecção |
| Justo | Qualificação de Leads |
| Vitor | Auditoria Técnica de Sites |
| Gael | SEO |
| Nando | SEO Local |
| Ravi | Performance |
| Vitalina | Core Web Vitals |
| Clara | Acessibilidade |
| Sofia | Inteligência Competitiva |
| Gabi | Google Business Profile |
| Nina | UX/UI |
| Bruna | Branding |
| Clarice | Copywriting |
| Cris | CRO |
| Fê | Front-end |
| Quel | QA |
| Valentina | Precificação/Proposta Comercial |
| Diego | Deploy |
| Carmem | CRM |
| Fabi | Follow-up |
| Ana | Analytics |
| Lia | LGPD |
| Renata | Geração de Relatórios |
| Gustavo | Governança de Prompts/Qualidade |

</details>

## 📊 CRM local (dashboard)

Kanban com drag & drop, funil (11 estágios: `encontrado` até
`fechado`/`perdido`), clientes, sites, comparador antes/depois, follow-ups,
execuções de agentes, auditoria/diagnóstico, status de LGPD por lead,
controle de contratos e painel financeiro — tudo num banco SQLite **na sua
pasta**, nunca na nuvem. Duplo clique no `iniciar-dashboard.bat` (Windows)
ou `iniciar-dashboard.command` (Mac). Requisito: [Python](https://www.python.org/downloads/) (marque "Add to PATH").

## 🌐 Hospedagem: VPS própria com Docker

O `/publicar` sobe os sites de clientes numa VPS que você contrata (Hostinger,
DigitalOcean, etc.), atrás de uma pilha Docker: **Traefik** cuida do HTTPS
automaticamente (Let's Encrypt, sem `certbot` manual) e **Portainer** dá
uma interface visual pra acompanhar os containers. Passo a passo completo
de configurar a VPS do zero: [`docs/RUNBOOK_VPS.md`](docs/RUNBOOK_VPS.md).

## Como instalar

**No Claude Cowork:** Plugins → Gerenciar plugins → Adicionar marketplace → cole a URL deste repositório → instale o **prospector-de-sites** → rode `/setup`.

**No Claude Code:**
```
/plugin marketplace add ArrecheNeto/PROSPECTOR-DE-SITES
/plugin install prospector-de-sites@arrecheneto-plugins
```

## 🔄 Já tem o plugin e não atualiza?

Re-adicionar o link NÃO atualiza (fica em cache). Faça:
```
/plugin marketplace update arrecheneto-plugins
```
e reinicie o app — a versão certa é a **3.0.0** (confira em Gerenciar plugins). Se não subir: desinstale o plugin → remova o marketplace → feche o app → adicione e instale de novo. A atualização é automática (autoUpdate ativado).

## Requisitos

Claude Cowork · extensão Claude in Chrome · conectores Gmail e Google Drive · VPS própria com Docker (Traefik + Portainer) e domínio apontado (acesso SSH) · Python (para o dashboard e o publicador) · Windows ou Mac.

## Documentação

Todo o desenho da plataforma foi escrito e aprovado em etapas, antes da
implementação — cada documento cobre uma camada:

| Documento | Conteúdo |
|---|---|
| [`docs/PRD.md`](docs/PRD.md) | Visão de produto, personas, requisitos funcionais e não funcionais, roadmap |
| [`docs/AGENTES.md`](docs/AGENTES.md) | Especificação dos 26 agentes: contrato, responsabilidades, critérios de sucesso |
| [`docs/ARQUITETURA_TECNICA.md`](docs/ARQUITETURA_TECNICA.md) | Módulos, banco de dados, filas, integrações, observabilidade |
| [`docs/CRM.md`](docs/CRM.md) | Máquina de estados do pipeline, transições válidas, telas do dashboard |
| [`docs/MEMORIA.md`](docs/MEMORIA.md) | Os 8 tipos de memória do sistema e o RAG local (embeddings + LGPD) |
| [`docs/PROMPTS.md`](docs/PROMPTS.md) | Prompt de sistema e operacional de cada agente |
| [`docs/PLANO_IMPLEMENTACAO.md`](docs/PLANO_IMPLEMENTACAO.md) | As 10 fases de implementação, entregas, critérios de aceite e reversibilidade de cada uma |
| [`docs/RUNBOOK_VPS.md`](docs/RUNBOOK_VPS.md) | Passo a passo operacional para provisionar a VPS (Docker/Traefik/Portainer) |

## Manual do usuário

O `/setup` entrega o [manual completo](prospector-de-sites/manual.html) na sua pasta — passo a passo de tudo, incluindo a seção "E no Mac?" e os problemas comuns.

---

Feito por **Helio Arreche** · [YouTube](https://youtube.com/@helioarreche) · [Instagram @helioarreche](https://instagram.com/helioarreche) · Série completa do plugin no canal 🎬
