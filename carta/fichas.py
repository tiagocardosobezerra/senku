"""
O jogo de fichas: a prova de que o fluxo funciona, não só de que está ligado.

Uma ficha sai de cada início e anda pelo fluxo com as regras do BPMN:
    atividade, evento   consome uma ficha que chega e solta uma em cada saída
    decisão             consome uma ficha e solta em UMA saída (cada saída é um caminho possível)
    paralelo            divide: solta em todas; junta: espera uma ficha em CADA entrada
    inclusivo           divide: um ou mais caminhos; junta: aproximado como "o que chegou segue"
    fim                 consome a ficha
Todos os estados alcançáveis são explorados. O que se procura:
    travamento          sobra ficha parada e nada pode andar (ex.: decisão que fecha num paralelo:
                        o paralelo espera o caminho que nunca vem)
    falta de sincronia  duas fichas no mesmo ponto: a atividade seguinte roda duas vezes (ex.: paralelo
                        que fecha numa atividade ou numa decisão, em vez de outro paralelo)
    sem saída           estado de onde nunca se chega ao fim (laço sem saída)
Processos muito grandes têm estados demais: acima do limite a checagem para e diz que não foi completa.
"""

import time

from .modelo import PORTAS

LIMITE = 300000
SEGUNDOS = 4


def _disparos(c, estado, incl_saidas):
    """Para cada nó que pode andar no estado (dict fluxo -> fichas), os estados seguintes possíveis."""
    fichas = {f: n for f, n in estado if n}
    nos = {c.fluxo[f]['para'] for f in fichas}
    for no in nos:
        if no not in c.elementos:
            continue
        e = c.elementos[no]
        ent = [f['id'] for f in c.entradas[no] if f['id'] in fichas]
        sai = [f['id'] for f in c.saidas[no] if f['para'] in c.elementos]
        tipo = e['tipo']
        if tipo == 'paralelo' and len(c.entradas[no]) > 1:
            if len(ent) < len(c.entradas[no]):
                continue                                    # junção: espera todas as entradas
            consumo = [f['id'] for f in c.entradas[no]]
            yield no, consumo, [sai]
        elif tipo == 'inclusivo' and len(c.entradas[no]) > 1:
            # junção OU: espera enquanto ainda pode chegar ficha por uma entrada vazia (semântica do BPMN 2.0)
            vazias = [f['id'] for f in c.entradas[no] if f['id'] not in fichas]
            if any(g in c.acima[v] for v in vazias for g in fichas if g not in ent):
                continue
            yield no, ent, [sai] if len(sai) <= 1 else incl_saidas(sai)
        else:
            for f in ent:
                if tipo == 'fim' and e.get('encerra'):
                    yield no, [x for x, _ in estado], [[]]         # fim terminal: recolhe todas as fichas
                elif tipo == 'fim':
                    yield no, [f], [[]]
                elif tipo in ('decisao', 'corrida') and len(sai) > 1:
                    yield no, [f], [[s] for s in sai]
                elif tipo == 'inclusivo' and len(sai) > 1:
                    yield no, [f], incl_saidas(sai)
                elif any(c.fluxo[s]['borda'] for s in sai):
                    # atividade com borda: termina normal, OU a borda interrompe (só ela segue), OU a borda que não
                    # interrompe dispara junto com o fim normal
                    normal = [s for s in sai if not c.fluxo[s]['borda']]
                    opcoes = [normal]
                    for s in sai:
                        if c.fluxo[s]['borda']:
                            b = c.elementos[c.fluxo[s]['para']]
                            opcoes.append([s] if b['interrompe'] else normal + [s])
                    yield no, [f], opcoes
                else:
                    yield no, [f], [sai]


def _subconjuntos(sai):
    from itertools import combinations
    out = []
    for k in range(1, len(sai) + 1):
        out.extend(list(x) for x in combinations(sai, k))
    return out


def jogar(c):
    """Explora os estados e devolve {'completa', 'travamentos', 'sem_sincronia', 'sem_saida', 'estados'}.
    Cada achado traz os elementos envolvidos."""
    c.fluxo = {f['id']: f for f in c.fluxos if f['de'] in c.elementos and f['para'] in c.elementos}
    # caminho de uma borda que não interrompe (lembrete, aviso): pode disparar mais de uma vez num laço e cada
    # disparo segue sozinho até um fim. Fichas repetidas nele não são erro.
    nao_interrompe = [f for f in c.fluxos if f['borda'] and f['para'] in c.elementos
                      and not c.elementos[f['para']]['interrompe']]
    c.lembretes = {f['id'] for f in nao_interrompe}
    pilha = [f['para'] for f in nao_interrompe]
    vistos_l = set()
    while pilha:
        x = pilha.pop()
        if x in vistos_l or x not in c.elementos:
            continue
        vistos_l.add(x)
        e = c.elementos[x]
        if e['tipo'] in ('paralelo', 'inclusivo') and len(c.entradas[x]) > 1:
            continue                                     # voltou a juntar com o fluxo principal: aí vale a regra
        for g in c.saidas[x]:
            c.lembretes.add(g['id'])
            pilha.append(g['para'])
    # para cada fluxo, os fluxos de onde uma ficha ainda pode chegar até ele (para a junção OU)
    c.acima = {}
    for fid, f in c.fluxo.items():
        vistos, pilha = set(), [g['id'] for g in c.entradas[f['de']] if g['id'] in c.fluxo]
        while pilha:
            g = pilha.pop()
            if g in vistos:
                continue
            vistos.add(g)
            pilha.extend(h['id'] for h in c.entradas[c.fluxo[g]['de']] if h['id'] in c.fluxo)
        c.acima[fid] = vistos
    out = {'completa': True, 'travamentos': [], 'sem_sincronia': [], 'sem_saida': [], 'estados': 0}
    inicios = c.de_tipo('inicio')
    if not inicios or not c.de_tipo('fim'):
        return out
    vistos_trav, vistos_sinc = set(), set()
    for ini in inicios:
        saidas = tuple(sorted((f['id'], 1) for f in c.saidas[ini['id']] if f['id'] in c.fluxo))
        if not saidas:
            continue
        inicial = saidas
        grafo, fila, conhecidos = {}, [inicial], {inicial}
        relogio = time.monotonic()
        while fila:
            # para no limite de estados ou de tempo (o validar roda a cada mudança na carta: não pode demorar)
            if len(conhecidos) > LIMITE or (len(conhecidos) % 2000 == 0 and time.monotonic() - relogio > SEGUNDOS):
                out['completa'] = False
                break
            estado = fila.pop()
            prox = []
            for no, consumo, opcoes in _disparos(c, estado, _subconjuntos):
                for saida in opcoes:
                    d = dict(estado)
                    for f in consumo:
                        d[f] = 0 if c.elementos[no].get('encerra') else d[f] - 1
                    for f in saida:
                        d[f] = d.get(f, 0) + 1
                    # duas fichas no mesmo ponto já mostram o problema; mais que isso só multiplica estados
                    novo = tuple(sorted((f, min(n, 2)) for f, n in d.items() if n))
                    prox.append(novo)
                    for f, n in novo:
                        if n > 1 and f not in vistos_sinc and f not in c.lembretes:
                            vistos_sinc.add(f)
                            out['sem_sincronia'].append(c.fluxo[f]['para'])
                    if novo not in conhecidos:
                        conhecidos.add(novo)
                        fila.append(novo)
            grafo[estado] = prox
            if not prox and estado:
                parados = tuple(sorted({c.fluxo[f]['para'] for f, _ in estado}))
                if parados not in vistos_trav:
                    vistos_trav.add(parados)
                    out['travamentos'].append(list(parados))
        out['estados'] += len(conhecidos)
        if out['completa']:
            # estados que nunca chegam ao fim nem a um travamento (já avisado): laço sem saída
            chega = {()} | {est for est, nxt in grafo.items() if not nxt}
            mudou = True
            while mudou:
                mudou = False
                for est, nxt in grafo.items():
                    if est not in chega and any(n in chega for n in nxt):
                        chega.add(est)
                        mudou = True
            presos = [est for est in grafo if est not in chega and grafo[est]]
            nos = set()
            for est in presos:
                nos.update(c.fluxo[f]['para'] for f, _ in est)
            if nos:
                out['sem_saida'].append(sorted(nos))
    return out


def achados(c):
    """Os resultados do jogo como (nivel, codigo, elemento, texto)."""
    if any(e['tipo'] == 'inclusivo' for e in c.elementos.values()):
        pass                                                # a junção inclusiva é aproximada; ainda vale a checagem
    r = jogar(c)
    out = []
    for parados in r['travamentos']:
        esperando = [x for x in parados if c.elementos[x]['tipo'] == 'paralelo']
        if esperando:
            nomes = ', '.join(f'"{c.nome(x)}"' for x in parados)
            out.append(('erro', 'travamento', esperando[0],
                        f'o fluxo trava: a ficha para em {nomes}, que espera TODOS os caminhos, mas algum caminho '
                        'antes dele não chega (saiu por uma decisão ou terminou num fim). Feche decisão com decisão '
                        'e paralelo com paralelo; se o caminho que não chega cancela o processo inteiro, marque o fim '
                        'dele com "encerra": true (fim terminal)'))
        else:
            out.append(('erro', 'travamento', parados[0], 'o fluxo trava em ' +
                        ', '.join(f'"{c.nome(x)}"' for x in parados)))
    # um ponto sem sincronia faz tudo depois dele rodar duas vezes: reporta a raiz (quem não tem antes de si
    # outro elemento com o mesmo problema) e conta o resto, em vez de uma avalanche de erros iguais
    marcados = list(dict.fromkeys(r['sem_sincronia']))
    raizes = [n for n in marcados if not any(f['de'] in marcados for f in c.entradas[n])] or marcados[:1]
    efeito = len(marcados) - len(raizes)
    for i, no in enumerate(raizes):
        e = c.elementos[no]
        origem_incl = any(x['tipo'] == 'inclusivo' and len(c.saidas[x['id']]) > 1 for x in c.elementos.values())
        if e['tipo'] in PORTAS and e['tipo'] != 'paralelo':
            fecho = 'outro inclusivo' if origem_incl else 'outro paralelo'
            texto = (f'dois caminhos que correm juntos chegam em "{c.nome(no)}" e o processo segue duas vezes: '
                     f'feche-os com {fecho} antes')
        elif origem_incl:
            texto = (f'"{c.nome(no)}" recebe caminhos de um OU inclusivo que podem correr juntos e roda mais de uma '
                     'vez: feche-os com outro inclusivo antes dela')
        else:
            texto = (f'"{c.nome(no)}" recebe dois caminhos que correm ao mesmo tempo e roda duas vezes: feche os '
                     'caminhos com um paralelo antes dela')
        if i == 0 and efeito > 0:
            texto += f' ({efeito} elemento(s) depois dele também rodam duas vezes: é efeito deste ponto)'
        out.append(('erro', 'sem_sincronia', no, texto))
    for nos in r['sem_saida']:
        out.append(('erro', 'laco_sem_saida', nos[0], 'há um laço de onde o processo nunca sai: ' +
                    ', '.join(f'"{c.nome(x)}"' for x in nos[:4])))
    if not r['completa']:
        achou = any(n == 'erro' for n, *_ in out)
        out.append(('aviso', 'fichas_incompleto', None, f'a prova de travamento não terminou em {SEGUNDOS} s '
                    f'({LIMITE} estados): muitos ramos paralelos com laço multiplicam os estados. '
                    + ('Corrija os erros acima e rode de novo; ' if achou else
                       'Na parte explorada não há problema; ') +
                    'para ter a prova completa, ponha os laços de cada ramo num subprocesso'))
    return out
