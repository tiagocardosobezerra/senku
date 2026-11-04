# Licenças de terceiros

O código do Senku é MIT (veja [LICENSE](LICENSE)) e usa só a biblioteca padrão
do Python. O que vem de fora está listado aqui.

## Fontes das animações do README

As animações de `assets/` embutem, em base64, subconjuntos destas fontes
(latim básico, Latin-1 e alguns símbolos), guardados em
`ferramentas/animacoes_fontes.css`. Todas são da SIL Open Font License 1.1,
que permite embutir e redistribuir. O texto completo da licença está em
[`ferramentas/OFL.txt`](ferramentas/OFL.txt).

| Fonte | Copyright | Origem |
|---|---|---|
| Inter | Copyright 2020 The Inter Project Authors | https://github.com/rsms/inter (via google/fonts) |
| Poppins | Copyright 2020 The Poppins Project Authors | https://github.com/itfoundry/Poppins (via google/fonts) |
| JetBrains Mono | Copyright 2020 The JetBrains Mono Project Authors | https://github.com/JetBrains/JetBrainsMono (via google/fonts) |

As fontes ficam fora do pacote da skill: o `ferramentas/empacotar.py` não leva
`ferramentas/` nem `assets/` para o zip.

## Projetos que inspiraram o desenho

Nenhum código destes projetos foi copiado. Eles são MIT e escritos em Node, e
por isso não entram aqui.

- [quickpre/bpmn-skills](https://github.com/quickpre/bpmn-skills): entrevista,
  depois schema fixo, depois compilação.
- [architawr/claude-bpmn-skill](https://github.com/architawr/claude-bpmn-skill):
  o modelo raciocina, o script desenha e valida.

## Referências de método

As regras de verificação seguem publicações, não código de terceiros:

- Mendling, J.; Reijers, H. A.; van der Aalst, W. M. P. *Seven Process
  Modeling Guidelines (7PMG)*. Information and Software Technology, 2010.
- Silver, B. *BPMN Method and Style*. Cody-Cassidy Press.
- ABPMP. *BPM CBOK: Guia para o Gerenciamento de Processos de Negócio*.
- OMG. *Business Process Model and Notation (BPMN) 2.0*.
