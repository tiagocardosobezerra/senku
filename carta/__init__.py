"""
A carta do processo: o motor do Senku (o roadmap, do gatilho ao resultado).

A carta (`carta.json`) é a descrição do processo: identificação, escopo, SIPOC,
papéis (raias), elementos do fluxo, regras, indicadores, dores, riscos e
melhorias. Tudo que sai do Senku (fluxograma BPMN, draw.io, Mermaid, SVG e o
documento de mapeamento) é desenhado a partir dela, nunca à mão.

    util        erros de uso, leitura de JSON com a linha do erro, tempos ("2h", "3d")
    modelo      carrega e normaliza a carta (grafo, papéis, fluxos)
    validacao   regras estruturais e de estilo (7PMG, Method and Style, regras da casa)
    lacunas     as perguntas que faltam, em linguagem de negócio, por prioridade
    layout      posição de cada elemento nas raias (usado por BPMN, draw.io e SVG)
    analise     valor agregado, passagens de bastão, tempos, retrabalho, oportunidades
    aprovacao   o "sim" do dono do processo (hash da carta) e a diferença entre versões
"""

VERSAO = '1.14.0'
FORMATO = 'senku/1'
