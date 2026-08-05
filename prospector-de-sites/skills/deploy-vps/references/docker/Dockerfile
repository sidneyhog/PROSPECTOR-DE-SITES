# Imagem "prospector-sites" — serve as páginas publicadas pelo Prospector
# de Sites (/publicar) atrás do Traefik. Ver docs/RUNBOOK_VPS.md.
FROM nginx:1.27-alpine

LABEL org.opencontainers.image.title="prospector-sites"
LABEL org.opencontainers.image.description="Servidor estático dos sites de clientes publicados pelo Prospector de Sites, atrás do Traefik (proxy reverso + HTTPS automático)."

COPY nginx.conf /etc/nginx/conf.d/default.conf

HEALTHCHECK --interval=30s --timeout=3s --retries=3 \
  CMD wget -qO- http://localhost/ >/dev/null 2>&1 || exit 1
