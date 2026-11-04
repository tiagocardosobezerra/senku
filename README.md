# Senku

**Português** | [English](README.en.md)

**Conte o processo em português. Receba o fluxograma em raias e o mapeamento completo, conferidos e prontos para o dono aprovar.**

![Python 3.8+](https://img.shields.io/badge/python-3.8%2B-3776AB?style=flat-square&logo=python&logoColor=white)
![Sem dependências](https://img.shields.io/badge/depend%C3%AAncias-nenhuma-2ea44f?style=flat-square)
![BPMN 2.0](https://img.shields.io/badge/BPMN-2.0-A3E635?style=flat-square)
[![Testes](https://github.com/tiagocardosobezerra/senku/actions/workflows/testes.yml/badge.svg)](https://github.com/tiagocardosobezerra/senku/actions/workflows/testes.yml)
![MIT](https://img.shields.io/badge/licen%C3%A7a-MIT-blue?style=flat-square)

<img width="100%" alt="Senku: da conversa ao fluxograma e ao mapeamento do processo, com prova" src="assets/senku-banner.svg" />

O Senku é uma skill do Claude para quem mapeia processos de negócio: analistas de processos, escritórios de BPM, qualidade, auditoria e quem precisa documentar "como o trabalho anda" de verdade. Você conta o processo do seu jeito (conversa, áudio transcrito, procedimento colado, planilha ou um `.bpmn` que já existe). O Senku conduz a entrevista, escreve a **carta do processo**, pergunta o que falta, **prova** que o fluxo se sustenta e entrega o fluxograma e o mapeamento. Tudo sai de um arquivo só, nada é desenhado à mão.

## O que ele faz por você

* **Conduz a entrevista.** Sete blocos de perguntas (abertura, SIPOC, passos, decisões, tempos, gestão, TO-BE), na ordem em que um bom analista pergunta. Ele não espera o relato perfeito: pergunta o que falta.
* **Nunca inventa o processo.** Passo, responsável, sistema, regra, tempo e percentual vêm de você. O que ele deduz vira pergunta. O que ninguém respondeu vira **lacuna**, com prioridade, e o documento sai marcado como rascunho.
* **Prova que o fluxo termina.** Fichas (tokens) percorrem todos os caminhos: decisão sem saída, paralelo que nunca se junta, laço sem fim e atividade que não chega a lugar nenhum aparecem antes do desenho. São 73 verificações, das regras 7PMG ao estilo do *BPMN Method and Style*.
* **Mede com simulação, não com chute.** Simula 4.000 casos com os tempos e percentuais da entrevista e entrega o lead time típico, o prazo em que 80% e 90% dos casos terminam, a eficiência do ciclo, as passagens de bastão, o retrabalho e a carga de cada área.
* **Desenha o fluxograma em raias.** SVG, PNG, **BPMN 2.0** (abre no Bizagi, bpmn.io, Camunda, ARIS e Signavio), **draw.io** (edita e exporta para o Visio) e Mermaid. Cliente e fornecedor podem sair em pool próprio, com mensagens.
* **Escreve o mapeamento completo.** Ficha, escopo, SIPOC, descrição das atividades, regras de negócio, matriz RACI, indicadores, tempos, valor agregado, dores, riscos e controles, oportunidades Lean priorizadas e glossário, em HTML, Word, Markdown e uma planilha CSV das atividades.
* **Pede o aceite do dono e guarda.** O `aprovar` registra quem aprovou, quando e um hash por seção. Mudou depois? O `situacao` avisa e o `comparar` mostra o que mudou, campo por campo.
* **Redesenha com base.** O TO-BE nasce da carta aprovada e é comparado com o AS-IS, atividade por atividade.
* **Guarda o processo aprovado no Memory Card.** Como o cartão de memória de um videogame: depois do aceite, cada processo vira um save no seu repositório privado do GitHub (o mesmo cartão do Vegapunk), com o fluxograma, o mapeamento, a carta, a versão e o motivo de cada mudança. Antes de mapear um processo novo, ele procura no cartão se já existe.
* **Traz o que você já tem.** Importa `.bpmn` do Bizagi, bpmn.io, Camunda, ARIS e Signavio. Exportou, editou no modelador e trouxe de volta? As suas edições valem, e o que o BPMN não guarda volta da carta.

## Como fica na prática

> **Você:** quero mapear o processo de compras. O pedido chega por e-mail, o comprador cota com três fornecedores e, acima de R$ 5 mil, o gerente aprova.
>
> **Claude (com o Senku):** cria a carta, desenha o primeiro rascunho e pergunta só o que muda o mapa: "Quem aprova quando o gerente está de férias?", "Quanto tempo o pedido espera antes da cotação?". Com as respostas, valida, analisa e mostra o fluxograma e o mapeamento: "Posso registrar o aceite do Gerente de Suprimentos?"
>
> **Dono do processo:** aprovo.
>
> **Claude:** registra o aceite e aponta as três maiores oportunidades: "a espera de 3 dias antes da cotação é o maior desperdício; quer redesenhar o TO-BE a partir daqui?"

Nada de "acho que o gerente aprova depois". Se não veio de você, entra como pergunta, não como passo.

## Veja o que ele entrega

Tudo abaixo saiu de **um comando**, sem nenhum retoque à mão:

```bash
python3 senku.py documentar exemplos/compras/carta.json
```

O exemplo é um processo fictício, mas completo: **SUP-01 · Compra de materiais indiretos**, com 6 áreas, 14 atividades, 2 decisões, retrabalho, um fornecedor externo e trabalho em paralelo. O relato que deu origem a ele cabe num parágrafo:

> A área que precisa de material abre a requisição no ERP. O gestor analisa e, se faltar centro de custo, devolve para correção. O comprador cota com os fornecedores, escolhe, lança a cotação no ERP e emite o pedido. O fornecedor entrega o material com a nota. O almoxarifado confere (e devolve o que não está conforme) e entrega ao solicitante, enquanto o fiscal lança a nota.

### O fluxograma em raias

<a href="exemplos/compras/saida/sup-01-compra-de-materiais-indiretos-as-is.svg"><img width="100%" alt="Fluxograma em raias do processo SUP-01, gerado pelo Senku" src="exemplos/compras/saida/sup-01-compra-de-materiais-indiretos-as-is.svg" /></a>

Abra o mesmo fluxo no seu modelador: [`.bpmn`](exemplos/compras/saida/sup-01-compra-de-materiais-indiretos-as-is.bpmn) (Bizagi, bpmn.io, Camunda, ARIS, Signavio) · [`.drawio`](exemplos/compras/saida/sup-01-compra-de-materiais-indiretos-as-is.drawio) (diagrams.net e Visio) · [`.mmd`](exemplos/compras/saida/sup-01-compra-de-materiais-indiretos-as-is.mmd) (Mermaid).

### O mapeamento do processo

<table>
<tr>
<td width="50%"><a href="assets/vitrine/mapa-ficha.png"><img alt="Ficha do processo" src="assets/vitrine/mapa-ficha.png" /></a><br /><sub><b>Ficha do processo</b>: objetivo, dono, gatilho, volume, prazo e as 12 seções.</sub></td>
<td width="50%"><a href="assets/vitrine/mapa-analise.png"><img alt="Análise do processo" src="assets/vitrine/mapa-analise.png" /></a><br /><sub><b>Análise</b>: lead time, prazo de 50%, 80% e 90% dos casos (simulação), eficiência do ciclo, passagens de bastão e carga de cada área.</sub></td>
</tr>
<tr>
<td width="50%"><a href="assets/vitrine/mapa-oportunidades.png"><img alt="Oportunidades Lean" src="assets/vitrine/mapa-oportunidades.png" /></a><br /><sub><b>Oportunidades Lean</b>: os desperdícios que o mapa mostra, do maior para o menor.</sub></td>
<td width="50%"><a href="assets/vitrine/mapa-riscos.png"><img alt="Dores, melhorias e riscos" src="assets/vitrine/mapa-riscos.png" /></a><br /><sub><b>Dores, plano de ação e riscos</b>: cada dor com a melhoria que a resolve e cada risco com o seu controle.</sub></td>
</tr>
</table>

O documento inteiro: [Markdown](exemplos/compras/saida/sup-01-compra-de-materiais-indiretos-as-is.md) (abre direto no GitHub) · [Word](exemplos/compras/saida/sup-01-compra-de-materiais-indiretos-as-is.docx) · [HTML](exemplos/compras/saida/sup-01-compra-de-materiais-indiretos-as-is.html) (baixe e abra no navegador para imprimir em PDF) · [planilha das atividades](exemplos/compras/saida/sup-01-compra-de-materiais-indiretos-as-is-atividades.csv).

## Resultados

Medidos na versão 1.14.0, com os exemplos do repositório (um processo de compras e um de crédito, fictícios).

| O quê | Resultado |
|---|---|
| Testes automatizados | **213 passando** |
| Verificações de boa modelagem (7PMG, BPMN Method and Style, tempos, RACI, prazos) | **73** |
| Casos simulados a cada análise | **4.000** |
| Formatos de saída (SVG, PNG, BPMN 2.0, draw.io, Mermaid, HTML, Word, Markdown, CSV) | **9** |
| Modeladores de onde o `.bpmn` pode vir | **5** (Bizagi, bpmn.io, Camunda 7 e 8, ARIS, Signavio) |
| Ida e volta BPMN (exportar, abrir, importar) sem mudar o fluxo | **sim**, conferido nos testes |
| Dependências para instalar | **0** |

## Comece em 3 passos

Você precisa de Python 3.8+ (só a biblioteca padrão, nada para instalar). Os comandos rodam **da pasta da skill**; no Windows, use `python` (ou `py`) no lugar de `python3`, se for o seu caso.

### 1. Instale

Para todos os projetos:

```bash
git clone https://github.com/tiagocardosobezerra/senku.git ~/.claude/skills/senku
```

```powershell
git clone https://github.com/tiagocardosobezerra/senku.git $HOME\.claude\skills\senku
```

Só para o projeto atual, troque o destino por `.claude/skills/senku`.

### 2. Conte o processo

Peça ao Claude: "quero mapear o processo de reembolso de despesas". Ele cria a pasta do processo, conduz a entrevista e preenche a carta. Prefere ver o roteiro antes?

```bash
python3 senku.py
python3 senku.py novo C:/processos/reembolso --processo "Reembolso de despesas"
```

### 3. Confira, desenhe e aprove

```bash
python3 senku.py lacunas C:/processos/reembolso/carta.json
python3 senku.py validar C:/processos/reembolso/carta.json
python3 senku.py documentar C:/processos/reembolso/carta.json
python3 senku.py aprovar C:/processos/reembolso/carta.json --por "Gerente Financeiro"
```

Perdeu o fio? `python3 senku.py situacao <carta>` diz em que etapa você está e qual é o próximo passo.

## Para ir além

### Os comandos

| Comando | O que faz |
|---|---|
| `novo` | cria a pasta do processo com a carta vazia e o roteiro |
| `entrevista [bloco]` | o roteiro de perguntas: abertura, sipoc, passos, decisoes, tempos, gestao, tobe |
| `lacunas` | o que falta perguntar, da prioridade mais alta para a mais baixa |
| `validar` | as 73 verificações e a prova de fichas |
| `analisar` | tempos, simulação, carga, valor agregado, passagens e oportunidades Lean |
| `desenhar [--pools]` | o fluxograma: SVG, PNG, BPMN 2.0, draw.io e Mermaid |
| `documentar` | o mapeamento completo: HTML, Word, Markdown e CSV, mais os desenhos |
| `aprovar --por "Nome"` | o aceite do dono do processo, com hash por seção |
| `situacao` | onde a carta está e o que mudou depois do aceite |
| `comparar [--contra]` | o que mudou desde o aceite, ou AS-IS x TO-BE |
| `tobe` | começa o TO-BE a partir da carta aprovada |
| `importar ARQ.bpmn [--base carta.json]` | traz um mapa que já existe, ou a volta de um mapa editado no modelador |
| `cartao buscar \| enviar \| catalogo \| marcar` | o Memory Card: procura antes de mapear, salva depois do aceite |

### O que é gerado

Numa pasta `saida/` ao lado da carta, com o código e o nome do processo no nome de cada arquivo:

| Arquivo | Para quê |
|---|---|
| `.svg` / `.png` | o fluxograma em raias, para ver e colar em apresentação |
| `.bpmn` | BPMN 2.0 com diagrama, para abrir e editar no Bizagi, bpmn.io, Camunda, ARIS ou Signavio |
| `.drawio` | para editar no diagrams.net e exportar para o Visio |
| `.mmd` | Mermaid, para colar em wiki e Markdown |
| `.html` | o mapeamento completo, pronto para imprimir em PDF |
| `.docx` | o mapeamento no Word, com sumário, retrato e paisagem por seção e quadro de aceite |
| `.md` | o mapeamento em Markdown |
| `-atividades.csv` | a planilha das atividades, para o Excel |

### Memory Card: seus processos salvos

Processo aprovado não precisa se perder numa pasta. O Memory Card salva cada um num repositório **seu** no GitHub (privado por padrão), o mesmo cartão do [Vegapunk](https://github.com/tiagocardosobezerra/vegapunk): os relatórios dele em `saves/vegapunk/`, os processos do Senku em `saves/senku/<área>/<macroprocesso>/<processo>/`.

```bash
gh auth login                                                  # uma vez
python3 senku.py cartao iniciar --repo SEU_USUARIO/memory-card  # liga ao cartão (ou cria um privado)
```

Depois do aceite, o Claude oferece salvar: mostra a prévia (o artigo com o fluxograma e os números, a ficha, os arquivos, o diff de uma versão nova) e só envia com o seu "sim". Cada save leva a carta aprovada, o aceite, o `.bpmn`, o `.drawio`, o Word, o HTML e o Markdown, e o AS-IS e o TO-BE do mesmo processo ficam ligados. Antes de mapear um processo novo, ele procura no cartão se alguém já mapeou. Guia completo em [`referencias/memory-card.md`](referencias/memory-card.md).

### De onde vêm as regras

* *Seven Process Modeling Guidelines (7PMG)*, de Mendling, Reijers e van der Aalst (2010).
* *BPMN Method and Style*, de Bruce Silver: as regras de estilo do desenho.
* BPM CBOK (ABPMP), SIPOC, RACI e os oito desperdícios do Lean.

As fontes e o motivo de cada verificação estão em [`referencias/`](referencias/).

## Como funciona por dentro

<img width="100%" alt="Como o Senku funciona: entrevista, carta, prova, desenho, mapeamento e aceite" src="assets/senku-fluxo.svg" />

| Peça | O que faz |
|---|---|
| **Entrevista** | o roteiro de perguntas, bloco a bloco (`carta/entrevista.py`) |
| **Carta** | o `carta.json`: o processo inteiro num arquivo só, fonte de tudo (`carta/modelo.py`) |
| **Lacunas** | o que falta perguntar, por prioridade (`carta/lacunas.py`) |
| **Validação** | as 73 verificações de boa modelagem (`carta/validacao.py`) |
| **Fichas** | a prova: tokens por todos os caminhos, atrás de travamento e caminho sem fim (`carta/fichas.py`) |
| **Simulação** | 4.000 casos com os tempos e percentuais da entrevista (`carta/simulacao.py`) |
| **Análise** | lead time, percentis, carga, valor agregado e oportunidades Lean (`carta/analise.py`) |
| **Layout** | posiciona raias, atividades e setas sem cruzar caixas (`carta/layout.py`) |
| **Saídas** | SVG, PNG, BPMN, draw.io, Mermaid, HTML, Word e Markdown (`saidas/`) |
| **Aceite** | o "sim" do dono, o hash por seção e a comparação de versões (`carta/aprovacao.py`) |
| **Importar** | traz `.bpmn` de outros modeladores e a volta de um mapa editado (`carta/importar.py`) |
| **Memory Card** | salva, versiona e procura os processos aprovados no cartão do usuário (`carta/memory_card.py`) |

Para conferir a instalação a qualquer momento:

```bash
python3 senku.py status
python3 -m unittest discover -s testes
```

## Estrutura do repositório

```
senku/
├── SKILL.md               # O que o Claude lê: regras, fluxo e como conduzir a entrevista
├── README.md              # Este arquivo
├── README.en.md           # README em inglês
├── COMO-INSTALAR.md       # Instalação, conferência e atualização
├── AVISO.md               # Dados de processo, privacidade e marcas
├── LICENCAS-DE-TERCEIROS.md  # Fontes das animações (OFL) e projetos que inspiraram o desenho
├── LICENSE                # MIT License
├── senku.py               # Porta de entrada: todos os comandos
├── carta/                 # O motor: carta, entrevista, lacunas, validação, fichas, simulação, análise, layout, aceite, importação, Memory Card
├── saidas/                # Os geradores: SVG, PNG, BPMN, draw.io, Mermaid, HTML, Word e Markdown
├── referencias/           # Guias: carta, entrevista, notação, estilo, análise, documento e Memory Card
├── exemplos/              # Processos fictícios completos, com tudo o que o Senku gera: compras (SUP-01) e crédito
├── roteiros/              # Roteiros das animações do README
├── ferramentas/           # Empacotador da skill, gerador das animações, fuzz e testes de estresse
├── assets/                # Animações e vitrine do README
└── testes/                # Suíte de testes e casos de regressão
```

## Créditos

**Criador:** Tiago Cardoso Bezerra | [tiagocardosobezerra](https://github.com/tiagocardosobezerra)

Batizado em homenagem a Senku, o cientista de Dr. Stone que reconstrói a civilização do zero com método: observa, registra, testa e só então afirma. Aqui, a observação é a entrevista, o registro é a carta, o teste é a prova de fichas e a simulação, e a afirmação é o mapa aprovado.

Ideias de desenho de projetos MIT em Node, que por isso não entram aqui: [quickpre/bpmn-skills](https://github.com/quickpre/bpmn-skills) (entrevista, depois schema fixo, depois compilação) e [architawr/claude-bpmn-skill](https://github.com/architawr/claude-bpmn-skill) (o modelo raciocina, o script desenha e valida). Nenhum código foi copiado deles.

## Agradecimentos

* Minha esposa **Júlia** e meus filhos **Arthur** e **Dante**, o porto seguro onde encontro paz, inspiração e a leveza de que preciso todos os dias.
* **Bruna Cardoso Bezerra** | [brunacbezerra](https://github.com/brunacbezerra), por me ensinar tudo o que sei sobre o Claude Code.
* **Você**, por usar o Senku!

## Aviso sobre dados de processo

Este repositório traz só o motor e exemplos fictícios: nenhum processo real de empresa. Os mapeamentos que você fizer ficam fora do repositório (em `local/` ou em outra pasta), e você se compromete a não publicá-los. Detalhes em [`AVISO.md`](AVISO.md).

## Licença

MIT License, veja [LICENSE](LICENSE) para detalhes.

---

<p align="center"><strong>Senku</strong>, não desenha no chute. prova.</p>
