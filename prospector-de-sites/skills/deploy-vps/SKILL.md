---
name: deploy-vps
description: Esta skill deve ser usada ao publicar páginas em VPS própria (SSH/SCP + nginx + Let's Encrypt) — upload via publicador local automático, SSH/SCP direto do sandbox, ou instrução copiável para o terminal do usuário; criação de pastas por cliente, verificação da URL pública e HTTPS. Acione quando o usuário disser "publicar", "subir o site", "colocar no ar", "deploy", "vps" ou rodar /publicar ou o teste de conexão do /setup.
---

# Deploy em VPS própria

Publicar páginas em `[caminhoRemoto]/[pastaBase]/[slug]/` no servidor do
usuário e garantir a URL pública `https://[dominio]/[pastaBase]/[slug]/`
funcionando. Substitui o fluxo HostGator/cPanel da v2 — `deploy-hostgator`
continua disponível como caminho secundário/manual para quem ainda não
migrou (ver "Migração de instalações HostGator" ao final).

## Credenciais

Tudo vem de `prospector-config.json` (bloco `vps`): `host`, `porta`
(padrão 22), `usuario`, `caminhoRemoto` (raiz do site no nginx, ex.:
`/var/www/html`), `dominio`, `pastaBase` (padrão `clientes`), e
**autenticação**: `chaveSshPath` (caminho para uma chave privada SSH —
preferido, mais seguro) ou `senha` (fallback, se o usuário só tiver acesso
por senha). **A senha (quando usada) vive SÓ no arquivo, no computador do
usuário — nunca é digitada no chat, nunca é exibida em nenhuma saída, log
ou comando mostrado ao usuário**, mesma regra já aplicada ao HostGator na
v2. Prefira sempre `chaveSshPath` quando o usuário tiver uma chave gerada;
oriente a gerar uma (`ssh-keygen`) se ele só tiver senha e quiser migrar.

## Configuração única do domínio (nginx + Let's Encrypt) — feita uma vez no /setup

Antes do primeiro deploy, o domínio precisa estar apontando para a VPS
(registro DNS tipo A) e a VPS precisa ter nginx com um server block para o
domínio, servindo `caminhoRemoto` como raiz, e certificado Let's Encrypt
válido (`certbot --nginx -d [dominio] --non-interactive --agree-tos -m
[email]`, rodado uma vez no servidor). Isso NÃO se repete por cliente —
uma vez que o domínio tem HTTPS válido, toda subpasta nova
(`[pastaBase]/[slug]/`) já herda o mesmo certificado, sem configuração
adicional de nginx por cliente. Se o usuário ainda não tem isso pronto,
oriente-o (ou, se ele autorizar acesso SSH, você mesmo pode rodar os
comandos via `lib/ssh_deploy.py`/SSH direto) antes de tentar o primeiro
deploy.

## Método 1 — Publicador automático local (RECOMENDADO: instala uma vez, nunca mais clica)

A rede do sandbox do Cowork pode não alcançar a porta SSH da VPS do
usuário — vale o mesmo aviso do HostGator. A publicação roda na máquina do
usuário via um publicador instalado no agendador do sistema: a cada minuto
ele verifica a fila e sobe o que houver, escondido, lendo as credenciais
do config. O usuário instala UMA vez e o `/publicar` vira 100% automático.

1. **Garanta os arquivos do publicador na pasta conectada** (copie de
   `references/` desta skill, sobrescrevendo versões antigas), conforme o
   sistema do usuário:
   - **Windows**: `publicar-agora.ps1`, `publicar-agora.bat`,
     `publicador-oculto.vbs`, `instalar-publicador.bat` — usa
     `pscp.exe`/`plink.exe` (PuTTY, baixados uma vez no `/setup`, ver
     `commands/setup.md` item 7A / `agents/onboarding.md`).
   - **Mac**: `publicar-agora.command` e `instalar-publicador.command` —
     usa `scp`/`ssh` nativos (chave) ou `sshpass` (senha, `brew install
     sshpass`).
   Em dúvida, copie todos.
2. **Primeira vez**: peça UM duplo clique no `instalar-publicador.bat`
   (Windows — cria a tarefa "ProspectorPublicadorVPS"; erro de permissão =
   botão direito → Executar como administrador) ou no
   `instalar-publicador.command` (Mac — registra no launchd, label
   `com.prospector.publicadorvps`; se o macOS bloquear por segurança:
   botão direito → Abrir na primeira vez). Só uma vez na vida.
3. **Monte a fila**: escreva `fila-publicacao.txt` na raiz da pasta
   conectada, uma linha por arquivo: `caminho/local/arquivo.html|[pastaBase]/[slug]/index.html`
   (mesmo formato já usado no HostGator — o caminho remoto aqui é relativo
   a `caminhoRemoto`). Inclua página (`index.html`) e capa
   (`proposta.html`) de cada cliente. Em até 1 minuto o publicador sobe
   tudo sozinho e renomeia a fila para `fila-publicada-[data].txt` (log em
   `publicador-log.txt`).
4. **Aguarde ~90s e verifique**: confira se a fila foi renomeada e teste
   as URLs (verificação abaixo). Sem tarefa instalada, o fallback manual é
   o duplo clique no `publicar-agora.bat`/`.command`.

## Método 2 — SSH/SCP direto do sandbox (tentar primeiro, silencioso)

Antes de acionar o usuário, tente publicar você mesmo via
`lib/ssh_deploy.py` (cópia em `references/ssh_deploy.py`):

```python
import sys; sys.path.insert(0, '<PASTA_CONECTADA>')
import ssh_deploy
ok, msg = ssh_deploy.garantir_diretorio_remoto(host, porta, usuario, caminho_remoto_completo,
                                                chave_ssh_path=chave, senha=senha)
ok, msg = ssh_deploy.publicar_arquivo(caminho_local, host, porta, usuario, caminho_remoto_completo,
                                      chave_ssh_path=chave, senha=senha)
```

Se funcionar, ótimo: zero ação do usuário. Se a rede do sandbox bloquear
(timeout/recusado) ou `ssh`/`scp`/`sshpass` não estiverem disponíveis,
caia SEM DRAMA para o Método 1 — não insista em tentativas repetidas.

## Método 3 — Instrução copiável (último recurso)

Sem cPanel/File Manager numa VPS genérica — se os métodos 1 e 2
falharem, gere um bloco de comandos prontos para o usuário colar no
próprio terminal (ex.: `scp -P [porta] [arquivo] [usuario]@[host]:[caminhoRemoto]/[pastaBase]/[slug]/index.html`),
explicando que ele roda isso uma vez com as próprias credenciais (nunca
peça a senha no chat).

## Verificação (obrigatória, após qualquer método)

1. Abra `https://[dominio]/[pastaBase]/[slug]/` e a capa
   `.../proposta.html` — confirme que carregam com conteúdo certo. Pode
   usar `ssh_deploy.verificar_https(url)` (stdlib, sem depender de
   navegador) como checagem programática antes/depois da checagem visual.
2. **HTTPS obrigatório**: precisa carregar com certificado válido. Se
   falhar apesar da configuração única já feita, verifique se o domínio
   realmente aponta pra VPS (DNS) e se o certbot renovou automaticamente
   (`certbot renew --dry-run` no servidor). Link `http://` NUNCA vai para
   cliente.
3. Registre `urlNova` e `https_validado_em` no lead via o agente `crm`
   (`atualizar_campos`, não é uma transição de estado —
   `docs/CRM.md` §3).

## Teste de conexão do /setup

Publique `teste.html` simples ("Funcionou!") em
`[caminhoRemoto]/[pastaBase]/teste/index.html` pelo Método 2; se
bloqueado, já deixe os scripts do Método 1 copiados na pasta, monte a fila
com o teste e peça os 2 cliques — assim o usuário aprende o fluxo logo no
setup.

## Migração de instalações HostGator

Instalações que já usavam `deploy-hostgator` continuam funcionando sem
mudança — o bloco `hostgator` do config é só leitura para elas (nunca
mais escrito, `docs/ARQUITETURA_TECNICA.md` §4.3). Para migrar: rodar
`/setup` de novo e preencher o bloco `vps` na aba Configurações do
dashboard. Os dois blocos podem coexistir no mesmo `prospector-config.json`
durante a transição.
