# Aviso sobre dados de processo

O Senku é só o motor. Ele não traz, não recebe e não envia nenhum processo
real de empresa. O que muda de uma instalação para outra é o que cada pessoa
mapeia, e isso fica com ela.

| O quê | Onde fica | Pode publicar? |
|---|---|---|
| **O Senku** (`senku.py`, `carta/`, `saidas/`, `referencias/`, `ferramentas/`, `testes/`, `roteiros/`, `assets/`) e os exemplos fictícios de `exemplos/` | este repositório | sim |
| **Os seus mapeamentos** (cada `carta.json`, a pasta `saida/`, os aceites `*.aprovacao.json`, os `.bpmn` importados) | fora da pasta da skill, ou em `local/` dentro dela | **não**: são do processo da sua empresa |

## O que nunca entra no repositório

**Nenhum processo real.** Uma carta descreve como uma empresa trabalha:
quem aprova o quê, alçadas, sistemas, prazos, riscos e controles. Isso pode
ser informação interna ou confidencial. O `.gitignore` já mantém `local/`,
`saida/` e os aceites fora do controle de versão, e o empacotador
(`ferramentas/empacotar.py`) não leva nada disso para o zip da skill.

Os exemplos de `exemplos/` (compras SUP-01 e crédito) e os casos de
`testes/casos/` são 100% fictícios: nomes de pessoas, empresas, valores e
tempos foram inventados para mostrar e testar o Senku.

## Responsabilidade pelo uso

Ao mapear um processo com o Senku:

1. Você confirma que pode registrar e tratar as informações desse processo.
2. As cartas, os documentos e os aceites que você gera são de sua
   responsabilidade. Este projeto não os recebe e não tem acesso a eles.
3. **Não publique, faça commit ou compartilhe** cartas e saídas de processos
   reais em repositório público, issue, pull request ou canal de suporte. Para
   pedir ajuda, reproduza o problema numa carta fictícia.
4. Ao contribuir (código, documentação, casos de teste), use só dados
   fictícios, nunca copiados ou derivados de um processo real.
5. Dados pessoais (nome de quem aprova, participantes da entrevista) entram na
   carta só se você os puser lá. Siga as regras de privacidade da sua empresa
   (no Brasil, a LGPD).

## Os números do Senku são estimativas

Os tempos, percentuais e volumes vêm da entrevista, não de medição no sistema.
A análise e a simulação mostram o que acontece **se** o relato estiver certo, e
o documento diz isso. Confirme os números antes de usá-los numa decisão.

## Marcas e nomes de terceiros

O nome "Senku" é uma homenagem de tom criativo ao personagem de Dr. Stone e
não indica afiliação, endosso ou associação com os detentores dessa obra. O
símbolo das animações é um frasco de laboratório desenhado para o projeto, não
o personagem. Bizagi, Camunda, ARIS, Signavio, Visio, draw.io/diagrams.net,
Mermaid, Microsoft Word e Excel são marcas dos respectivos donos e aparecem só
para dizer com o que as saídas do Senku são compatíveis.

## Isenção

Este aviso é uma declaração de política do projeto, não aconselhamento
jurídico.
