# O formato da carta (`carta.json`)

Um objeto JSON. Só `processo.nome` e `elementos` são obrigatórios para
desenhar; o resto enriquece o documento e a análise. Exemplo completo:
`exemplos/compras/carta.json`.

## processo

```json
"processo": {
  "codigo": "SUP-01", "nome": "Compra de materiais indiretos",
  "cenario": "as-is",                 // as-is | to-be
  "versao": "0.3", "nivel": "processo",   // macroprocesso | processo | subprocesso
  "macroprocesso": "Gestão de suprimentos", "area": "Suprimentos",
  "dono": "Gerente de Suprimentos",   // cargo que responde pelo resultado e aprova o mapa
  "objetivo": "...", "gatilho": "...", "resultado": "...",
  "frequencia": "contínuo", "volume": "120 requisições/mês",
  "prazo_informado": "10 a 15 dias úteis",   // o que a pessoa diz do todo (sem tempos por atividade, é o único prazo)
  "escopo": {"inicio": "...", "fim": "...", "inclui": ["..."], "nao_inclui": ["..."]},
  "normas": ["Política de Compras PC-001"], "premissas": ["..."]
}
```

## sipoc, papeis, sistemas

```json
"sipoc": {"fornecedores": [], "entradas": [], "saidas": [], "clientes": []},
"papeis": [{"id": "compras", "nome": "Comprador", "tipo": "interno"}],   // interno | externo | sistema
"sistemas": [{"id": "erp", "nome": "ERP", "descricao": "SAP S/4"}]
```

A coluna P do SIPOC sai sozinha do caminho feliz. Cada papel usado vira uma
raia, na ordem da lista (ponha na ordem em que o trabalho passa). Papel e
sistema podem ser citados pelo `id` ou pelo `nome`.

## elementos

Cada passo do fluxo. `segue` diz para onde ele vai.

| campo | uso |
|---|---|
| `id` | curto e estável (`a1`, `d1`): é por ele que a pessoa aponta a correção |
| `tipo` | `inicio`, `atividade` (padrão), `subprocesso`, `decisao`, `paralelo`, `inclusivo`, `corrida` (o que vier primeiro), `evento`, `fim` |
| `nome` | atividade: verbo + objeto; decisão: pergunta com `?`; início/fim: o estado ("Pedido recebido") |
| `papel` | quem executa (id ou nome do papel) |
| `sistema` | id ou lista; `[]` ou `"manual"` = feito sem sistema; ausente, `""` ou `null` = ainda não perguntado |
| `segue` | `"a2"`, `["a8", "a9"]` (paralelo) ou `[{"para": "a3", "rotulo": "Sim", "percentual": 85, "condicao": "valor <= 10000"}]` |
| `descricao` | o que é feito, em uma ou duas frases |
| `como` | passos da instrução de trabalho (lista) |
| `entradas`, `saidas`, `documentos` | listas de texto |
| `regras` | ids de `regras` que valem aqui |
| `tempo` | `{"execucao": "15min", "espera": "2d"}`. Tudo em tempo útil: `min`, `h` (hora de expediente), `d` (dia útil = 8 h), `sem` (5 d), `mes` (20 d). Tempo de calendário: `dc` (dia corrido = 5/7 de dia útil) e `hc` (hora corrida). Também: `1h30`, `1:30`, `1,5d`, `1 hora e meia`, `meia hora`, `duas horas`, `D+1`, `dia seguinte`, `mesmo dia` (meio dia útil), `imediato`, `quinzena`, `1 ano`, `2 a 4h`, `entre 2 e 3 dias` e `2 ou 3 dias` (média) |
| `valor` | `VA` (agrega ao cliente), `NAV-N` (necessário: lei, controle), `NAV` (desperdício) |
| `raci` | `{"A": "gestor", "C": ["juridico"], "I": ["solicitante"]}` (R é o `papel`) |
| `excecoes` | casos raros que não entram no desenho (lista de texto) |
| `gatilho` | em início e evento: `nenhum`, `tempo`, `mensagem`, `condicao`, `sinal`, `erro` |
| `automatizada` | `true` quando o sistema faz sozinho (vira serviceTask no BPMN); aceita também "sim"/"não" |
| `recebe` | `true` quando a atividade é esperar algo chegar de fora ("Receber documentos do cliente"): vira receiveTask no BPMN, pode vir logo depois de uma `corrida` e, com `--pools`, recebe a mensagem do externo. O tempo de espera vai em `tempo.espera` |
| `envia` | `true` quando a atividade (ou um evento de mensagem) só manda algo para fora ("Enviar proposta"): vira sendTask (ou evento de envio) no BPMN. Um evento com `envia` não pode vir depois de uma `corrida` (ela só espera) |
| `encerra` | só no `fim`: `true` encerra o processo inteiro, mesmo com outro ramo paralelo andando (fim terminal do BPMN) |
| `bordas` | na atividade: exceções presas nela (evento de borda do BPMN). Lista de `{"gatilho": "tempo", "nome": "Prazo de 48h estourado", "tempo": "48hc", "percentual": 10, "segue": "a9"}`; gatilho `tempo` (prazo), `mensagem`, `erro`, `sinal` ou `condicao`; `"interrompe": false` quando a atividade continua (ex.: lembrete) |
| `detalhe` | no `subprocesso`: caminho da carta dele, a partir desta pasta (`"kyc/carta.json"`) |

Evento e porta sem `papel` ficam na raia de quem vem antes; atividade sem
`papel` cai na raia "(sem responsável)" e o `lacunas` pergunta quem faz.

Sinônimos aceitos em `tipo`: tarefa, task, gateway, xor, and, or, start, end,
espera. Em vez de `segue`, também vale uma lista `fluxos` no topo:
`[{"de": "a1", "para": "a2", "rotulo": ""}]` (o `importar` usa `segue`).

### Padrões de fluxo

```json
// decisão com retrabalho
{"id": "d1", "tipo": "decisao", "nome": "Requisição aprovada?", "papel": "gestor",
 "segue": [{"para": "a3", "rotulo": "Sim", "percentual": 85}, {"para": "a1b", "rotulo": "Não", "percentual": 15}]}

// paralelo: abre e fecha com paralelo
{"id": "p1", "tipo": "paralelo", "papel": "almox", "segue": ["a8", "a9"]},
{"id": "p2", "tipo": "paralelo", "papel": "almox", "segue": "a11"}   // a8 e a9 seguem para p2

// "o que acontecer primeiro": corrida (porta por evento); cada saída começa com o evento que pode chegar
{"id": "c", "tipo": "corrida", "nome": "O que vier primeiro", "papel": "com",
 "segue": [{"para": "e1", "percentual": 70}, {"para": "e2", "percentual": 30}]},
{"id": "e1", "tipo": "evento", "gatilho": "mensagem", "nome": "Aceite do cliente recebido", "segue": "a2"},
{"id": "e2", "tipo": "evento", "gatilho": "tempo", "nome": "Aguardar 10 dias corridos", "segue": "a3"}

// prazo estourado durante a atividade: borda (a atividade é interrompida e o caso segue pela exceção)
{"id": "a2", "nome": "Analisar pedido", "papel": "an", "segue": "a3",
 "bordas": [{"gatilho": "tempo", "nome": "Prazo de 48h estourado", "tempo": "48hc", "percentual": 10, "segue": "a9"}]}

// espera por prazo ou resposta
{"id": "e1", "tipo": "evento", "gatilho": "tempo", "nome": "Aguardar 2 dias úteis", "segue": "a5"}

// vários finais, cada um com o estado
{"id": "fim_ok", "tipo": "fim", "nome": "Pedido entregue"},
{"id": "fim_canc", "tipo": "fim", "nome": "Pedido cancelado"}

// cancelar tudo com um ramo paralelo ainda andando: fim terminal
{"id": "fim_exp", "tipo": "fim", "nome": "Proposta expirada", "encerra": true}
```

## regras, indicadores, dores, riscos, melhorias

```json
"regras": [{"id": "R1", "texto": "Gestor aprova até R$ 10 mil", "fonte": "Tabela de alçadas"}],
"indicadores": [{"nome": "Lead time", "formula": "...", "atual": "14 dias úteis", "meta": "≤ 10 dias úteis",
                 "polaridade": "menor é melhor", "periodicidade": "mensal", "fonte": "ERP", "dono": "Gerente de Suprimentos"}],
"dores": [{"id": "D1", "descricao": "...", "elementos": ["a1"], "impacto": "alto", "frequencia": "15%"}],
"riscos": [{"id": "K1", "descricao": "...", "elementos": ["a9"], "probabilidade": "média", "impacto": "alto",
            "controle": "...", "tipo_controle": "preventivo"}],
"melhorias": [{"id": "M1", "descricao": "...", "resolve": ["D1"], "elementos": ["a1"], "impacto": "alto", "esforco": "baixo",
               "responsavel": "Coordenador Comercial", "prazo": "31/01/2027", "status": "em andamento"}]
```

## glossario, pendencias, participantes, historico

```json
"glossario": [{"termo": "...", "definicao": "..."}],
"pendencias": [{"pergunta": "...", "para": "Controladoria"}],
"participantes": [{"nome": "Ana Ribeiro", "papel": "Compradora", "data": "28/10/2026"}],
"historico": [{"versao": "0.1", "data": "28/10/2026", "autor": "...", "mudanca": "Entrevista inicial"}]
```

O aceite não fica na carta: o `aprovar` grava `carta.aprovacao.json` ao lado.

### Vários inícios

Processo que começa por mais de um canal (e-mail e portal, por exemplo) tem um `inicio` para cada canal. Diga
em `percentual` a parte dos casos que entra por cada um (`{"id": "i1", "tipo": "inicio", "nome": "Pedido por
e-mail", "percentual": 70, "segue": "a1"}`); sem ele, a simulação divide em partes iguais.
