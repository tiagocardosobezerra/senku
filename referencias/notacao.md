# Notação e saídas

O Senku usa um subconjunto pequeno do BPMN 2.0, o que um gestor lê sem curso
(Bruce Silver chama de "paleta descritiva"). Fluxograma de raias e BPMN saem
da mesma carta e com o mesmo desenho.

## Símbolos

| Na carta | No desenho | BPMN 2.0 | Quando usar |
|---|---|---|---|
| `inicio` | círculo fino verde | startEvent | o gatilho; ícone pelo `gatilho` (relógio = data, envelope = algo chega) |
| `atividade` | retângulo arredondado, número e sistema no topo | task / userTask (com sistema) / serviceTask (`automatizada`) | trabalho de um papel |
| `subprocesso` | retângulo com [+] | subProcess recolhido | conjunto de atividades mapeado em outra carta |
| `decisao` | losango, pergunta acima à esquerda | exclusiveGateway | um caminho OU outro |
| `paralelo` | losango com + | parallelGateway | todos os caminhos ao mesmo tempo; fecha com outro paralelo |
| `inclusivo` | losango com o | inclusiveGateway | um ou mais caminhos (evite: 7PMG G5) |
| `evento` | círculo duplo | intermediateCatchEvent | espera por prazo, mensagem ou condição |
| `corrida` | losango com círculo duplo e pentágono | eventBasedGateway | "o que acontecer primeiro": resposta x prazo |
| `bordas` da atividade | círculo duplo preso na borda de baixo (tracejado se não interrompe) | boundaryEvent | prazo estourado, erro ou mensagem durante a atividade |
| `fim` | círculo grosso vermelho | endEvent | cada resultado final, com nome |
| saída com `rotulo` | linha com texto (e %) | sequenceFlow `name` | resposta da decisão |
| fluxo para trás | linha tracejada | sequenceFlow | retrabalho |

Raia = papel (cargo ou área). Papel `externo` (cliente, fornecedor) tem a raia
cinza e o rótulo "(externo)". No BPMN, por padrão, todas as raias ficam num
pool só. Com `desenhar --pools` (ou `documentar --pools`), cada externo vira um
pool "caixa-preta" e a troca com ele vira fluxo de mensagem, como pede o Method
and Style: a mensagem sai da atividade de dentro e a resposta chega na
atividade seguinte (ou num evento "recebido" antes de uma decisão); processo
que começa no externo ganha início de mensagem. Só é possível quando o trecho
externo é uma sequência simples (sem decisão do lado de fora): senão o BPMN sai
em raias e o comando diz por quê.

## Leitura do desenho

- Da esquerda para a direita; a coluna é a ordem em que as coisas acontecem.
- Atividades numeradas (01, 02...): primeiro o fluxo normal, na ordem do tempo
  (coluna do desenho; ramos paralelos se intercalam); depois as exceções e
  correções (caminhos de borda e de retrabalho), também pela coluna. O número é
  o mesmo no desenho, na tabela de atividades, na RACI e no CSV.
- Retrabalho sai por baixo da atividade e volta tracejado.
- Passe o mouse sobre um elemento (SVG/HTML) para ver responsável, sistema,
  descrição, tempo e regras.

## As saídas (`desenhar` e `documentar`)

| Arquivo | Abre em | Para quê |
|---|---|---|
| `.svg` | navegador, Word, PowerPoint, Confluence | figura oficial, imprime nítida |
| `.bpmn` | bpmn.io (demo.bpmn.io), Camunda Modeler, Bizagi Modeler (Importar BPMN), ARIS, Signavio, Visual Paradigm, Enterprise Architect, Visio (BPMN) | editar num modelador, padrão do escritório de processos |
| `.drawio` | diagrams.net / draw.io desktop, extensão do VS Code, Confluence; o Lucidchart importa | editar à mão; exporta para Visio (.vsdx), PDF, PNG |
| `.mmd` | GitHub, GitLab, Notion, Obsidian, Confluence (macro), mermaid.live | prévia no chat e em wiki (sem raia de verdade) |
| `.html` | navegador; Ctrl+P salva em PDF (A4 paisagem) | o mapeamento completo |
| `.docx` | Word 2016/365, LibreOffice 7+ | o mapeamento para editar e aplicar o modelo da empresa (o fluxograma entra como figura SVG) |
| `.md` | Git, wiki, Confluence | o mapeamento em texto, com o Mermaid dentro |
| `-atividades.csv` | Excel (; e acentos certos) | lista de atividades para plano de ação, POP, treinamento |

Editou no modelador e quer trazer de volta? Exporte .bpmn e use `importar`.
O BPMN do Senku leva a carta inteira numa extensão (`senku:dados` em cada
elemento e `senku:carta` no processo): sistemas, tempos, regras, RACI, valor,
indicadores e riscos voltam; nome, tipo, raia e ligações vêm do que foi
editado no modelador. Só as posições não voltam (o Senku desenha de novo pelo
fluxo). Modelador que apaga extensões (alguns fazem) devolve só o desenho.

Na importação de BPMN de outras ferramentas: evento de borda vira `bordas` da
atividade (com prazo, interrompe ou não), porta por evento vira `corrida`,
evento de ligação (link) vira ligação direta, lançar mensagem ou escalonamento
vira atividade, tarefa de receber mensagem fica marcada (`"recebe": true`),
chamada de processo (callActivity) vira `detalhe`, objetos de dados viram
entradas e saídas, anotação de texto vira nota na descrição, caminho que só
para (fim implícito) ganha um fim. O que não tem equivalente é avisado.
O BPMN feito com `--pools` é de mão única: importado de volta, o externo vem
como pool sem as atividades dele (use o BPMN padrão para ida e volta).

## Fluxograma clássico x BPMN

O "fluxograma ANSI" (retângulo, losango, terminador, documento) não tem raia
nem evento. O Senku usa os símbolos BPMN mesmo quando a pessoa pede
"fluxograma": a leitura é igual (retângulo = passo, losango = decisão) e o
arquivo serve também para quem trabalha com BPMN. Se a pessoa estranhar o
círculo, explique: verde fino = começa, vermelho grosso = termina.
