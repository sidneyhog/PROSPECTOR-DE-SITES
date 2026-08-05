# RUNBOOK_VPS.md — Passo a passo de hospedagem na VPS

**Depende de:** `docs/PLANO_IMPLEMENTACAO.md` §8 (Fase 5) e §12 (Fase 9,
conclusão) e `prospector-de-sites/skills/deploy-vps/SKILL.md`. Este
documento não é uma nova etapa de arquitetura — é um runbook operacional
para o operador (e para o próprio Claude, durante o `/setup`) configurar
uma VPS nova do zero e ligá-la ao plugin, sem depender de acesso real a um
servidor a partir deste ambiente de desenvolvimento.

Escrito pensando na VPS Hostinger do operador (ficará disponível em
05/08/2026), mas os passos servem para qualquer VPS Ubuntu/Debian com
acesso root via SSH (DigitalOcean, Contabo, etc.).

## 0. O que este runbook resolve

`skills/deploy-vps/` já sabe **publicar** páginas numa VPS que já tem
nginx + domínio + HTTPS configurados (§39-51 do `SKILL.md`). O que falta —
e não pode ser feito por este ambiente sandboxed, que não tem acesso de
rede à VPS do operador — é a **configuração inicial de servidor**: criar o
usuário, instalar nginx, apontar DNS, emitir o certificado. Este runbook
é esse passo a passo, para o operador rodar uma vez (com o Claude
orientando via chat, ou copiando os comandos para o próprio terminal SSH).

## 1. Pré-requisitos do lado do operador

1. **VPS provisionada** (Hostinger ou outra), com Ubuntu 22.04+ ou Debian
   12+, IP público anotado.
2. **Domínio próprio** que o operador controla (registro.br ou outro
   registrador) — não precisa ser o domínio final de cada cliente, mas o
   domínio-base onde as páginas de todos os clientes vão morar em
   subpastas (`dominio.com/clientes/[slug]/`), conforme já modelado em
   `prospector-config.json.vps.dominio` + `pastaBase`.
3. **Acesso root via SSH** à VPS (senha inicial do provedor, ou já com
   chave se o provedor permitir enviar uma na criação).

## 2. Configuração única do servidor (rodar uma vez, como root)

```bash
# 2.1 — Atualizar e instalar nginx + certbot
apt update && apt upgrade -y
apt install -y nginx certbot python3-certbot-nginx

# 2.2 — Criar usuário dedicado para o deploy (evitar usar root direto)
adduser --disabled-password --gecos "" prospector
usermod -aG www-data prospector

# 2.3 — Gerar (no computador do OPERADOR, não na VPS) um par de chaves SSH
#       dedicado ao plugin, e copiar a pública para a VPS:
#   No computador do operador: ssh-keygen -t ed25519 -f ~/.ssh/prospector_vps -N ""
#   Depois: ssh-copy-id -i ~/.ssh/prospector_vps.pub prospector@SEU_IP
#   (ou copiar manualmente o conteúdo de prospector_vps.pub para
#   /home/prospector/.ssh/authorized_keys na VPS)

# 2.4 — Raiz do site: pasta que o nginx vai servir
mkdir -p /var/www/prospector
chown -R prospector:www-data /var/www/prospector
```

## 3. DNS

No painel do registrador do domínio, criar um registro **A** apontando o
domínio (ou subdomínio, ex. `sites.seudominio.com.br`) para o IP da VPS.
Propagação pode levar de minutos a algumas horas — teste com
`dig +short seudominio.com.br` até aparecer o IP certo antes de seguir
para o certificado.

## 4. Server block do nginx (uma vez por domínio-base, não por cliente)

```nginx
# /etc/nginx/sites-available/prospector
server {
    listen 80;
    server_name seudominio.com.br;
    root /var/www/prospector;
    index index.html;
    location / {
        try_files $uri $uri/ =404;
    }
}
```

```bash
ln -s /etc/nginx/sites-available/prospector /etc/nginx/sites-enabled/
nginx -t && systemctl reload nginx
```

## 5. Certificado HTTPS (Let's Encrypt, uma vez por domínio-base)

```bash
certbot --nginx -d seudominio.com.br --non-interactive --agree-tos -m seu@email.com
```

Isso já reescreve o server block para redirecionar HTTP→HTTPS e configura
a renovação automática (`certbot renew` via systemd timer, já instalado
junto do pacote). Confirme com:

```bash
certbot renew --dry-run
```

**Importante (RNF já documentado em `deploy-vps/SKILL.md`):** essa
configuração é feita **uma única vez** para o domínio-base. Toda subpasta
nova por cliente (`/var/www/prospector/clientes/[slug]/`) já é servida com
o mesmo certificado, sem repetir este passo.

## 6. Preencher o bloco `vps` no plugin

Rodar `/setup` no Claude Cowork (ou abrir o dashboard → aba
Configurações → Conexão VPS) e preencher:

| Campo | Valor |
|---|---|
| `host` | IP ou hostname da VPS |
| `porta` | `22` (padrão, a menos que tenha sido trocada) |
| `usuario` | `prospector` (criado no passo 2.2) |
| `caminhoRemoto` | `/var/www/prospector` |
| `dominio` | `seudominio.com.br` |
| `pastaBase` | `clientes` (padrão) |
| `chaveSshPath` | caminho da chave privada gerada no passo 2.3 (`~/.ssh/prospector_vps`) — **preferir sempre chave a senha** |

O teste de conexão do `/setup` publica um `teste.html` simples e confirma
`https://seudominio.com.br/clientes/teste/` respondendo com HTTPS válido
(`skills/deploy-vps/SKILL.md` §"Teste de conexão do /setup").

## 7. Primeira publicação real

Depois do teste OK, `/publicar` já funciona normalmente para qualquer
lead em `pagina_revisada` — sem mais nenhuma configuração manual por
cliente (§39-51 do `SKILL.md` cobre os 3 métodos de publicação e a
verificação obrigatória de HTTPS).

## 8. Troubleshooting rápido

- **`dig` não mostra o IP novo ainda**: aguardar propagação de DNS antes
  de rodar o certbot (ele valida o domínio via HTTP, precisa do DNS já
  apontando certo).
- **Certbot falha com "Connection refused"**: `ufw allow 'Nginx Full'`
  (ou liberar as portas 80/443 no firewall da VPS/painel da Hostinger).
- **`ssh` pede senha mesmo com chave configurada**: confirmar permissões
  (`chmod 700 ~/.ssh && chmod 600 ~/.ssh/authorized_keys` no usuário
  `prospector` da VPS) e que o caminho em `chaveSshPath` está correto e
  legível pelo processo que roda o publicador.
- **Erro de certificado depois de meses**: `certbot renew --dry-run` na
  VPS para confirmar que a renovação automática está funcionando; se não
  estiver, `systemctl status certbot.timer`.
