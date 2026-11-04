# Memory Card: o cartão dos processos aprovados

Carregado sob demanda pelo `SKILL.md`. Como o memory card de um videogame:
cada processo aprovado fica salvo (um "save"), com versão e histórico, para
ser carregado de novo quando precisar: na próxima revisão, num TO-BE, ou
quando alguém perguntar "esse processo já foi mapeado?".

**É o mesmo cartão do Vegapunk.** O cartão é um repositório git do usuário no
GitHub, privado por padrão, com uma pasta por solução: os relatórios do
Vegapunk em `saves/vegapunk/`, os processos do Senku em `saves/senku/`. O
Senku só grava a própria pasta e o `CATALOGO.md`, nunca os saves de outra
solução, e gera o catálogo linha por linha igual ao do Vegapunk: quem enviar
por último não reescreve o que é do outro. Qual é o cartão fica só nesta
instalação (`local/memory_card.json`, fora do git e do pacote).

## O que é preciso

- O [GitHub CLI](https://cli.github.com/) (`gh`) instalado e autenticado
  (`gh auth login`). O envio usa a sua autenticação: nenhum token fica na skill.
- O `git`.

## Onde funciona

No Claude Code (ou num terminal) da máquina onde o cartão está clonado. Numa
sandbox, como a do claude.ai, não há o `gh` autenticado nem a pasta do cartão:
os comandos recusam dizendo isso, o `status` mostra "configurado, mas NÃO
funciona aqui" e o lembrete depois do aceite diz para entregar os arquivos e
deixar o envio para o Claude Code.

## Ligar ao cartão (uma vez)

```bash
python senku.py cartao iniciar --repo SEU_USUARIO/memory-card
```

- Se o repositório já existe (o do Vegapunk, por exemplo), ele é usado; se
  estiver público, é recusado.
- Se a pasta `~/memory-card` já é um clone dele, o Senku usa o mesmo clone.
- Se não existe, é criado **privado**, com um `README.md` de raiz mínimo.
- `--pasta DIR` escolhe outra pasta; `--publico` aceita um cartão público
  (só de propósito: a carta descreve como a empresa trabalha).
- Uma instalação que já tem cartão só troca com `--substituir`, a pedido.
- Sem GitHub: `cartao iniciar --pasta DIR` cria um cartão só local (git sem
  remoto).

As variáveis `SENKU_MEMORY_CARD_REPO` e `SENKU_MEMORY_CARD_DIR` têm
precedência sobre a configuração (`SENKU_MEMORY_CARD_DIR=-` desliga o cartão;
`SENKU_MEMORY_CARD_REPO=-` usa a pasta como cartão local).

## Como o cartão é organizado

```
memory-card/
├── README.md                          da raiz
├── CATALOGO.md                        gerado a cada envio: por solução, categoria e seção
└── saves/
    ├── vegapunk/...                   os relatórios do Vegapunk (o Senku não toca)
    └── senku/<categoria>/<secao>/<artigo>/
        ├── README.md                  o artigo, com o fluxograma (o GitHub mostra ao abrir a pasta)
        ├── ficha.json                 versão, status, processo, aceite, números, arquivos, relacionados, histórico
        ├── carta.json                 a carta aprovada: a fonte de tudo
        ├── carta.aprovacao.json       o aceite do dono do processo
        └── <base>.svg .bpmn .drawio .mmd .md .docx .html -atividades.csv
```

- **Categoria** é a área da carta (`processo.area`), **seção** é o
  macroprocesso (`processo.macroprocesso`) e **artigo** é
  `CÓDIGO · Nome (CENÁRIO)`, por exemplo
  `SUP-01 · Compra de materiais indiretos (AS-IS)`. Dá para trocar com
  `--categoria`, `--secao` e `--artigo`. As pastas usam o nome sem acento e
  com hífen.
- Um save é citado por **REF** = `senku/<categoria>/<secao>/<artigo>`, com os
  nomes das pastas.
- **Status**: `em-uso` (o processo vigente, com aceite) ou `rascunho`.
- Os arquivos do save são gerados pelo `documentar` na hora do envio: o save
  é sempre a versão de agora, nunca uma saída antiga ou editada à mão.
- O AS-IS e o TO-BE do mesmo processo (mesmo `processo.codigo`) ficam
  ligados sozinhos como relacionados, nos dois sentidos.

### O artigo

O `README.md` de cada save tem: título, solução, categoria, seção, versão e
status; a descrição (o objetivo do processo); o texto do artigo entre
`<!-- corpo -->` e `<!-- /corpo -->` (montado da carta: o que é, quem
participa, números e as maiores oportunidades; ou o seu, com `--texto`); o
fluxograma; os links para os arquivos; o aceite; os relacionados; o histórico.
Só o corpo pode ser editado à mão, e os marcadores não devem ser apagados.

## Comandos

Os que gravam mostram uma **prévia** primeiro e só gravam com `--confirmar`.
`memory-card` é sinônimo de `cartao`.

| Comando | O que faz |
|---|---|
| `cartao iniciar --repo DONO/NOME [--pasta DIR] [--publico] [--substituir]` | liga ao cartão (ou cria um privado) |
| `cartao catalogo [--todas] [--json]` | os processos salvos (`--todas`: de todas as soluções) |
| `cartao buscar TERMO [TERMO ...]` | procura em todo o cartão: título e descrição pesam mais, depois área, macroprocesso e processo, depois o artigo e os nomes das atividades e dos papéis. Só aparece o save que cobre pelo menos metade dos termos |
| `cartao enviar CARTA [--categoria C] [--secao S] [--artigo A] [--descricao D] [--texto ARQ.md] [--motivo M] [--status S] [--relacionado REF] [--sem-aceite] [--confirmar]` | salva o processo aprovado, ou uma versão nova dele |
| `cartao marcar REF --status em-uso\|rascunho [--confirmar]` | muda o status de um save do Senku |

### Regras

- **Procure antes.** Antes de mapear um processo novo: `cartao buscar`. O
  `novo` lembra disso. Se algo serve, ofereça partir dele (um TO-BE, uma
  revisão) em vez de começar do zero.
- **Só aprovado entra.** O `enviar` recusa carta sem aceite válido (ou que
  mudou depois do aceite) e carta com erro de fluxo. Para guardar mesmo assim,
  como rascunho, só a pedido: `--sem-aceite`.
- **Ofereça salvar logo depois do aceite.** O `aprovar` imprime um
  `LEMBRETE:` com o comando. Mostre a prévia e só com o "sim" use
  `--confirmar`.
- **Mudança pede motivo.** Um processo já salvo que mudou sobe de versão com
  `--motivo`; a prévia mostra o diff da carta e do artigo. O histórico guarda
  quando e por quê, e o git do cartão guarda o resto.
- **Saber se está salvo.** O `situacao` de uma carta aprovada diz se o aceite
  atual já está no cartão, se o cartão tem uma versão anterior, ou se ainda
  não foi salvo (só a cópia local, sem rede).

## Proteções

- **Privado por padrão.** Antes e depois de cada commit, a visibilidade do
  cartão é conferida no GitHub; se não for privado (e não foi ligado com
  `--publico`), o envio é recusado.
- **Só a pasta do Senku.** O commit leva só `saves/senku/` e o `CATALOGO.md`.
  Arquivos pendentes de outras soluções ficam como estão.
- **Antes de gravar, traz o que os outros enviaram** (`git pull --ff-only`).
- **Nada do cartão no repositório da skill.** A configuração fica em `local/`,
  fora do git e do zip.
- **Convivência com o Vegapunk.** A ficha do Senku segue o formato do
  Vegapunk (solução, categoria, seção, artigo, versão, status, relacionados,
  histórico) e marca `instancia: senku`: o `conferir` do Vegapunk, que confere
  SQL no schema, pula os processos do Senku.
