"""
O aceite do dono do processo e a comparação entre versões.

O aceite grava, ao lado da carta, `<carta>.aprovacao.json`: quem aprovou,
quando, o hash da carta e o retrato do fluxo. Mudou a carta depois disso? O
documento sai marcado como RASCUNHO até um novo aceite, e o `comparar` diz o
que mudou. O mesmo `comparar` põe o AS-IS ao lado do TO-BE.
"""

import datetime
import hashlib
import json
import os

from .analise import analisar
from .modelo import NOS_DE_TRABALHO
from .util import ErroDeUso, gravar_json, ler_json, sem_acento


def hash_carta(c):
    # o histórico de versões é registro do documento, não conteúdo aprovado: anotar "aprovado em..." não
    # transforma o mapa em rascunho
    dados = {k: v for k, v in c.dados.items() if k != 'historico'}
    texto = json.dumps(dados, ensure_ascii=False, sort_keys=True, separators=(',', ':'))
    return hashlib.sha256(texto.encode('utf-8')).hexdigest()


_SECOES = {'processo': 'dados do processo', 'elementos': 'fluxo', 'papeis': 'papéis', 'sistemas': 'sistemas',
           'regras': 'regras', 'indicadores': 'indicadores', 'riscos': 'riscos', 'dores': 'dores',
           'melhorias': 'melhorias', 'pendencias': 'pendências', 'participantes': 'participantes',
           'documentos': 'documentos', 'glossario': 'glossário', 'premissas': 'premissas', 'normas': 'normas'}


def hash_secoes(c):
    """Um hash por parte da carta: diz O QUE mudou quando o aceite deixa de valer."""
    return {k: hashlib.sha256(json.dumps(v, ensure_ascii=False, sort_keys=True, separators=(',', ':'))
                              .encode('utf-8')).hexdigest()
            for k, v in c.dados.items() if k != 'historico'}


def mudou_fora_do_fluxo(c, reg):
    """Partes da carta que mudaram desde o aceite (nomes legíveis). None: aceite antigo, sem o detalhe."""
    antes = (reg or {}).get('secoes')
    if antes is None:
        return None
    agora = hash_secoes(c)
    return [_SECOES.get(k, k) for k in sorted(set(antes) | set(agora), key=str) if antes.get(k) != agora.get(k)]


def arquivo_aprovacao(caminho):
    base = caminho[:-5] if caminho.endswith('.json') else caminho
    return base + '.aprovacao.json'


def retrato(c):
    return {
        'elementos': {eid: {'nome': e['nome'], 'tipo': e['tipo'], 'papel': c.nome_papel(e['papel']),
                            'sistema': sorted(c.nome_sistema(s) for s in e['sistema']),
                            'tempo': e['tempo_texto'], 'regras': list(e['regras']),
                            'raci': {k: sorted(c.nome_papel(p) for p in v) for k, v in e['raci'].items() if v},
                            'valor': e['valor'] or '', 'automatizada': e['automatizada'],
                            'encerra': e['encerra'], 'gatilho': e['gatilho'],
                            'anexo': e['anexo'], 'interrompe': e['interrompe'],
                            'descricao': e['descricao'], 'como': list(e['como']), 'entradas': list(e['entradas']),
                            'saidas': list(e['saidas']), 'excecoes': list(e['excecoes']),
                            'segue': sorted(([f['rotulo'], f['para'], f['percentual']] for f in c.saidas[eid]),
                                            key=lambda x: (x[0], x[1]))}
                      for eid, e in c.elementos.items()},
        'regras': {rid: r.get('texto', '') for rid, r in c.regras.items()},
        'indicadores': {str(i.get('nome') or '?'): {k: i.get(k, '') for k in ('formula', 'meta', 'polaridade',
                                                                       'periodicidade', 'fonte', 'dono', 'atual')}
                        for i in c.indicadores},
        'riscos': {str(r.get('id') or r.get('descricao') or '?'): {k: r.get(k, '') for k in (
            'descricao', 'controle', 'tipo_controle', 'probabilidade', 'impacto')} for r in c.riscos},
        'dores': {str(d.get('id') or d.get('descricao') or '?'): d.get('descricao', '') for d in c.dores},
        'melhorias': {str(m.get('id') or m.get('descricao') or '?'): {k: m.get(k, '') for k in (
            'descricao', 'responsavel', 'prazo', 'status', 'impacto', 'esforco')} for m in c.melhorias},
        'processo': dict({k: c.processo.get(k, '') for k in ('nome', 'objetivo', 'dono', 'gatilho', 'resultado',
                                                              'prazo_informado', 'volume', 'frequencia')},
                         escopo={k: v for k, v in (c.processo.get('escopo') or {}).items() if v},
                         sipoc={k: list(v) for k, v in c.sipoc.items() if v}),
    }


def aprovar(c, por, observacao=''):
    if not por or not por.strip():
        raise ErroDeUso('diga quem aprovou: --por "Nome (cargo)"')
    from .validacao import validar
    erros = [a for a in validar(c) if a.nivel == 'erro']
    if erros:
        raise ErroDeUso(f'a carta tem {len(erros)} erro(s) de fluxo; o aceite vale para um mapa que se sustenta. '
                        'Rode validar e corrija antes.')
    reg = {
        'por': por.strip(), 'quando': datetime.datetime.now().strftime('%d/%m/%Y %H:%M'),
        'hash': hash_carta(c), 'versao': c.processo.get('versao', ''), 'cenario': c.cenario(),
        'observacao': observacao, 'retrato': retrato(c), 'secoes': hash_secoes(c),
    }
    destino = arquivo_aprovacao(c.caminho)
    if os.path.exists(destino):
        # o aceite novo não apaga os anteriores: quem aprovou o quê e quando fica registrado
        try:
            velho = ler_json(destino)
            anteriores = velho.pop('anteriores', [])
            velho.pop('retrato', None)
            velho.pop('secoes', None)
            reg['anteriores'] = anteriores + [velho]
        except Exception:
            pass
    gravar_json(destino, reg)
    return destino, reg


def situacao_aprovacao(c):
    """(None | 'aprovada' | 'mudou', registro)."""
    if not c.caminho:
        return None, None
    arq = arquivo_aprovacao(c.caminho)
    if not os.path.exists(arq):
        return None, None
    reg = ler_json(arq)
    return ('aprovada' if reg.get('hash') == hash_carta(c) else 'mudou'), reg


def _chave_nome(n):
    return sem_acento(n or '').lower().strip()


def _casar(ea, ed):
    """Qual elemento de antes é qual de depois. Por id; o que sobrar, por tipo + nome (no TO-BE os ids costumam
    mudar); o que ainda sobrar (portas e eventos sem nome), pela vizinhança: mesmo tipo e ligado aos mesmos
    vizinhos já casados."""
    pares = {i: i for i in ea if i in ed and ea[i]['tipo'] == ed[i]['tipo']}
    usados = set(pares.values())
    por_nome = {}
    for j, v in ed.items():
        if j not in usados and _chave_nome(v['nome']):
            por_nome.setdefault((v['tipo'], _chave_nome(v['nome'])), []).append(j)
    for i, v in ea.items():
        k = (v['tipo'], _chave_nome(v['nome']))
        if i not in pares and k[1] and por_nome.get(k):
            pares[i] = por_nome[k].pop(0)
    # um id que ficou (mas mudou de tipo) só casa se nada melhor apareceu
    usados = set(pares.values())

    def vizinhos(el):
        seg = {eid: {s[1] for s in v.get('segue') or []} for eid, v in el.items()}
        ant = {eid: set() for eid in el}
        for eid, ss in seg.items():
            for s in ss:
                if s in ant:
                    ant[s].add(eid)
        return seg, ant
    seg_a, ant_a = vizinhos(ea)
    seg_d, ant_d = vizinhos(ed)
    mudou = True
    while mudou:
        mudou = False
        for i in ea:
            if i in pares:
                continue
            alvo_seg = {pares[x] for x in seg_a[i] if x in pares}
            alvo_ant = {pares[x] for x in ant_a[i] if x in pares}
            if not alvo_seg and not alvo_ant:
                continue
            melhor, nota = None, 0
            for j in ed:
                if j in usados or ed[j]['tipo'] != ea[i]['tipo']:
                    continue
                n = len(alvo_seg & seg_d[j]) + len(alvo_ant & ant_d[j])
                if n > nota:
                    melhor, nota = j, n
            if melhor:
                pares[i] = melhor
                usados.add(melhor)
                mudou = True
    return pares


def comparar(antes, depois, retrato_antes=None):
    """Diferença entre duas cartas (ou entre a aprovada e a atual). antes/depois: Carta. Com o aceite, o
    retrato gravado nele é o "antes" (a carta fantasma só serve para os números)."""
    ra, rd = retrato_antes or retrato(antes), retrato(depois)
    ea, ed = ra['elementos'], rd['elementos']
    pares = _casar(ea, ed)
    usados = set(pares.values())
    linhas = []
    for i, v in ea.items():
        if i not in pares and v['tipo'] in NOS_DE_TRABALHO + ('decisao',):
            linhas.append(('removido', f'{v["tipo"]} removida: "{v["nome"]}" ({v["papel"]})'))
    for i, v in ed.items():
        if i not in usados and v['tipo'] in NOS_DE_TRABALHO + ('decisao',):
            linhas.append(('novo', f'{v["tipo"]} nova: "{v["nome"]}" ({v["papel"]})'))
    for i, j in pares.items():
        a, d = ea[i], ed[j]
        if a['nome'] != d['nome']:
            linhas.append(('mudou', f'"{a["nome"]}" passou a se chamar "{d["nome"] or "(" + d["tipo"] + ")"}"'))
        # papel de evento, fim e borda é herdado de quem vem antes: a mudança já aparece na atividade
        if a['papel'] != d['papel'] and d['tipo'] in NOS_DE_TRABALHO + ('decisao',):
            linhas.append(('mudou', f'"{d["nome"] or "(" + d["tipo"] + ")"}": responsável {a["papel"]} -> {d["papel"]}'))
        if a['sistema'] != d['sistema']:
            linhas.append(('mudou', f'"{d["nome"] or "(" + d["tipo"] + ")"}": sistema {", ".join(a["sistema"]) or "manual"} -> '
                           f'{", ".join(d["sistema"]) or "manual"}'))
        linhas.extend(_diferenca_de_saidas(a, d, pares, ea, ed))
        for campo, rot in (('raci', 'RACI'), ('valor', 'valor'), ('automatizada', 'automática'),
                           ('encerra', 'fim terminal'), ('gatilho', 'gatilho'), ('interrompe', 'interrompe'),
                           ('descricao', 'descrição'),
                           ('como', 'como fazer'), ('entradas', 'entradas'), ('saidas', 'saídas'),
                           ('excecoes', 'exceções')):
            if campo in a and campo in d and a[campo] != d[campo]:
                linhas.append(('mudou', f'"{d["nome"] or "(" + d["tipo"] + ")"}": {rot} {_curto(a[campo])} -> {_curto(d[campo])}'))
        if a.get('tempo', {}) != d.get('tempo', {}) and 'tempo' in a and 'tempo' in d:
            linhas.append(('mudou', f'"{d["nome"] or "(" + d["tipo"] + ")"}": tempo {_tempo_txt(a["tempo"])} -> {_tempo_txt(d["tempo"])}'))
        if sorted(a.get('regras', [])) != sorted(d.get('regras', [])) and 'regras' in a and 'regras' in d:
            linhas.append(('mudou', f'"{d["nome"] or "(" + d["tipo"] + ")"}": regras {", ".join(a["regras"]) or "nenhuma"} -> '
                           f'{", ".join(d["regras"]) or "nenhuma"}'))
    for chave, rot in (('indicadores', 'indicador'), ('riscos', 'risco'), ('dores', 'dor'), ('melhorias', 'melhoria'),
                       ('processo', 'processo')):
        xa, xd = ra.get(chave), rd.get(chave)
        if xa is None or xd is None:
            continue
        for k in sorted(set(xa) | set(xd), key=str):
            if k not in xd:
                linhas.append(('mudou', f'{rot} removido: {k}'))
            elif k not in xa:
                linhas.append(('mudou', f'{rot} novo: {k}'))
            elif xa[k] != xd[k]:
                if isinstance(xd[k], dict) and not isinstance(xa[k], dict):
                    # aceite antigo guardava só o texto: compara só o texto
                    if xa[k] != xd[k].get('descricao'):
                        linhas.append(('mudou', f'{rot} {k}: {_curto(xa[k])} -> {_curto(xd[k].get("descricao"))}'))
                elif isinstance(xa[k], dict):
                    # só os campos que os dois retratos têm (aceite antigo não guardava todos)
                    mud = [f'{c}: {_curto(xa[k].get(c))} -> {_curto(xd[k].get(c))}' for c in xd[k]
                           if c in xa[k] and xa[k].get(c) != xd[k].get(c)]
                    if mud:
                        linhas.append(('mudou', f'{rot} "{k}": ' + '; '.join(mud)))
                else:
                    linhas.append(('mudou', f'{rot} {k}: {_curto(xa[k])} -> {_curto(xd[k])}'))
    for k in sorted(set(ra['regras']) | set(rd['regras']), key=str):
        if ra['regras'].get(k) != rd['regras'].get(k):
            linhas.append(('regra', f'regra {k}: ' + ('removida' if k not in rd['regras'] else
                                                      'nova' if k not in ra['regras'] else 'texto mudou')))
    xa, xd = analisar(antes), analisar(depois)
    numeros = []
    for rot, f in (('atividades', lambda x: x['contagem']['atividades']),
                   ('decisões', lambda x: x['contagem']['decisoes']),
                   ('raias', lambda x: x['contagem']['raias']),
                   ('passagens de bastão', lambda x: len(x['passagens'])),
                   ('laços de retrabalho', lambda x: len(x['retrabalho'])),
                   ('esforço', lambda x: x['tempos']['execucao']),
                   ('espera (caminho feliz)', lambda x: x['tempos']['espera']),
                   ('lead time (caminho feliz)', lambda x: x['tempos']['lead_time']),
                   ('lead time esperado', lambda x: x['tempos']['lead_time_esperado'] or 0)):
        numeros.append((rot, f(xa), f(xd)))
    return linhas, numeros


def _curto(v):
    if v in (None, '', [], {}):
        return '(vazio)'
    if isinstance(v, bool):
        return 'sim' if v else 'não'
    if isinstance(v, dict):
        return ', '.join(f'{k}={"/".join(x) if isinstance(x, list) else x}' for k, x in v.items())
    t = str(v)
    return f'"{t[:60]}…"' if len(t) > 60 else f'"{t}"'


def _tempo_txt(t):
    return ', '.join(f'{ {"execucao": "execução"}.get(k, k)} {v}' for k, v in (t or {}).items()) or 'sem tempo'


def _saidas(v):
    """As saídas do retrato como (rótulo, destino, percentual); aceita o formato antigo "rotulo:destino"."""
    out = []
    for s in v['segue']:
        if isinstance(s, str):
            rot, _, para = s.rpartition(':')
            out.append((rot, para, None))
        else:
            out.append((s[0] or '', s[1], s[2] if len(s) > 2 else None))
    return out


def _diferenca_de_saidas(a, d, pares, ea, ed):
    """Para onde cada saída vai, antes e depois: pega troca de destino, rótulo trocado e ligação nova."""
    def nome(dic, x):
        return f'"{dic[x]["nome"]}"' if x in dic and dic[x]['nome'] else f'"{x}"'
    antes = [(rot, pares.get(para, '?' + para), pct, para) for rot, para, pct in _saidas(a)]
    depois = [(rot, para, pct, para) for rot, para, pct in _saidas(d)]
    out = []
    rotulados = {r for r, *_ in antes + depois if r}
    for r in sorted(rotulados):
        xa = [x for x in antes if x[0] == r]
        xd = [x for x in depois if x[0] == r]
        if xa and xd and xa[0][1] != xd[0][1]:
            out.append(('mudou', f'saída "{r}" de "{d["nome"] or "(" + d["tipo"] + ")"}": ia para {nome(ea, xa[0][3])}, agora vai para '
                        f'{nome(ed, xd[0][1])}'))
        elif xa and not xd:
            out.append(('mudou', f'saída "{r}" de "{d["nome"] or "(" + d["tipo"] + ")"}" ({nome(ea, xa[0][3])}) foi removida'))
        elif xd and not xa:
            out.append(('mudou', f'nova saída "{r}" de "{d["nome"] or "(" + d["tipo"] + ")"}" para {nome(ed, xd[0][1])}'))
        elif xa and xd and xa[0][2] != xd[0][2] and None not in (xa[0][2], xd[0][2]):
            out.append(('mudou', f'saída "{r}" de "{d["nome"] or "(" + d["tipo"] + ")"}": {xa[0][2]:.0f}% -> {xd[0][2]:.0f}%'))
    sem_a = {x[1] for x in antes if not x[0]}
    sem_d = {x[1] for x in depois if not x[0]}
    for x in sorted(sem_a - sem_d):
        orig = next(y[3] for y in antes if y[1] == x and not y[0])
        out.append(('mudou', f'"{d["nome"] or "(" + d["tipo"] + ")"}" não segue mais para {nome(ea, orig)}'))
    for x in sorted(sem_d - sem_a):
        out.append(('mudou', f'"{d["nome"] or "(" + d["tipo"] + ")"}" agora segue para {nome(ed, x)}'))
    # saída sem rótulo (corrida, OU) que continua indo ao mesmo lugar, mas com outro percentual
    for x in sorted(sem_a & sem_d):
        pa = next(y[2] for y in antes if y[1] == x and not y[0])
        pd = next(y[2] for y in depois if y[1] == x and not y[0])
        if pa != pd and not (pa is None and pd is None):
            def pct(v):
                return 'sem percentual' if v is None else f'{v:.0f}%'
            out.append(('mudou', f'"{d["nome"] or "(" + d["tipo"] + ")"}" para {nome(ed, x)}: {pct(pa)} -> {pct(pd)}'))
    return out


def carregar_retrato_aprovado(c):
    """Uma Carta 'fantasma' a partir do retrato aprovado, para o comparar."""
    estado, reg = situacao_aprovacao(c)
    if not reg:
        raise ErroDeUso('esta carta ainda não tem aceite: use --contra OUTRA_CARTA.json')
    from .modelo import Carta
    els, por_id = [], {}
    retrato = reg['retrato']['elementos']
    bordas = {eid: v for eid, v in retrato.items() if v.get('tipo') == 'borda' and v.get('anexo')}
    for eid, v in retrato.items():
        if eid in bordas:
            continue
        segue = [{'para': para, 'rotulo': rot, 'percentual': pct} for rot, para, pct in _saidas(v)
                 if para not in bordas]
        el = {'id': eid, 'nome': v['nome'], 'tipo': v['tipo'], 'papel': v['papel'], 'sistema': v['sistema'],
              'tempo': v.get('tempo') or {}, 'regras': v.get('regras', []),
              'gatilho': v.get('gatilho', 'nenhum'), 'encerra': v.get('encerra', False),
              'automatizada': v.get('automatizada', False), 'valor': v.get('valor') or None, 'segue': segue}
        els.append(el)
        por_id[eid] = (el, v)
    # a borda volta presa na atividade, com o percentual que estava na saída da atividade para ela
    for bid, v in bordas.items():
        host = por_id.get(v['anexo'])
        if not host:
            continue
        pct = next((p for _, para, p in _saidas(host[1]) if para == bid), None)
        host[0].setdefault('bordas', []).append({
            'id': bid, 'nome': v['nome'], 'gatilho': v.get('gatilho'), 'tempo': (v.get('tempo') or {}).get('espera'),
            'percentual': pct, 'interrompe': v.get('interrompe', True),
            'segue': [{'para': para, 'rotulo': rot, 'percentual': p} for rot, para, p in _saidas(v)]})
    dados = {'processo': dict(c.processo), 'elementos': els,
             'regras': [{'id': k, 'texto': t} for k, t in reg['retrato']['regras'].items()]}
    return Carta(dados), reg
