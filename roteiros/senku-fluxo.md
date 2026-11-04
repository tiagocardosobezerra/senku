# Roteiro: `senku-fluxo.svg`

| | |
|---|---|
| Arquivos | `assets/senku-fluxo.svg` (pt-BR) e `assets/senku-fluxo-en.svg` |
| Onde | `README.md` / `README.en.md`, seção "Como funciona por dentro", antes da tabela de peças |
| Tela | 1280 × 640, fundo `#0B1220`, grade de 32 px em `#1E2A44` a 45% |
| Duração | 36 s em laço, 5 passos |
| `aria-label` / `alt` (pt) | Como o Senku funciona: entrevista, carta, prova, desenho, mapeamento e aceite |
| `aria-label` / `alt` (en) | How Senku works: interview, charter, proof, flowchart, process map and sign-off |
| Paralelo | `vegapunk-sonar.svg` e `deidara-fluxo.svg` (passo a passo, faixa de progresso, uma legenda por vez) |

## A ideia em uma frase

O Senku trabalha como um cientista: primeiro coleta (a entrevista), depois
registra (a carta), depois **prova** (fichas por todos os caminhos e 4.000
casos simulados), só então publica (fluxograma e mapeamento) e pede o
aceite. O que não se sustenta aparece e é corrigido na frente de quem assiste.

## Linha do tempo

```css
/* Linha do tempo: 36 s. 1 Você conta 0–5 · 2 A carta 5–12 · 3 A prova 12–21 · 4 Desenho e mapeamento 21–29 · 5 Aceite e TO-BE 29–36 */
```

| Passo | Tempo | Etapas do Senku | Comandos | Ensina |
|---|---|---|---|---|
| 1 · Você conta | 0–5 s | abertura, passos, decisões | `entrevista` | o Senku conduz a conversa, bloco a bloco |
| 2 · A carta | 5–12 s | carta, lacunas | `novo`, `lacunas` | tudo vai para a `carta.json`; o que falta vira pergunta por prioridade |
| 3 · A prova | 12–21 s | validar, analisar | `validar`, `analisar` | fichas percorrem todos os caminhos; a simulação dá o p50 e o p80 |
| 4 · Desenho e mapeamento | 21–29 s | desenhar, documentar | `desenhar`, `documentar` | do mesmo arquivo saem o fluxograma e o mapeamento |
| 5 · Aceite e TO-BE | 29–36 s | aprovar, TO-BE | `aprovar`, `tobe`, `comparar` | o dono aprova; o TO-BE nasce comparado com o AS-IS |

## Elementos fixos (o tempo todo)

- **Faixa de progresso no topo** (y 70): cinco segmentos de 200 × 4 px com o
  número embaixo. O segmento do passo atual se enche durante o passo; os já
  feitos ficam claros (`#F1F5F9`), os que faltam ficam `#334155`. O nome do
  passo atual fica grande no centro (y 24) e troca com subida de 8 px.
- **Legenda embaixo** (y 586), uma por vez, Inter 20 px, `#CBD5E1`.
- **O frasco** no canto inferior direito, menor que no banner, com bolhas.

**Texto fixo da faixa.**

| # | pt-BR | en |
|---|---|---|
| 1 | 1 · Você conta | 1 · You tell |
| 2 | 2 · A carta | 2 · The charter |
| 3 | 3 · A prova | 3 · The proof |
| 4 | 4 · Desenho e mapeamento | 4 · Flowchart and process map |
| 5 | 5 · Aceite e TO-BE | 5 · Sign-off and TO-BE |

---

## Passo 1 · Você conta (0–5 s)

**Ensina.** O começo é uma conversa, não um formulário. O Senku pergunta e a
pessoa responde do jeito dela.

**O que aparece.** Quatro balões alternados: o Senku à esquerda, com o frasco,
e a pessoa à direita. No fim do passo, os balões encolhem e voam para o
centro, onde vai nascer a carta.

**Texto na tela.**

| Elemento | pt-BR | en |
|---|---|---|
| Senku 1 | Quando o pedido chega, quem dá o primeiro passo? | When a request arrives, who takes the first step? |
| você 1 | O comprador cota com três fornecedores. | The buyer gets quotes from three suppliers. |
| Senku 2 | E quando passa de R$ 5 mil? | And when it is above $5k? |
| você 2 | Aí o gerente aprova. | Then the manager approves. |
| legenda (1,4–4,7 s) | O Senku conduz a **entrevista**, um bloco por vez. | Senku runs the **interview**, one block at a time. |

**Movimento.**

| Marca | O que acontece |
|---|---|
| 0,3 / 1,1 / 1,9 / 2,7 s | cada balão sobe 12 px e aparece |
| 1,4 s | a legenda entra |
| 4,4–4,9 s | os balões encolhem para 0,3 e voam para o centro (`cubic-bezier(.5,0,.7,1)`) |

---

## Passo 2 · A carta (5–12 s)

**Ensina.** Tudo o que a pessoa conta vira um arquivo só, a `carta.json`,
fonte de tudo o que o Senku entrega. O que falta não é inventado: vira
pergunta, da mais importante para a menos.

**O que aparece.**

- À esquerda, o cartão `carta.json` (borda verde-lima), com as linhas de JSON
  entrando uma a uma, coloridas pelo tipo (papéis em azul, decisão em âmbar,
  regra em verde-lima).
- À direita, o cartão `python senku.py lacunas` com três perguntas e a
  prioridade de cada uma.
- A primeira pergunta é respondida (selo verde).

**Texto na tela.**

| Elemento | pt-BR | en |
|---|---|---|
| carta | `"processo": {"nome": "Compra de materiais"}` · `"papeis": ["Solicitante", "Comprador", "Gerente"]` · `{"id": "a2", "nome": "Cotar com 3 fornecedores"}` · `{"id": "d1", "tipo": "decisao", "nome": "Acima de R$ 5 mil?"}` · `"regras": ["Acima de R$ 5 mil, o gerente aprova"]` | igual (é o arquivo) |
| lacuna alta | ALTA · Quem aprova quando o gerente está de férias? | HIGH · Who approves when the manager is on leave? |
| lacuna média | MÉDIA · Quanto tempo o pedido espera antes da cotação? | MEDIUM · How long does a request wait before quoting? |
| lacuna baixa | BAIXA · Em que sistema a cotação fica registrada? | LOW · Which system records the quote? |
| resposta | ✓ respondida: nas férias, aprova o diretor | ✓ answered: on leave, the director approves |
| legenda A (5,6–8,6 s) | Tudo o que você conta vira a **carta do processo**. | Everything you say goes into the **process charter**. |
| legenda B (8,8–11,7 s) | O que falta vira **pergunta**, da mais importante para a menos. | What is missing becomes a **question**, most important first. |

**Movimento.**

| Marca | O que acontece |
|---|---|
| 5,0–5,4 s | a carta nasce no centro-esquerda (escala 0,7 → 1) |
| 5,5–7,3 s | as dez linhas entram da esquerda, 0,18 s entre elas |
| 7,2–7,5 s | o cartão das lacunas entra pela direita (30 px) |
| 7,6 / 8,0 / 8,4 s | as três lacunas entram, da ALTA para a BAIXA |
| 9,6 s | o selo "respondida" estala |
| 11,5–12,0 s | os dois cartões sobem 16 px e somem |

---

## Passo 3 · A prova (12–21 s)

**Ensina.** O Senku não confia no desenho: ele **roda fichas** (tokens) por
todos os caminhos. Um caminho que não chega ao fim aparece em vermelho e é
consertado (o "Corrigir" volta para o "Pedir"). Depois, a simulação de 4.000
casos dá o prazo real, com faixa, em vez de uma média só.

**O que aparece.**

- À esquerda, um fluxo pequeno: início → "Pedir" → losango → "Sim" para
  "Cotar" e fim; "Não" para "Corrigir", que no começo não tem saída.
- Duas fichas verde-lima. A primeira vai pelo "Sim" até o fim. A segunda vai
  pelo "Não" e para em "Corrigir", que fica vermelho.
- A seta de volta (verde) se desenha de "Corrigir" até "Pedir"; a segunda
  ficha segue por ela, dá a volta e chega ao fim.
- À direita, o histograma da simulação, com as barras crescendo e as marcas do
  p50 e do p80.

**Texto na tela.**

| Elemento | pt-BR | en |
|---|---|---|
| caixas | Pedir · Sim · Cotar · Não · Corrigir | Request · Yes · Quote · No · Fix |
| erro | ⚠ “Corrigir” não chega ao fim | ⚠ “Fix” never reaches the end |
| prova | ✓ todo caminho chega ao fim · nada trava | ✓ every path ends · nothing deadlocks |
| cabeçalho | simulação · 4.000 casos | simulation · 4,000 cases |
| marcas | 50% até 14,1 d · 80% até 17,2 d | 50% within 14.1 d · 80% within 17.2 d |
| eixo | dias úteis, do pedido ao material entregue | business days, from request to delivery |
| legenda A (12,6–15,9 s) | Fichas percorrem **todos os caminhos**: nada trava, tudo termina. | Tokens run down **every path**: nothing deadlocks, everything ends. |
| legenda B (16,2–20,7 s) | E **4.000 casos simulados** dão o prazo real, não só a média. | And **4,000 simulated cases** give the real lead time, not just the average. |

**Fonte dos números.** O p50 e o p80 são os do `analisar` no exemplo de
compras. O formato do histograma é ilustrativo.

**Movimento.**

| Marca | O que acontece |
|---|---|
| 12,0–12,3 s | o fluxo sobe 16 px e aparece |
| 12,6–14,5 s | a primeira ficha anda pelo "Sim" até o fim e some |
| 13,0–14,3 s | a segunda ficha anda pelo "Não" e para em "Corrigir" |
| 14,4–15,9 s | "Corrigir" fica vermelho; o selo de erro aparece |
| 15,4–15,9 s | a seta de volta se desenha; "Corrigir" volta a azul |
| 15,9–18,2 s | a segunda ficha volta por ela, passa pelo "Sim" e chega ao fim |
| 16,0 s | o selo verde da prova estala |
| 16,0–16,3 s | o cartão da simulação entra pela direita |
| 16,4–18,0 s | as 14 barras crescem de baixo, 0,09 s entre elas (cinza até o p50, âmbar depois do p80) |
| 18,0 s e 18,4 s | as marcas do p50 e do p80 descem |
| 20,5–21,0 s | tudo sobe 16 px e some |

---

## Passo 4 · Desenho e mapeamento (21–29 s)

**Ensina.** A mesma carta gera o fluxograma em raias e o mapeamento completo.
Nada é desenhado nem escrito à mão.

**O que aparece.**

- À esquerda, o fluxograma em raias do banner, em tamanho menor, desenhado
  peça por peça, e embaixo os formatos de desenho.
- À direita, a matriz RACI do mapeamento, preenchida célula por célula, e
  embaixo os formatos do documento.

**Texto na tela.**

| Elemento | pt-BR | en |
|---|---|---|
| raias | Solicitante · Comprador · Gerente | Requester · Buyer · Manager |
| formatos do desenho | SVG · PNG · BPMN 2.0 · draw.io · Mermaid | iguais |
| cabeçalho RACI | Matriz RACI · do mapeamento | RACI matrix · from the process map |
| colunas | Solic. · Compr. · Gerente | Req. · Buyer · Mgr. |
| linhas | Pedir material · Cotar · Aprovar compra · Emitir pedido | iguais (nomes do exemplo) |
| formatos do documento | HTML · Word · Markdown · CSV | iguais |
| legenda (23,6–28,6 s) | Do **mesmo arquivo** saem o fluxograma e o mapeamento completo. | The flowchart and the full process map come from the **same file**. |

**Movimento.**

| Marca | O que acontece |
|---|---|
| 21,0–21,3 s | o quadro de raias aparece |
| 21,7–24,4 s | o fluxo se desenha, como na cena 3 do banner |
| 22,6–22,9 s | o cartão RACI entra pela direita |
| 23,2–24,2 s | as células R, A, C e I aparecem linha por linha |
| 24,6–25,1 s | os formatos do desenho sobem |
| 25,2–25,6 s | os formatos do documento sobem |
| 28,5–29,0 s | tudo sobe 16 px e some |

---

## Passo 5 · Aceite e TO-BE (29–36 s)

**Ensina.** O dono do processo aprova com um comando, e o aceite fica com
hash por seção. O redesenho (TO-BE) não é uma folha em branco: nasce da carta
aprovada e é comparado com o AS-IS, linha por linha.

**O que aparece.**

- À esquerda, o comando `aprovar` digitado, o carimbo APROVADO e a linha do
  hash com cadeado.
- À direita, as etiquetas AS-IS → TO-BE e o cartão do `comparar`, com três
  diferenças: o que sai (−), o que entra (+) e o que muda (~).

**Texto na tela.**

| Elemento | pt-BR | en |
|---|---|---|
| comando | `$ aprovar carta.json --por "Gerente de Suprimentos"` | `$ aprovar carta.json --por "Supply manager"` |
| carimbo | APROVADO | APPROVED |
| hash | hash 9C41E07B · por seção | hash 9C41E07B · per section |
| cabeçalho | `comparar --contra to-be/carta.json` | igual |
| diferenças | − Lançar cotação no ERP · + Aprovação automática até R$ 5 mil · ~ espera antes de cotar: 3d → 1d | − Lançar cotação no ERP · + Aprovação automática até R$ 5 mil · ~ wait before quoting: 3d → 1d |
| legenda (31,0–35,6 s) | O dono **aprova**. O TO-BE nasce comparado com o AS-IS. | The owner **signs off**. The TO-BE is born compared with the AS-IS. |

As diferenças são um TO-BE de exemplo, para mostrar o formato do `comparar`.

**Movimento.**

| Marca | O que acontece |
|---|---|
| 29,3–30,2 s | o comando é digitado |
| 30,4 s | o carimbo cai girado −8°, da escala 1,6 para 1 |
| 30,9 s | a linha do hash aparece |
| 31,3 s | as etiquetas e o cartão do `comparar` entram pela direita |
| 31,8 / 32,2 / 32,6 s | as três diferenças entram |
| 35,6–36,0 s | tudo some e o laço volta ao passo 1 |

---

## Movimento reduzido

Com `prefers-reduced-motion: reduce`, a animação fica parada no segundo 34: o
passo 5 inteiro, com o aceite e a comparação na tela, e a faixa de progresso
cheia.

## Erros a evitar

- Pular a prova. O passo 3 é o que diferencia o Senku de uma ferramenta de
  desenho: sem ele, o vídeo vira "mais um gerador de fluxograma".
- Mostrar o TO-BE antes do aceite: o redesenho parte do AS-IS aprovado.
- Prometer automação que o Senku não faz (ler o ERP, medir tempos do sistema).
  Os tempos vêm da entrevista, e o documento diz isso.
