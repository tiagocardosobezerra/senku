# Entrevista de levantamento

O mapa é tão bom quanto a entrevista. O objetivo é sair com o processo **como
ele é feito** (AS-IS), não como o manual diz que deveria ser.

## Antes de começar

- **Quem entrevistar**: quem executa (sabe o que acontece de verdade) e o dono
  do processo (sabe o porquê e aprova). Num processo que cruza áreas, ouça
  pelo menos uma pessoa de cada raia; a passagem entre áreas é onde mora o
  problema e cada lado só vê a sua metade.
- **O que pedir antes**: procedimento escrito (POP), formulários, telas,
  relatórios, e-mails-modelo. Leia, monte um rascunho da carta e use a
  entrevista para confirmar e preencher.
- **Combine o nível**: um processo (5 a 30 atividades), não a empresa inteira
  nem o clique na tela. Se a conversa descer para "aí eu aperto F5", anote em
  `como` da atividade e volte ao nível.

## Os blocos (`python senku.py entrevista <bloco>`)

| Bloco | O que sai | Onde entra na carta |
|---|---|---|
| abertura | nome, objetivo, dono, gatilho, volume, escopo, normas | `processo` |
| sipoc | fornecedores, entradas, 5-7 grandes passos, saídas, clientes | `sipoc` |
| passos | caminho principal: atividade, papel, sistema, entradas e saídas | `papeis`, `sistemas`, `elementos` |
| decisoes | perguntas, critérios, exceções, retrabalho e percentuais | `elementos` (decisao), `regras`, `segue[].percentual` |
| tempos | execução, espera, prazo combinado, picos | `elementos[].tempo` |
| gestao | indicadores, dores, riscos e controles | `indicadores`, `dores`, `riscos` |
| tobe | o que resolver, o que eliminar, o que automatizar | `melhorias`, carta TO-BE |

Ordem que funciona: abertura → sipoc → passos → decisoes → tempos → gestao.
O SIPOC primeiro dá o contorno; sem ele a conversa se perde no detalhe.

## Técnicas que destravam

- **O último caso real.** "Pense no último pedido que você atendeu. O que
  chegou primeiro?" Caso real traz o que o manual esquece (o e-mail paralelo,
  a planilha de controle, a ligação para confirmar).
- **"E depois?"** Repita até o fim. Depois volte a cada ponto em que a pessoa
  hesitou ou disse "depende": ali há uma decisão.
- **"Depende de quê?"** transforma "depende" em pergunta e critério:
  "Depende do valor" → decisão "Valor acima de R$ 10 mil?" + regra de alçada.
- **"E quando dá errado?"** em cada decisão: o caso volta (retrabalho), é
  cancelado (fim com estado) ou segue outro caminho?
- **"De cada 100, quantos?"** para o percentual de cada saída. Ninguém sabe
  exato; a estimativa basta e diz onde está o retrabalho.
- **"Como você fica sabendo que chegou a sua vez?"** revela o gatilho de cada
  passagem de bastão (e-mail, fila do sistema, alguém avisa, ninguém avisa).
- **"Onde fica isso?"** para cada informação: sistema, planilha, papel,
  cabeça de alguém. Planilha paralela e "eu anoto aqui" são achados.
- **Tempo em duas perguntas**: "fazendo, leva quanto?" (execução) e "quanto
  fica parado antes de você pegar?" (espera). Somadas, a espera quase sempre
  é muito maior.

## Devolva o entendimento

A cada bloco, devolva em passos numerados, com as palavras da pessoa:

> Entendi assim: 1. o solicitante abre a requisição no ERP; 2. o gestor
> analisa; 3. se aprova, vai para Compras cotar; se não, volta para o
> solicitante corrigir. Está certo? Faltou alguma coisa?

Só grave na carta o que ela confirmou. Mostre o desenho (`desenhar`) assim que
houver um caminho do início ao fim: a correção visual é mais rápida.

## Armadilhas

- **O processo ideal**: "deveria ser assim" não é AS-IS. Pergunte "e na
  prática?".
- **Nome de pessoa como papel**: "a Maria aprova" → "Analista Fiscal". O mapa
  sobrevive à troca de pessoas; a pessoa vai em `participantes`.
- **Sistema como responsável**: o sistema não é dono de atividade humana. Se
  a atividade é automática, papel = o sistema (raia "ERP", `"tipo":
  "sistema"`) e `"automatizada": true`.
- **Atividade gigante**: "Fazer a compra" é um processo inteiro. Quebre até
  cada atividade ter um responsável e um resultado.
- **Decisão sem dono**: o losango não decide sozinho. Antes dele há a
  atividade de quem analisa ("Analisar requisição").
- **Tudo é exceção**: se metade das falas começa com "mas às vezes",
  pergunte qual é o caminho da maioria e desenhe esse primeiro.

## Entrevista por texto (procedimento, áudio transcrito, e-mail)

1. Leia tudo e escreva a carta com o que o texto diz.
2. Rode `lacunas` e `validar`: o que o texto não responde vira pergunta.
3. Mande as perguntas em bloco, numeradas, com a sua hipótese: "No passo 4,
   entendi que é o Comprador quem escolhe o fornecedor; confirma?".
