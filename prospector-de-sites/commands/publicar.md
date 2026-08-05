---
description: Publica as páginas revisadas em VPS própria (SSH/nginx/Let's Encrypt) e retorna as URLs públicas
argument-hint: "[nome do cliente ou todos]"
---

Acione o Orquestrador (`agents/atlas.md`) para processar este
comando, seguindo a seção "Deploy (publicação em VPS própria)" de
`agents/atlas.md`.

## Passos

1. Ler `prospector-config.json`. Se o bloco `vps` não estiver preenchido
   (nem `chaveSshPath` nem `senha`), oriente a rodar `/setup` primeiro —
   não prossiga sem credenciais de VPS.
2. Determinar o que publicar: `$ARGUMENTS` (um cliente ou "todos"), ou
   listar os leads com status `pagina_revisada` (via `carmem`) e perguntar.
3. **Gerar a página-capa de cada cliente**: preencher
   `references/capa-proposta-template.html` (skill `proposta-email`) com
   os dados do lead + assinatura do config e salvar como
   `sites/[slug]/proposta.html` (comportamento inalterado desta v2 — a
   decomposição de Precificação/Copywriting-proposta é da Fase 6).
4. **Publicar via o agente `diego`**, para cada cliente: página
   (`[slug].html`), editor (`[slug]-editor.html`) e capa
   (`proposta.html`).
5. **Verificação HTTPS (bloqueante)**: o próprio `diego` só reporta
   sucesso com HTTPS validado (`ssh_deploy.verificar_https`) — se ele
   retornar bloqueado, não considere publicado; reporte o erro específico
   ao operador.
6. Registrar via `carmem` → `atualizar_campos`: `urlNova` (URL pública da
   página) e `https_validado_em`, para cada cliente publicado com
   sucesso. O lead permanece `pagina_revisada` (a transição para
   `fechado` acontece só quando o contrato for assinado).

## Saída

Listar, por cliente: URL da página nova e URL da capa
(`.../proposta.html`), ambas com HTTPS confirmado. Sugerir o próximo
passo: `/proposta` para enviar os e-mails.

## Reversibilidade (Fase 5)

A skill `deploy-hostgator` da v2 continua disponível e inalterada, para
instalações que ainda não migraram para VPS própria — o bloco `hostgator`
do config permanece funcional (somente leitura por este comando; a
publicação por HostGator continua acionável manualmente seguindo a skill
diretamente, se o operador preferir não migrar ainda).
