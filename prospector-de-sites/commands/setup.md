---
description: Configura o plugin — assinatura, preferências e conexão com a VPS própria (roda uma vez)
---

Configure o ambiente do Prospector de Sites. Siga esta ordem:

## 1. Pasta de trabalho

Verifique se há uma pasta do usuário conectada. Se não houver, peça para conectar uma pasta (ex.: "Clientes") usando a ferramenta de solicitação de pasta — tudo (config, leads e sites criados) será salvo nela para persistir entre sessões.

## 2. Verificar config existente

Procure `prospector-config.json` na pasta conectada. Se existir, mostre um resumo (sem exibir a senha) e pergunte o que o usuário quer atualizar. Se não existir, colete os dados abaixo.

## 3. Dados do usuário (perguntar via AskUserQuestion / formulário)

Colete:

- **Assinatura da proposta**: nome completo, como quer se apresentar (ex.: "Designer de páginas de alta conversão") e WhatsApp/telefone de contato (é o número que envia as propostas e aparece nas páginas).
- **Nichos padrão de prospecção**: sugira nutricionistas, psicólogos, advogados e psiquiatras como ponto de partida, mas deixe o usuário editar livremente.
- **Cidade/região padrão**.
- **Leads qualificados por busca**: padrão 10.

## 4. Conexão com a VPS própria

Pergunte se o usuário já tem uma VPS contratada (qualquer provedor: Hetzner, DigitalOcean, Contabo etc.) com nginx (ou outro servidor web) já instalado.

- **Se ainda não tem**: explique brevemente que precisa de (1) uma VPS com IP público, (2) nginx (ou apache) instalado e configurado com um diretório raiz para os sites, e (3) um domínio próprio que possa apontar pra ela. Depois de ter isso, deve voltar e rodar `/setup` de novo. Salve o config parcial e encerre.
- **Se já tem**: NÃO colete nenhum dado da VPS pelo chat (nem host, nem usuário — e JAMAIS a senha). Tudo vai num lugar só, a aba Configurações do dashboard:
  1. Instrua: abra o dashboard (`iniciar-dashboard.bat` na pasta conectada) → aba **Configurações** → seção **Conexão VPS**.
  2. Lá ele preenche os campos + senha: host/IP, porta SSH (padrão 22), usuário, caminho remoto (raiz do site no nginx, ex.: `/var/www/html`), domínio, pasta base e a senha SSH. Clica em "Salvar conexão" → tudo vai do navegador direto pro `prospector-config.json` no computador dele, sem passar pelo chat.
  3. Peça para ele avisar quando salvar ("salvei") — aí você LÊ o config (verificando que os campos estão preenchidos, sem nunca exibir a senha) e roda o teste de conexão.

  Nunca exiba, imprima ou registre a senha em nenhuma saída. Se ele preferir, editar o `prospector-config.json` na mão também vale.

  Se o **domínio ainda não aponta pra VPS** (DNS), oriente a seção "Domínio e HTTPS" da skill `deploy-vps` antes de seguir para o teste de conexão.

## 5. Salvar e testar

Salve tudo em `prospector-config.json` na pasta conectada, neste formato:

```json
{
  "assinatura": { "nome": "", "apresentacao": "", "whatsapp": "" },
  "prospeccao": { "nichos": ["nutricionistas", "psicologos", "advogados", "psiquiatras"], "cidade": "", "leadsPorBusca": 10 },
  "vps": { "host": "", "porta": 22, "usuario": "", "senha": "", "caminhoRemoto": "/var/www/html", "dominio": "", "pastaBase": "clientes" }
}
```

Se os dados da VPS foram informados, teste a conexão seguindo a skill `deploy-vps`: publique uma página `teste.html` simples e informe a URL pública ao usuário. Se o teste falhar, diagnostique (credenciais, host/porta, firewall, caminho remoto) antes de concluir.

## 6. Dashboard inicial

Siga a seção "Setup" da skill `dashboard-leads`: copie `dashboard-server.py` e `iniciar-dashboard.bat` para a raiz da pasta conectada, crie o banco `prospector.db` (schema da skill) e gere o `dashboard.html` do template. Explique ao usuário: duplo clique em `iniciar-dashboard.bat` abre o painel completo em http://localhost:8765 com edição/exclusão salvando no banco (requer Python no Windows; sem ele, o dashboard.html abre no modo leitura).

## 7B. Entregar o manual e os scripts

Copie da pasta do plugin para a pasta conectada (sobrescrevendo versões antigas): `manual.html` (manual do usuário) e os arquivos do publicador conforme o sistema do usuário (skill `deploy-vps`, references) — Windows: `publicar-agora.ps1/.bat`, `publicador-oculto.vbs`, `instalar-publicador.bat` (mais `pscp.exe`/`plink.exe`, baixados uma vez) · Mac: `publicar-agora.command`, `instalar-publicador.command` (mais `sshpass` via `brew install sshpass`) — mais o iniciador do dashboard certo (`iniciar-dashboard.bat` ou `.command`). Peça UM duplo clique no instalador do publicador (registra o publicador automático — única vez na vida; o teste de conexão do item 5 pode usar esse fluxo). Apresente o `manual.html` ao usuário com a frase: "Esse é o seu manual — guarda ele que responde 90% das dúvidas."

## 7C. Gerador de variedade estética (ui-ux-pro-max)

Verifique se `.claude/skills/ui-ux-pro-max/scripts/search.py` já existe na pasta conectada. Se não existir, rode uma vez (requer Python 3, já verificado no item 6):

```
npx --yes ui-ux-pro-max-cli init --ai claude --offline
```

Isso instala localmente o gerador de sistemas de design (base aberta de paletas/tipografia) usado pela skill `redesign-premium` para não repetir a mesma estética em clientes seguidos — ver `redesign-premium/references/design-system.md`. Avise o usuário que esse instalador pode trazer junto outras skills do mesmo pacote sem relação com o Prospector (`design`, `brand`, `banner-design`, `design-system`, `slides`, `ui-styling`); são inofensivas, mas podem ser removidas depois se ele preferir (pedindo confirmação, já que arquivos na pasta conectada não se apagam sem aviso).

## 7. Encerrar

Confirme o que foi salvo e explique o ciclo (guiando SEMPRE o próximo passo ao fim de cada comando): `/prospectar` → `/redesenhar` → `/publicar` → `/proposta` (pelo WhatsApp), com `/editor` opcional para ajustes manuais e o `dashboard.html` como painel de controle de tudo.
