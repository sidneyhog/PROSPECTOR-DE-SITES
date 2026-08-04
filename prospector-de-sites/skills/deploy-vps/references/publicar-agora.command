#!/bin/bash
# Prospector de Sites — publica a fila na VPS própria via SSH/SCP (Mac).
# Manual: duplo clique. Automatico (launchd): chamado com --auto (log em publicador-log.txt, sem pause).
cd "$(dirname "$0")"
AUTO=0; [ "$1" = "--auto" ] && AUTO=1
log(){ if [ $AUTO -eq 1 ]; then echo "[$(date '+%d/%m %H:%M:%S')] $1" >> publicador-log.txt; else echo "$1"; fi; }
fim(){ [ $AUTO -eq 0 ] && read -p "Pressione Enter para fechar..."; exit $1; }
[ -f fila-publicacao.txt ] || { [ $AUTO -eq 0 ] && log "Nada na fila — peca /publicar ao Claude primeiro."; fim 0; }
CFG=prospector-config.json
[ -f $CFG ] || { log "ERRO: prospector-config.json nao encontrado."; fim 1; }
ler(){ python3 -c "import json;print(json.load(open('$CFG')).get('vps',{}).get('$1',''))"; }
H=$(ler host); PORTA=$(ler porta); [ -z "$PORTA" ] && PORTA=22
U=$(ler usuario); REMOTO_BASE=$(ler caminhoRemoto); CHAVE=$(ler chaveSshPath); SENHA=$(ler senha)
[ -n "$H" ] && [ -n "$U" ] && [ -n "$REMOTO_BASE" ] || { log "ERRO: preencha a conexao VPS no dashboard (Configuracoes) - host, usuario e caminho remoto."; fim 1; }
[ -n "$CHAVE" ] || [ -n "$SENHA" ] || { log "ERRO: informe uma chave SSH (chaveSshPath) ou senha na conexao VPS."; fim 1; }

SSH_OPTS=(-o StrictHostKeyChecking=accept-new -p "$PORTA")
SCP_OPTS=(-o StrictHostKeyChecking=accept-new -P "$PORTA")
if [ -n "$CHAVE" ]; then
  SSH_OPTS+=(-i "$CHAVE"); SCP_OPTS+=(-i "$CHAVE")
  ssh_run(){ ssh "${SSH_OPTS[@]}" "$U@$H" "$1"; }
  scp_run(){ scp "${SCP_OPTS[@]}" "$1" "$U@$H:$2"; }
else
  command -v sshpass >/dev/null || { log "ERRO: sshpass nao instalado (brew install sshpass) - necessario para autenticacao por senha."; fim 1; }
  ssh_run(){ SSHPASS="$SENHA" sshpass -e ssh "${SSH_OPTS[@]}" "$U@$H" "$1"; }
  scp_run(){ SSHPASS="$SENHA" sshpass -e scp "${SCP_OPTS[@]}" "$1" "$U@$H:$2"; }
fi

OK=0; FALHA=0
while IFS='|' read -r LOCAL REMOTO_REL; do
  LOCAL=$(echo "$LOCAL" | xargs); REMOTO_REL=$(echo "$REMOTO_REL" | xargs)
  [ -z "$LOCAL" ] && continue
  if [ ! -f "$LOCAL" ]; then log "PULOU (nao existe): $LOCAL"; FALHA=$((FALHA+1)); continue; fi
  REMOTO="$REMOTO_BASE/$REMOTO_REL"
  REMOTO_DIR=$(dirname "$REMOTO")
  log "Garantindo diretorio remoto $REMOTO_DIR ..."
  ssh_run "mkdir -p '$REMOTO_DIR'" >/dev/null 2>&1
  log "Subindo $LOCAL -> $REMOTO ..."
  if scp_run "$LOCAL" "$REMOTO"; then
    log "  OK"; OK=$((OK+1))
  else
    log "  FALHOU"; FALHA=$((FALHA+1))
  fi
done < fila-publicacao.txt
log "Concluido: $OK enviados, $FALHA falhas."
if [ $FALHA -eq 0 ] && [ $OK -gt 0 ]; then
  mv fila-publicacao.txt "fila-publicada-$(date '+%Y%m%d-%H%M').txt"
  log "Fila concluida. Avise o Claude ('publiquei') para verificar as URLs."
fi
fim 0
