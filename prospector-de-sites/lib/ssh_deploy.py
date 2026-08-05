#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Publicação em VPS própria via SSH/SCP + verificação de HTTPS.

Sem dependências externas: stdlib (`subprocess`, `urllib`, `ssl`) + os
binários de sistema `ssh`/`scp` (OpenSSH, já presentes no sandbox e em
Linux/Mac; no Windows, ver `pscp.exe`/`plink.exe` na skill `deploy-vps`).
Ver docs/PLANO_IMPLEMENTACAO.md §8 (Fase 5) e docs/ARQUITETURA_TECNICA.md
§8.2 (integração SSH).

Usado pelo agente `diego` (Método 2 — "tentar publicar direto do
sandbox", análogo ao Método 2 de FTP silencioso de `deploy-hostgator`).
Se `ssh`/`scp` não estiverem disponíveis, ou a rede do sandbox bloquear,
o agente cai para o Método 1 (publicador automático local) ou o Método 3
(instrução copiável) da skill `deploy-vps` — esta função apenas tenta e
reporta sucesso/falha, nunca insiste.

Autenticação: prioriza chave SSH (`chave_ssh_path`, mais segura — RNF-03);
se só houver `senha`, usa `sshpass` (se instalado) passando a senha via
variável de ambiente `SSHPASS` (nunca via argumento de linha de comando,
que ficaria visível na lista de processos do sistema).

NOTA DE MANUTENÇÃO: sem cópia em skills/dashboard-leads/references/ — este
módulo é usado pelo agente `diego`/skill `deploy-vps`, não pelo
dashboard-server.py. Ver skills/deploy-vps/references/ssh_deploy.py.
"""
import shutil
import subprocess
import urllib.request
import ssl


def _binario_disponivel(nome):
    return shutil.which(nome) is not None


def _rodar(comando, senha=None, timeout=30):
    env = None
    if senha:
        import os
        env = dict(os.environ)
        env['SSHPASS'] = senha
        comando = ['sshpass', '-e'] + comando
    try:
        r = subprocess.run(comando, capture_output=True, text=True, timeout=timeout, env=env)
        return r.returncode == 0, (r.stdout + r.stderr).strip()
    except subprocess.TimeoutExpired:
        return False, 'timeout ao executar: %s' % ' '.join(comando[:2])
    except FileNotFoundError as e:
        return False, 'binário não encontrado: %s' % e


def garantir_diretorio_remoto(host, porta, usuario, caminho_remoto,
                               chave_ssh_path=None, senha=None, timeout=20):
    """Roda `mkdir -p caminho_remoto` no servidor via SSH. Idempotente —
    rodar de novo sobre um diretório já existente não é erro (RNF-05)."""
    if not _binario_disponivel('ssh'):
        return False, 'ssh não disponível neste ambiente'
    if senha and not _binario_disponivel('sshpass'):
        return False, 'sshpass não instalado (necessário para autenticação por senha)'
    comando = ['ssh', '-o', 'StrictHostKeyChecking=accept-new', '-p', str(porta)]
    if chave_ssh_path:
        comando += ['-i', chave_ssh_path]
    comando += ['%s@%s' % (usuario, host), 'mkdir -p %s' % caminho_remoto]
    return _rodar(comando, senha=senha, timeout=timeout)


def publicar_arquivo(caminho_local, host, porta, usuario, caminho_remoto,
                      chave_ssh_path=None, senha=None, timeout=30):
    """Copia `caminho_local` para `usuario@host:caminho_remoto` via scp.
    Sobrescreve se já existir (republicação idempotente — RNF-05). Retorna
    (ok, mensagem)."""
    if not _binario_disponivel('scp'):
        return False, 'scp não disponível neste ambiente'
    if senha and not _binario_disponivel('sshpass'):
        return False, 'sshpass não instalado (necessário para autenticação por senha)'
    comando = ['scp', '-o', 'StrictHostKeyChecking=accept-new', '-P', str(porta)]
    if chave_ssh_path:
        comando += ['-i', chave_ssh_path]
    comando += [caminho_local, '%s@%s:%s' % (usuario, host, caminho_remoto)]
    return _rodar(comando, senha=senha, timeout=timeout)


def verificar_https(url, timeout=15):
    """Confirma que `url` carrega com HTTPS válido (certificado confiável,
    resposta 2xx/3xx). Só usa stdlib — sem requests/urllib3. Retorna
    (ok, mensagem)."""
    if not url.startswith('https://'):
        return False, 'URL não começa com https://'
    contexto = ssl.create_default_context()
    try:
        with urllib.request.urlopen(url, timeout=timeout, context=contexto) as resp:
            if 200 <= resp.status < 400:
                return True, 'HTTPS válido, status %d' % resp.status
            return False, 'HTTPS válido, mas status inesperado %d' % resp.status
    except urllib.error.HTTPError as e:
        # Certificado válido (chegou a fazer o handshake TLS), mas resposta HTTP de erro.
        return False, 'certificado OK, mas HTTP %d' % e.code
    except ssl.SSLCertVerificationError as e:
        return False, 'certificado inválido/não confiável: %s' % e
    except Exception as e:
        return False, 'falha ao conectar: %s' % e
