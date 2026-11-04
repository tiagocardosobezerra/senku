"""
Parte externa como pool próprio (BPMN Method and Style): cliente, fornecedor ou órgão público vira um pool
"caixa-preta" (só o nome, sem o processo dele) e a troca com ele vira fluxo de mensagem.

A carta continua com o externo em raia (é como o time conversa sobre o processo); aqui ela é transformada só
para o BPMN:
    interno X -> externo ... -> interno Y   vira   X --mensagem--> [pool]  e  [pool] --mensagem--> Y,
                                                   com a ligação X -> Y no processo interno
    o início é do externo (o cliente pede)   vira   início de mensagem, que recebe do pool
    o fim é do externo                       vira   fim do lado de dentro, depois da última atividade interna
Mensagem só liga em atividade ou evento (é o que o BPMN aceita): quando o lado de dentro é uma porta, entra
um evento "mensagem recebida" antes dela, e a mensagem que sai vem da atividade anterior à porta.

Só funciona quando o trecho externo é uma sequência simples (sem decisão, paralelo ou borda do lado de
fora). Se não for, devolve o motivo e o BPMN sai em raias, como antes. A ida é de mão única: importar este
BPMN traz o externo como pool, sem as atividades dele.
"""

import copy

from carta.modelo import NOS_DE_TRABALHO, PORTAS, Carta
from carta.util import sem_acento


def _externo(c, eid):
    return (c.papeis.get(c.elementos[eid]['papel']) or {}).get('tipo') == 'externo'


def transformar(c):
    """(carta_interna, pools, mensagens) ou (None, motivo, None).
    pools: [{'id', 'nome'}]; mensagens: [{'de': id interno ou None, 'para': id interno ou None, 'pool': id,
    'nome': texto}] (None é o lado do pool)."""
    externos = [eid for eid in c.elementos if c.elementos[eid]['papel'] and _externo(c, eid)]
    if not externos:
        return None, 'não há papel externo', None
    pontas = [eid for eid in externos if c.elementos[eid]['tipo'] in ('inicio', 'fim')]
    meio = [eid for eid in externos if eid not in pontas]
    for eid in meio:
        e = c.elementos[eid]
        if e['tipo'] not in NOS_DE_TRABALHO + ('evento',):
            return None, f'o externo tem "{c.nome(eid)}" ({e["tipo"]}): só sequência simples vira pool', None
        if len([f for f in c.saidas[eid] if not f['borda']]) != 1 or any(f['borda'] for f in c.saidas[eid]):
            return None, f'"{c.nome(eid)}" (externo) segue para mais de um lugar: só sequência simples vira pool', None
        for f in c.entradas[eid]:
            de = c.elementos[f['de']]
            if de['tipo'] == 'corrida':
                return None, (f'a corrida "{c.nome(f["de"])}" espera "{c.nome(eid)}", que está na raia do externo: '
                              'o evento que o processo espera fica na raia de quem espera'), None
            if de['tipo'] == 'borda' or f['borda']:
                return None, f'uma borda leva ao externo ("{c.nome(eid)}"): só sequência simples vira pool', None

    def interno_depois(x):
        """Anda pelo trecho externo (só atividades e eventos de fora) até o primeiro elemento de dentro."""
        cadeia, vistos = [], set()
        while x in meio and x not in vistos:
            vistos.add(x)
            cadeia.append(x)
            x = next(g['para'] for g in c.saidas[x] if not g['borda'])
        return cadeia, x

    dados = copy.deepcopy(c.dados)
    els = {str(e.get('id')): e for e in dados.get('elementos', []) if isinstance(e, dict)}
    papel_interno = next((p for p in c.papeis if c.papeis[p].get('tipo') != 'externo'), None)
    mensagens, novos = [], []

    def papel_de(eid):
        p = c.elementos[eid]['papel']
        return p if p and not _externo(c, eid) else papel_interno

    def religar(de, antigo, novo_alvo):
        e = els.get(de)
        if e is None:
            return
        segue = e.get('segue')
        lista = segue if isinstance(segue, list) else ([segue] if segue else [])
        e['segue'] = [dict(s, para=novo_alvo) if isinstance(s, dict) and s.get('para') == antigo
                      else (novo_alvo if s == antigo else s) for s in lista]

    # início e fim do lado de fora passam para dentro
    for eid in pontas:
        e = els[eid]
        e.pop('papel', None)
        if c.elementos[eid]['tipo'] == 'inicio':
            cadeia, y = interno_depois(next((f['para'] for f in c.saidas[eid]), None))
            if y is None or y in meio:
                return None, 'o início do externo não chega ao processo interno', None
            e['gatilho'] = 'mensagem'
            e['papel'] = papel_de(y) if y in c.elementos else papel_interno
            e['segue'] = y
            pool = c.elementos[cadeia[-1] if cadeia else eid]['papel']
            mensagens.append({'de': None, 'para': eid, 'pool': pool,
                              'nome': c.nome(cadeia[-1]) if cadeia else c.nome(eid)})
        else:
            anteriores = [f['de'] for f in c.entradas[eid] if f['de'] not in meio]
            e['papel'] = papel_de(anteriores[0]) if anteriores else papel_interno
    for f in c.fluxos:
        if f['de'] in meio or f['para'] not in meio or f['de'] in pontas:
            continue
        cadeia, y = interno_depois(f['para'])
        if y in meio or y not in c.elementos:
            return None, 'o trecho externo não volta para o processo', None
        pool = c.elementos[cadeia[0]]['papel']
        # quem manda: a atividade (ou evento) de dentro; se for porta, a atividade logo antes dela
        x = f['de']
        alvo = y
        # o externo só recebe ("Receber orçamento", tarefa que recebe): mensagem de ida, sem resposta
        ultimo = c.elementos[cadeia[-1]]
        so_ida = bool(ultimo['bruto'].get('recebe')) or sem_acento(ultimo['nome'] or '').lower().startswith('receb')
        ey = c.elementos[y]
        espera_outra = ey['tipo'] == 'evento' and (ey['gatilho'] != 'mensagem' or ey['bruto'].get('envia'))
        if (ey['tipo'] in PORTAS + ('fim',) or espera_outra) and not so_ida:
            # mensagem só chega em atividade ou evento de mensagem: antes de porta, fim ou prazo, entra um
            # evento "recebido"
            # a resposta chega num evento "mensagem recebida" antes da porta (mensagem não liga em porta)
            ev = f'msg_{y}_{len(novos) + 1}'
            novos.append({'id': ev, 'tipo': 'evento', 'gatilho': 'mensagem', 'nome': f'{c.nome(cadeia[-1])}: recebido',
                          'papel': papel_de(y) if not _externo(c, y) else papel_interno, 'segue': y})
            alvo = ev
        tipo_x = c.elementos[x]['tipo']
        if tipo_x == 'corrida':
            return None, f'a corrida "{c.nome(x)}" leva direto ao externo: só sequência simples vira pool', None
        if tipo_x in NOS_DE_TRABALHO:
            mensagens.append({'de': x, 'para': None, 'pool': pool, 'nome': c.nome(x)})
            primeiro = alvo
        elif tipo_x == 'inicio':
            primeiro = alvo                             # o início não manda: só a resposta chega
        else:
            # porta ou evento de espera não mandam mensagem: entra um evento "enviar" NESTE caminho (assim a
            # mensagem só sai quando o caso passa por ele, não em todos os caminhos)
            ev_envia = f'msgout_{x}_{len(novos) + 1}'
            novos.append({'id': ev_envia, 'tipo': 'evento', 'gatilho': 'mensagem', 'envia': True,
                          'nome': f'Enviar a {c.nome_papel(pool)}', 'papel': papel_de(x) if not _externo(c, x)
                          else papel_interno, 'segue': alvo})
            mensagens.append({'de': ev_envia, 'para': None, 'pool': pool, 'nome': c.nome(cadeia[0])})
            primeiro = ev_envia
        if not so_ida:
            mensagens.append({'de': None, 'para': alvo, 'pool': pool, 'nome': c.nome(cadeia[-1])})
        religar(f['de'], f['para'], primeiro)
    # troca com o externo que já está no lado de dentro: "Pedir documentos" (envia) e "Documentos recebidos"
    # (evento de mensagem). Com quem? "com" na carta; o nome do externo no nome do passo; para quem recebe, o
    # mesmo de quem enviou antes; para quem envia, o próximo externo do fluxo; com um externo só, ele
    externos = [p for p in c.papeis if (c.papeis[p] or {}).get('tipo') == 'externo' and
                any(c.elementos[x]['papel'] == p for x in meio + pontas)]
    ja_manda = {m['de'] for m in mensagens}
    ja_recebe = {m['para'] for m in mensagens}
    parceiro = {}

    def por_nome(eid):
        e = c.elementos[eid]
        com = e['bruto'].get('com')
        texto = sem_acento(f'{com or ""} {e["nome"] or ""} {e["descricao"] or ""}').lower()
        for p in externos:
            nome = sem_acento(c.nome_papel(p)).lower()
            if p == com or (nome and (nome in texto or nome.split()[0][:6] in texto.split())):
                return p
        return None

    def proximo_externo(eid):
        fila, vistos = [eid], set()
        while fila:
            x = fila.pop(0)
            if x in vistos or x not in c.elementos or len(vistos) > 60:
                continue
            vistos.add(x)
            if x != eid and c.elementos[x]['papel'] in externos:
                return c.elementos[x]['papel']
            fila.extend(f['para'] for f in c.saidas[x])
        return None

    def envio_anterior(eid):
        fila, vistos = [eid], set()
        while fila:
            x = fila.pop(0)
            if x in vistos or x not in c.elementos or len(vistos) > 30:
                continue
            vistos.add(x)
            if x != eid and x in parceiro:
                return parceiro[x]
            fila.extend(f['de'] for f in c.entradas[x])
        return None
    if externos:
        sem_parceiro = []
        for eid, e in c.elementos.items():
            if eid in meio or eid in pontas:
                continue
            envia = bool(e['bruto'].get('envia'))
            recebe = (e['tipo'] == 'evento' and e['gatilho'] == 'mensagem' and not envia) or \
                (e['tipo'] in NOS_DE_TRABALHO and e['bruto'].get('recebe'))
            if not envia and not recebe:
                continue
            p = por_nome(eid) or (proximo_externo(eid) if envia else envio_anterior(eid)) or \
                (externos[0] if len(externos) == 1 else None)
            if p is None:
                sem_parceiro.append(c.nome(eid))
                continue
            parceiro[eid] = p
            if envia and eid not in ja_manda:
                mensagens.append({'de': eid, 'para': None, 'pool': p, 'nome': c.nome(eid)})
            if recebe and eid not in ja_recebe:
                mensagens.append({'de': None, 'para': eid, 'pool': p, 'nome': c.nome(eid)})
    for eid in meio:
        els.pop(eid, None)
    ordem = [str(e.get('id')) for e in dados.get('elementos', []) if isinstance(e, dict) and str(e.get('id')) in els]
    dados['elementos'] = [els[i] for i in ordem] + novos
    usados = {c.elementos[x]['papel'] for x in meio} | {c.elementos[x]['papel'] for x in pontas}
    usados = {p for p in usados if p and (c.papeis.get(p) or {}).get('tipo') == 'externo'}
    dados['papeis'] = [p for p in dados.get('papeis', []) if not (isinstance(p, dict) and
                                                                   (p.get('id') or p.get('nome')) in usados)]
    pools = [{'id': p, 'nome': c.nome_papel(p)} for p in dict.fromkeys(m['pool'] for m in mensagens)]
    return Carta(dados, c.caminho), pools, mensagens
