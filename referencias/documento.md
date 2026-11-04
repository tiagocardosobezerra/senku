# O documento de mapeamento

`python senku.py documentar <carta>` gera, em `saida/`, o HTML, o Word
(.docx), o Markdown, o CSV das atividades e os quatro desenhos. O documento
segue a estrutura usada
em escritórios de processos (BPM CBOK / ABPMP) e em auditoria de controles.

| # | Seção | Vem de | Para quem |
|---|---|---|---|
| 1 | Ficha do processo | `processo` | todos: o que é, de quem é, para que serve |
| 2 | Escopo | `processo.escopo`, `premissas` | evita discussão sobre o que não foi mapeado |
| 3 | SIPOC | `sipoc` + caminho feliz | visão de uma linha para diretoria |
| 4 | Fluxograma | elementos (SVG) | todos |
| 5 | Descrição das atividades | elementos (tabela + detalhe) | quem executa, treinamento, POP |
| 6 | Decisões e regras de negócio | decisões, `regras` | auditoria, TI (automação) |
| 7 | Matriz RACI | `papel` + `raci` | gestores, RH |
| 8 | Indicadores | `indicadores` | dono do processo |
| 9 | Análise | `analisar` | melhoria contínua |
| 10 | Dores, melhorias, riscos e controles | `dores`, `melhorias`, `riscos` | dono, auditoria, compliance |
| 11 | Glossário, normas, sistemas, pendências | vários + lacunas de prioridade 1-2 | todos |
| 12 | Participantes, histórico, aceite | `participantes`, `historico`, aprovação | governança do documento |

## Como apresentar

- Mostre o HTML (artifact ou arquivo). Comece pelo fluxograma e pelo
  caminho feliz; depois as 2-3 oportunidades mais fortes.
- Diga o que é estimativa (tempos, percentuais) e o que é pendência.
- O selo no topo diz se é RASCUNHO ou aprovado. Peça o aceite com uma
  pergunta direta: "Aprova este mapeamento como o processo atual (AS-IS)?".
- Para PDF: abrir o HTML no navegador, Ctrl+P, "Salvar como PDF", paisagem.
- Para Word: o `.docx` já sai pronto (estilos do Word: Título 1, Título 2,
  tabelas com grade; A4 paisagem, e em pé só na parte do fluxograma com muitas
  raias). O fluxograma entra como figura SVG, que o
  Word 2016/365 e o LibreOffice 7+ mostram; em versões antigas, use o `.svg`.
  Não abra o `.md` direto no Word: ele mostra o Markdown cru.
- Para PDF: HTML > Ctrl+P > Salvar como PDF (paisagem), ou o `.docx` > Salvar
  como PDF.
- Mapa longo: HTML e Word mostram o fluxograma nas MESMAS partes (5 colunas em
  página deitada; a parte com tantas raias que a letra ficaria abaixo de ~6 pt
  vira partes de 3 colunas em página em pé, também na impressão do HTML), com
  o cabeçalho das raias repetido, raias e linhas vazias encolhidas e
  "continua" nas pontas; o `.svg` inteiro fica na pasta para a visão completa.

## POP (procedimento operacional padrão)

A seção 5 já é a base do POP: por atividade, responsável, sistema, entradas,
saídas, regras e o "como fazer" (`como`). Para um POP de uma atividade
específica, preencha `como` (passos numerados, um verbo por passo) e
`excecoes` dela, e entregue a seção.
