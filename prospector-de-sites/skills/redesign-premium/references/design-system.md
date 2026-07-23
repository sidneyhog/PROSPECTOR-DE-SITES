# Gerador de sistema de design (ui-ux-pro-max)

Dependência opcional que resolve a variedade estética entre clientes: consulta uma base real de 161 paletas de cor, 57 pares de tipografia e 67 estilos (projeto open-source [ui-ux-pro-max](https://github.com/nextlevelbuilder/ui-ux-pro-max-skill), MIT) em vez de escolher sempre entre as mesmas opções fixas.

## Instalação (uma vez, feita pelo `/setup`)

Requer Python 3 (já é pré-requisito do dashboard). Na pasta conectada:

```
npx --yes ui-ux-pro-max-cli init --ai claude --offline
```

Isso cria `.claude/skills/ui-ux-pro-max/` na pasta conectada (script `scripts/search.py` + bases de dados em `data/*.csv`, ~2-3 MB). Não faz parte do repositório do plugin — é instalado localmente por usuário, como o Python do dashboard ou o `pscp.exe` do publicador.

**Atenção**: o instalador do `ui-ux-pro-max-cli` pode trazer junto outras skills do mesmo pacote (`design`, `brand`, `banner-design`, `design-system`, `slides`, `ui-styling`) que não têm relação com o Prospector. Elas são inofensivas (só ocupam espaço), mas se o usuário preferir remover, use a ferramenta de exclusão de arquivo do Cowork (arquivos na pasta conectada não podem ser apagados sem confirmação) e mantenha apenas `.claude/skills/ui-ux-pro-max/`.

## Uso no redesign

```
python3 .claude/skills/ui-ux-pro-max/scripts/search.py "<nicho e personalidade EM INGLÊS>" --design-system -p "<Nome do cliente>"
```

**A busca só funciona bem em inglês** — a base é indexada em inglês (BM25 sobre descrições em inglês). Query em português cai no resultado genérico de fallback (sempre Inter/Inter + azul #2563EB) — testado e confirmado. Traduza mentalmente o nicho + 2-3 palavras de personalidade antes de rodar. Exemplos já testados:

| Nicho (PT) | Query (EN) |
|---|---|
| Nutricionista esportiva, acolhedor | `"sports nutritionist warm welcoming"` |
| Psicólogo(a), calmo e confiável | `"psychologist calm trustworthy therapy"` |
| Advocacia, corporativo, confiável | `"corporate law firm trustworthy"` |
| Clínica odontológica premium | `"premium dental clinic"` |
| Salão de beleza, vibrante, jovem | `"beauty salon vibrant young"` |

Não precisa traduzir o nome do cliente (`-p`) nem mostrar a tradução ao usuário — é uso interno da consulta.

A saída traz: padrão de página (pattern), estilo (style), paleta de 10 cores semânticas (primary/secondary/accent/background/foreground/muted/border/destructive/ring), par de tipografia com link do Google Fonts, efeitos-chave e uma lista de "avoid" (anti-padrões pro nicho).

## Como aplicar o resultado (regras do Prospector continuam valendo)

- **Padrão de página (pattern)**: IGNORAR. O gerador sugere estruturas de SaaS/app ("Solutions by Industry", "Client Logos", "Contact Sales") que não fazem sentido pra um negócio local. A seção "Estrutura da página" deste `SKILL.md` é sempre quem manda na ordem e no conteúdo das seções.
- **Cor primária**: NUNCA usar a cor sugerida pelo gerador no lugar da cor de marca do cliente — regra inviolável 3 (identidade preservada) é mais forte que a sugestão do gerador. Usar a paleta sugerida como guia de **humor e contraste** (ex.: "paleta quente com acento dourado" → aplicar isso em cima da cor real do cliente), não como substituição.
- **Tipografia**: o par sugerido pode ser usado direto — é aí que está o ganho de variedade (evita cair sempre em Playfair+Inter). Carregar via Google Fonts, só 2 famílias, como já manda a regra de velocidade.
- **Stack**: o gerador foi pensado para vários frameworks; aqui a saída relevante é só paleta + tipografia + estilo + efeitos. Ignorar qualquer sugestão de componente/lib de framework (React, Tailwind etc.) — a página continua HTML+CSS puro, arquivo único, sem dependências.
- **Checklist de entrega do gerador** (emojis, cursor-pointer, contraste, reduced-motion) já está coberta pelas regras e pelo checklist final deste SKILL.md — não precisa duplicar.

## Se não estiver instalado

Sem `.claude/skills/ui-ux-pro-max/scripts/search.py` na pasta conectada, seguir o fallback manual de 5 direções descrito na seção "Direção estética" do `SKILL.md` principal.
