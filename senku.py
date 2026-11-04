#!/usr/bin/env python3
"""
================================================================================
 SENKU — da conversa ao mapa do processo
================================================================================
O cientista de Dr. Stone que transforma "do zero" num roadmap: cada passo, quem
faz, do que depende. A pessoa conta como o trabalho anda; o Senku escreve a carta (`carta.json`), aponta o que falta perguntar,
confere o fluxo com as regras de boa modelagem e desenha: fluxograma em raias
(SVG, BPMN 2.0, draw.io, Mermaid) e o documento de mapeamento (ficha, escopo,
SIPOC, atividades, regras, RACI, indicadores, análise, dores, riscos).

Fluxo:
    novo        cria a pasta do processo com a carta vazia e o roteiro
    entrevista  as perguntas por bloco (abertura, sipoc, passos, decisoes, tempos, gestao, tobe)
    lacunas     o que ainda falta perguntar, por prioridade, e onde a resposta entra na carta
    validar     o fluxo se sustenta? (erros) e segue as boas práticas? (avisos 7PMG / Method and Style)
    desenhar    SVG + BPMN 2.0 XML + .drawio + Mermaid
    analisar    tempos, valor agregado, passagens de bastão, retrabalho, oportunidades (Lean)
    documentar  o mapeamento completo: HTML (imprime em PDF), Word (.docx), Markdown e CSV das atividades
    aprovar     o "sim" do dono do processo (hash da carta); depois disso, mudança = RASCUNHO
    comparar    o que mudou desde o aceite, ou AS-IS x TO-BE
    tobe        começa o TO-BE a partir do AS-IS
    importar    traz um .bpmn que já existe (Bizagi, bpmn.io, Camunda, ARIS...) para uma carta
    situacao    em que etapa está e qual é o próximo passo
    cartao      Memory Card: procura, salva e versiona os processos aprovados no cartão do usuário

Uso:
    python senku.py novo PASTA --processo "NOME" [--codigo C] [--dono "CARGO"]
    python senku.py entrevista [BLOCO]
    python senku.py lacunas CARTA [--todas] [--json]
    python senku.py validar CARTA [--json] [--sem-dicas]
    python senku.py desenhar CARTA [-o PASTA] [--formatos svg,bpmn,drawio,mermaid] [--cores-valor] [--pools]
    python senku.py analisar CARTA [--json]
    python senku.py documentar CARTA [-o PASTA] [--pools]
    python senku.py aprovar CARTA --por "NOME (CARGO)" [--observacao TEXTO]
    python senku.py comparar CARTA [--contra OUTRA_CARTA]
    python senku.py tobe CARTA [-o carta-tobe.json]
    python senku.py importar ARQUIVO.bpmn -o PASTA/carta.json
    python senku.py situacao CARTA
    python senku.py cartao iniciar --repo DONO/memory-card | buscar TERMOS | catalogo
    python senku.py cartao enviar CARTA [--categoria C --secao S --artigo A] [--motivo M] [--confirmar]
    python senku.py cartao marcar REF --status em-uso|rascunho [--confirmar]
    python senku.py status
================================================================================
"""

import argparse
import json
import os
import sys

RAIZ = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, RAIZ)

from carta import VERSAO  # noqa: E402
from carta import analise, aprovacao, entrevista, lacunas, modelo, validacao  # noqa: E402
from carta.util import ErroDeUso, gravar_json, gravar_texto, slug  # noqa: E402

GUIA = """Senku — da conversa ao mapa do processo.

Por onde começar
  python senku.py novo PASTA --processo "Nome"     cria a pasta com a carta vazia e o roteiro
  python senku.py situacao PASTA/carta.json         onde estou e qual é o próximo passo

O fluxo
  1. abertura      objetivo, dono, gatilho, escopo e SIPOC          (entrevista abertura | sipoc)
  2. passos        o caminho principal, quem faz, em que sistema   (entrevista passos)
  3. decisões      perguntas, critérios, exceções, retrabalho       (entrevista decisoes)
  4. lacunas       o que falta, por prioridade                      (lacunas)
  5. validar       o fluxo se sustenta e segue as boas práticas     (validar)
  6. desenhar      fluxograma em raias: SVG, BPMN, draw.io, Mermaid (desenhar)
  7. analisar      tempos, valor, passagens, oportunidades          (analisar)
  8. documentar    o mapeamento completo (HTML, Word, Markdown, CSV) (documentar)
  9. aprovar       o "sim" do dono do processo                      (aprovar)
 10. TO-BE         redesenho a partir das dores                     (tobe, comparar)

Apoio
  importar ARQ.bpmn   traz um mapa que já existe (Bizagi, bpmn.io, Camunda, ARIS, Signavio)
  entrevista [BLOCO]  o roteiro de perguntas (abertura, sipoc, passos, decisoes, tempos, gestao, tobe)
  comparar            o que mudou desde o aceite, ou AS-IS x TO-BE (--contra)
  --pools             (desenhar/documentar) no BPMN, cliente e fornecedor em pool próprio, com mensagens
  cartao              Memory Card: procure antes de mapear, salve depois do aceite (buscar, enviar)

Ajuda de um comando: python senku.py COMANDO --help
"""

ROTEIRO = """# {nome}

Pasta do mapeamento criada pelo Senku. A fonte de tudo é o `carta.json`: o
fluxograma e o documento saem dele (`saida/`), nunca à mão.

1. Entrevista: `python senku.py entrevista abertura` (e os outros blocos).
2. Grave as respostas no `carta.json` (formato em `referencias/carta.md`, na pasta da skill).
3. `python senku.py lacunas carta.json`: o que ainda falta perguntar.
4. `python senku.py validar carta.json` até zerar os erros.
5. `python senku.py desenhar carta.json` e mostre o fluxograma à pessoa.
6. `python senku.py documentar carta.json`: o mapeamento completo.
7. Com o "sim" do dono: `python senku.py aprovar carta.json --por "Nome (cargo)"`.
"""


def _carta(caminho):
    if os.path.isdir(caminho):
        caminho = os.path.join(caminho, 'carta.json')
    return modelo.carregar(caminho)


def _pasta_saida(c, o):
    return o or os.path.join(os.path.dirname(os.path.abspath(c.caminho)), 'saida')


def _base_nome(c):
    p = c.processo
    return slug(' '.join(x for x in (p.get('codigo'), p.get('nome')) if x), 70) + '-' + c.cenario()


# ---------------------------------------------------------------- comandos
def cmd_novo(a):
    destino = os.path.normpath(os.path.join(a.pasta, 'carta.json'))
    if os.path.exists(destino):
        raise ErroDeUso(f'{destino} já existe: para continuar, use python senku.py situacao {destino}')
    gravar_json(destino, modelo.esqueleto(a.processo, a.codigo or '', a.dono or ''))
    gravar_texto(os.path.join(a.pasta, 'ROTEIRO.md'), ROTEIRO.format(nome=a.processo))
    print(f'✓ criada {destino}')
    print('Próximo: python senku.py entrevista abertura  (pergunte poucas por vez e grave na carta)')
    from carta import memory_card
    if memory_card.disponivel()[0]:
        memory_card.lembrete(f'procure no Memory Card se este processo já foi mapeado: python senku.py cartao '
                             f'buscar {a.processo}')


def cmd_entrevista(a):
    return entrevista.imprimir(a.bloco)


def cmd_lacunas(a):
    c = _carta(a.carta)
    qs = lacunas.levantar(c)
    if a.json:
        print(json.dumps([q.como_dict() for q in qs], ensure_ascii=False, indent=2))
        return 0
    lacunas.imprimir(c, qs, None if a.todas else a.max)
    return 0


def cmd_validar(a):
    c = _carta(a.carta)
    achados = validacao.validar(c)
    if a.json:
        print(json.dumps([x.como_dict() for x in achados], ensure_ascii=False, indent=2))
    else:
        validacao.imprimir(c, achados, not a.sem_dicas)
    return 1 if any(x.nivel == 'erro' for x in achados) else 0


FORMATOS = ('svg', 'bpmn', 'drawio', 'mermaid')


def _desenhar(c, pasta, formatos, cores_valor=False, pools=False):
    from carta.layout import calcular
    from saidas import bpmn, drawio, mermaid, svg
    lay = calcular(c)
    base = os.path.join(pasta, _base_nome(c))
    feitos = []
    if 'svg' in formatos:
        gravar_texto(base + '.svg', svg.desenhar(c, lay, cores_valor=cores_valor))
        feitos.append(base + '.svg')
    if 'bpmn' in formatos:
        if pools:
            xml, aviso = bpmn.gerar_com_pools(c)
            if aviso:
                print(f'! {aviso}')
        else:
            xml = bpmn.gerar(c, lay)
        gravar_texto(base + '.bpmn', xml)
        feitos.append(base + '.bpmn')
    if 'drawio' in formatos:
        gravar_texto(base + '.drawio', drawio.gerar(c, lay))
        feitos.append(base + '.drawio')
    if 'mermaid' in formatos:
        gravar_texto(base + '.mmd', mermaid.gerar(c))
        feitos.append(base + '.mmd')
    return feitos


def _erros_antes(c):
    erros = [x for x in validacao.validar(c) if x.nivel == 'erro']
    if erros:
        print(f'! {len(erros)} erro(s) na carta: o desenho sai, mas pode estar incompleto. Rode validar para ver.')
    return erros


def cmd_desenhar(a):
    c = _carta(a.carta)
    formatos = [f.strip() for f in a.formatos.split(',') if f.strip()]
    ruins = [f for f in formatos if f not in FORMATOS]
    if ruins:
        raise ErroDeUso(f'formato desconhecido: {", ".join(ruins)} (use {", ".join(FORMATOS)})')
    _erros_antes(c)
    for arq in _desenhar(c, _pasta_saida(c, a.o), formatos, a.cores_valor, a.pools):
        print(f'✓ {arq}')
    from carta.layout import calcular, numerar
    nums = numerar(c, calcular(c))
    print('Números do desenho: ' + ', '.join(f'{n}={eid}' for eid, n in sorted(nums.items(), key=lambda x: x[1])))
    print('Abrir: .svg no navegador · .bpmn no bpmn.io, Camunda Modeler ou Bizagi (importar) · '
          '.drawio no diagrams.net · .mmd em qualquer visualizador Mermaid.')
    return 0


def cmd_analisar(a):
    c = _carta(a.carta)
    r = analise.analisar(c)
    if a.json:
        print(json.dumps(r, ensure_ascii=False, indent=2, default=list))
    else:
        analise.imprimir(c, r, None if a.todas else 10)
    return 0


def cmd_documentar(a):
    from saidas import docx, documento
    c = _carta(a.carta)
    pasta = _pasta_saida(c, a.o)
    _erros_antes(c)
    d = documento.montar(c)
    feitos = _desenhar(c, pasta, FORMATOS, cores_valor=any(e['valor'] for e in d['ativ']), pools=a.pools)
    base = os.path.join(pasta, _base_nome(c))
    gravar_texto(base + '.html', documento.html_documento(c, d))
    gravar_texto(base + '.md', documento.markdown_documento(c, d, os.path.basename(base) + '.svg'))
    gravar_texto(base + '-atividades.csv', documento.csv_atividades(c, d), bom=True)
    docx.gerar(c, d, base + '.docx')
    for arq in [base + '.html', base + '.docx', base + '.md', base + '-atividades.csv'] + feitos:
        print(f'✓ {arq}')
    print(f'Situação: {d["texto_status"]}')
    if d['status'] != 'aprovada':
        print('Próximo: mostre o HTML ao dono; com o "sim", python senku.py aprovar <carta> --por "Nome (cargo)".')
    return 0


def cmd_aprovar(a):
    c = _carta(a.carta)
    destino, reg = aprovacao.aprovar(c, a.por, a.observacao or '')
    print(f'✓ aceite de {reg["por"]} em {reg["quando"]} gravado em {destino}')
    qs = lacunas.levantar(c)
    graves = [q for q in qs if q.prioridade in (1, 2, 3)]
    if graves:
        print(f'Atenção: o aceite foi gravado com {len(qs)} lacuna(s) aberta(s), {len(graves)} de prioridade 1 a 3 '
              '(papéis, tempos, percentuais). Registre na observação do aceite que o dono aprovou assim, ou '
              'feche as lacunas e aprove de novo.')
    print('Gere o documento de novo (documentar) para sair sem a marca de RASCUNHO.')
    _lembrar_cartao(c)
    return 0


def _lembrar_cartao(c):
    """Depois do aceite: o processo aprovado vai para o Memory Card (prévia; envio só com o "sim")."""
    from carta import memory_card
    ok, motivo = memory_card.disponivel()
    if ok:
        memory_card.lembrete(f'processo aprovado: ofereça salvar no Memory Card. Prévia: python senku.py cartao '
                             f'enviar {c.caminho} (mostre a prévia; --confirmar só com o "sim")')
    elif memory_card.configurado():
        memory_card.lembrete(f'o Memory Card não está disponível aqui ({motivo}). Entregue os arquivos e diga que '
                             'salvar é pelo Claude Code na máquina do cartão.')


def cmd_comparar(a):
    c = _carta(a.carta)
    if a.contra:
        antes, depois = c, _carta(a.contra)
        def rotulo(caminho):
            # duas cartas com o mesmo nome de arquivo: mostra a pasta também
            base = os.path.basename(caminho)
            if base == os.path.basename(depois.caminho if caminho == c.caminho else c.caminho):
                return os.path.join(os.path.basename(os.path.dirname(os.path.abspath(caminho))), base)
            return base
        titulo = f'{c.cenario().upper()} ({rotulo(c.caminho)}) x {depois.cenario().upper()} ' \
                 f'({rotulo(depois.caminho)})'
    else:
        antes, reg = aprovacao.carregar_retrato_aprovado(c)
        depois = c
        titulo = f'aceite de {reg["por"]} em {reg["quando"]} x carta atual'
    linhas, numeros = aprovacao.comparar(antes, depois, None if a.contra else reg['retrato'])
    print(f'Comparação: {titulo}')
    if not linhas:
        print('  nenhuma diferença no fluxo')
    if not a.contra:
        fora = aprovacao.mudou_fora_do_fluxo(c, reg)
        outras = [x for x in (fora or []) if x != 'fluxo']
        if fora is None and not linhas and aprovacao.hash_carta(c) != reg.get('hash'):
            print('  - a carta mudou desde o aceite (aceite antigo: não guarda qual parte; aprove de novo)')
        if fora and 'fluxo' in fora and not linhas:
            print('  - o fluxo mudou só na escrita (ids, ordem, formato): o desenho e as regras são os mesmos')
        if outras:
            print(f'  - mudou fora do desenho: {", ".join(outras)} (o aceite vale para a carta inteira: aprove '
                  'de novo)')
    for _, texto in linhas:
        print(f'  - {texto}')
    from carta.util import formatar_minutos
    print('\n  {:<27} {:>13} {:>13} {:>14}'.format('', 'antes', 'depois', 'diferença'))
    for rot, x, y in numeros:
        if isinstance(x, float) or isinstance(y, float):
            dif = y - x
            sinal = '+' if dif > 0 else '-' if dif < 0 else ''
            print('  {:<27} {:>13} {:>13} {:>14}'.format(rot, formatar_minutos(x), formatar_minutos(y),
                                                          sinal + formatar_minutos(abs(dif)) if dif else '='))
        else:
            print('  {:<27} {:>13} {:>13} {:>+14}'.format(rot, x, y, y - x))
    if not a.contra:
        print('\nOs números "antes" vêm do retrato do aceite.')
    print('Próximo: leve as diferenças ao dono do processo; com o "sim", aprovar de novo.' if not a.contra else
          'Próximo: use as diferenças no documento do TO-BE (dores resolvidas, ganhos de tempo).')
    return 0


def cmd_tobe(a):
    c = _carta(a.carta)
    if c.cenario() != 'as-is':
        raise ErroDeUso('o TO-BE parte de uma carta AS-IS (processo.cenario = "as-is")')
    destino = a.o or os.path.join(os.path.dirname(os.path.abspath(c.caminho)), 'carta-tobe.json')
    if os.path.exists(destino):
        raise ErroDeUso(f'{destino} já existe')
    import copy
    dados = copy.deepcopy(c.dados)
    p = dados.setdefault('processo', {})
    p['cenario'] = 'to-be'
    p['versao'] = '0.1'
    p['base_as_is'] = os.path.basename(c.caminho)
    dados['historico'] = [{'versao': '0.1', 'mudanca': f'TO-BE iniciado a partir de {os.path.basename(c.caminho)}'}]
    gravar_json(destino, dados)
    print(f'✓ {destino} (cópia do AS-IS com cenário TO-BE)')
    print('Próximo: aplique as melhorias na carta TO-BE (cada uma resolve uma dor) e compare:')
    print(f'  python senku.py comparar {c.caminho} --contra {destino}')
    return 0


def cmd_importar(a):
    from carta import importar
    carta, avisos = importar.importar(a.arquivo, getattr(a, 'pool', None))
    if getattr(a, 'base', None):
        # o .bpmn não leva nomes de pessoas (participantes, autores do histórico): vêm da carta de antes
        from carta.util import ler_json
        base = ler_json(a.base)
        from carta.importar import completar_com_base
        avisos += completar_com_base(carta, base)
    carta.pop('_extensao_senku', None)
    # "detalhe" relativo: era a partir da carta original; refaz a partir da carta nova, se o arquivo existe
    base_bpmn = os.path.dirname(os.path.abspath(a.arquivo))
    destino_dir = os.path.dirname(os.path.abspath(a.o))
    for e in carta.get('elementos') or []:
        det = e.get('detalhe')
        if isinstance(det, str) and det and not os.path.isabs(det):
            for base in (base_bpmn, os.path.dirname(base_bpmn)):
                cand = os.path.normpath(os.path.join(base, det))
                if os.path.exists(cand):
                    e['detalhe'] = os.path.relpath(cand, destino_dir).replace(os.sep, '/')
                    break
    if os.path.exists(a.o):
        raise ErroDeUso(f'{a.o} já existe')
    gravar_json(a.o, carta)
    print(f'✓ {a.o}: {len(carta["elementos"])} elementos, {len(carta["papeis"])} papéis')
    for x in avisos:
        print(f'  ! {x}')
    print('Próximo: python senku.py validar e lacunas na carta importada; confirme papéis e regras com o dono.')
    return 0


def cmd_situacao(a):
    c = _carta(a.carta)
    achados = validacao.validar(c)
    erros = [x for x in achados if x.nivel == 'erro']
    qs = lacunas.levantar(c)
    estado, reg = aprovacao.situacao_aprovacao(c)
    print(f'{c.titulo()} · {c.cenario().upper()} · {len(c.elementos)} elementos')
    if not c.elementos:
        etapa, prox = 'entrevista', 'python senku.py entrevista abertura, depois passos; grave na carta'
    elif erros:
        etapa, prox = 'fluxo com erro', f'python senku.py validar {c.caminho} ({len(erros)} erro(s))'
    elif estado == 'mudou':
        fora = aprovacao.mudou_fora_do_fluxo(c, reg)
        etapa, prox = ('mudou depois do aceite' + (f' ({", ".join(fora)})' if fora else ''),
                       f'python senku.py comparar {c.caminho}; leve as mudanças ao dono e aprove de novo')
    elif estado == 'aprovada':
        etapa = 'aprovado' + (f' (com {len(qs)} lacuna(s) aberta(s))' if qs else '')
        prox = (f'aceite de {reg["por"]} em {reg["quando"]}. Próximo: documentar (versão final) ou tobe '
                '(redesenho)')
    elif any(q.prioridade in (1, 3) for q in qs):
        etapa, prox = 'entrevista', f'python senku.py lacunas {c.caminho} ({len(qs)} lacuna(s))'
    elif estado is None:
        etapa, prox = 'revisão com o dono', (f'python senku.py documentar {c.caminho}; mostre e, com o "sim", '
                                              'aprovar --por "Nome (cargo)"')
    else:
        etapa, prox = 'aprovado', (f'aceite de {reg["por"]} em {reg["quando"]}. Próximo: documentar (versão final) '
                                   'ou tobe (redesenho)')
    print(f'Etapa: {etapa}')
    n = validacao.resumo(achados)
    print(f'Validação: {n["erro"]} erro(s), {n["aviso"]} aviso(s) · lacunas: {len(qs)}')
    print(f'Próximo: {prox}')
    from carta import memory_card
    no_cartao = memory_card.situacao_da_carta(c)
    if no_cartao and estado == 'aprovada':
        print('Memory Card: ' + {'salvo': 'este aceite está salvo no cartão',
                                 'desatualizado': 'o cartão tem uma versão anterior; salve a nova '
                                                  f'(python senku.py cartao enviar {c.caminho} --motivo "...")',
                                 'ausente': f'ainda não salvo (python senku.py cartao enviar {c.caminho})'}[no_cartao])
    return 0


def cmd_status(a):
    print(f'Senku {VERSAO} · Python {sys.version.split()[0]} · pasta {RAIZ}')
    from carta import memory_card
    if memory_card.configurado():
        ok, motivo = memory_card.disponivel()
        if ok:
            cfg = memory_card.config()
            meus = [f for f in memory_card.ler_catalogo(cfg['pasta']) if f.get('solucao') == memory_card.SOLUCAO]
            print(f'Memory Card: {cfg["repo"] or "local"} · pasta {cfg["pasta"]} · {len(meus)} processo(s) do Senku')
        else:
            print(f'Memory Card: configurado, mas NÃO funciona aqui ({motivo})')
    else:
        print('Memory Card: não configurado (python senku.py cartao iniciar --repo SEU_USUARIO/memory-card)')
    return 0


# ---------------------------------------------------------------- Memory Card
def cmd_cartao(a):
    from carta import memory_card as mc
    try:
        return _cartao(mc, a)
    except mc.CartaoRecusado as e:
        print(f'✗ RECUSADO: {e}')
        return 1


def _cartao(mc, a):
    if a.acao == 'iniciar':
        cfg = mc.iniciar(a.repo, a.pasta, a.publico, a.substituir)
        print(f'✓ cartão: {cfg["repo"] or "local (sem GitHub)"} ({"PÚBLICO" if cfg["publico"] else "privado"})')
        print(f'  pasta: {cfg["pasta"]}')
        print(f'  configuração: {mc.caminho_config()} (fora do git e do pacote)')
        return 0
    if a.acao == 'catalogo':
        fichas = mc.ler_catalogo(mc.preparar_pasta())
        if not a.todas:
            fichas = [f for f in fichas if f.get('solucao') == mc.SOLUCAO]
        if a.json:
            print(json.dumps(fichas, ensure_ascii=False, indent=2))
        else:
            print(mc.gerar_catalogo_md(fichas) if fichas else 'nenhum processo do Senku no cartão')
        return 0
    if a.acao == 'buscar':
        achados = mc.buscar(mc.preparar_pasta(), a.termos, a.limite)
        if not achados:
            print('nenhum save para esses termos')
        for pontos, f in achados:
            print(f'{pontos:3d}  {f["ref"]}  (v{f["versao"]}, {f["status"]})  {f["artigo"]} — {f.get("descricao", "")}')
        return 0
    if a.acao == 'marcar':
        pasta = mc.preparar_pasta()
        ficha = mc.ler_ficha(pasta, a.ref)
        print(f'{a.ref}: {ficha["status"]} → {a.status}')
        if ficha['status'] == a.status:
            print('nada a mudar')
            return 0
        if not a.confirmar:
            print('prévia: nada foi gravado. Repita com --confirmar.')
            return 0
        mc.marcar(pasta, a.ref, a.status)
        print('✓ enviado')
        return 0
    pasta = mc.preparar_pasta()                    # enviar
    e = mc.montar_envio(a.carta, pasta, a.categoria, a.secao, a.artigo, a.descricao, a.texto, a.motivo, a.status,
                        a.relacionado or (), a.sem_aceite)
    cfg = mc.config()
    try:
        fi = e['ficha']
        print(f'destino: {cfg["repo"] or cfg["pasta"]} → {mc.SAVES}/{e["ref"]}/  versão {fi["versao"]}'
              + (' (SUBSTITUI a anterior)' if e['substitui'] else ' (save novo)'))
        print(f'status: {fi["status"]} · aceite: ' + (f'{fi["aceite"]["por"]} em {fi["aceite"]["quando"]}'
                                                      if fi['aceite'] else 'nenhum'))
        print('arquivos: ' + ', '.join(sorted(os.listdir(e['tmp']))))
        for av in e['avisos']:
            print(f'AVISO: {av}')
        if e['novos_relacionados']:
            print('relacionados novos (ganham o link de volta): ' + ', '.join(e['novos_relacionados']))
        print('\nficha:')
        print(json.dumps(fi, ensure_ascii=False, indent=2))
        if e['substitui']:
            print('\n--- diff da carta ---\n' + (e['diff_carta'] or '(carta igual)'))
            print('--- diff do artigo ---\n' + (e['diff_readme'] or '(artigo igual)'))
        else:
            print('\n--- artigo ---\n' + e['readme'])
        if not a.confirmar:
            print('prévia: nada foi gravado. Mostre ao usuário e, com o "sim", repita com --confirmar.')
            return 0
        mc.gravar_envio(e, pasta)
    finally:
        mc.descartar(e)
    if cfg['repo']:
        print(f'✓ enviado: https://github.com/{cfg["repo"]}/tree/main/{mc.SAVES}/{e["ref"]}')
    else:
        print(f'✓ gravado no cartão local: {e["destino"]}')
    return 0


class _Parser(argparse.ArgumentParser):
    """argparse falando português."""
    TROCAS = (('usage:', 'uso:'), ('positional arguments', 'argumentos'), ('options:', 'opções:'),
              ('optional arguments:', 'opções:'), ('show this help message and exit', 'mostra esta ajuda'))

    def format_help(self):
        texto = super().format_help()
        for x, y in self.TROCAS:
            texto = texto.replace(x, y)
        return texto

    def format_usage(self):
        return super().format_usage().replace('usage:', 'uso:')

    def error(self, message):
        import difflib
        if 'invalid choice' in message:
            escolhido = message.split("'")[1] if "'" in message else ''
            opcoes = [x.strip(" '") for x in message.split('choose from')[-1].strip(' ()').split(',')]
            parecido = difflib.get_close_matches(escolhido, opcoes, n=1)
            if parecido:
                message += f'. Você quis dizer: {parecido[0]}?'
        message = (message.replace('the following arguments are required', 'faltam os argumentos')
                   .replace('invalid choice', 'opção inválida').replace('choose from', 'escolha entre')
                   .replace('unrecognized arguments', 'argumentos desconhecidos'))
        self.print_usage(sys.stderr)
        self.exit(2, f'{self.prog}: {message}\nVeja: python senku.py (sem argumentos) para o roteiro.\n')


def main(argv=None):
    argv = sys.argv[1:] if argv is None else argv
    if not argv:
        print(GUIA)
        return 0
    ap = _Parser(prog='senku', description='Da conversa ao mapa do processo.')
    sub = ap.add_subparsers(dest='cmd', required=True, parser_class=_Parser, metavar='COMANDO')

    s = sub.add_parser('novo', help='cria a pasta do processo com a carta vazia')
    s.add_argument('pasta')
    s.add_argument('--processo', required=True, help='nome do processo')
    s.add_argument('--codigo')
    s.add_argument('--dono', help='cargo do dono do processo')
    s.set_defaults(func=cmd_novo)

    s = sub.add_parser('entrevista', help='o roteiro de perguntas, por bloco')
    s.add_argument('bloco', nargs='?', help='abertura, sipoc, passos, decisoes, tempos, gestao, tobe')
    s.set_defaults(func=cmd_entrevista)

    s = sub.add_parser('lacunas', help='o que falta perguntar, por prioridade')
    s.add_argument('carta')
    s.add_argument('--todas', action='store_true')
    s.add_argument('--max', type=int, default=7)
    s.add_argument('--json', action='store_true')
    s.set_defaults(func=cmd_lacunas)

    s = sub.add_parser('validar', help='erros de fluxo e avisos de boa modelagem')
    s.add_argument('carta')
    s.add_argument('--json', action='store_true')
    s.add_argument('--sem-dicas', action='store_true')
    s.set_defaults(func=cmd_validar)

    s = sub.add_parser('desenhar', help='SVG, BPMN 2.0, draw.io e Mermaid')
    s.add_argument('carta')
    s.add_argument('-o', help='pasta de saída (padrão: saida/ ao lado da carta)')
    s.add_argument('--formatos', default=','.join(FORMATOS))
    s.add_argument('--cores-valor', action='store_true', help='borda da atividade pela cor do valor (VA/NAV-N/NAV)')
    s.add_argument('--pools', action='store_true', help='no BPMN, cada papel externo vira um pool com fluxo de mensagem')
    s.set_defaults(func=cmd_desenhar)

    s = sub.add_parser('analisar', help='tempos, valor, passagens, retrabalho e oportunidades')
    s.add_argument('carta')
    s.add_argument('--json', action='store_true')
    s.add_argument('--todas', action='store_true', help='mostra todas as oportunidades (padrão: as 10 maiores)')
    s.set_defaults(func=cmd_analisar)

    s = sub.add_parser('documentar', help='o mapeamento completo: HTML, Word, Markdown, CSV e os desenhos')
    s.add_argument('--pools', action='store_true', help='no BPMN, cada papel externo vira um pool com fluxo de mensagem')
    s.add_argument('carta')
    s.add_argument('-o', help='pasta de saída (padrão: saida/ ao lado da carta)')
    s.set_defaults(func=cmd_documentar)

    s = sub.add_parser('aprovar', help='grava o "sim" do dono do processo')
    s.add_argument('carta')
    s.add_argument('--por', required=True, help='"Nome (cargo)" de quem aprovou')
    s.add_argument('--observacao')
    s.set_defaults(func=cmd_aprovar)

    s = sub.add_parser('comparar', help='o que mudou desde o aceite, ou contra outra carta (AS-IS x TO-BE)')
    s.add_argument('carta')
    s.add_argument('--contra', help='outra carta (ex.: carta-tobe.json)')
    s.set_defaults(func=cmd_comparar)

    s = sub.add_parser('tobe', help='começa o TO-BE a partir da carta AS-IS')
    s.add_argument('carta')
    s.add_argument('-o', help='padrão: carta-tobe.json ao lado')
    s.set_defaults(func=cmd_tobe)

    s = sub.add_parser('importar', help='traz um .bpmn que já existe para uma carta')
    s.add_argument('arquivo')
    s.add_argument('-o', required=True, help='carta de destino (ex.: PASTA/carta.json)')
    s.add_argument('--pool', help='qual pool trazer, quando o arquivo tem mais de um (nome do participante)')
    s.add_argument('--base', help='carta de antes (volta do modelador): traz participantes e histórico dela')
    s.set_defaults(func=cmd_importar)

    s = sub.add_parser('situacao', help='em que etapa está e o próximo passo')
    s.add_argument('carta')
    s.set_defaults(func=cmd_situacao)

    sub.add_parser('status', help='versão do Senku e o Memory Card').set_defaults(func=cmd_status)

    for nome in ('cartao', 'memory-card'):
        s = sub.add_parser(nome, help='Memory Card: procura, salva e versiona os processos aprovados'
                           if nome == 'cartao' else 'o mesmo que cartao')
        cs = s.add_subparsers(dest='acao', required=True, parser_class=_Parser, metavar='ACAO')
        x = cs.add_parser('iniciar', help='liga ao cartão (o mesmo do Vegapunk) ou cria um privado')
        x.add_argument('--repo', help='DONO/NOME no GitHub (sem ele: cartão só local, com --pasta)')
        x.add_argument('--pasta')
        x.add_argument('--publico', action='store_true')
        x.add_argument('--substituir', action='store_true', help='troca o cartão desta instalação')
        x = cs.add_parser('catalogo', help='os processos salvos')
        x.add_argument('--todas', action='store_true', help='todas as soluções, não só o Senku')
        x.add_argument('--json', action='store_true')
        x = cs.add_parser('buscar', help='procura no cartão antes de mapear')
        x.add_argument('termos', nargs='+')
        x.add_argument('--limite', type=int, default=10)
        x = cs.add_parser('enviar', help='salva o processo aprovado (prévia; grava só com --confirmar)')
        x.add_argument('carta')
        x.add_argument('--categoria', help='padrão: a área da carta')
        x.add_argument('--secao', help='padrão: o macroprocesso da carta')
        x.add_argument('--artigo', help='padrão: "CÓDIGO · Nome (CENÁRIO)"')
        x.add_argument('--descricao', help='padrão: o objetivo do processo')
        x.add_argument('--texto', help='corpo do artigo em Markdown (padrão: montado da carta)')
        x.add_argument('--motivo', help='obrigatório numa versão nova')
        x.add_argument('--status', choices=('rascunho', 'em-uso'))
        x.add_argument('--relacionado', action='append', help='REF de outro save do Senku')
        x.add_argument('--sem-aceite', action='store_true', help='salva sem aceite válido, como rascunho')
        x.add_argument('--confirmar', action='store_true')
        x = cs.add_parser('marcar', help='muda o status de um save')
        x.add_argument('ref')
        x.add_argument('--status', required=True, choices=('rascunho', 'em-uso'))
        x.add_argument('--confirmar', action='store_true')
        s.set_defaults(func=cmd_cartao)
    a = ap.parse_args(argv)
    return a.func(a) or 0


if __name__ == '__main__':
    if hasattr(sys.stdout, 'reconfigure'):
        sys.stdout.reconfigure(encoding='utf-8')
        sys.stderr.reconfigure(encoding='utf-8')
    try:
        sys.exit(main())
    except ErroDeUso as e:
        print(f'✗ {e}')
        sys.exit(1)
    except (KeyboardInterrupt, SystemExit):
        raise
    except Exception as e:                          # nunca um traceback cru: diz o que fazer
        if os.environ.get('SENKU_DEPURAR'):
            raise
        print(f'✗ erro interno do Senku ({type(e).__name__}: {e}).')
        print('  Confira o tipo dos campos da carta (texto, lista [ ] ou objeto { }) em referencias/carta.md e '
              'rode validar. Para ver o detalhe técnico: SENKU_DEPURAR=1.')
        sys.exit(2)
