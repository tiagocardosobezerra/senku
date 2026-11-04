"""
Análise do processo: os números e as oportunidades que o mapa mostra.

    caminho feliz       do início ao fim pelo caminho mais comum (sem retrabalho)
    tempos              execução x espera; eficiência do ciclo = execução / (execução + espera)
    passagens de bastão quantas vezes o trabalho muda de raia (cada uma é fila, espera e risco de perda)
    vai e volta         A -> B -> A: o trabalho volta para quem já tinha passado por ele
    valor agregado      VA / NAV-N / NAV, em atividades e em tempo
    retrabalho          laços para trás e o percentual que volta
    oportunidades       cada achado ligado a um desperdício Lean (referencias/analise.md)

Os números valem o que valem os tempos informados: são estimativas da
entrevista, não medição. O relatório diz isso.
"""

import re

from .modelo import ESCOLHA, NOS_DE_TRABALHO, PORTAS
from .util import formatar_minutos, numero_br, sem_acento

_SIM = re.compile(r'^(sim|s|yes|ok|aprovad[oa]s?|conforme|completo|correto|dentro|valido|disponivel|existe|tem)\b')
_APROVA = re.compile(r'^(aprovar|validar|conferir|autorizar|revisar|checar|verificar|assinar|homologar|vistar)\b')
_DIGITA = re.compile(r'^(lancar|digitar|registrar|cadastrar|transcrever|redigitar|preencher|copiar|incluir|inserir)\b')
DESPERDICIOS = {
    'espera': 'Espera', 'transporte': 'Transporte (passagem de bastão)', 'defeito': 'Defeitos (retrabalho)',
    'superprocessamento': 'Superprocessamento', 'movimentacao': 'Movimentação', 'estoque': 'Estoque (fila)',
    'talento': 'Talento não aproveitado', 'excesso': 'Excesso de produção',
}


# fim "ruim": o caso não chegou ao resultado. "Encerrado" fica de fora: "Chamado encerrado" é o fim normal.
_RUIM = re.compile(r'cancel|reprov|recus|negad|erro|expir|desist|perdid|indefer|interromp|inapt|bloque|devolvid|'
                   r'rejeit|abandon|descart|sem sucesso|nao (aprov|atend|conclu|entreg)')


def _fim_ruim(c, eid):
    e = c.elementos.get(eid)
    return bool(e and e['tipo'] == 'fim' and _RUIM.search(sem_acento(e['nome']).lower()))


def _chega_bem(c, volta):
    """Elementos que chegam a um fim "bom" (não cancelado, recusado...) sem passar por retrabalho."""
    fins = [e['id'] for e in c.de_tipo('fim')]
    bons = [x for x in fins if not _fim_ruim(c, x)] or fins
    ok, pilha = set(), list(bons)
    while pilha:
        x = pilha.pop()
        if x in ok:
            continue
        ok.add(x)
        pilha.extend(f['de'] for f in c.entradas.get(x, []) if f['id'] not in volta)
    return ok


def _chega_fim(c, volta):
    """Elementos que chegam a algum fim (bom ou ruim) sem passar por retrabalho. Guardado por carta."""
    chave = ('_chega_fim', frozenset(volta))
    cache = c.__dict__.setdefault('_cache_analise', {})
    if chave not in cache:
        ok, pilha = set(), [e['id'] for e in c.de_tipo('fim')]
        while pilha:
            x = pilha.pop()
            if x in ok:
                continue
            ok.add(x)
            pilha.extend(f['de'] for f in c.entradas.get(x, []) if f['id'] not in volta)
        cache[chave] = ok
    return cache[chave]


def _peso_saida(c, f, volta, ok=None):
    """Ordena as saídas de uma decisão para achar o caminho feliz, que é o caminho MAIS COMUM:
    1. nunca o retrabalho (fluxo que volta);
    2. o maior percentual informado;
    3. sem percentual: a saída que chega a um fim bom sem voltar (pergunta negativa como "Tem erro?" se
       resolve aqui: o "Sim" dela volta para corrigir), depois a que não termina num fim ruim, depois
       "Sim/Aprovado"."""
    if f['id'] in volta:
        return (2, 0, 0, 0, 0)
    rot = sem_acento(f['rotulo']).lower()
    pct = f['percentual'] if f['percentual'] is not None else -1
    nao_chega = 1 if ok is not None and f['para'] not in ok else 0
    # só volta para o laço (não chega a fim nenhum sem voltar): vai depois de tudo que termina, bom ou ruim
    so_volta = 1 if f['para'] not in _chega_fim(c, volta) else 0
    # pergunta de limite ("Valor acima de 100 mil?", "Excede a alçada?"): o caso comum é ficar abaixo, o "Não"
    pergunta = sem_acento(c.elementos[f['de']]['nome']).lower()
    limite = re.search(r'\b(acima|maior|mais de|excede|ultrapassa|supera|fora d|alem d)\b|>', pergunta)
    preferido = (not _SIM.match(rot)) if limite else bool(_SIM.match(rot))
    # a saída que só leva de volta (correção que retorna ao laço) nunca é o caminho feliz, mesmo com 60%: o caso
    # típico passa por ela e depois segue; o caminho feliz é o que chega ao fim
    return (0, so_volta, -pct, nao_chega, 1 if _fim_ruim(c, f['para']) else 0, 0 if preferido else 1)


def _duracao(c, eid):
    e = c.elementos[eid]
    return (e['execucao'] or 0) + (e['espera'] or 0)


def passagens_do_caminho(c, caminho):
    """Trocas de raia no caminho feliz (o que um caso típico vive), contando só atividades."""
    trab = [x for x in caminho if c.elementos[x]['tipo'] in NOS_DE_TRABALHO]
    return [(a, b) for a, b in zip(trab, trab[1:]) if c.raia_de(a) != c.raia_de(b)]


def _ramo(c, inicio, volta):
    """Os elementos de um ramo de paralelo até a junção (exclusive) e a junção."""
    ramo, x, vistos = [], inicio, set()
    while x in c.elementos and x not in vistos:
        if c.elementos[x]['tipo'] == 'paralelo' and len(c.entradas[x]) > 1:
            return ramo, x
        vistos.add(x)
        ramo.append(x)
        prox = [f for f in c.saidas[x] if f['para'] in c.elementos and f['id'] not in volta]
        if any(not f['borda'] for f in prox):
            prox = [f for f in prox if not f['borda']]          # a borda é exceção: o ramo segue o caso típico
        prox = sorted(prox, key=lambda f: _peso_saida(c, f, volta))
        x = prox[0]['para'] if prox else None
    return ramo, None


def caminho_feliz(c):
    """(caminho, paralelos): o caminho mais comum do primeiro início até um fim. Num paralelo, o ramo mais
    demorado entra no caminho (é ele que define o prazo); os outros vão em `paralelos` (contam no esforço)."""
    volta = c.arestas_de_volta()
    ok = _chega_bem(c, volta)
    inicios = c.de_tipo('inicio')
    if not inicios:
        return [], []
    atual, visto, caminho, paralelos = inicios[0]['id'], set(), [], []
    while atual in c.elementos and atual not in visto:
        visto.add(atual)
        caminho.append(atual)
        saidas = [f for f in c.saidas[atual] if f['para'] in c.elementos and f['id'] not in volta]
        if any(not f['borda'] for f in saidas):
            saidas = [f for f in saidas if not f['borda']]          # a borda é exceção: fora do caso típico
        if not saidas:
            break
        if c.elementos[atual]['tipo'] == 'paralelo' and len(saidas) > 1:
            ramos = [_ramo(c, f['para'], volta) for f in saidas]
            if _corrida(c, ramos):
                # corrida (um ramo encerra tudo): o caso típico é o ramo que chega ao fim bom; os outros são
                # cancelados, então não entram nem no caminho nem no esforço
                bons = [r for r in ramos if r[0] and not _fim_ruim(c, r[0][-1])] or ramos
                bons.sort(key=lambda r: sum(_duracao(c, x) for x in r[0]))
                caminho.extend(x for x in bons[0][0] if x not in visto)
                break
            ramos.sort(key=lambda r: -sum(_duracao(c, x) for x in r[0]))
            principal, juncao = ramos[0]
            for outro, _ in ramos[1:]:
                paralelos.extend(x for x in outro if x not in visto)
                visto.update(outro)
            caminho.extend(x for x in principal if x not in visto)
            visto.update(principal)
            if juncao is None:
                break
            atual = juncao
            continue
        saidas.sort(key=lambda f: _peso_saida(c, f, volta, ok))
        atual = saidas[0]['para']
    return caminho, paralelos


def _corrida(c, ramos):
    """Paralelo em que algum ramo termina num fim que encerra tudo, sem passar pela junção."""
    return any(j is None and r and c.elementos[r[-1]]['tipo'] == 'fim' and c.elementos[r[-1]]['encerra']
               for r, j in ramos)


def probabilidades(c, eid):
    """Probabilidade de cada saída (0 a 1). Decisão: o percentual; o que falta é dividido igualmente entre as
    saídas sem percentual. Paralelo e atividade com várias saídas: todas acontecem (1)."""
    saidas = [f for f in c.saidas[eid] if f['para'] in c.elementos]
    e = c.elementos[eid]
    bordas = [f for f in saidas if f['borda']]
    if bordas:
        # atividade com borda: a borda acontece no percentual dela (sem percentual, conta zero e o lacunas
        # pergunta); a que interrompe tira esse tanto do fim normal
        p = {f['id']: (f['percentual'] or 0) / 100 for f in bordas}
        corta = sum(p[f['id']] for f in bordas if c.elementos[f['para']]['interrompe'])
        out = {f['id']: max(0.0, 1 - corta) for f in saidas if not f['borda']}
        out.update(p)
        return out, any(f['percentual'] is None for f in bordas)
    if e['tipo'] not in ESCOLHA or len(saidas) < 2:
        return {f['id']: 1.0 for f in saidas}, False
    if e['tipo'] == 'inclusivo':
        # no OU inclusivo cada caminho tem a sua chance, em % de todos os casos (80% frete e 60% seguro: os dois
        # podem acontecer; sem percentual, meio a meio). A junção roda uma vez por caso (ver visitas)
        return ({f['id']: (f['percentual'] if f['percentual'] is not None else 50) / 100 for f in saidas},
                any(f['percentual'] is None for f in saidas))
    dados = [f['percentual'] for f in saidas if f['percentual'] is not None]
    sem = [f for f in saidas if f['percentual'] is None]
    resto = max(0.0, 100 - sum(dados))
    out = {}
    for f in saidas:
        out[f['id']] = (f['percentual'] if f['percentual'] is not None else resto / len(sem)) / 100
    soma = sum(out.values()) or 1
    return {k: v / soma for k, v in out.items()}, bool(sem)


def _abertura_inclusiva(c, juncao):
    """O OU que abre os caminhos que esta junção fecha: sobe por um dos caminhos até achar um OU que divide."""
    x, vistos = c.entradas[juncao][0]['de'] if c.entradas[juncao] else None, set()
    while x and x in c.elementos and x not in vistos:
        vistos.add(x)
        e = c.elementos[x]
        if e['tipo'] == 'inclusivo' and len(c.saidas[x]) > 1:
            return x
        ent = c.entradas[x]
        x = ent[0]['de'] if ent else None
    return None


def _amostra_ramo(c, x, juncao, probs, volta, rng, prof=0):
    """Uma vez do ramo, do elemento x até a junção (sorteando cada saída pelo percentual): quanto demorou."""
    total, passos = 0.0, 0
    while x in c.elementos and x != juncao and passos < 400:
        passos += 1
        e = c.elementos[x]
        if e['tipo'] == 'fim':
            return total
        total += _duracao(c, x)
        saidas = [f for f in c.saidas[x] if f['para'] in c.elementos]
        if not saidas:
            return total
        normal = [f for f in saidas if not f['borda']]
        if e['tipo'] == 'paralelo' and len(normal) > 1 and prof < 4:
            j = _ramo(c, normal[0]['para'], volta)[1]
            if j:
                total += max(_amostra_ramo(c, f['para'], j, probs, volta, rng, prof + 1) for f in normal)
                x = j
                continue
        pesos = [probs[x].get(f['id'], 0) for f in saidas]
        if sum(pesos) <= 0:
            pesos = [1.0 if not f['borda'] else 0.0 for f in saidas] if normal else [1.0] * len(saidas)
        sorteio, acum = rng.random() * sum(pesos), 0.0
        escolha = saidas[-1]
        for f, w in zip(saidas, pesos):
            acum += w
            if sorteio <= acum:
                escolha = f
                break
        x = escolha['para']
    return total


def _media_do_maximo(c, inicios, juncao, probs, volta, vezes=4000):
    """Média, em muitas vezes sorteadas, do ramo mais demorado (semente fixa: o número não muda entre rodadas)."""
    import random
    rng = random.Random(20261103)
    soma = 0.0
    for _ in range(vezes):
        soma += max(_amostra_ramo(c, x, juncao, probs, volta, rng) for x in inicios)
    return soma / vezes


def _dur_ramo(c, ramo):
    return sum(_duracao(c, x) for x in ramo if x in c.elementos)


def _chance_de_encerrar(c, inicio, probs, volta):
    """Chance de um ramo de paralelo chegar a um fim que encerra tudo antes da junção (por borda ou decisão)."""
    total, pilha = 0.0, [(inicio, 1.0, 0)]
    while pilha:
        x, p, prof = pilha.pop()
        e = c.elementos.get(x)
        if not e or p < 1e-4 or prof > 80:
            continue
        if e['tipo'] == 'paralelo' and len(c.entradas[x]) > 1:
            continue                                     # chegou à junção
        if e['tipo'] == 'fim':
            total += p if e['encerra'] else 0
            continue
        for f in c.saidas[x]:
            if f['id'] in volta:
                continue
            pilha.append((f['para'], p * probs[x].get(f['id'], 0 if len(c.saidas[x]) > 1 else 1), prof + 1))
    return min(1.0, total)


def _produto(valores):
    out = 1.0
    for v in valores:
        out *= v
    return out


def visitas(c):
    """Quantas vezes, em média, cada elemento roda por caso (retrabalho conta: 35% de volta = 1,54 vez)."""
    probs = {eid: probabilidades(c, eid)[0] for eid in c.elementos}
    inicios = [e['id'] for e in c.de_tipo('inicio')]
    v = {eid: 0.0 for eid in c.elementos}
    for _ in range(400):
        novo = {}
        for eid, e in c.elementos.items():
            if eid in inicios:
                novo[eid] = 1.0 / len(inicios)
                continue
            chega = sum(v[f['de']] * probs[f['de']].get(f['id'], 0) for f in c.entradas[eid] if f['de'] in v)
            if e['tipo'] == 'paralelo' and len(c.entradas[eid]) > 1:
                # a junção só roda quando TODOS os ramos chegam: vale o ramo que chega menos (um ramo que pode
                # encerrar o caso no meio faz a junção rodar menos)
                chega = min(v[f['de']] * probs[f['de']].get(f['id'], 0) for f in c.entradas[eid] if f['de'] in v)
            elif e['tipo'] == 'inclusivo' and len(c.entradas[eid]) > 1:
                # a junção OU roda uma vez por vez que o OU de abertura rodou (os caminhos se juntam numa ficha só)
                abre = _abertura_inclusiva(c, eid)
                if abre:
                    chega = v[abre]
            novo[eid] = min(chega, 50.0)
        if not v or max(abs(novo[k] - v[k]) for k in v) < 1e-6:
            v = novo
            break
        v = novo
    return v


def tempo_esperado(c):
    """Lead time esperado (minutos úteis) do início ao fim, pesando cada caminho pelo percentual e contando o
    retrabalho. Num paralelo vale o ramo mais longo. Devolve (minutos, decisões sem percentual)."""
    probs, faltam = {}, []
    for eid in c.elementos:
        probs[eid], falta = probabilidades(c, eid)
        if falta:
            faltam.append(eid)
    volta = c.arestas_de_volta()
    corridas = {e['id'] for e in c.de_tipo('paralelo') if len(c.saidas[e['id']]) > 1 and
                _corrida(c, [_ramo(c, f['para'], volta) for f in c.saidas[e['id']]])}
    encerra_ramos = {}
    for e in c.de_tipo('paralelo'):
        normal = [f for f in c.saidas[e['id']] if not f['borda']]
        if len(normal) < 2 or e['id'] in corridas:
            continue
        ramos = [(r, _chance_de_encerrar(c, f['para'], probs, volta)) for f in normal
                 for r in [_ramo(c, f['para'], volta)[0]]]
        juncoes = {_ramo(c, f['para'], volta)[1] for f in normal}
        if any(q > 0 for _, q in ramos) and len(juncoes) == 1 and None not in juncoes:
            encerra_ramos[e['id']] = (ramos, juncoes.pop(), _produto(1 - q for _, q in ramos))
    max_ramos = {}
    for e in c.de_tipo('paralelo'):
        normal = [f for f in c.saidas[e['id']] if not f['borda']]
        if len(normal) < 2 or e['id'] in corridas or e['id'] in encerra_ramos:
            continue
        juncoes = {_ramo(c, f['para'], volta)[1] for f in normal}
        if len(juncoes) != 1 or None in juncoes:
            continue
        juncao = juncoes.pop()
        ramos = [_ramo(c, f['para'], volta)[0] for f in normal]
        if not any(len(c.saidas[x]) > 1 for r in ramos for x in r):
            continue                                     # ramos em linha reta: o máximo das somas já é exato
        max_ramos[e['id']] = (_media_do_maximo(c, [f['para'] for f in normal], juncao, probs, volta), juncao)
    t = {eid: 0.0 for eid in c.elementos}
    for _ in range(600):
        novo = {}
        for eid, e in c.elementos.items():
            proprio = (e['execucao'] or 0) + (e['espera'] or 0)
            saidas = [f for f in c.saidas[eid] if f['para'] in t]
            if not saidas:
                novo[eid] = proprio
            elif e['tipo'] == 'inclusivo' and len(saidas) > 1:
                # os caminhos escolhidos correm juntos: vale o mais longo entre os que acontecem. Com as chances
                # independentes (e pelo menos um sempre), o esperado do máximo: ordena do mais longo ao mais curto;
                # o i-ésimo é o máximo quando acontece e os mais longos não
                bruto = {f['id']: (f['percentual'] if f['percentual'] is not None else 50) / 100 for f in saidas}
                ordem = sorted(saidas, key=lambda f: -t[f['para']])
                algum = 1 - _produto(1 - bruto[f['id']] for f in saidas) or 1
                esperado, nenhum_antes = 0.0, 1.0
                for f in ordem:
                    esperado += nenhum_antes * bruto[f['id']] * t[f['para']]
                    nenhum_antes *= 1 - bruto[f['id']]
                novo[eid] = proprio + esperado / algum
            elif e['tipo'] in ESCOLHA and len(saidas) > 1:
                novo[eid] = proprio + sum(probs[eid][f['id']] * t[f['para']] for f in saidas)
            elif eid in corridas:
                novo[eid] = proprio + min(t[f['para']] for f in saidas)   # o primeiro a terminar encerra tudo
            else:
                normal = [f for f in saidas if not f['borda']]
                bordas = [f for f in saidas if f['borda'] and c.elementos[f['para']]['interrompe']]
                if bordas:
                    # interrompe: no caso normal, a atividade inteira e o que vem depois; no caso da borda, o tempo
                    # até ela disparar (o prazo, se for de tempo; a atividade, se for erro ou mensagem) e o que vem
                    # depois dela. O prazo já está no tempo da borda: não soma a atividade de novo.
                    pb = probs[eid]
                    resto = max([t[f['para']] for f in normal] or [0])
                    p_bordas = sum(pb[f['id']] for f in bordas)
                    total = (1 - p_bordas) * (proprio + resto)
                    for f in bordas:
                        b = c.elementos[f['para']]
                        ate = 0 if (b['gatilho'] == 'tempo' and b['espera']) else proprio
                        total += pb[f['id']] * (ate + t[f['para']])
                    novo[eid] = total
                elif e['tipo'] == 'paralelo' and eid in max_ramos:
                    # ramos com decisão ou retrabalho: vale a MÉDIA DO MAIS LONGO (o caso espera o ramo que
                    # demorar mais naquela vez), não o mais longo das médias, que sai menor
                    media_max, juncao = max_ramos[eid]
                    novo[eid] = proprio + media_max + t[juncao]
                elif e['tipo'] == 'paralelo' and len(normal) > 1 and eid in encerra_ramos:
                    # um ramo pode encerrar o caso (fim terminal): com chance P_ok nenhum encerra e vale o ramo
                    # mais longo até a junção e o resto; senão, o caso acaba quando o ramo que encerra termina
                    ramos, juncao, p_ok = encerra_ramos[eid]
                    longo = max(_dur_ramo(c, r) for r, _ in ramos) + (t[juncao] if juncao in t else 0)
                    curto = min(_dur_ramo(c, r) for r, q in ramos if q > 0)
                    novo[eid] = proprio + p_ok * longo + (1 - p_ok) * curto
                else:
                    novo[eid] = proprio + max(t[f['para']] for f in (normal or saidas))
        if not t or max(abs(novo[k] - t[k]) for k in t) < 0.01:
            t = novo
            break
        t = novo
    inicios = c.de_tipo('inicio')
    if not inicios:
        return None, faltam
    return sum(t[e['id']] for e in inicios) / len(inicios), faltam


def percentual_do_laco(c, f):
    """O percentual de um fluxo de retrabalho: o dele, ou o da saída de decisão que leva ao início do laço
    (decisão "Não 35%" -> corrigir -> volta: o laço acontece em 35% dos casos)."""
    if f['percentual'] is not None:
        return f['percentual']
    origem = c.elementos.get(f['de'])
    if origem and origem['tipo'] == 'borda':                # a borda diz em quantos casos acontece
        return origem.get('percentual_borda')
    if origem and origem['tipo'] in ESCOLHA:
        return None                                         # o próprio fluxo sai da decisão e não tem percentual
    x, vistos = f['de'], set()
    while x in c.elementos and x not in vistos:
        vistos.add(x)
        ent = c.entradas[x]
        if len(ent) != 1:
            return None
        de = c.elementos.get(ent[0]['de'])
        if de and de['tipo'] in ESCOLHA:
            return ent[0]['percentual']                     # só a saída da decisão que abre este laço
        if de and de['tipo'] == 'borda':
            return de.get('percentual_borda')
        if not de or de['tipo'] in PORTAS:
            return None
        x = ent[0]['de']
    return None


_CRITERIO_NO_NOME = re.compile(r'\d|[<>%]|\b(acima|abaixo|maior|menor|ate|entre|mais de|menos de|dentro|fora|'
                               r'vencid|prazo|limite|alcada|faixa)\b')


def decisao_sem_criterio(c, d):
    """Decisão que divide sem regra escrita nela, nas saídas, no próprio nome ("Valor acima de R$ 10 mil?") nem
    na atividade logo antes. Corrida de eventos ("o que chega primeiro") não tem critério a escrever."""
    if len(c.saidas[d['id']]) < 2 or d['regras'] or any(f['condicao'] for f in c.saidas[d['id']]):
        return False
    if _CRITERIO_NO_NOME.search(sem_acento(d['nome']).lower()):
        return False
    if all(c.elementos.get(f['para'], {}).get('tipo') == 'evento' for f in c.saidas[d['id']]):
        return False
    antes = [c.elementos.get(f['de']) for f in c.entradas[d['id']]]
    return not any(a and a['regras'] for a in antes)


def _proximos_de_trabalho(c, eid, limite=30, sem_volta=False, sem_juncao=False, sem_borda=False):
    """As próximas atividades depois de eid, atravessando portas e eventos. sem_volta: não segue o retrabalho;
    sem_juncao: não atravessa a junção de um paralelo (ali o trabalho espera os outros ramos); sem_borda: não
    segue a exceção presa na atividade."""
    volta = c.arestas_de_volta() if sem_volta else set()
    if sem_borda:
        volta = volta | {f['id'] for f in c.fluxos if f['borda']}
    out, pilha, vistos = [], [f['para'] for f in c.saidas[eid] if f['id'] not in volta], set()
    while pilha and limite:
        limite -= 1
        x = pilha.pop()
        if x in vistos or x not in c.elementos:
            continue
        vistos.add(x)
        e = c.elementos[x]
        if e['tipo'] in NOS_DE_TRABALHO:
            out.append(x)
        elif sem_juncao and e['tipo'] == 'paralelo' and len(c.entradas[x]) > 1:
            continue
        else:
            pilha.extend(f['para'] for f in c.saidas[x] if f['id'] not in volta)
    return out


def analisar(c):
    volta = c.arestas_de_volta()
    ativ = c.atividades()
    caminho, paralelos = caminho_feliz(c)
    trabalho_no_caminho = [x for x in caminho + paralelos if c.elementos[x]['tipo'] in NOS_DE_TRABALHO]
    exec_caminho = sum(c.elementos[x]['execucao'] or 0 for x in caminho)
    exec_ = exec_caminho + sum(c.elementos[x]['execucao'] or 0 for x in paralelos)
    espera = sum(c.elementos[x]['espera'] or 0 for x in caminho)
    sem_tempo = [x for x in trabalho_no_caminho if c.elementos[x]['execucao'] is None]
    # espera por resposta de fora (mensagem, condição, tarefa que recebe) sem tempo: o lead time sai menor do que é
    espera_sem_tempo = [x for x in caminho if _espera_de_fora(c.elementos[x]) and c.elementos[x]['espera'] is None]
    lead = exec_caminho + espera
    # frequências e lead time esperado vêm da simulação caso a caso (regras de ficha do BPMN): paralelo com laço,
    # borda dentro de ramo, fim que encerra no meio e OU saem certos sem fórmula aproximada. Sem início
    # (carta incompleta), fica a conta analítica
    from .simulacao import simular
    precisa = _precisa_simular(c) or any(e['tipo'] in ('paralelo', 'inclusivo', 'borda')
                                         or (e['tipo'] == 'fim' and e['encerra'])
                  for e in c.elementos.values())
    # subprocesso com "detalhe": o tempo dele é o da carta filha (o mesmo que a carga usa), não o do mapa de cima
    duracoes = _duracoes_do_detalhe(c)
    precisa = precisa or bool(duracoes)
    sim = simular(c, duracoes=duracoes) if precisa else None   # fluxo só com decisões: a conta exata basta
    esperado, sem_pct = tempo_esperado(c)
    if sim and not sim['incompletos']:
        vis, esperado = sim['visitas'], sim['media']
    else:
        vis = visitas(c)
    completo = bool(caminho) and c.elementos[caminho[-1]]['tipo'] == 'fim'
    r = {
        'contagem': {
            'atividades': len(ativ), 'decisoes': len(c.de_tipo('decisao')),
            'paralelos': len(c.de_tipo('paralelo')), 'eventos': len(c.de_tipo('inicio', 'fim', 'evento')),
            'raias': len(c.raias()), 'sistemas': len(c.sistemas), 'fins': len(c.de_tipo('fim')),
        },
        'caminho_feliz': caminho, 'paralelos': paralelos, 'caminho_completo': completo,
        'tempos': {'execucao': exec_, 'espera': espera, 'lead_time': lead,
                   'eficiencia': (exec_caminho / lead) if lead else None, 'sem_tempo': sem_tempo,
                   'espera_sem_tempo': espera_sem_tempo,
                   'lead_time_esperado': esperado if (exec_ or espera) else None,
                   'percentis': ({k: sim[k] for k in ('p50', 'p80', 'p90')} if sim and not sim['incompletos']
                                 and (exec_ or espera) else None),
                   'decisoes_sem_percentual': sem_pct,
                   'tempo_incompleto': len(sem_tempo) * 2 > len(trabalho_no_caminho)},
        'visitas': vis,
        'passagens': [], 'passagens_caminho': passagens_do_caminho(c, caminho),
        'vai_e_volta': [], 'retrabalho': [], 'valor': {}, 'gargalos': [],
        'oportunidades': [], 'raci': {},
    }
    # ------------------------------------------------------------ passagens de bastão
    for e in ativ:
        for d in _proximos_de_trabalho(c, e['id'], sem_borda=True):
            if c.raia_de(d) != c.raia_de(e['id']):
                r['passagens'].append((e['id'], d))
                # vai e volta: com quem é de fora, pedir e receber é o normal; só conta entre áreas da casa
                if (c.papeis.get(c.raia_de(d)) or {}).get('tipo') == 'externo':
                    continue
                # vai e volta: sem atravessar retrabalho (já é outra oportunidade) nem junção de paralelo
                for z in _proximos_de_trabalho(c, d, sem_volta=True, sem_juncao=True, sem_borda=True):
                    if (c.raia_de(z) == c.raia_de(e['id']) and c.raia_de(d) != c.raia_de(z) and z != e['id']
                            and not any(x[:2] == (e['id'], d) for x in r['vai_e_volta'])):
                        r['vai_e_volta'].append((e['id'], d, z))
    # ------------------------------------------------------------ retrabalho
    for f in c.fluxos:
        if f['id'] in volta:
            r['retrabalho'].append({'de': f['de'], 'para': f['para'], 'rotulo': f['rotulo'],
                                    'percentual': percentual_do_laco(c, f)})
    # ------------------------------------------------------------ valor
    for v in ('VA', 'NAV-N', 'NAV', None):
        lista = [e for e in ativ if e['valor'] == v]
        r['valor'][v or 'sem'] = {'atividades': len(lista), 'execucao': sum(e['execucao'] or 0 for e in lista)}
    # ------------------------------------------------------------ gargalos (espera x quantas vezes acontece)
    # espera por resposta de fora fica no evento de mensagem (é como o SKILL manda escrever): entra também
    esperas_evento = [e for e in c.de_tipo('evento') if e['espera'] and e['gatilho'] in ('mensagem', 'condicao', 'sinal')
                      and not e['bruto'].get('envia')]
    com_espera = sorted([e for e in ativ if e['espera']] + esperas_evento,
                        key=lambda e: -e['espera'] * min(vis.get(e['id'], 0), 3))
    r['gargalos'] = [(e['id'], e['espera']) for e in com_espera[:3]]
    # ------------------------------------------------------------ RACI
    for e in ativ:
        r['raci'][e['id']] = {'R': [e['papel']] if e['papel'] else [], **e['raci']}
    r['carga'] = carga(c, vis, sim['trabalho'] if sim and not sim['incompletos'] else None)
    r['_sim'] = sim
    r['alertas'] = _alertas(c, r)
    r.pop('_sim', None)
    _oportunidades(c, r, ativ)
    return r


# mês de 20 dias úteis, o mesmo dos tempos ("1 mês" = 20 dias úteis em util.py)
_POR = {'dia': 20, 'semana': 4, 'quinzena': 2, 'mes': 1, 'trimestre': 1 / 3, 'semestre': 1 / 6, 'ano': 1 / 12,
        'hora': 20 * 8}
_PALAVRAS_NUM = {'um': 1, 'uma': 1, 'dois': 2, 'duas': 2, 'tres': 3, 'quatro': 4, 'cinco': 5, 'seis': 6, 'sete': 7,
                 'oito': 8, 'nove': 9, 'dez': 10, 'onze': 11, 'doze': 12, 'quinze': 15, 'vinte': 20, 'trinta': 30,
                 'quarenta': 40, 'cinquenta': 50, 'sessenta': 60, 'cem': 100, 'cento': 100, 'duzentos': 200,
                 'trezentos': 300, 'quinhentos': 500, 'mil': 1000}


_MULT = {'mil': 1000, 'milhao': 1e6, 'milhoes': 1e6, 'k': 1000}
from .util import EXTENSO as _EXTENSO  # noqa: E402  (o mesmo dicionário do tempo)


def _extenso_para_numero(t):
    """Troca número por extenso (e misto: "2 mil e quinhentos") pelos algarismos, no texto sem acento.
    "100 e 150" continua dois números: só junta com "e" quando o seguinte é menor (cento e vinte)."""
    tokens = re.findall(r'\d+(?:[.,]\d+)*|\w+|\S', t)
    out, total, atual, ultimo, em_numero, pendente_e = [], 0.0, 0.0, None, False, False

    def fecha():
        nonlocal total, atual, em_numero, ultimo
        if em_numero:
            v = total + atual
            out.append(str(int(v)) if v == int(v) else str(v).replace('.', ','))
        total, atual, ultimo, em_numero = 0.0, 0.0, None, False

    def valor(tk):
        if tk in _EXTENSO:
            return _EXTENSO[tk]
        nums = _numeros(tk) if re.fullmatch(r'\d+(?:[.,]\d+)*', tk) else []
        return nums[0] if nums else None
    for tk in tokens:
        v = valor(tk)
        if v is not None:
            if em_numero and (pendente_e or tk in _EXTENSO) and ultimo is not None and v < ultimo:
                atual += v                               # cento e vinte, vinte e cinco, 2 mil e quinhentos
            else:
                if pendente_e:
                    fecha()
                    out.append('e')
                else:
                    fecha()
                atual, em_numero = v, True
            ultimo, pendente_e = v, False
        elif tk == 'mil' and em_numero:
            total += (atual or 1) * 1000
            atual, ultimo, pendente_e = 0.0, 1000, False
        elif tk == 'e' and em_numero and not pendente_e:
            pendente_e = True
        else:
            fecha()
            if pendente_e:
                out.append('e')
                pendente_e = False
            out.append(tk)
    fecha()
    if pendente_e:
        out.append('e')
    return ' '.join(out)


def _numeros(t):
    """Números de um texto em português, na ordem: "1.200" (milhar), "2,5" e "2.5" (decimal), "1,5 mil",
    "dez mil", "duas"."""
    out = []
    mult = r'\s*(mil\b|milhao\b|milhoes\b|k\b)?'
    padrao = r'(\d+(?:[.,]\d+)*)' + mult + r'|\b(' + '|'.join(_PALAVRAS_NUM) + r')\b' + mult
    for m in re.finditer(padrao, t):
        if m.group(1):
            bruto, fator = m.group(1), m.group(2)
            if re.fullmatch(r'\d{1,3}(?:\.\d{3})+', bruto) and not fator:
                n = float(bruto.replace('.', ''))                 # 1.200 = mil e duzentos
            elif ',' in bruto:
                n = float(bruto.replace('.', '').replace(',', '.'))
            else:
                partes = bruto.split('.')
                n = float(''.join(partes[:-1]) + '.' + partes[-1]) if len(partes) > 1 else float(bruto)
        else:
            n, fator = float(_PALAVRAS_NUM[m.group(3)]), m.group(4)
        out.append(n * _MULT.get(fator, 1))
    return out


def casos_por_mes(texto):
    """'120 requisições por mês' -> 120; '15 por dia' -> 300 (20 dias úteis, como nos tempos); '600/ano' -> 50.
    None sem número ou sem período."""
    t = sem_acento(str(texto or '')).lower()
    # dinheiro não é volume: "R$ 2 milhões por mês em 300 pedidos" -> 300
    t = re.sub(r'r\$\s*[\d.,]+\s*(?:mil(?:hoes|hao)?\b|bi(?:lhoes|lhao)\b)?', ' ', t)
    # dinheiro escrito por extenso também: "20 mil reais", "5 milhões de reais"
    t = re.sub(r'[\d.,]+\s*(?:mil|milhoes|milhao|k)?\s*(?:de\s+)?reais\b', ' ', t)
    # ano não é volume: "em 2025 foram 14.400 no ano" -> 14.400
    t = re.sub(r'\b(?:em|de|no ano de|ano)\s+(19|20)\d\d\b', ' ', t)
    t = re.sub(r'\bmeio milhao\b', '500000', t)
    t = re.sub(r'\bmeio mil\b', '500', t)
    t = _extenso_para_numero(t)                # "cento e vinte" -> 120; "2 mil e quinhentos" -> 2500
    # "10% dos 500 pedidos": a parte que entra no processo
    parte = re.search(r'(\d+(?:[.,]\d+)?)\s*%\s*d[aeo]s?\s+(\d[\d.,]*)', t)
    if parte:
        tot = _numeros(parte.group(2))
        if tot:
            t = t[:parte.start()] + f' {float(parte.group(1).replace(",", ".")) / 100 * tot[0]:g} ' + t[parte.end():]
    # "pico de 300, normal 100": o volume do mês comum, não o pico
    normal = re.search(r'\b(?:normal(?:mente)?|em media|media de|geralmente|usual(?:mente)?|tipico)\s*(?:de\s+)?'
                       r'(\d[\d.,]*\s*(?:mil\b)?)', t)
    if normal and re.search(r'\bpico\b', t):
        t = re.sub(r'\bpico\s+de\s+[\d.,]+\s*(?:mil\b)?', ' ', t)
    # abreviações de período: "50/sem", "80/d", "300/m"
    t = re.sub(r'/\s*sem\b', ' por semana', t)
    t = re.sub(r'/\s*d\b', ' por dia', t)
    t = re.sub(r'/\s*m\b', ' por mes', t)
    # "4 a cada 2 semanas" = 2 por semana
    cada_n = re.search(r'(\d[\d.,]*)\s*(?:\w+\s+)?(?:a\s+)?cada\s+(\d+)\s+(dia|semana|quinzena|mes|trimestre|'
                       r'semestre|ano)', t)
    if cada_n:
        nums = _numeros(cada_n.group(1))
        if nums and float(cada_n.group(2)) > 0:
            return nums[0] / float(cada_n.group(2)) * _POR[cada_n.group(3)]
    # "3 lotes de 50" = 150; só com palavra de lote ("120 requisições de 3 áreas" continua 120)
    lote = re.search(r'(\d+)\s+(?:lotes?|remessas?|pacotes?|caixas?|cargas?|levas?)\s+de\s+(\d+)', t)
    # faixa: "entre 100 e 150", "300 a 400", "300-400" -> a média
    entre = (re.search(r'entre\s+(.+?)\s+e\s+(.+?)(?=\s+(?:por|/|ao|a cada|cada)\b|$)', t)
             or re.search(r'(\d[\d.,]*\s*(?:mil)?)\s*(?:a|-|ou)\s*(\d[\d.,]*\s*(?:mil)?)(?=\s|/|$)', t))
    numeros = _numeros(t)
    if entre and _numeros(entre.group(1)) and _numeros(entre.group(2)):
        a, b = _numeros(entre.group(1))[0], _numeros(entre.group(2))[0]
        if a < 1000 <= b and a * 1000 <= b:
            a *= 1000                                    # "de 2 a 3 mil": o mil vale para os dois
        n = (a + b) / 2
    elif lote:
        n = float(lote.group(1)) * float(lote.group(2))
    else:
        n = numeros[0] if numeros else None
    if re.search(r'(?:por|/|ao|a cada|cada)\s*dias?\s+corridos?', t) and n is not None:
        return n * 30                                    # "30 por dia corrido": todo dia do mês
    p = re.search(r'(?:por|/|ao|a cada|cada|na|no|em uma|em um)\s*(dia|semana|quinzena|mes|trimestre|semestre|ano|'
                  r'hora)|\b(diari|seman|quinzena|mensa|trimestra|semestra|anua)', t)
    if n is None or not p:
        return None
    periodo = p.group(1) or {'diari': 'dia', 'seman': 'semana', 'quinzena': 'quinzena', 'mensa': 'mes',
                             'trimestra': 'trimestre', 'semestra': 'semestre', 'anua': 'ano'}[p.group(2)]
    return n * _POR[periodo]


def _duracoes_do_detalhe(c):
    from .validacao import tempos_do_detalhe
    out = {}
    if not c.caminho:
        return out
    for e in c.de_tipo('subprocesso'):
        if isinstance(e['bruto'].get('detalhe'), str):
            r = tempos_do_detalhe(c, e)
            if r and r[1]:
                out[e['id']] = r[1]
    return out


# erros de cadastro (risco, dor, regra que cita o que não existe) não mudam os números do fluxo
_SO_CADASTRO = {'referencia_inexistente', 'dor_inexistente', 'regra_inexistente', 'raci_papel_inexistente',
                'sistema_inexistente', 'papel_inexistente', 'tipo_invalido', 'percentual_ilegivel', 'data_invalida'}


def _alertas(c, r):
    """O que faz os números da análise não valerem, ou parecerem errados: dito antes dos números."""
    from .util import minutos
    from .validacao import validar
    out = []
    erros = [a for a in validar(c) if a.nivel == 'erro' and a.codigo not in _SO_CADASTRO]
    if erros:
        out.append(f'o fluxo tem {len(erros)} erro(s) de validação (ex.: {erros[0].texto[:90]}): os números abaixo '
                   'não valem até corrigir (rode validar)')
    sim = r.get('_sim')
    if not erros and sim and sim.get('travados'):
        onde = ', '.join(f'"{c.nome(x)}" [{x}]' for x in list(sim['travados'])[:3])
        out.append(f'a simulação achou casos que não terminam (a ficha fica parada em {onde}): há travamento que a '
                   'prova do validar não alcançou (mapa grande). Confira se cada paralelo fecha com paralelo e se '
                   'cada caminho chega a um fim; os números abaixo não valem até corrigir')
    t = r['tempos']
    try:
        informado = minutos(c.processo.get('prazo_informado'))
    except Exception:
        informado = None
    esperado = t.get('lead_time_esperado')
    if informado and esperado and abs(esperado - informado) > max(480, 0.5 * max(esperado, informado)):
        out.append(f'o prazo que a pessoa informou ({c.processo.get("prazo_informado")}) e o lead time do mapa '
                   f'({formatar_minutos(esperado)}) não batem: falta tempo de espera em algum passo, ou o prazo '
                   'informado é outro (só do caminho feliz, só de uma área)?')
    cg = r.get('carga')
    if cg and (cg['pessoas'] > 60 or any(n > 25 for _, _, n in cg['por_papel'])):
        out.append(f'a carga dá {numero_br(cg["pessoas"], 1)} pessoas: confira o volume (entendido como '
                   f'{numero_br(cg["casos_mes"])} casos por mês) e os tempos de execução')
    for e in c.atividades():
        if e['execucao'] and e['execucao'] > 20 * 480:
            out.append(f'"{c.nome(e["id"])}" tem execução de {formatar_minutos(e["execucao"])}: é trabalho de alguém '
                       'nesse tempo todo, ou é espera (tempo.espera)?')
            break
    return out


def _precisa_simular(c):
    """Vários inícios ou tempo em faixa ("2 a 4h") também pedem a simulação (sorteio do início e da duração)."""
    from .util import faixa_minutos
    if len([e for e in c.de_tipo('inicio') if c.saidas[e['id']]]) > 1:
        return True
    return any(faixa_minutos(e['tempo_texto'].get(k)) for e in c.elementos.values() for k in ('execucao', 'espera'))


def _frequencias(c):
    """(visitas, trabalho em minutos por caso ou None): pela simulação quando o mapa pede, senão pela conta."""
    from .simulacao import simular
    precisa = _precisa_simular(c) or any(e['tipo'] in ('paralelo', 'inclusivo', 'borda')
                                         or (e['tipo'] == 'fim' and e['encerra']) for e in c.elementos.values())
    sim = simular(c) if precisa else None
    if sim and not sim['incompletos']:
        return sim['visitas'], sim['trabalho']
    return visitas(c), None


def carga(c, vis, trabalho=None):
    """Horas de trabalho por mês, no total e por papel: volume x vezes que cada atividade roda x execução.
    Pessoas equivalentes em 160 h/mês (jornada cheia, sem descontar pausa e reunião: é o mínimo)."""
    volume = casos_por_mes(c.processo.get('volume'))
    if not volume:
        return None
    por_caso, sem_tempo = _horas_por_caso(c, vis, trabalho=trabalho)
    # o papel da carta filha que tem o mesmo nome de um papel daqui soma nele; o resto aparece pelo nome
    por_nome = {sem_acento(c.nome_papel(p)).lower(): p for p in c.papeis}
    por_papel = {}
    for chave, h in por_caso.items():
        p = chave if chave in c.papeis else por_nome.get(sem_acento(str(chave)).lower(), chave)
        por_papel[p] = por_papel.get(p, 0) + h * volume
    total = sum(por_papel.values())
    return {'casos_mes': volume, 'horas_mes': total, 'pessoas': total / 160,
            'por_papel': sorted(((p, h, h / 160) for p, h in por_papel.items()), key=lambda x: -x[1]),
            'sem_tempo': sem_tempo}


def _horas_por_caso(c, vis, prof=0, trabalho=None):
    """Horas de trabalho por caso, por papel. Subprocesso com "detalhe": o trabalho é o da carta filha (com os
    papéis dela), vezes quantas vezes o subprocesso roda aqui; o tempo dele no mapa de cima não conta de novo."""
    import os
    from .modelo import carregar
    por, sem_tempo = {}, 0
    for e in c.atividades():
        if (c.papeis.get(e['papel']) or {}).get('tipo') == 'externo' or e['automatizada']:
            continue
        detalhe = e['bruto'].get('detalhe') if e['tipo'] == 'subprocesso' else None
        if detalhe and isinstance(detalhe, str) and c.caminho and prof < 3:
            arq = os.path.join(os.path.dirname(os.path.abspath(c.caminho)), detalhe)
            if os.path.isdir(arq):
                arq = os.path.join(arq, 'carta.json')
            if os.path.abspath(arq) != os.path.abspath(c.caminho) and os.path.exists(arq):
                try:
                    filha = carregar(arq)
                    v_filha, t_filha = _frequencias(filha)     # a mesma conta que a análise da filha usa
                    sub, sem = _horas_por_caso(filha, v_filha, prof + 1, trabalho=t_filha)
                except Exception:
                    sub, sem = None, 0
                if sub is not None:
                    for p, h in sub.items():
                        chave = filha.nome_papel(p) if p in filha.papeis else p
                        por[chave] = por.get(chave, 0) + h * vis.get(e['id'], 0)
                    sem_tempo += sem
                    continue
        if e['execucao'] is None:
            sem_tempo += 1
            continue
        # com a simulação, o trabalho de fato feito (a atividade cortada por um prazo conta só a parte feita)
        minutos_caso = trabalho[e['id']] if trabalho and e['id'] in trabalho else vis.get(e['id'], 0) * e['execucao']
        por[e['papel']] = por.get(e['papel'], 0) + minutos_caso / 60
    return por, sem_tempo


def _frequencia(r, elementos):
    # o padrão só acontece quando todos os elementos acontecem: vale o menos frequente
    return min([r['visitas'].get(x, 0) for x in elementos] or [0])


def _origem_do_laco(c, x):
    """A borda de onde sai o laço (andando para trás até uma atividade), ou None."""
    vistos = set()
    while x in c.elementos and x not in vistos and len(vistos) < 6:
        vistos.add(x)
        e = c.elementos[x]
        if e['tipo'] == 'borda':
            return e
        if e['tipo'] in NOS_DE_TRABALHO and len(vistos) > 1:
            return None
        ent = c.entradas[x]
        if len(ent) != 1:
            return None
        x = ent[0]['de']
    return None


def _laco_de_espera(c, x):
    """O laço sai de um prazo (evento de tempo, borda de prazo ou lembrete que não interrompe)?"""
    vistos = set()
    while x in c.elementos and x not in vistos and len(vistos) < 6:
        vistos.add(x)
        e = c.elementos[x]
        if e['tipo'] in ('evento', 'borda') and (e['gatilho'] == 'tempo' or
                                                 (e['tipo'] == 'borda' and not e['interrompe'])):
            return True
        if e['tipo'] in NOS_DE_TRABALHO and len(vistos) > 1:
            return False
        ent = c.entradas[x]
        if len(ent) != 1:
            return False
        x = ent[0]['de']
    return False


def _ramos_diferentes(c, a, b):
    """b só é alcançado a partir de a passando por um paralelo ou OU que divide (ramos que correm juntos)."""
    pilha, vistos = [f['para'] for f in c.saidas[a] if not f['borda']], set()
    while pilha:
        x = pilha.pop()
        if x == b:
            return False
        if x in vistos or x not in c.elementos:
            continue
        vistos.add(x)
        e = c.elementos[x]
        if e['tipo'] in NOS_DE_TRABALHO or (e['tipo'] in ('paralelo', 'inclusivo') and len(c.saidas[x]) > 1):
            continue
        pilha.extend(f['para'] for f in c.saidas[x])
    return True


def _oportunidades(c, r, ativ):
    """Cada oportunidade com o desperdício Lean e um peso (quantas vezes acontece x quanto custa), para a lista
    sair em ordem de impacto. Controle obrigatório (com regra ou subprocesso de conformidade) nunca é sugerido
    para corte."""
    ops = r['oportunidades']

    def op(tipo, texto, elementos, desperdicio, custo=1.0, freq=None):
        freq = _frequencia(r, elementos) if freq is None else freq
        ops.append({'tipo': tipo, 'texto': texto, 'elementos': elementos, 'desperdicio': DESPERDICIOS[desperdicio],
                    'frequencia': freq, 'peso': freq * custo})

    vistos_laco = set()
    for x in r['retrabalho']:
        if (x['de'], x['para']) in vistos_laco:
            continue
        vistos_laco.add((x['de'], x['para']))
        # quantas vezes por caso o laço é percorrido: as visitas de quem volta, vezes a chance da saída quando
        # quem volta é a própria decisão (35% de "Não" numa decisão que roda 0,8 vez = 28% dos casos)
        de = c.elementos[x['de']]
        chance = ((x['percentual'] if x['percentual'] is not None else 20) / 100) if de['tipo'] in ESCOLHA else 1
        freq_laco = (r['visitas'].get(x['de'], 0) or 0) * chance
        # "35% das vezes; 0,54 volta por caso": a chance em cada passagem e quantas voltas, em média, por caso
        voltas = numero_br(freq_laco, 2) if freq_laco >= 0.005 else 'menos de 0,01'
        quanto = (f' ({x["percentual"]:.0f}% das vezes; {voltas} volta por caso)'
                  if x['percentual'] is not None and freq_laco else '')
        destino = c.destino_legivel(x['para'])
        origem = _origem_do_laco(c, x['de'])
        if origem and origem['gatilho'] in ('erro', 'sinal', 'mensagem', 'condicao'):
            tipo_ev = {'erro': 'Falha', 'sinal': 'Aviso de fora', 'mensagem': 'Mensagem de fora',
                       'condicao': 'Condição'}[origem['gatilho']]
            op('excecao_em_laco', f'{tipo_ev} que faz refazer: "{c.nome(origem["id"])}" volta para "{destino}"'
               f'{quanto}. Trate a causa da exceção (disponibilidade, contingência, comunicação antes) em vez de '
               'refazer o trabalho.', [x['de'], x['para']], 'defeito', 8.0, freq=freq_laco)
            continue
        if _laco_de_espera(c, x['de']):
            op('espera_em_laco', f'Laço de espera: de "{c.nome(x["de"])}" volta para "{destino}"{quanto} '
               '(lembrete, cobrança). Quantas voltas até desistir? Um prazo final e um canal mais rápido encurtam '
               'a espera.', [x['de'], x['para']], 'espera', 10.0, freq=freq_laco)
            continue
        op('retrabalho', f'Retrabalho: de "{c.nome(x["de"])}" volta para "{destino}"{quanto}. Ataque a causa '
           'na origem (checklist, campo obrigatório, validação no sistema) em vez de conferir depois.',
           [x['de'], x['para']], 'defeito', 15.0, freq=freq_laco)
    volta_ids = c.arestas_de_volta()
    for a, b, z in r['vai_e_volta']:
        if any(f['id'] in volta_ids for f in c.saidas[z]):
            continue                                     # é o laço de retrabalho (já listado como retrabalho)
        if re.match(r'(comunicar|avisar|informar|notificar|responder|devolver resposta)\b',
                    sem_acento(c.nome(z)).lower()):
            continue                                     # voltar para avisar o resultado é o normal, não falta
        op('vai_e_volta', f'Vai e volta entre áreas: {c.nome_papel(c.raia_de(a))} -> {c.nome_papel(c.raia_de(b))} -> '
           f'{c.nome_papel(c.raia_de(z))} ("{c.nome(a)}", "{c.nome(b)}", "{c.nome(z)}"). Dá para uma raia só '
           'fazer as duas pontas, ou trazer a informação antes?', [a, b, z], 'transporte', 2.0)
    pc = r['passagens_caminho']
    trab_caminho = [x for x in r['caminho_feliz'] if c.elementos[x]['tipo'] in NOS_DE_TRABALHO]
    if trab_caminho and len(pc) >= max(4, len(trab_caminho) * 2 // 3):
        op('passagens', f'No caso típico, o trabalho troca de mãos {len(pc)} vezes em {len(trab_caminho)} '
           'atividades: cada troca é fila e risco de perda. Veja se atividades seguidas podem ficar com o mesmo '
           'responsável.', [a for a, _ in pc], 'transporte', 1.0, freq=1.0)
    for eid, m in r['gargalos']:
        if m < 480:
            continue
        if c.elementos[eid]['tipo'] == 'evento':
            op('espera', f'Espera de {formatar_minutos(m)} até "{c.nome(eid)}" (resposta de fora): dá para combinar '
               'prazo (SLA), pedir antes, mandar lembrete ou trocar o canal?', [eid], 'espera', m / 480)
        elif (c.papeis.get(c.elementos[eid]['papel']) or {}).get('tipo') == 'externo':
            op('espera', f'Prazo de {formatar_minutos(m)} de quem é de fora em "{c.nome(eid)}": dá para combinar '
               'prazo em contrato (SLA), pedir antes ou acompanhar com lembrete?', [eid], 'espera', m / 960)
        else:
            op('espera', f'Espera de {formatar_minutos(m)} antes de "{c.nome(eid)}": o que segura? (fila, alçada, '
               'lote, agenda). Prazo combinado (SLA) ou gatilho automático ajudam.', [eid], 'espera', m / 480)
    # conferências seguidas: pergunta, não corte (pode ser controle obrigatório)
    pares_conf = []
    for e in ativ:
        if not _APROVA.match(sem_acento(e['nome']).lower()):
            continue
        for d in _proximos_de_trabalho(c, e['id'], sem_borda=True, sem_volta=True):
            outro = c.elementos[d]
            if _ramos_diferentes(c, e['id'], d):
                continue                                 # cada uma num ramo de paralelo/OU: não são em série
            if not _APROVA.match(sem_acento(outro['nome']).lower()):
                continue
            obrigatorio = any(x['regras'] or x['tipo'] == 'subprocesso' for x in (e, outro))
            if obrigatorio:
                continue
            pares_conf.append((e['id'], d))
    # uma cadeia de conferências seguidas vira UM item ("A, B e C, uma depois da outra"), não um por par
    seguinte = dict(pares_conf)
    destinos = {b for _, b in pares_conf}
    for a0, _ in pares_conf:
        if a0 in destinos:
            continue
        cadeia, x = [a0], a0
        while x in seguinte and seguinte[x] not in cadeia:
            x = seguinte[x]
            cadeia.append(x)
        nomes = [f'"{c.nome(y)}"' for y in cadeia]
        lista = (', '.join(nomes[:-1]) + ' e ' + nomes[-1] if len(nomes) <= 5 else
                 f'{len(nomes)} conferências ({nomes[0]}, {nomes[1]} ... {nomes[-1]})')
        op('aprovacao_em_serie', f'Conferência em série: {lista}, uma depois da outra. Elas pegam o mesmo tipo '
           'de erro? Se sim, veja se uma cobre a outra; se não, dá para rodar em paralelo.', cadeia,
           'superprocessamento', 1.0 + 0.5 * (len(cadeia) - 2))
    # digitação em mais de um sistema
    digita = [e for e in ativ if _DIGITA.match(sem_acento(e['nome']).lower()) and e['sistema']]
    sistemas = {s for e in digita for s in e['sistema']}
    if len(sistemas) >= 2:
        nomes = ', '.join(sorted(c.nome_sistema(s) for s in sistemas))
        op('digitacao_dupla', f'Registro em {len(sistemas)} sistemas ({nomes}): os mesmos dados são digitados duas '
           'vezes? Se sim, uma integração ou um cadastro único elimina.', [e['id'] for e in digita],
           'superprocessamento', 1.5)
    # sem sistema E com cara de trabalho de dado (registrar, preencher, calcular, conferir...): o resto é manual
    # por natureza (assinar, entregar, visitar) e não é desperdício
    manuais = [e for e in ativ if e['sistema_respondido'] and not e['sistema'] and not e['automatizada']
               and (c.papeis.get(e['papel']) or {}).get('tipo') != 'externo'
               and re.match(r'(registrar|preencher|lancar|digitar|cadastrar|calcular|conferir|consultar|copiar|'
                            r'atualizar|controlar|planilhar|anotar|emitir|gerar|montar|consolidar)',
                            sem_acento(e['nome'] or '').lower())]
    if len(manuais) >= 3:
        op('manual', f'{len(manuais)} atividades internas sem sistema: candidatas a formulário, planilha controlada '
           'ou automação.', [e['id'] for e in manuais], 'movimentacao', 0.5,
           freq=max(r['visitas'].get(e['id'], 0) for e in manuais))
    for e in ativ:
        if e['valor'] == 'NAV':
            op('desperdicio', f'"{c.nome(e["id"])}" foi classificada como desperdício (NAV): dá para eliminar ou '
               'prevenir?', [e['id']], 'superprocessamento', 1.0)
    for d in c.de_tipo('decisao'):
        if decisao_sem_criterio(c, d):
            op('regra_implicita', f'A decisão "{c.nome(d["id"])}" não tem critério escrito: fica na cabeça de quem '
               'decide. Escreva a regra (e ela vira candidata a automação).', [d['id']], 'talento', 0.8)
    for eid, papeis in r['raci'].items():
        if len(papeis.get('A', [])) > 1:
            op('raci', f'"{c.nome(eid)}" tem {len(papeis["A"])} aprovadores (A): o RACI pede um só.', [eid],
               'superprocessamento', 0.5)
    ops.sort(key=lambda o: -o['peso'])


def _espera_de_fora(e):
    """Evento ou tarefa que espera alguém de fora responder: o tempo dele é espera, não trabalho."""
    if e['tipo'] == 'evento':
        return e['gatilho'] in ('mensagem', 'condicao', 'sinal') and not e['bruto'].get('envia')
    return e['tipo'] in NOS_DE_TRABALHO and bool(e['bruto'].get('recebe'))


def pct_txt(t):
    """Eficiência em texto: abaixo de 1% com uma casa; '—' quando metade do caminho não tem tempo ou quando
    uma espera por resposta de fora não tem tempo (sairia 100% para um processo que espera dias)."""
    if t['eficiencia'] is None or t.get('tempo_incompleto'):
        return '— (falta tempo em várias atividades)' if t.get('tempo_incompleto') else '—'
    if t.get('espera_sem_tempo'):
        return '— (falta a espera pela resposta)'
    v = t['eficiencia'] * 100
    return f'{v:.1f}%'.replace('.', ',') if v < 1 else f'{v:.0f}%'


def _freq_txt(v):
    """Quantas vezes acontece por caso: 35% dos casos, ou 1,5 vez por caso (retrabalho repete)."""
    if v >= 1.05:
        return f' [{v:.1f} vez por caso]'.replace('.', ',')
    if v < 0.995:
        return f' [{v * 100:.0f}% dos casos]'
    return ''


def imprimir(c, r, maximo=10):
    t = r['tempos']
    k = r['contagem']
    print(f'Análise: {c.titulo()} ({c.cenario().upper()})')
    for a in r.get('alertas') or []:
        print(f'  ! {a}')
    print(f'  {k["atividades"]} atividades · {k["decisoes"]} decisões · {k["raias"]} raias · '
          f'{k["sistemas"]} sistemas · {k["fins"]} fins')
    passos = [c.nome(x) for x in r['caminho_feliz'] if c.elementos[x]['tipo'] not in PORTAS]
    print(f'\nCaminho feliz ({len(passos)} passos): {" > ".join(passos)}')
    if not r['caminho_completo']:
        print('  ! o caminho feliz não chegou a um fim (parou num laço ou num beco): confira o fluxo e os '
              'percentuais das decisões')
    if r['paralelos']:
        print('  em paralelo: ' + ', '.join(c.nome(x) for x in r['paralelos']
                                             if c.elementos[x]['tipo'] not in PORTAS))
    if not t['execucao'] and not t['espera']:
        informado = c.processo.get('prazo_informado')
        print('  sem tempos por atividade ainda' + (f' (prazo informado pela pessoa: {informado})' if informado
                                                    else '') + ': pergunte execução e espera de cada passo')
    else:
        print(f'  esforço (execução, todos os ramos) {formatar_minutos(t["execucao"])} · '
              f'espera {formatar_minutos(t["espera"])} · lead time {formatar_minutos(t["lead_time"])}', end='')
        print(f' · eficiência do ciclo {pct_txt(t)}')
        if t['lead_time_esperado'] is not None:
            aviso = ''
            if t['decisoes_sem_percentual']:
                aviso = (f' ({len(t["decisoes_sem_percentual"])} decisão(ões) sem percentual: caminhos com peso '
                         'igual)')
            print(f'  lead time esperado, com exceções, retrabalho e todos os desfechos (inclusive recusas): {formatar_minutos(t["lead_time_esperado"])}'
                  + aviso)
            if t.get('percentis'):
                pc = t['percentis']
                print(f'  em 50% dos casos até {formatar_minutos(pc["p50"])} · 80% até {formatar_minutos(pc["p80"])} · '
                      f'90% até {formatar_minutos(pc["p90"])} (simulação de 4.000 casos)')
    if t.get('espera_sem_tempo'):
        print(f'  (sem tempo de resposta: {", ".join(c.nome(x) for x in t["espera_sem_tempo"])}: a espera por quem '
              'está de fora conta zero, o lead time real é maior)')
    if t['sem_tempo'] and (t['execucao'] or t['espera']):
        print(f'  (sem tempo informado: {", ".join(c.nome(x) for x in t["sem_tempo"])}: o total está subestimado)')
    print(f'\nPassagens de bastão no caso típico: {len(r["passagens_caminho"])} (ligações entre raias no mapa '
          f'todo: {len(r["passagens"])}) · vai e volta entre áreas: {len(r["vai_e_volta"])} · laços de retrabalho: '
          f'{len(r["retrabalho"])}')
    cg = r.get('carga')
    if cg:
        print(f'Carga: {numero_br(cg["casos_mes"])} casos/mês x tempo de execução = {numero_br(cg["horas_mes"])} h de '
              f'trabalho por mês (≈ {numero_br(cg["pessoas"], 1)} pessoa(s) em jornada cheia de 160 h)')
        for p, h, n in cg['por_papel'][:6]:
            print(f'  {c.nome_papel(p)}: {numero_br(h)} h/mês (≈ '
                  f'{numero_br(n, 1) if n >= 0.05 else "menos de 0,1"} pessoa)')
        if cg['sem_tempo']:
            print(f'  ({cg["sem_tempo"]} atividade(s) sem tempo: a carga está subestimada)')
    v = r['valor']
    total = sum(x['atividades'] for x in v.values()) or 1
    print('Valor agregado: ' + ' · '.join(f'{nome} {v[nome]["atividades"]} ({v[nome]["atividades"] / total:.0%})'
                                          for nome in ('VA', 'NAV-N', 'NAV', 'sem') if v[nome]['atividades']))
    ops = r['oportunidades']
    if ops:
        print(f'\nOportunidades, da maior para a menor ({len(ops)}):')
        mostrar = ops if not maximo else ops[:maximo]
        for i, o in enumerate(mostrar, 1):
            tag = '' if ('% dos casos' in o['texto'] or o['tipo'] in ('retrabalho', 'espera_em_laco', 'excecao_em_laco')) else _freq_txt(o['frequencia'])
            print(f'  {i}. [{o["desperdicio"]}]{tag} {o["texto"]}')
        if len(ops) > len(mostrar):
            print(f'  (+{len(ops) - len(mostrar)} de menor impacto: python senku.py analisar <carta> --todas)')
    print('\nOs tempos são estimativas da entrevista, não medição: confirme antes de usar em decisão.')
