# Como instalar o Senku

A skill é a pasta inteira. Python 3.8+ com a biblioteca padrão, sem nada para
instalar. Para abrir as saídas: navegador (SVG, HTML), Word (DOCX),
bpmn.io / Camunda Modeler / Bizagi (BPMN) e diagrams.net (draw.io).

Depois de instalar, para ver a versão e conferir que tudo responde:

```bash
python senku.py status
```

## No Claude Code

Para todos os projetos, clone (ou copie) a pasta para a pasta de skills do
usuário, com o nome `senku`:

```bash
git clone https://github.com/tiagocardosobezerra/senku.git ~/.claude/skills/senku
```

```powershell
git clone https://github.com/tiagocardosobezerra/senku.git $HOME\.claude\skills\senku
```

Só para um projeto, use `.claude/skills/senku` dentro dele. Para atualizar,
rode `git pull` na pasta da skill.

## No claude.ai

O claude.ai recebe a skill como `.zip`. Baixe o zip da última versão na
página de [Releases](https://github.com/tiagocardosobezerra/senku/releases),
ou gere o seu na raiz do repositório:

```bash
python ferramentas/empacotar.py
```

Ele cria `senku-skill-<versão>.zip` só com o que a skill usa: sem testes,
ferramentas, animações, saídas geradas nem aceites locais. Num clone git, só
entra arquivo rastreado, então um mapeamento real deixado na pasta nunca vai
junto. Suba o zip em **Configurações → Capacidades → Skills**.

## Conferir a instalação

```bash
python senku.py status
python -m unittest discover -s testes
python senku.py documentar exemplos/compras/carta.json -o <pasta temporária>
```

Os testes usam os exemplos fictícios e só escrevem em pasta temporária. A
suíte inteira leva uns quatro minutos.

## Onde ficam os mapeamentos

Fora da pasta da skill:

```bash
python senku.py novo C:/processos/<nome> --processo "<nome>"
```

Se for guardar dentro dela, use `local/`: fica fora do git e do zip. Cartas de
processos reais nunca vão para um repositório público (veja
[AVISO.md](AVISO.md)).

## Animações do README

Os SVGs de `assets/` saem de um gerador, a partir dos roteiros de
[`roteiros/`](roteiros/):

```bash
python ferramentas/animacoes.py
```

Mudou um número ou um nome que aparece no vídeo? Ajuste o roteiro e o
gerador juntos e gere de novo.
