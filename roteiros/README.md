# Roteiros das animações do README

Esta pasta guarda o roteiro de cada animação SVG de `assets/`. O roteiro vem
antes do desenho: diz o que cada cena ensina, quanto tempo dura, o que aparece,
o texto exato na tela (em pt-BR e em inglês) e como cada elemento entra e sai.
Quem for refazer um SVG começa por aqui. Quem mudar o produto (um comando, um
número, um nome) confere aqui se alguma cena ficou desatualizada.

| Animação | Roteiro | Onde aparece | Duração | Pergunta que responde |
|---|---|---|---|---|
| `senku-banner.svg` / `-en.svg` | [senku-banner.md](senku-banner.md) | topo do README, logo depois dos selos | 84 s, 6 cenas (48 s × 1,75) | por que o Senku existe e o que ele entrega |
| `senku-fluxo.svg` / `-en.svg` | [senku-fluxo.md](senku-fluxo.md) | seção "Como funciona por dentro", antes da tabela de peças | 63 s, 5 passos (36 s × 1,75) | como uma conversa vira um processo mapeado e aprovado |

Os SVGs saem de um gerador, não da mão:

```bash
python ferramentas/animacoes.py
```

O gerador grava os quatro arquivos em `assets/` na versão base (48 s e 36 s).
Os SVGs publicados foram refinados à mão a partir dela e rodam 1,75 vez mais
devagar (84 s e 63 s), com as mesmas cenas na mesma ordem. Rodar o gerador
sobrescreve os refinados: guarde-os antes. Os tempos no código
(`ferramentas/animacoes.py`) são os mesmos destes roteiros, em segundos, e cada
SVG traz no topo do `<style>` o comentário de linha do tempo para conferir um
contra o outro.

## O padrão que vem do Vegapunk e do Deidara

1. **Um laço só, sem JavaScript.** Uma duração para tudo (48 s no banner, 36 s
   no fluxo). Cada elemento tem seus `@keyframes` em porcentagem do laço:
   `% = segundo ÷ duração × 100`.
2. **Narrativa em arco.** O banner vai da dor ao produto: (1) o que dá errado
   hoje, (2) a conversa, (3 e 4) o que o Senku faz com cada parte, (5) os
   números medidos, (6) a assinatura. A animação de "como funciona" é um passo
   a passo numerado com uma faixa de progresso no topo.
3. **Um fio que atravessa as cenas.** A conversa se parte em dois chips,
   **fluxograma** (azul) e **mapeamento** (âmbar). Eles sobem para os cantos,
   cada um acende na cena dele e os dois voltam juntos na assinatura.
4. **Uma legenda por vez.** Uma frase curta embaixo. Ela entra depois da
   imagem e sai antes da próxima cena.
5. **O errado aparece e é descartado, nunca escondido.** A decisão sem o
   caminho do "Não", o documento que ninguém aprovou, o "Corrigir" que não
   chega ao fim e a mudança depois do aceite aparecem e são recusados.
6. **Exemplo fictício e plausível.** Tudo vem do exemplo do repositório
   (`exemplos/compras`, SUP-01 · Compra de materiais indiretos). Os números da
   análise (14,1 d úteis, 17,2 d no p80, 4% de eficiência, 7 passagens) são os
   que o `senku.py analisar` imprime para ele.
7. **Número só com a fonte da medição.** A cena de resultados termina com
   "Medido na versão 1.14.0, com os exemplos do repositório."
8. **Fim que emenda no começo.** Tudo some no último meio segundo e a cena 1
   começa do zero, sem salto.
9. **Autossuficiente.** Fontes embutidas em base64 (Inter, Poppins e
   JetBrains Mono, licença OFL, em `ferramentas/animacoes_fontes.css`), nenhuma
   imagem ou link externo. O GitHub serve o SVG como imagem e bloqueia o que vem
   de fora. O conteúdo animado mora num `<foreignObject>` de 1280 × 640.
10. **Pausável.** Toda classe animada lê `animation-delay: var(--d, 0s)` e
    `animation-play-state: var(--ps, running)`. Para revisar o segundo 12, ponha
    `--ps: paused; --d: -12s` no `div` de classe `raiz`.
11. **Movimento reduzido.** Com `prefers-reduced-motion: reduce`, o SVG fica
    parado no quadro final: a assinatura no banner, o aceite no fluxo.
12. **Duas línguas, mesma linha do tempo.** O `-en.svg` tem os mesmos tempos
    e posições. Todo texto de explicação é traduzido. Nomes que o Senku gera
    (atividades do exemplo, comandos, arquivos) ficam como são.
13. **Rótulo acessível próprio.** Cada SVG tem `role="img"` e um `aria-label`
    igual ao `alt` do README.

## A paleta do Senku

Fundo `#0B1220` com grade de 32 px em `#1E2A44`, como os projetos irmãos, e um
brilho verde-lima no centro. Cores com significado fixo:

| Cor | Hex | Significa |
|---|---|---|
| verde-lima | `#A3E635` | o Senku: a marca, a carta, as fichas da prova |
| azul | `#60A5FA` | o fluxograma (atividades, raias, formatos de desenho) |
| âmbar | `#F59E0B` | o mapeamento (documento, decisões, oportunidades) |
| verde | `#34D399` | provado, respondido, aprovado |
| vermelho | `#F87171` | erro: caminho que falta, mudança sem aceite |
| cinza | `#475569` / `#94A3B8` | o que foi descartado, texto de apoio |
| texto | `#E2E8F0` | texto principal |

Cor nunca é a única pista: todo estado também tem palavra ou ícone (✓, ⚠,
"APROVADO", "LACUNA").

**Sem o personagem.** O Senku usa um símbolo original: um frasco de
laboratório com um raio dentro e bolhas que sobem. Não desenha o personagem de
Dr. Stone.

## Como conferir um SVG contra o roteiro

1. O comentário de linha do tempo do SVG tem as mesmas cenas e os mesmos
   segundos do roteiro.
2. Cada texto da coluna "pt-BR" aparece no SVG em português, e a tradução da
   mesma linha aparece no `-en.svg`.
3. Pausando em cada marca, o quadro bate com "O que aparece".
4. Nenhum elemento fica na tela depois do tempo de saída escrito no roteiro.
5. Os números da cena de resultados são os mesmos da tabela "Resultados" do
   README no dia em que o SVG é gerado.

## Como gravar em vídeo (MP4 ou GIF)

Os SVGs já são o vídeo do README. Para levar a outro lugar (LinkedIn, slide,
apresentação):

1. Abra o SVG no Chrome ou no Edge, em tela cheia, com zoom de 100%.
2. Grave a tela por um laço inteiro (48 s ou 36 s) com o OBS ou a Barra de
   Jogo do Windows (Win + Alt + R).
3. Corte no ponto em que a cena 1 começa: o laço emenda sozinho.
4. Para GIF, converta o MP4 com
   `ffmpeg -i banner.mp4 -vf "fps=20,scale=960:-1" banner.gif`.
