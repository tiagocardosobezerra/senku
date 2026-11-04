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

## Resultados

Medidos na versão 1.13.0, com os exemplos do repositório (um processo de compras e um de crédito, fictícios).

| O quê | Resultado |
|---|---|
| Testes automatizados | **206 passando** |
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

Só para o projeto atual, troque o destino por `.claude/skills/senku`. No claude.ai, suba o zip da skill (veja [`COMO-INSTALAR.md`](COMO-INSTALAR.md)).

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
├── COMO-INSTALAR.md       # Instalação, conferência e zip para o claude.ai
├── AVISO.md               # Dados de processo, privacidade e marcas
├── LICENCAS-DE-TERCEIROS.md  # Fontes das animações (OFL) e projetos que inspiraram o desenho
├── LICENSE                # MIT License
├── senku.py               # Porta de entrada: todos os comandos
├── carta/                 # O motor: carta, entrevista, lacunas, validação, fichas, simulação, análise, layout, aceite, importação
├── saidas/                # Os geradores: SVG, PNG, BPMN, draw.io, Mermaid, HTML, Word e Markdown
├── referencias/           # Guias: carta, entrevista, notação, estilo, análise e documento
├── exemplos/              # Processos fictícios completos: compras (SUP-01) e crédito
├── roteiros/              # Roteiros das animações do README
├── ferramentas/           # Empacotador da skill, gerador das animações, fuzz e testes de estresse
├── assets/                # Animações do README
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
