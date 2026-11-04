# Análise e melhoria

`python senku.py analisar <carta>` lê o mapa e devolve números e
oportunidades. Tudo depende dos tempos e percentuais da entrevista: são
estimativas. Diga isso sempre que mostrar.

## Os números

| Número | Como é calculado | Leitura |
|---|---|---|
| caminho feliz | do primeiro início ao fim, pela saída mais comum de cada decisão (maior `percentual`); sem percentual, a saída que chega a um fim bom sem voltar, depois "Sim/Aprovado"; nunca o retrabalho; no paralelo, o ramo mais demorado | o caso mais comum (pode terminar em recusa, se a recusa for a maioria) |
| lead time esperado | média ponderada por todos os caminhos, com os percentuais e o retrabalho (35% de volta = a etapa roda 1,5 vez); decisão sem percentual conta com peso igual e o relatório avisa | o prazo médio real, com as exceções |
| esforço | soma da execução de todas as atividades do caminho (todos os ramos) | horas de trabalho por caso |
| lead time | execução + espera do caminho (no paralelo, só o ramo mais longo) | o prazo que o cliente sente |
| eficiência do ciclo | execução ÷ lead time do caminho; sai "—" quando um evento de mensagem (ou tarefa que recebe) no caminho não tem `tempo.espera` | abaixo de 10% é comum em processo administrativo: o trabalho passa a maior parte do tempo parado |
| passagens de bastão | atividade → próxima atividade em outra raia | cada uma é fila, espera e risco de perda |
| vai e volta | A → B → A | a informação não chegou completa da primeira vez |
| retrabalho | fluxo que volta para trás (com `percentual`) | defeito: corrija na origem |

**Carga de trabalho (capacidade).** Com `processo.volume` ("120 requisições
por mês", "15 por dia", "600 por ano"), a análise multiplica o volume pelas
vezes que cada atividade roda por caso (retrabalho e exceções contam) e pelo
tempo de execução: horas por mês por papel e pessoas equivalentes em 160 h
(jornada cheia, sem pausas: é o mínimo). Atividade de externo ou automática
não entra; atividade sem tempo fica de fora e o relatório avisa. Subprocesso
com `detalhe`: o trabalho é o da carta filha, com os papéis dela (o tempo do
subprocesso no mapa de cima não conta de novo). Mês = 20 dias úteis, o mesmo
dos tempos.

**Simulação (lead time esperado, percentis e frequências).** Quando o mapa
tem paralelo, OU, borda ou fim que encerra, o Senku simula 4.000 casos com as
regras de ficha do BPMN (`carta/simulacao.py`): decisão e corrida sorteiam
pelo percentual; paralelo espera todos os ramos; OU sorteia cada caminho pela
chance dele (se nenhum acontece, o caso segue direto, e o `validar` avisa);
borda que interrompe tira a ficha no prazo dela; fim que encerra acaba o caso.
Saem a média, o prazo em que terminam 50%, 80% e 90% dos casos e quantas
vezes cada elemento roda por caso. O sorteio depende do id de cada elemento:
mesma carta, mesmo número; no `comparar`, a diferença é do processo, não da
sorte. Fluxo só com decisões usa a conta exata (é o mesmo número).

Tudo é somado em tempo útil: `h` = hora de expediente, `d` = dia útil (8 h).
Prazo de calendário entra como `dc` (dia corrido) e `hc` (hora corrida): um dia
corrido vale 5/7 de dia útil, porque a semana tem 7 dias e só 5 úteis. Espera
de evento de prazo ("Aguardar 10 dias corridos") é lida do próprio nome quando
não há `tempo`.

## Valor agregado (VA / NAV-N / NAV)

Pergunte, atividade por atividade: o cliente pagaria por isso?

- **VA** (agrega valor): transforma o que o cliente recebe. Ex.: emitir o
  pedido, entregar o material.
- **NAV-N** (não agrega, mas é necessário): exigência legal, controle,
  segurança. Ex.: lançar a nota fiscal, aprovar pela alçada.
- **NAV** (desperdício): pode sair sem prejuízo. Ex.: redigitar, corrigir,
  conferir de novo o que já foi conferido, cobrar resposta.

Proponha a classificação e deixe a pessoa corrigir; nunca grave como fato o
que ela não confirmou.

## Os oito desperdícios (Lean) e o que o Senku procura

| Desperdício | No processo administrativo | Achado do Senku |
|---|---|---|
| Defeitos | retrabalho, correção, devolução | laço de retrabalho, `NAV` |
| Espera | fila, aprovação parada, resposta de terceiro | espera ≥ 1 dia útil antes de uma atividade |
| Transporte | passar o trabalho de uma área para outra | muitas passagens de bastão, vai e volta |
| Superprocessamento | conferência em série, aprovação demais, digitar duas vezes | aprovação seguida de aprovação, registro em 2+ sistemas, mais de um A na RACI |
| Movimentação | procurar informação, imprimir, levar papel | atividades manuais (sem sistema) |
| Estoque | lote acumulado, caixa de entrada cheia | (pergunte: "acumula para fazer de uma vez?") |
| Excesso de produção | relatório que ninguém lê, cópia para todos | (pergunte: "quem usa isso?") |
| Talento não aproveitado | decisão na cabeça de alguém, especialista fazendo tarefa simples | decisão sem critério escrito |

## RACI

R executa (o `papel`), A responde pelo resultado (um só por atividade), C é
consultado antes, I é informado depois. Sem A declarado, pergunte: muitas
vezes é quem executa (R/A); quando é outro, é um ponto de controle.

## Indicadores

Bom indicador de processo tem: nome, fórmula (numerador/denominador e
período), meta, polaridade (maior ou menor é melhor), periodicidade, fonte do
dado e dono. Comece por três: **prazo** (lead time ou % no prazo),
**qualidade** (% de retrabalho ou devolução) e **volume/custo**. Cada
melhoria do TO-BE deve mover um indicador; se nenhum mede, falta indicador.

## Do AS-IS ao TO-BE

1. Priorize as dores por impacto × frequência (com o dono).
2. Para cada dor, pergunte a causa (5 porquês) antes da solução.
3. Heurísticas de redesenho, nesta ordem: **eliminar** (o passo NAV),
   **simplificar** (menos aprovações, alçada por valor), **juntar** (atividades
   seguidas do mesmo papel, uma raia só para o vai e volta), **paralelizar**
   (o que não depende um do outro), **automatizar** (regra escrita vira regra
   no sistema; cópia vira integração), **prevenir** (validar na entrada em
   vez de conferir depois).
4. `python senku.py tobe <carta>`; aplique na `carta-tobe.json`, cada
   melhoria com `resolve: [dores]`.
5. `python senku.py comparar <as-is> --contra <to-be>`: menos atividades,
   passagens, retrabalho e lead time são o argumento para o dono.
6. Liste o que muda além do fluxo (sistema, norma, treinamento, cargo) em
   `melhorias` e `pendencias`: TO-BE sem isso não sai do papel.
