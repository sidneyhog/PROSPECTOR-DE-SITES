# Prospector de Sites — publicação automática em VPS própria (SSH/SCP via PuTTY)
# Manual: duplo clique no publicar-agora.bat (mostra janela)
# Automático: instalado pelo instalar-publicador.bat, roda a cada minuto escondido (-Auto)
param([switch]$Auto)
$ErrorActionPreference = "Stop"
$pasta = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $pasta
function Fim($code){ if(-not $Auto){ pause }; exit $code }
function Log($msg,$cor="Gray"){
  if($Auto){ Add-Content "publicador-log.txt" ("[" + (Get-Date -Format "dd/MM HH:mm:ss") + "] " + $msg) }
  else { Write-Host $msg -ForegroundColor $cor }
}
if (-not (Test-Path "fila-publicacao.txt")) { if(-not $Auto){ Log "Nada na fila - peca /publicar ao Claude primeiro." "Yellow" }; Fim 0 }
try { $cfg = Get-Content "prospector-config.json" -Raw -Encoding UTF8 | ConvertFrom-Json } catch { Log "ERRO: prospector-config.json nao encontrado/invalido." "Red"; Fim 1 }
$vps = $cfg.vps
$h = $vps.host; $porta = $(if ($vps.porta) { $vps.porta } else { 22 }); $u = $vps.usuario
$remotoBase = $vps.caminhoRemoto; $chave = $vps.chaveSshPath; $senha = $vps.senha
if (-not $h -or -not $u -or -not $remotoBase) { Log "ERRO: preencha a conexao VPS (dashboard > Configuracoes) - host, usuario e caminho remoto." "Red"; Fim 1 }
if (-not $chave -and -not $senha) { Log "ERRO: informe uma chave SSH (chaveSshPath) ou senha na conexao VPS." "Red"; Fim 1 }
if (-not (Get-Command pscp.exe -ErrorAction SilentlyContinue)) { Log "ERRO: pscp.exe nao encontrado nesta pasta/PATH." "Red"; Fim 1 }

function Args-Auth {
  if ($chave) { return @("-i", $chave) } else { return @("-pw", $senha) }
}

$fila = Get-Content "fila-publicacao.txt" -Encoding UTF8 | Where-Object { $_ -match "\|" }
$ok = 0; $falha = 0
foreach ($linha in $fila) {
  $par = $linha -split "\|", 2
  $local = $par[0].Trim(); $remotoRel = $par[1].Trim()
  if (-not (Test-Path $local)) { Log ("PULOU (nao existe): " + $local) "Yellow"; $falha++; continue }
  $remotoCompleto = "$remotoBase/$remotoRel"
  $remotoDir = ($remotoCompleto -replace '/[^/]*$', '')
  Log ("Garantindo diretorio remoto " + $remotoDir + " ...")
  & plink.exe -ssh -batch -P $porta (Args-Auth) "$u@$h" "mkdir -p $remotoDir" 2>$null
  Log ("Subindo " + $local + " -> " + $remotoCompleto + " ...")
  & pscp.exe -batch -P $porta (Args-Auth) "$local" "${u}@${h}:${remotoCompleto}"
  if ($LASTEXITCODE -eq 0) { Log "  OK" "Green"; $ok++ } else { Log ("  FALHOU (codigo " + $LASTEXITCODE + ")") "Red"; $falha++ }
}
Log ("Concluido: " + $ok + " enviados, " + $falha + " falhas.") "Cyan"
if ($falha -eq 0 -and $ok -gt 0) {
  Rename-Item "fila-publicacao.txt" ("fila-publicada-" + (Get-Date -Format "yyyyMMdd-HHmm") + ".txt") -Force
  Log "Fila concluida. Avise o Claude ('publiquei') para verificar as URLs." "Cyan"
}
Fim 0
