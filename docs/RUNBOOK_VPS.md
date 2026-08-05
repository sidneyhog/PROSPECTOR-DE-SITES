# RUNBOOK_VPS.md — Passo a passo de hospedagem na VPS (Docker/Traefik/Portainer)

**Depende de:** `docs/PLANO_IMPLEMENTACAO.md` §8 (Fase 5), §12 (Fase 9,
conclusão) e §14 (Fase 10, containerização) e
`prospector-de-sites/skills/deploy-vps/SKILL.md`. Este documento não é uma
nova etapa de arquitetura — é um runbook operacional para o operador (e
para o próprio Claude, durante o `/setup`) configurar uma VPS nova do zero
e ligá-la ao plugin, sem depender de acesso real a um servidor a partir
deste ambiente de desenvolvimento.

Escrito pensando na VPS Hostinger do operador (disponível a partir de
05/08/2026), mas os passos servem para qualquer VPS Ubuntu/Debian com
acesso root via SSH (DigitalOcean, Contabo, etc.).

## 0. O que este runbook resolve

`skills/deploy-vps/` já sabe **publicar** páginas (via SSH/SCP) numa pasta
do host da VPS (§39-51 do `SKILL.md`) — isso não muda. O que este runbook
cobre é o que precisa existir **antes** do primeiro `/publicar`: provisionar
a VPS com uma pilha Docker (Traefik + Portainer + a imagem própria
`prospector-sites`) que serve essa pasta publicamente com HTTPS automático.
Nada disso pode ser feito por este ambiente sandboxed, que não tem acesso
de rede à VPS do operador — é o operador quem roda (com o Claude orientando
via chat, ou copiando os comandos para o próprio terminal SSH).

**Por que Docker/Traefik/Portainer em vez de nginx+certbot manual:**
decisão do operador (Fase 10) — Traefik emite e renova certificados
Let's Encrypt automaticamente por container (sem `certbot` manual por
domínio), e o Portainer dá uma interface visual para acompanhar/reiniciar
os containers sem decorar comandos `docker`. A publicação em si
(`/publicar`, SSH/SCP) **não muda em nada** — grava arquivos numa pasta do
host, que o container `prospector-sites` só serve.

## 1. Pré-requisitos do lado do operador

1. **VPS provisionada** (Hostinger ou outra), com Ubuntu 22.04+ ou Debian
   12+, IP público anotado.
2. **Domínio próprio** que o operador controla (registro.br ou outro
   registrador) — o domínio-base onde as páginas de todos os clientes vão
   morar em subpastas (`dominio.com/clientes/[slug]/`), conforme já
   modelado em `prospector-config.json.vps.dominio` + `pastaBase`. Um
   segundo subdomínio (ex. `portainer.dominio.com.br`) é recomendado para
   o painel do Portainer.
3. **Acesso root via SSH** à VPS (senha inicial do provedor, ou já com
   chave se o provedor permitir enviar uma na criação).

## 2. Instalar Docker (rodar uma vez, como root)

```bash
curl -fsSL https://get.docker.com | sh
```

Isso instala Docker Engine + Docker Compose plugin (`docker compose`,
sem hífen) numa tacada só — script oficial da Docker Inc., idempotente
(pode rodar de novo sem problema se já estiver instalado).

## 3. Criar usuário dedicado para o deploy

```bash
adduser --disabled-password --gecos "" prospector
usermod -aG docker prospector
```

Gerar (no computador do **operador**, não na VPS) um par de chaves SSH
dedicado ao plugin, e copiar a pública para a VPS:

```bash
# No computador do operador:
ssh-keygen -t ed25519 -f ~/.ssh/prospector_vps -N ""
ssh-copy-id -i ~/.ssh/prospector_vps.pub prospector@SEU_IP
```

(ou copiar manualmente o conteúdo de `prospector_vps.pub` para
`/home/prospector/.ssh/authorized_keys` na VPS).

## 4. DNS

No painel do registrador do domínio, criar registros **A** apontando para
o IP da VPS:

- `seudominio.com.br` (ou o subdomínio-base escolhido) → sites de clientes
- `portainer.seudominio.com.br` → painel do Portainer

Propagação pode levar de minutos a algumas horas — teste com
`dig +short seudominio.com.br` até aparecer o IP certo antes de seguir
para o passo do certificado (o Traefik só emite o certificado quando
o DNS já responde certo).

## 5. Copiar e configurar a pilha Docker

Os arquivos da pilha (`Dockerfile`, `nginx.conf`, `docker-compose.yml`,
`.env.example`) já foram entregues na pasta conectada pelo `/setup`, em
`skills/deploy-vps/references/docker/` — copie essa pasta inteira para a
VPS (SCP, a partir do computador do operador):

```bash
scp -r skills/deploy-vps/references/docker prospector@SEU_IP:/opt/prospector-stack
```

Na VPS, como o usuário `prospector`:

```bash
cd /opt/prospector-stack
cp .env.example .env
nano .env   # preencher DOMINIO, PORTAINER_DOMINIO, ACME_EMAIL, CAMINHO_SITES
mkdir -p "$(grep ^CAMINHO_SITES .env | cut -d= -f2)"
docker compose up -d
```

`CAMINHO_SITES` no `.env` **precisa ser exatamente igual** ao campo
`vps.caminhoRemoto` que vai no `prospector-config.json` (passo 7) — é essa
pasta que o `/publicar` grava via SSH/SCP e que o container
`prospector-sites` serve como raiz do site.

Confirme que os 3 containers subiram:

```bash
docker compose ps
```

O Traefik emite o certificado Let's Encrypt automaticamente no primeiro
acesso a cada domínio configurado nos `labels` — não precisa rodar
`certbot` nem nenhum comando manual. Acesse
`https://portainer.seudominio.com.br` na primeira vez para definir a
senha de administrador do Portainer (obrigatório nos primeiros minutos,
senão qualquer um que chegar primeiro vira admin).

**Importante:** essa configuração é feita **uma única vez** para o
domínio-base. Toda subpasta nova por cliente
(`CAMINHO_SITES/clientes/[slug]/`) já é servida com o mesmo certificado,
sem repetir nenhum passo deste runbook.

## 6. Alternativa sem Docker (reversibilidade)

Quem preferir não usar Docker pode montar a mesma coisa com nginx +
certbot tradicionais na VPS (`apt install nginx certbot
python3-certbot-nginx`, server block manual, `certbot --nginx -d
seudominio.com.br`) — a skill `deploy-vps` publica por SSH/SCP em
qualquer pasta que sirva HTTPS, com ou sem container. Essa opção existe
para quem já tem experiência com nginx bare-metal ou não quer rodar
Docker na VPS; o caminho recomendado e documentado em detalhe por este
runbook é o da seção 5.

## 7. Preencher o bloco `vps` no plugin

Rodar `/setup` no Claude Cowork (ou abrir o dashboard → aba
Configurações → Conexão VPS) e preencher:

| Campo | Valor |
|---|---|
| `host` | IP ou hostname da VPS |
| `porta` | `22` (padrão, a menos que tenha sido trocada) |
| `usuario` | `prospector` (criado no passo 3) |
| `caminhoRemoto` | o mesmo valor de `CAMINHO_SITES` no `.env` (passo 5) |
| `dominio` | `seudominio.com.br` |
| `pastaBase` | `clientes` (padrão) |
| `chaveSshPath` | caminho da chave privada gerada no passo 3 (`~/.ssh/prospector_vps`) — **preferir sempre chave a senha** |

O teste de conexão do `/setup` publica um `teste.html` simples e confirma
`https://seudominio.com.br/clientes/teste/` respondendo com HTTPS válido
(`skills/deploy-vps/SKILL.md` §"Teste de conexão do /setup").

## 8. Primeira publicação real

Depois do teste OK, `/publicar` já funciona normalmente para qualquer
lead em `pagina_revisada` — sem mais nenhuma configuração manual por
cliente (§39-51 do `SKILL.md` cobre os 3 métodos de publicação e a
verificação obrigatória de HTTPS). O container `prospector-sites` não
precisa ser reiniciado nem reconfigurado a cada novo cliente — ele serve
qualquer subpasta nova que apareça em `CAMINHO_SITES/clientes/`.

## 9. Troubleshooting rápido

- **`dig` não mostra o IP novo ainda**: aguardar propagação de DNS antes
  de subir a pilha (o Traefik valida o domínio via HTTP challenge,
  precisa do DNS já apontando certo).
- **Traefik não emite certificado / erro "acme: error"**: `docker compose
  logs traefik` para ver a razão exata; confirme que as portas 80/443 estão
  liberadas no firewall da VPS/painel da Hostinger
  (`ufw allow 80 && ufw allow 443`, se usar `ufw`).
- **`ssh` pede senha mesmo com chave configurada**: confirmar permissões
  (`chmod 700 ~/.ssh && chmod 600 ~/.ssh/authorized_keys` no usuário
  `prospector` da VPS) e que o caminho em `chaveSshPath` está correto e
  legível pelo processo que roda o publicador.
- **Portainer mostra tela de "não configurado" depois de dias**: alguém
  não definiu a senha a tempo (janela de poucos minutos após o primeiro
  start) — nesse caso, recrie o volume `portainer_data`
  (`docker compose down && docker volume rm docker_portainer_data &&
  docker compose up -d`) e defina a senha imediatamente no próximo acesso.
- **Container `prospector-sites` não reflete um site novo publicado**:
  confirme que `CAMINHO_SITES` no `.env` é *exatamente* o mesmo caminho de
  `vps.caminhoRemoto` no `prospector-config.json` — se divergirem, o
  `/publicar` grava num lugar e o container serve outro.
