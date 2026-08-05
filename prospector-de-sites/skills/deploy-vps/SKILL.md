---
name: deploy-vps
description: Esta skill deve ser usada ao publicar páginas em VPS própria (SSH/SCP + Docker/Traefik/Portainer, com Let's Encrypt automático) — upload via publicador local automático, SSH/SCP direto do sandbox, ou instrução copiável para o terminal do usuário; criação de pastas por cliente, verificação da URL pública e HTTPS. Acione quando o usuário disser "publicar", "subir o site", "colocar no ar", "deploy", "vps" ou rodar /publicar ou o teste de conexão do /setup.
---

# Deploy em VPS própria

Publicar páginas em `[caminhoRemoto]/[pastaBase]/[slug]/` no servidor do
usuário e garantir a URL pública `https://[dominio]/[pastaBase]/[slug]/`
funcionando. Único caminho de publicação da plataforma (o antigo fluxo
HostGator/cPanel da v2 foi removido — `docs/PLANO_IMPLEMENTACAO.md` §12).

## Credenciais

Tudo vem de `prospector-config.json` (bloco `vps`): `host`, `porta`
(padrão 22), `usuario`, `caminhoRemoto` (pasta do host montada como volume
no container `prospector-sites`, ex.: `/opt/prospector/sites` — precisa
ser igual ao `CAMINHO_SITES` do `.env` da pilha Docker, `docs/RUNBOOK_VPS.md`
§5), `dominio`, `pastaBase` (padrão `clientes`), e
**autenticação**: `chaveSshPath` (caminho para uma chave privada SSH —
preferido, mais seguro) ou `senha` (fallback, se o usuário só tiver acesso
por senha). **A senha (quando usada) vive SÓ no arquivo, no computador do
usuário — nunca é digitada no chat, nunca é exibida em nenhuma saída, log
ou comando mostrado ao usuário**, mesma regra já aplicada ao HostGator na
v2. Prefira sempre `chaveSshPath` quando o usuário tiver uma chave gerada;
oriente a gerar uma (`ssh-keygen`) se ele só tiver senha e quiser migrar.

**Risco conhecido e documentado (autenticação por senha no Windows):** no
publicador do Mac/Linux e em `lib/ssh_deploy.py`, a senha é passada ao
`ssh`/`scp` via variável de ambiente (`SSHPASS`, lida pelo `sshpass`),
nunca como argumento de linha de comando. No Windows, porém, `pscp.exe`/
`plink.exe` (PuTTY) só aceitam senha via a flag `-pw`, que fica
brevemente visível na lista de processos do sistema (Gerenciador de
Tarefas, `Get-Process`) durante a publicação — não há equivalente ao
`sshpass` para essas ferramentas. Isso é uma limitação real das
ferramentas escolhidas, não um descuido: **por isso a recomendação de usar
chave SSH é mais forte ainda no Windows** — com `chaveSshPath` preenchido,
nem `pscp`/`plink` nem o script tocam na senha.

## Configuração única do domínio (Docker + Traefik + Portainer) — feita uma vez, `docs/RUNBOOK_VPS.md`

Antes do primeiro deploy, o domínio precisa estar apontando para a VPS
(registro DNS tipo A) e a VPS precisa ter a pilha Docker no ar: Traefik
(proxy reverso, emite e renova o certificado Let's Encrypt automaticamente
por container, sem `certbot` manual), Portainer (gestão visual dos
containers) e a imagem própria `prospector-sites` (serve `caminhoRemoto`
como raiz do site) — `docker-compose.yml`/`Dockerfile` em
`references/docker/` desta skill, passo a passo completo em
`docs/RUNBOOK_VPS.md`. Isso NÃO se repete por cliente — uma vez que o
domínio tem HTTPS válido, toda subpasta nova (`[pastaBase]/[slug]/`) já
herda o mesmo certificado, sem configuração adicional por cliente, e sem
precisar reiniciar nem reconfigurar o container. Se o usuário ainda não
tem isso pronto, oriente-o a seguir `docs/RUNBOOK_VPS.md` (ou, se ele
autorizar acesso SSH, você mesmo pode rodar os comandos via SSH direto)
antes de tentar o primeiro deploy. Quem preferir não usar Docker pode
montar o equivalente com nginx + certbot tradicionais (`docs/RUNBOOK_VPS.md`
§6) — a publicação por SSH/SCP funciona igual dos dois jeitos.

## Método 1 — Publicador automático local (RECOMENDADO: instala uma vez, nunca mais clica)

A rede do sandbox do Cowork pode não alcançar a porta SSH da VPS do
usuário. A publicação roda na máquina do usuário via um publicador
instalado no agendador do sistema: a cada minuto
ele verifica a fila e sobe o que houver, escondido, lendo as credenciais
do config. O usuário instala UMA vez e o `/publicar` vira 100% automático.

1. **Garanta os arquivos do publicador na pasta conectada** (copie de
   `references/` desta skill, sobrescrevendo versões antigas), conforme o
   sistema do usuário:
   - **Windows**: `publicar-agora.ps1`, `publicar-agora.bat`,
     `publicador-oculto.vbs`, `instalar-publicador.bat` — usa
     `pscp.exe`/`plink.exe` (PuTTY, baixados uma vez no `/setup`, ver
     `commands/setup.md` item 7A / `agents/bia.md`).
   - **Mac**: `publicar-agora.command` e `instalar-publicador.command` —
     usa `scp`/`ssh` nativos (chave) ou `sshpass` (senha, `brew install
     sshpass`).
   Em dúvida, copie todos. A pasta `references/docker/` (Dockerfile,
   `docker-compose.yml`, `nginx.conf`, `.env.example`) é separada — só
   precisa ir para a VPS (via `scp`), não para o publicador local
   (`docs/RUNBOOK_VPS.md` §5).
2. **Primeira vez**: peça UM duplo clique no `instalar-publicador.bat`
   (Windows — cria a tarefa "ProspectorPublicadorVPS"; erro de permissão =
   botão direito → Executar como administrador) ou no
   `instalar-publicador.command` (Mac — registra no launchd, label
   `com.prospector.publicadorvps`; se o macOS bloquear por segurança:
   botão direito → Abrir na primeira vez). Só uma vez na vida.
3. **Monte a fila**: escreva `fila-publicacao.txt` na raiz da pasta
   conectada, uma linha por arquivo: `caminho/local/arquivo.html|[pastaBase]/[slug]/index.html`
   (o caminho remoto aqui é relativo a `caminhoRemoto`). Inclua página
   (`index.html`) e capa
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
   realmente aponta pra VPS (DNS) e se o Traefik está de pé
   (`docker compose logs traefik` no servidor — renovação é automática,
   não precisa de comando manual). Link `http://` NUNCA vai para cliente.
3. Registre `urlNova` e `https_validado_em` no lead via o agente `carmem`
   (`atualizar_campos`, não é uma transição de estado —
   `docs/CRM.md` §3).

## Teste de conexão do /setup

Publique `teste.html` simples ("Funcionou!") em
`[caminhoRemoto]/[pastaBase]/teste/index.html` pelo Método 2; se
bloqueado, já deixe os scripts do Método 1 copiados na pasta, monte a fila
com o teste e peça os 2 cliques — assim o usuário aprende o fluxo logo no
setup.
