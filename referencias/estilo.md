# Regras de boa modelagem

O `validar` confere a carta contra três fontes. Cada achado diz a fonte.

- **7PMG**: Mendling, Reijers e van der Aalst, *Seven Process Modeling
  Guidelines (7PMG)*, Information and Software Technology 52(2), 2010. Sete
  regras tiradas de pesquisa empírica sobre o que causa erro e dificulta a
  leitura de modelos.
- **M&S**: Bruce Silver, *BPMN Method and Style* (regras de estilo para BPMN
  descritivo: o diagrama sozinho tem de contar a história).
- **Casa**: convenções do Senku para o mapa ser lido por gestor e auditor.

## As sete diretrizes (7PMG)

| | Diretriz | Como o Senku aplica |
|---|---|---|
| G1 | Use o mínimo de elementos | aviso `mapa_grande`; exceção rara vai para `excecoes` |
| G2 | Minimize caminhos por elemento | aviso `porta_mista` (porta que junta e divide) |
| G3 | Um início e um fim | aviso `varios_inicios`; vários fins só com estados diferentes |
| G4 | Modele o mais estruturado possível (abre e fecha do mesmo tipo) | `travamento`, `sem_sincronia` (jogo de fichas), `divisao_implicita` |
| G5 | Evite o OU inclusivo | aviso `inclusivo` |
| G6 | Rótulo de atividade verbo-objeto | aviso `nome_sem_verbo` (com sugestão) |
| G7 | Decomponha acima de 50 elementos | aviso `mapa_grande` |

## Method and Style (o que o Senku cobra)

- Todo nível tem início e fim explícitos (`sem_inicio`, `sem_fim`).
- Início nomeado pelo gatilho; fim nomeado pelo estado final quando há mais de
  um (`fins_sem_estado`): "Pedido entregue", "Pedido cancelado".
- Decisão escrita como pergunta, com "?" (`decisao_sem_interrogacao`), e cada
  saída com a resposta (`saida_sem_rotulo` é erro).
- A porta não decide: antes dela vem a atividade de quem analisa
  (`decisao_sem_trabalho`).
- Saída de paralelo e junção não levam rótulo (`paralelo_rotulado`,
  `juncao_com_nome`).
- Evento intermediário tem nome e gatilho (`evento_sem_nome`,
  `evento_sem_gatilho`).
- "O que vier primeiro" é corrida, não paralelo: paralelo que espera um prazo
  E outro evento ao mesmo tempo gera `paralelo_de_esperas`. A corrida só abre
  (`corrida_juntando` é erro) e tem pelo menos dois caminhos
  (`corrida_um_caminho`).
- A borda segue para um lugar só (`borda_divide`); vários ao mesmo tempo pedem
  um paralelo depois dela.
- Subprocesso com `detalhe`: o tempo no mapa de cima bate com o da carta filha
  (`detalhe_tempo_diferente`; sem tempo, `detalhe_sem_tempo` sugere o da
  filha).
- Nada fica pendurado: `beco_sem_saida`, `sem_entrada`, `inalcancavel`,
  `nunca_termina` são erros.

## Regras da casa

- Atividade com dois verbos ("Conferir e aprovar") → `duas_atividades`.
- Nome com mais de 60 caracteres → `nome_longo` (detalhe vai na `descricao`).
- Atividade sem papel → `sem_responsavel` (cai na raia "sem responsável").
- Papel sem atividade → `papel_sem_atividade` (tire da raia ou ponha no RACI).
- Referência a papel, sistema, regra, dor ou elemento que não existe → erro.

## Erros x avisos

| Nível | Significado | O que fazer |
|---|---|---|
| erro | o desenho sai errado ou incompleto; o `aprovar` recusa | corrigir na carta |
| aviso | o fluxo funciona, mas fere uma regra | levar à pessoa em linguagem de negócio; ela decide |
| dica | só leitura | aplicar se for fácil |

Exemplo de tradução: `beco_sem_saida [a8]` → "Depois de conferir o material,
o que acontece? Quem recebe?". `porta_mista [d2]` → "aqui juntam dois
caminhos e logo se decide outra coisa; vou separar em dois pontos para ficar
claro, ok?".

## Outros códigos do `validar`

| Código | Nível | O que quer dizer |
|---|---|---|
| `sem_elementos`, `processo_sem_nome` | erro / aviso | carta vazia; processo sem nome |
| `destino_inexistente` | erro | `segue` aponta um id que não existe (vem com "quis dizer ...?"); os erros de ligação que dependem dele não se repetem |
| `papel_inexistente`, `sistema_inexistente`, `regra_inexistente`, `raci_papel_inexistente`, `dor_inexistente`, `referencia_inexistente` | erro | cita algo que não está na lista (sistema só é cobrado quando a carta tem `sistemas`) |
| `fluxo_repetido`, `rotulo_repetido`, `laco_em_si` | erro / aviso | mesma ligação duas vezes; duas saídas com o mesmo rótulo; atividade que volta para si |
| `inicio_com_entrada`, `inicio_sem_nome`, `fim_com_saida`, `fins_repetidos` | erro / aviso | início e fim fora do lugar ou sem nome; dois fins com o mesmo estado |
| `atividade_sem_nome`, `decisao_sem_pergunta`, `porta_inutil`, `evento_divide` | erro / aviso | elemento sem nome; porta com uma entrada e uma saída; evento com duas saídas |
| `laco_sem_saida`, `travamento`, `sem_sincronia` | erro | jogo de fichas: laço sem saída, caso que trava, atividade que roda duas vezes |
| `fichas_incompleto` | aviso | o mapa passou de 300 mil estados e a prova não terminou: quebre em subprocessos |
| `borda_sem_atividade`, `borda_gatilho`, `borda_sem_prazo`, `borda_sem_nome`, `borda_divide`, `bordas_demais`, `bordas_mais_de_100`, `fluxo_para_borda`, `lembrete_volta_ao_fluxo` | erro / aviso | bordas: presa em atividade, com gatilho e prazo, um destino só, até 4 por atividade, somando até 100%, sem fluxo chegando, e lembrete que não volta ao caminho normal |
| `corrida_sem_evento`, `corrida_evento_compartilhado`, `corrida_sem_encerra`, `corrida_juntando`, `corrida_um_caminho`, `paralelo_de_esperas` | erro / aviso | corrida: depois dela só eventos que esperam, cada um só dela; paralelo que deveria ser corrida |
| `encerra_sozinho`, `erro_fora_do_fim`, `fim_de_tempo` | aviso / erro | fim terminal único (não precisa); evento de erro fora do fim; fim com gatilho de tempo |
| `percentual_soma`, `percentual_fracao` | aviso | percentuais da decisão não somam 100; "0,3" em vez de 30 |
| `dias_ambiguos`, `horas_ambiguas` | aviso | prazo em dias ou horas sem dizer se é útil ou corrido |
| `papel_pessoa` | aviso | papel com nome de pessoa: use o cargo |
| `subprocesso_sem_detalhe`, `detalhe_nao_existe`, `detalhe_tempo_diferente`, `detalhe_sem_tempo` | dica / aviso | ligação com a carta do subprocesso e tempo dele batendo com o da carta filha |
| `caractere_invisivel` | aviso | texto com caractere invisível, já limpo na leitura |
