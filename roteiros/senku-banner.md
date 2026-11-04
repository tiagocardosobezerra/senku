# Roteiro: `senku-banner.svg`

| | |
|---|---|
| Arquivos | `assets/senku-banner.svg` (pt-BR) e `assets/senku-banner-en.svg` |
| Onde | topo do `README.md` / `README.en.md`, logo depois dos selos |
| Tela | 1280 × 640, fundo `#0B1220`, grade de 32 px em `#1E2A44` |
| Duração | 48 s em laço, 6 cenas |
| `aria-label` / `alt` (pt) | Senku: da conversa ao fluxograma e ao mapeamento do processo, com prova |
| `aria-label` / `alt` (en) | Senku: from conversation to flowchart and process map, with proof |
| Paralelo | `vegapunk-banner.svg` e `deidara-banner.svg` (48 s, 6 cenas, mesmo arco) |

## A ideia em uma frase

Mapeamento de processo costuma dar errado de dois jeitos: alguém desenha o
fluxo sem perguntar o que acontece no "Não", e alguém escreve um documento
que ninguém mede nem aprova. O banner mostra os dois erros, depois o Senku
resolvendo cada um (fluxograma provado; mapeamento completo com aceite), o que
sai de um comando só e os números que provam.

## Linha do tempo

```css
/* Linha do tempo: 48 s. Cena 1 0–7 · Cena 2 7–13 · Cena 3 13–23 · Cena 4 23–35 · Cena 5 35–43 · Cena 6 43–48 */
```

| Cena | Tempo | Nome | Ensina |
|---|---|---|---|
| 1 | 0–7 s | Os dois erros | desenhar sem perguntar e documentar sem medir custam caro |
| 2 | 7–13 s | A conversa | uma conversa tem duas entregas: o fluxograma e o mapeamento |
| 3 | 13–23 s | O fluxograma | o Senku pergunta o que falta e prova que todo caminho termina |
| 4 | 23–35 s | O mapeamento | o documento completo sai com números, e o dono do processo aprova |
| 5 | 35–43 s | Um comando, nove arquivos | tudo sai da `carta.json`, e os números são medidos |
| 6 | 43–48 s | Assinatura | o nome, a promessa e onde o Senku roda |

Fio entre as cenas: a conversa se parte em dois chips, **fluxograma** (azul,
`#60A5FA`) e **mapeamento** (âmbar, `#F59E0B`). Eles sobem para os cantos de
cima, cada um acende na cena dele (3 e 4) e voltam a se juntar na cena 6.

---

## Cena 1 · Os dois erros (0–7 s)

**Ensina.** Os dois defeitos que o Senku existe para evitar. O da esquerda é
de modelagem (decisão sem saída). O da direita é de processo (documento sem
dono, sem medida e sem aceite). Juntos, fazem o espectador pensar "já vi isso".

**O que aparece.** Tela dividida ao meio, como no Vegapunk.

- Esquerda (fundo `rgba(96,165,250,.04)`): cartão "Fluxograma · desenho à
  mão" com um fluxo tracejado, peça por peça: início, "Pedir", "Aprovar?", o
  losango "Valor alto?" e "Comprar", só com a saída "Sim".
- Direita (fundo `rgba(245,158,11,.05)`): cartão "Mapeamento.docx" com quatro
  campos vazios em vermelho e o carimbo vermelho girado −10°.

**Texto na tela.**

| Elemento | pt-BR | en |
|---|---|---|
| cabeçalho esquerdo | Fluxograma · desenho à mão | Flowchart · hand-drawn |
| caixas | Pedir · Aprovar? · Valor alto? · Sim · Comprar | Request · Approve? · High value? · Yes · Buy |
| erro esquerdo | ⚠ decisão sem o caminho do “Não” | ⚠ decision with no “No” path |
| cabeçalho direito | Mapeamento.docx | Process_map.docx |
| campos | Responsável: a definir · Tempo de ciclo: ??? · Última revisão: 2019 · Aprovado por: — | Owner: TBD · Cycle time: ??? · Last review: 2019 · Approved by: — |
| carimbo | NINGUÉM APROVOU | NOBODY SIGNED OFF |
| legenda (5,5–6,9 s) | Desenhar sem **perguntar**. Documentar sem **medir**. | Draw without **asking**. Document without **measuring**. |

**Movimento.**

| Marca | O que acontece |
|---|---|
| 0,3–1,5 s | as peças do fluxo aparecem uma a uma, 0,2 s entre elas |
| 1,8–2,3 s | o losango fica vermelho e treme 4 px para os lados |
| 1,9 s | o selo de erro sobe 8 px e aparece embaixo do fluxo |
| 2,4–3,3 s | os quatro campos do documento entram da esquerda, 0,3 s entre eles |
| 3,9 s | o carimbo cai da escala 1,6 para 1 |
| 5,5 s | a legenda entra de baixo (10 px) |
| 6,6–7,0 s | as duas metades vão para o centro com escala 0,9 e somem |

---

## Cena 2 · A conversa (7–13 s)

**Ensina.** A pessoa conta o processo do jeito que contaria a um colega. O
Senku tira dali duas entregas.

**O que aparece.**

- A grade de fundo aparece (7,0–7,8 s) e fica até 47,5 s.
- O frasco (símbolo do Senku) entra pela direita e fica no canto inferior
  direito até o fim, com bolhas que sobem.
- Balão de fala grande, rótulo "você" em cima, com o relato.
- As palavras-chave ganham fundo verde-lima, uma depois da outra.
- O balão some e nascem os dois chips, colados no centro, que se afastam.

**Texto na tela.**

| Elemento | pt-BR | en |
|---|---|---|
| rótulo | você | you |
| relato | O pedido chega por **e-mail**, o **comprador** cota com **três fornecedores** e, **acima de R$ 5 mil**, o **gerente aprova**. | Requests arrive by **email**, the **buyer** gets **three quotes** and, **above $5k**, the **manager approves**. |
| chip azul | **fluxograma** quem faz o quê, em que ordem | **flowchart** who does what, in which order |
| chip âmbar | **mapeamento** tempos, regras, RACI, riscos | **process map** times, rules, RACI, risks |
| legenda (10,5–12,9 s) | Uma conversa, duas entregas. O Senku faz **as duas**. | One conversation, two deliverables. Senku makes **both**. |

**Movimento.**

| Marca | O que acontece |
|---|---|
| 7,3 s | o balão aparece com escala 0,92 → 1 |
| 7,4–8,2 s | o frasco entra da direita (160 px → 0) |
| 7,9–9,4 s | as cinco palavras acendem, 0,3 s entre elas |
| 9,9–10,2 s | o balão some |
| 10,0–11,0 s | os chips nascem colados (x 220 e 640) e se afastam |
| 13,0–13,4 s | a legenda sai; os chips sobem para os cantos (azul em x 40, âmbar em x 870, escala 0,8) |

---

## Cena 3 · O fluxograma (13–23 s)

**Ensina.** O Senku desenha o fluxograma em raias a partir da conversa, mas
antes pergunta o que falta. E ele não entrega um desenho bonito: entrega um
fluxo **provado**, em que toda decisão tem todas as saídas e todo caminho chega
ao fim. É a resposta à cena 1.

**O que aparece.** O chip **fluxograma** acende; o **mapeamento** fica a 35%.

- Um quadro de raias (1040 × 330) com três raias: Solicitante, Comprador e
  Gerente.
- O fluxo se desenha peça por peça: início → "Pedir material" → "Cotar com 3
  fornecedores" → losango "Acima de R$ 5 mil?" → "Não" vai para "Emitir
  pedido", "Sim" desce para "Aprovar compra" e volta para "Emitir pedido" →
  fim. Cada seta se desenha e só ganha a ponta quando chega.
- O cartão LACUNA aparece embaixo, à esquerda.
- Dois selos verdes aparecem à direita.
- Uma fileira de formatos aparece embaixo.

**Texto na tela.**

| Elemento | pt-BR | en |
|---|---|---|
| raias | Solicitante · Comprador · Gerente | Requester · Buyer · Manager |
| atividades | Pedir material · Cotar com 3 fornecedores · Emitir pedido · Aprovar compra | Request material · Get quotes from 3 suppliers · Issue PO · Approve purchase |
| decisão | Acima de R$ 5 mil? · Sim · Não | Above $5k? · Yes · No |
| lacuna | LACUNA · o Senku pergunta antes de desenhar · Quem aprova quando o gerente está de férias? | GAP · Senku asks before drawing · Who approves when the manager is on leave? |
| selos | ✓ 7PMG e BPMN Method & Style · ✓ todo caminho chega ao fim | ✓ 7PMG and BPMN Method & Style · ✓ every path reaches the end |
| formatos | BPMN 2.0 · Bizagi · Camunda · draw.io · Visio · Mermaid · SVG | iguais |
| legenda (19,6–22,8 s) | Ele pergunta o que falta e **prova** que o fluxo termina. | It asks what is missing and **proves** the flow ends. |

**Movimento.**

| Marca | O que acontece |
|---|---|
| 13,4 s | as raias aparecem |
| 13,8–16,5 s | início, setas, caixas, losango e fim entram em ordem; as saídas "Sim" e "Não" se desenham juntas (15,6 s) |
| 16,9–19,6 s | o cartão LACUNA sobe e fica |
| 17,8 s e 18,2 s | os dois selos verdes estalam (escala 0,9 → 1) |
| 19,0–19,7 s | os sete formatos sobem, 0,12 s entre eles |
| 22,6–23,0 s | tudo da cena sobe 16 px e some; o chip **fluxograma** volta a 35% |

---

## Cena 4 · O mapeamento (23–35 s)

**Ensina.** O mesmo processo vira o mapeamento completo, com números que saem
da análise (não do achismo) e uma oportunidade de melhoria priorizada. O dono
do processo aprova, o aceite fica guardado com hash, e mudar depois do aceite
é recusado.

**O que aparece.** O chip **mapeamento** acende; o **fluxograma** fica a 35%.

- À esquerda, o documento "SUP-01 · Compra de materiais indiretos" com as sete
  seções, cada uma com ✓ verde.
- À direita, quatro cartões de número, que caem de cima, e o cartão da
  oportunidade 1.
- Os cartões da direita saem; entram o balão do dono do processo, o carimbo
  APROVADO sobre o documento e a linha do aceite com cadeado no rodapé dele.
- Por último, o "fantasma": uma mudança feita depois do aceite, que fica cinza
  e é recusada.

**Texto na tela.**

| Elemento | pt-BR | en |
|---|---|---|
| cabeçalho | SUP-01 · Compra de materiais indiretos | igual (nome do exemplo) |
| seções | Ficha e escopo · SIPOC · Atividades e regras · Matriz RACI · Indicadores e tempos · Riscos e controles · Oportunidades Lean | Profile and scope · SIPOC · Activities and rules · RACI matrix · KPIs and times · Risks and controls · Lean opportunities |
| números | 14,1 d úteis · lead time típico / 17,2 d úteis · 80% dos casos até / 4% · eficiência do ciclo / 7 · passagens de bastão | 14.1 bus. days · typical lead time / 17.2 bus. days · 80% of cases within / 4% · cycle efficiency / 7 · handoffs |
| oportunidade | OPORTUNIDADE 1 · ESPERA · 3 dias úteis antes de “Cotar com fornecedores”: o que segura? | OPPORTUNITY 1 · WAITING · 3 business days before “Cotar com fornecedores”: what is holding it? |
| balão | dono do processo · Aprovo. | process owner · Approved. |
| carimbo | APROVADO | APPROVED |
| aceite | aceite 9C41E07B · v0.3 | sign-off 9C41E07B · v0.3 |
| fantasma | “Aprovar compra” · espera 1d → 3d | “Aprovar compra” · wait 1d → 3d |
| recusa | situacao: mudou depois do aceite. Precisa de novo “sim”. | situacao: changed after sign-off. Needs a new “yes”. |
| legenda (31,0–34,8 s) | Mapeamento completo, com o **aceite** do dono do processo. | A full process map, with the process owner’s **sign-off**. |

**Fonte dos números.** `python senku.py analisar exemplos/compras/carta.json`
(lead time típico, p80 da simulação, eficiência do ciclo, passagens no caso
típico) e a oportunidade 1 da mesma saída. O hash é ilustrativo.

**Movimento.**

| Marca | O que acontece |
|---|---|
| 23,0–23,4 s | o documento sobe 16 px e aparece |
| 23,6–25,3 s | as sete seções entram da esquerda, 0,28 s entre elas |
| 25,0–26,3 s | os quatro números caem 24 px, 0,3 s entre eles |
| 26,6 s | o cartão da oportunidade sobe |
| 28,6–29,0 s | números e oportunidade somem |
| 29,2 s | o balão do dono aparece (escala 0,92 → 1) |
| 29,6 s | o carimbo APROVADO cai girado −10°, da escala 1,6 para 1 |
| 30,0 s | a linha do aceite com cadeado aparece no rodapé do documento |
| 31,0 s | a legenda entra |
| 32,0 s | o fantasma entra pela direita (120 px), em vermelho |
| 32,4–32,85 s | o cadeado treme 4 px; o fantasma fica cinza; a recusa aparece |
| 33,6–34,0 s | o fantasma sai pela direita |
| 34,4–35,0 s | tudo da cena sobe 16 px e some; o chip **mapeamento** volta a 35% |

---

## Cena 5 · Um comando, nove arquivos (35–43 s)

**Ensina.** Tudo sai de um arquivo só (`carta.json`) com um comando, nunca à
mão. E o que o README promete foi medido.

**O que aparece.** Dois momentos.

1. **Os arquivos (35,0–38,6 s).** O comando é digitado em cima. A
   `carta.json` acende no centro. À esquerda, cinco arquivos do fluxograma; à
   direita, quatro do mapeamento.
2. **Os números (38,6–43,0 s).** Quatro painéis, com o número grande que conta
   de 0 até o valor (o último conta de 14 até 0) e uma barra fina embaixo.

**Texto na tela.**

| Elemento | pt-BR | en |
|---|---|---|
| comando | `$ python senku.py documentar carta.json` | igual |
| centro | `carta.json` | igual |
| rótulos | FLUXOGRAMA · MAPEAMENTO | FLOWCHART · PROCESS MAP |
| arquivos | `fluxograma.svg` · `fluxograma.png` · `processo.bpmn` · `processo.drawio` · `processo.mmd` / `mapeamento.html` · `mapeamento.docx` · `mapeamento.md` · `atividades.csv` | iguais |
| painel 1 | **206** · testes automatizados | **206** · automated tests |
| painel 2 | **73** · verificações de boa modelagem | **73** · modeling checks |
| painel 3 | **4.000** · casos simulados a cada análise | **4,000** · cases simulated per analysis |
| painel 4 | **0** · dependências para instalar | **0** · dependencies to install |
| nota (40,6–43,0 s) | Medido na versão 1.13.0, com os exemplos do repositório. | Measured on version 1.13.0, with the repository examples. |

**Fonte dos números.** 206: `python -m unittest discover -s testes`. 73:
códigos distintos de achado em `carta/validacao.py`. 4.000: `CASOS` em
`carta/simulacao.py`. 0: o Senku só usa a biblioteca padrão. Confira antes de
gerar o SVG de novo.

**Movimento.**

| Marca | O que acontece |
|---|---|
| 35,0–35,9 s | o comando é digitado (`steps()`, um passo por caractere) com cursor piscando |
| 35,6 s | a `carta.json` nasce no centro (escala 0,6 → 1) com brilho verde-lima |
| 35,8–36,1 s | os rótulos FLUXOGRAMA e MAPEAMENTO aparecem |
| 36,0–37,3 s | os arquivos entram dos lados para fora do centro, 0,2 s entre eles |
| 38,2–38,6 s | tudo desfoca (`blur(8px)`) e some |
| 38,6–39,9 s | os quatro painéis sobem 40 px, 0,3 s entre eles; os números contam |
| 40,5–42,2 s | as barras finas crescem da esquerda |
| 40,6 s | a nota aparece |
| 42,4–43,0 s | painéis e nota desfocam e somem |

---

## Cena 6 · Assinatura (43–48 s)

**Ensina.** Nome, promessa e onde o Senku roda. É o quadro que fica na
memória e o que aparece para quem tem movimento reduzido.

**O que aparece.** Os chips descem dos cantos e se colam sobre o nome.
"SENKU" grande no centro, a promessa em verde-lima, três pílulas e o rodapé.
O frasco continua no canto.

**Texto na tela.**

| Elemento | pt-BR | en |
|---|---|---|
| chips juntos | fluxograma · mapeamento | flowchart · process map |
| nome | SENKU | SENKU |
| promessa | não desenha no chute. prova. | doesn’t guess the flow. proves it. |
| pílulas | Fluxograma em raias BPMN 2.0 · Mapeamento completo · Aceite do dono do processo | Swimlane flowchart in BPMN 2.0 · Full process map · Process owner sign-off |
| rodapé | Claude Code · BPMN 2.0 · Bizagi · Camunda · draw.io · Word · MIT | igual |

A promessa é a frase do fim do README, para o banner e o rodapé fecharem com a
mesma ideia.

**Movimento.**

| Marca | O que acontece |
|---|---|
| 43,0–43,6 s | os chips descem com mola (`cubic-bezier(.3,1.4,.5,1)`) e se colam em x 220 / 640, y 118 |
| 43,6 s | "SENKU" aparece com escala 0,92 → 1 e espaçamento .18em → .06em |
| 44,0 s | a promessa sobe 10 px |
| 44,3 s | as três pílulas sobem 10 px, 0,15 s entre elas |
| 44,6 s | o rodapé aparece |
| 47,5–48,0 s | tudo some junto, inclusive o frasco e a grade, e o laço volta à cena 1 |

---

## Movimento reduzido

Com `prefers-reduced-motion: reduce`, a animação fica parada no segundo 46: a
cena 6 inteira, com os chips já juntos.

## Erros a evitar

- Mostrar o aceite antes do mapeamento: a ordem (mapear → números → "sim") é a
  mensagem.
- Usar número que não sai do exemplo ou da suíte. Os da cena 4 vêm do
  `analisar`; os da cena 5, da tabela "Resultados" do README.
- Desenhar o personagem de Dr. Stone. O símbolo é o frasco.
- Deixar texto de explicação em português no SVG em inglês. Só ficam em
  pt-BR os nomes do exemplo (SUP-01, "Cotar com fornecedores", "Aprovar
  compra"), os comandos e os arquivos.
