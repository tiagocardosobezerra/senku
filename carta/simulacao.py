"""
Simulação do processo, caso a caso, com as regras de ficha do BPMN.

Cada caso começa no início com uma ficha. A ficha anda pelo fluxo:
    atividade / evento     demora execução + espera; com borda, sorteia se a borda dispara (pelo percentual
                           dela). A que interrompe tira a ficha da atividade quando dispara (prazo: no prazo da
                           borda; erro ou mensagem: no fim da atividade); a que não interrompe solta uma ficha a
                           mais pelo caminho dela e a atividade segue
    decisão / corrida      sorteia uma saída pelo percentual
    paralelo que divide    uma ficha em cada saída
    paralelo que junta     espera uma ficha de cada entrada
    OU que divide          cada saída acontece pela sua chance; se nenhuma, o caso segue direto para a junção
    OU que junta           espera as fichas que o OU de abertura soltou
    fim                    a ficha some; fim que encerra ("encerra": true) acaba o caso na hora
O lead time do caso é a hora em que a última ficha some (ou o fim que encerra). Muitos casos sorteados com
semente fixa dão a média, os percentis (P50, P80, P90) e quantas vezes cada elemento roda por caso: o mesmo
número em toda rodada, para o comparar AS-IS x TO-BE ser justo.

É o que um analista faria num simulador (Bizagi, Signavio): sem fórmula aproximada para paralelo com laço,
borda dentro de ramo paralelo ou fim que encerra no meio de um ramo.
"""

import heapq

from .modelo import NOS_DE_TRABALHO

CASOS = 4000
SEMENTE = 20261103
PASSOS_MAX = 4000          # por caso: laço que quase nunca sai não trava a análise


_MASCARA = (1 << 64) - 1


class _Sorte:
    """Número "aleatório" que depende só do caso, do id do elemento, de quantas vezes ele já rodou no caso e
    do motivo do sorteio. Duas versões da carta com o mesmo elemento tiram a mesma sorte para ele: o comparar
    AS-IS x TO-BE (ou aceite x atual) mostra a diferença do processo, não do sorteio."""

    def __init__(self, semente):
        import zlib
        self.semente = semente
        self.chaves = {}
        self.caso = 0
        self.contagem = {}
        self._crc = zlib.crc32

    def novo_caso(self, k):
        self.caso, self.contagem = k, {}

    def random(self, eid='', motivo=0):
        chave = self.chaves.get(eid)
        if chave is None:
            chave = self.chaves[eid] = self._crc(str(eid).encode('utf-8'))
        n = self.contagem.get((eid, motivo), 0)
        self.contagem[(eid, motivo)] = n + 1
        z = (self.semente * 0x9E3779B97F4A7C15 + self.caso * 0xBF58476D1CE4E5B9 + chave * 0x94D049BB133111EB
             + n * 0x2545F4914F6CDD1D + motivo * 0x632BE59BD9B4E019) & _MASCARA
        z = ((z ^ (z >> 30)) * 0xBF58476D1CE4E5B9) & _MASCARA          # splitmix64
        z = ((z ^ (z >> 27)) * 0x94D049BB133111EB) & _MASCARA
        z ^= z >> 31
        return (z >> 11) / float(1 << 53)


def _sortear(rng, opcoes, eid='', motivo=0):
    """opcoes: [(peso, valor)] -> valor sorteado pelo peso (pesos zerados: a primeira)."""
    total = sum(p for p, _ in opcoes)
    if total <= 0:
        return opcoes[0][1]
    r, acum = rng.random(eid, motivo) * total, 0.0
    for p, v in opcoes:
        acum += p
        if r <= acum:
            return v
    return opcoes[-1][1]


def _abertura_de(c):
    """Junção OU -> OU que abriu os caminhos dela."""
    from .analise import _abertura_inclusiva
    out = {}
    for e in c.de_tipo('inclusivo'):
        if len(c.entradas[e['id']]) > 1:
            abre = _abertura_inclusiva(c, e['id'])
            if abre:
                out[e['id']] = abre
    return out


ORCAMENTO = 1_500_000      # passos no total: para mapa enorme, menos casos (o mesmo número em qualquer máquina)
MINIMO_CASOS = 400


def simular(c, casos=CASOS, semente=SEMENTE, duracoes=None):
    """{'media', 'p50', 'p80', 'p90', 'visitas': {id: média por caso}, 'incompletos': n} ou None sem início."""
    from .analise import probabilidades
    inicios = [e['id'] for e in c.de_tipo('inicio') if c.saidas[e['id']]]
    if not inicios:
        return None
    probs = {eid: probabilidades(c, eid)[0] for eid in c.elementos}
    bordas_de = {}
    for f in c.fluxos:
        if f['borda'] and f['para'] in c.elementos:
            bordas_de.setdefault(f['de'], []).append(f)
    abre_de = _abertura_de(c)
    fecha_de = {}
    for j, a in abre_de.items():
        fecha_de.setdefault(a, j)
    rng = _Sorte(semente)
    # a borda não demora por si: o prazo dela já decidiu a hora em que a ficha sai da atividade
    duracao = {eid: 0.0 if e['tipo'] == 'borda' else (e['execucao'] or 0) + (e['espera'] or 0)
               for eid, e in c.elementos.items()}
    duracao.update(duracoes or {})              # subprocesso com detalhe: o tempo vem da carta filha
    # tempo escrito como faixa ("2 a 4h"): cada caso sorteia dentro dela
    from .util import faixa_minutos
    faixas = {}
    for eid, e in c.elementos.items():
        if e['tipo'] == 'borda':
            continue
        fx = [faixa_minutos(e['tempo_texto'].get(k)) for k in ('execucao', 'espera')]
        if any(fx):
            faixas[eid] = (fx[0] or (e['execucao'] or 0, e['execucao'] or 0),
                           fx[1] or (e['espera'] or 0, e['espera'] or 0))
    # junção OU (regra do BPMN): dispara quando nenhuma ficha que ainda pode chegar nela está a caminho. Para
    # isso, de cada junção, os elementos de onde dá para chegar nela
    juncoes_ou = [x for x, e in c.elementos.items() if e['tipo'] == 'inclusivo' and len(c.entradas[x]) > 1]
    alcanca = {}
    for j in juncoes_ou:
        vistos, pilha = set(), [f['de'] for f in c.entradas[j]]
        while pilha:
            y = pilha.pop()
            if y in vistos or y not in c.elementos or y == j:
                continue
            vistos.add(y)
            pilha.extend(f['de'] for f in c.entradas[y])
        alcanca[j] = vistos
    # vários inícios: cada um na sua parte dos casos ("percentual" no início; sem ele, partes iguais)
    pesos_inicio = [(float(c.elementos[i]['bruto'].get('percentual') or 0) or 1.0, i) for i in inicios]
    visitas = {eid: 0 for eid in c.elementos}
    trabalho = {eid: 0.0 for eid in c.elementos}
    tempos, incompletos = [], 0

    travados = {}
    gastos = 0
    for k_caso in range(casos):
        # fluxo que não fecha (fichas que se multiplicam ou laço sem saída) não termina: depois de alguns casos
        # assim, desiste e a análise usa a conta analítica. Mapa enorme: para no orçamento de passos (o mesmo em
        # qualquer máquina) com os casos já feitos, se forem bastantes
        if incompletos >= 20:
            break
        if gastos > ORCAMENTO:
            if len(tempos) < MINIMO_CASOS:
                incompletos = max(incompletos, 1)
            break
        rng.novo_caso(k_caso)
        fila = []                                   # (hora, ordem, elemento, fluxo de entrada)
        ordem = 0
        chegou = {}                                 # junção -> {fluxo: [horas]}
        pendente_ou = {}                            # junção OU -> horas das fichas que já chegaram
        fim_caso, passos, encerrou = 0.0, 0, False

        def soltar(hora, fluxo):
            nonlocal ordem
            ordem += 1
            heapq.heappush(fila, (hora, ordem, fluxo['para'], fluxo['id']))

        inicio = _sortear(rng, pesos_inicio, '__inicio__', 5) if len(inicios) > 1 else inicios[0]
        visitas[inicio] += 1
        for f in c.saidas[inicio]:
            if f['para'] in c.elementos and not f['borda']:
                soltar(0.0, f)
        while (fila or any(pendente_ou.values())) and passos < PASSOS_MAX and len(fila) < 500:
            passos += 1
            if pendente_ou and any(pendente_ou.values()):
                # junção OU com ficha esperando: dispara se nenhuma ficha a caminho ainda pode chegar nela
                a_caminho = {item[2] for item in fila} | {y for y, d in chegou.items() if any(d.values())}
                for j, horas in pendente_ou.items():
                    # (uma ficha já indo para a própria junção também conta: ela chega depois)
                    if horas and not (a_caminho & alcanca[j]) and j not in {item[2] for item in fila}:
                        ordem += 1
                        heapq.heappush(fila, (max(horas), ordem, j, '__dispara__'))
                        pendente_ou[j] = []
            if not fila:
                break
            hora, _, x, fid = heapq.heappop(fila)
            e = c.elementos[x]
            t = e['tipo']
            entradas = c.entradas[x]
            # junções esperam
            if t == 'paralelo' and len(entradas) > 1:
                d = chegou.setdefault(x, {})
                d.setdefault(fid, []).append(hora)
                if not all(d.get(g['id']) for g in entradas if g['de'] in c.elementos):
                    continue
                hora = max(d[g['id']].pop(0) for g in entradas if g['de'] in c.elementos)
            elif t == 'inclusivo' and len(entradas) > 1 and fid != '__dispara__':
                pendente_ou.setdefault(x, []).append(hora)
                continue
            visitas[x] += 1
            if t == 'fim':
                fim_caso = max(fim_caso, hora)
                if e['encerra']:
                    fim_caso, encerrou = hora, True
                    break
                continue
            saidas = [f for f in c.saidas[x] if f['para'] in c.elementos]
            normais = [f for f in saidas if not f['borda']]
            if t in NOS_DE_TRABALHO or t in ('evento', 'borda'):
                dur = duracao[x]
                execucao = e['execucao'] or 0
                if x in faixas:
                    (a1, b1), (a2, b2) = faixas[x]
                    execucao = a1 + (b1 - a1) * rng.random(x, 6)
                    dur = execucao + a2 + (b2 - a2) * rng.random(x, 7)
                fim_ativ = hora + dur
                interrompeu = None
                bs = bordas_de.get(x, [])
                corta = [f for f in bs if c.elementos[f['para']]['interrompe']]
                if corta:
                    p_corta = {f['id']: probs[x].get(f['id'], 0) for f in corta}
                    escolha = _sortear(rng, [(max(0.0, 1 - sum(p_corta.values())), None)] +
                                       [(p, f) for f, p in zip(corta, p_corta.values())], x, 1)
                    if escolha is not None:
                        b = c.elementos[escolha['para']]
                        quando = hora + (b['espera'] if b['gatilho'] == 'tempo' and b['espera'] else dur)
                        # o trabalho feito é só a parte da atividade até o prazo vencer
                        trabalho[x] += execucao * (min(1.0, (quando - hora) / dur) if dur else 1.0)
                        soltar(quando, escolha)
                        interrompeu = escolha
                for f in bs:
                    if f in corta:
                        continue
                    if rng.random(f['para'], 2) < probs[x].get(f['id'], 0):
                        b = c.elementos[f['para']]
                        quando = hora + (b['espera'] if b['gatilho'] == 'tempo' and b['espera'] else dur / 2)
                        soltar(min(quando, fim_ativ), f)
                if interrompeu is not None:
                    continue
                trabalho[x] += execucao
                if len(normais) > 1 and t not in NOS_DE_TRABALHO:
                    for f in normais:                       # evento que divide: todos os caminhos
                        soltar(fim_ativ, f)
                elif len(normais) > 1:
                    for f in normais:                       # atividade com várias saídas: divisão implícita
                        soltar(fim_ativ, f)
                elif normais:
                    soltar(fim_ativ, normais[0])
                else:
                    fim_caso = max(fim_caso, fim_ativ)
                continue
            if not normais:
                fim_caso = max(fim_caso, hora)
                continue
            if t in ('decisao', 'corrida') and len(normais) > 1:
                f = _sortear(rng, [(probs[x].get(g['id'], 0), g) for g in sorted(normais, key=lambda g: g['para'])],
                             x, 3)
                soltar(hora + duracao[x], f)
            elif t == 'inclusivo' and len(normais) > 1:
                escolhidos = [g for g in normais if rng.random(g['para'], 4) < probs[x].get(g['id'], 0)]
                juncao = fecha_de.get(x)
                if not escolhidos:
                    # nenhum caminho: o caso segue direto (o validar avisa); vai uma ficha para a junção
                    if juncao:
                        ordem += 1
                        heapq.heappush(fila, (hora, ordem, juncao, '_'))
                    continue
                for g in escolhidos:
                    soltar(hora + duracao[x], g)
            else:
                for g in normais:                           # paralelo que divide, ou passagem
                    soltar(hora + duracao[x], g)
        gastos += passos
        # ficha parada numa junção que nunca completa (travamento) também é caso que não terminou
        parados = [y for y, d in chegou.items() if any(v for v in d.values())]
        if (fila or parados) and not encerrou:
            incompletos += 1
            for y in parados or [item[2] for item in fila[:1]]:
                travados[y] = travados.get(y, 0) + 1
        tempos.append(fim_caso)

    if not tempos:
        return {'media': 0.0, 'p50': 0.0, 'p80': 0.0, 'p90': 0.0, 'visitas': {k: 0.0 for k in visitas},
                'trabalho': {k: 0.0 for k in visitas}, 'incompletos': max(incompletos, 1), 'travados': travados,
                'casos': 0}
    casos = len(tempos)
    tempos.sort()

    def pct(q):
        return tempos[min(len(tempos) - 1, int(q * len(tempos)))]
    return {'media': sum(tempos) / len(tempos), 'p50': pct(0.5), 'p80': pct(0.8), 'p90': pct(0.9),
            'visitas': {k: v / casos for k, v in visitas.items()},
            'trabalho': {k: v / casos for k, v in trabalho.items()}, 'incompletos': incompletos,
            'travados': travados, 'casos': casos}
