"""
BPMN 2.0 XML com diagrama (BPMNDI): abre com o desenho pronto no bpmn.io / Camunda Modeler, e importa no
Bizagi Modeler, ARIS, Signavio, Visual Paradigm, Enterprise Architect e no Visio (BPMN).

Mapeamento (referencias/notacao.md):
    processo                 -> participant (pool) + process com laneSet (uma lane por papel)
    inicio / fim / evento    -> startEvent / endEvent / intermediateCatchEvent (+ timer, message,
                                conditional, signal, error conforme o "gatilho")
    atividade                -> task (userTask se tem sistema, serviceTask se "automatizada")
    subprocesso              -> subProcess recolhido (o detalhe fica na carta do subprocesso)
    decisao / paralelo / inclusivo -> exclusiveGateway / parallelGateway / inclusiveGateway
    segue / fluxos           -> sequenceFlow (o rótulo vira name; a condição, conditionExpression)
    descricao, regras, tempo -> documentation do elemento
"""

import re
from xml.sax.saxutils import escape

from carta.layout import calcular
from carta.util import DIA_CORRIDO, DIA_UTIL, sem_acento

NS_SENKU = 'http://senku/carta'

NS = {
    'bpmn': 'http://www.omg.org/spec/BPMN/20100524/MODEL',
    'bpmndi': 'http://www.omg.org/spec/BPMN/20100524/DI',
    'dc': 'http://www.omg.org/spec/DD/20100524/DC',
    'di': 'http://www.omg.org/spec/DD/20100524/DI',
    'xsi': 'http://www.w3.org/2001/XMLSchema-instance',
}
POOL_CAB = 30           # faixa do nome do pool (à esquerda)
RAIA_CAB = 30           # faixa do nome da raia
MARGEM = 20
DEF_EVENTO = {'tempo': 'timerEventDefinition', 'mensagem': 'messageEventDefinition',
              'condicao': 'conditionalEventDefinition', 'sinal': 'signalEventDefinition',
              'erro': 'errorEventDefinition'}


def _a(x):
    return escape(str(x), {'"': '&quot;', '\n': '&#10;'})


def xml_id(eid, prefixo='Id_'):
    # o ponto fica reservado para os ids técnicos (x.di, x.def, Msg.x): assim nunca colidem com os da carta
    s = re.sub(r'[^A-Za-z0-9_-]', '_', sem_acento(str(eid)))
    return s if re.match(r'[A-Za-z_]', s) else prefixo + s


def ids_unicos(chaves, prefixo='', usados=None):
    """id XML de cada chave, sem colisão ("ação 1" e "acao_1" não viram o mesmo id)."""
    usados = set() if usados is None else usados
    out = {}
    for k in chaves:
        base = xml_id(prefixo + str(k))
        x, n = base, 2
        while x.lower() in usados:
            x, n = f'{base}_{n}', n + 1
        usados.add(x.lower())
        out[k] = x
    return out


def _iso(minutos_uteis, texto=''):
    """Duração ISO 8601 em tempo de RELÓGIO, que é como os motores BPMN leem o temporizador.
    Prazo escrito em tempo corrido ("10dc", "48 horas corridas") volta exato; prazo em tempo útil vira dias de
    calendário (5 dias úteis = 7 dias), e menos de um dia útil fica em horas."""
    corrido = re.search(r'corrid|\bdc\b|\bhc\b|\d\s*(dc|hc)\b', sem_acento(str(texto)).lower())
    # abaixo de um dia de trabalho, hora útil e hora de relógio são a mesma (o prazo corre no expediente);
    # a partir daí, o relógio passa por noite e fim de semana: dias de calendário, em horas inteiras, para o
    # importar ler de volta o mesmo prazo (2 dias úteis = 67 h de relógio = P2DT19H)
    if minutos_uteis < 60:
        return f'PT{max(1, round(minutos_uteis))}M'
    if minutos_uteis < DIA_UTIL or (corrido and minutos_uteis < 24 * 60 and minutos_uteis < DIA_CORRIDO):
        h, m = divmod(round(minutos_uteis), 60)                    # xsd:duration não aceita hora quebrada
        return f'PT{h}H{m}M' if m else f'PT{h}H'
    horas = max(1, round(minutos_uteis / (DIA_CORRIDO / 24)))
    d, h = divmod(horas, 24)
    return (f'P{d}D' if not h else f'P{d}DT{h}H') if d else f'PT{h}H'


def _tag(e):
    t = e['tipo']
    if t == 'borda':
        return 'boundaryEvent'
    if t == 'inicio':
        return 'startEvent'
    if t == 'fim':
        return 'endEvent'
    if t == 'evento':
        # evento "nenhum" no meio do fluxo só marca um estado: no BPMN é o intermediário de lançamento
        # e o evento que ENVIA mensagem (entra no --pools quando quem manda é uma porta) também lança
        lanca = e['gatilho'] == 'nenhum' or e['bruto'].get('envia')
        return 'intermediateThrowEvent' if lanca else 'intermediateCatchEvent'
    if t == 'subprocesso':
        return 'subProcess'
    if t == 'decisao':
        return 'exclusiveGateway'
    if t == 'corrida':
        return 'eventBasedGateway'
    if t == 'paralelo':
        return 'parallelGateway'
    if t == 'inclusivo':
        return 'inclusiveGateway'
    if e['automatizada']:
        return 'serviceTask'
    if e['bruto'].get('recebe'):
        return 'receiveTask'
    if e['bruto'].get('envia'):
        return 'sendTask'
    return 'userTask' if e['sistema'] else 'task'


def _documentacao(c, e):
    partes = []
    if e['descricao']:
        partes.append(e['descricao'])
    if e['sistema']:
        partes.append('Sistema: ' + ', '.join(c.nome_sistema(s) for s in e['sistema']))
    if e['tempo_texto']:
        partes.append('Tempo: ' + ', '.join(f'{ {"execucao": "execução"}.get(k, k)} {v}'
                                            for k, v in e['tempo_texto'].items()))
    for r in e['regras']:
        if r in c.regras:
            partes.append(f'Regra {r}: {c.regras[r].get("texto", "")}')
    if e['valor']:
        partes.append(f'Valor: {e["valor"]}')
    return '\n'.join(partes)


def _json(dados):
    import json
    return _a(json.dumps(dados, ensure_ascii=False, separators=(',', ':')))


def _dados_elemento(e, doc=''):
    """O que a carta sabe do elemento e o BPMN não tem onde guardar: vai numa extensão (senku:dados), para
    voltar inteiro no importar depois de editado num modelador. Leva também o texto da documentação como saiu
    (`_doc`): no importar, documentação diferente quer dizer que alguém editou no modelador."""
    d = {k: v for k, v in e['bruto'].items() if k not in ('segue', 'proximo')}
    if doc:
        d['_doc'] = ' '.join(doc.split())
    return d


def _dados_carta(c):
    # nomes de pessoas (participantes, autores do histórico) não viajam escondidos dentro do .bpmn
    return {k: v for k, v in c.dados.items() if k not in ('elementos', 'fluxos', 'participantes', 'historico')}


def gerar(c, lay=None, _prefixo='', _pools=None):
    xml = _gerar(c, lay or calcular(c), _prefixo, _pools)
    import re as _re
    todos = _re.findall(r'\bid="([^"]+)"', xml)
    if len(todos) != len(set(todos)) and not _prefixo:
        return gerar(c, lay, 'E_', _pools)          # um id da carta bate com um id técnico: prefixa os da carta
    return xml


def gerar_com_pools(c):
    """BPMN com cada papel externo num pool caixa-preta e a troca com ele em fluxo de mensagem.
    Devolve (xml, aviso): sem como fazer (trecho externo com decisão, por ex.), sai em raias e o aviso diz por quê."""
    from .pools import transformar
    interna, pools, mensagens = transformar(c)
    if interna is None:
        return gerar(c), f'BPMN em raias: {pools}'
    return gerar(interna, _pools=(pools, mensagens)), ''


ALT_POOL_EXT = 60


def _gerar(c, lay, prefixo, pools_ext=None):
    pools, msg_ext = pools_ext or ([], [])
    pid = xml_id('Processo_' + (c.processo.get('codigo') or 'senku'))
    usados = {pid.lower()}
    ids = ids_unicos(c.elementos, prefixo, usados=usados)
    fid = ids_unicos([f['id'] for f in c.fluxos], 'Fluxo_', usados)
    raia_id = ids_unicos([r['id'] for r in lay.raias], 'Raia_', usados)
    mensagens = {eid: f'Msg.{ids[eid]}' for eid, e in c.elementos.items()
                 if e['gatilho'] == 'mensagem' and e['tipo'] in ('inicio', 'evento', 'fim', 'borda')}
    # atividade -> borda não é fluxo no BPMN: a borda fica presa na atividade (attachedToRef)
    validos = [f for f in c.fluxos if f['de'] in c.elementos and f['para'] in c.elementos and not f['borda']]
    nome = c.titulo()
    x0 = MARGEM + POOL_CAB + RAIA_CAB
    y0 = MARGEM + len(pools) * (ALT_POOL_EXT + 40)   # os pools externos ficam em cima
    pool_id = {p['id']: f'PoolExt.{k}' for k, p in enumerate(pools, 1)}
    L = ['<?xml version="1.0" encoding="UTF-8"?>',
         '<bpmn:definitions ' + ' '.join(f'xmlns:{k}="{v}"' for k, v in NS.items()) +
         f' xmlns:senku="{NS_SENKU}" id="Definicoes.{pid}" targetNamespace="http://senku/processos" '
         'exporter="Senku" exporterVersion="2">']
    for eid, mid in mensagens.items():
        L.append(f'  <bpmn:message id="{mid}" name="{_a(c.nome(eid))}"/>')
    L += [
         f'  <bpmn:collaboration id="Colaboracao.{pid}">',
         f'    <bpmn:participant id="Pool.{pid}" name="{_a(nome)}" processRef="{pid}"/>']
    for p in pools:
        L.append(f'    <bpmn:participant id="{pool_id[p["id"]]}" name="{_a(p["nome"])}"/>')
    for k, m in enumerate(msg_ext, 1):
        de = ids[m['de']] if m['de'] else pool_id[m['pool']]
        para = ids[m['para']] if m['para'] else pool_id[m['pool']]
        L.append(f'    <bpmn:messageFlow id="MsgFlow.{k}" name="{_a(m["nome"])}" sourceRef="{de}" targetRef="{para}"/>')
    L += [
         '  </bpmn:collaboration>',
         f'  <bpmn:process id="{pid}" name="{_a(nome)}" isExecutable="false">']
    doc_proc = c.processo.get('objetivo')
    if doc_proc:
        L.append(f'    <bpmn:documentation>{_a(doc_proc)}</bpmn:documentation>')
    L.append(f'    <bpmn:extensionElements><senku:carta>{_json(_dados_carta(c))}</senku:carta>'
             '</bpmn:extensionElements>')
    L.append(f'    <bpmn:laneSet id="Raias.{pid}">')
    for r in lay.raias:
        L.append(f'      <bpmn:lane id="{raia_id[r["id"]]}" name="{_a(r["nome"])}">')
        for eid, n in lay.nos.items():
            if n['raia'] == r['id']:
                L.append(f'        <bpmn:flowNodeRef>{ids[eid]}</bpmn:flowNodeRef>')
        L.append('      </bpmn:lane>')
    L.append('    </bpmn:laneSet>')
    for eid, e in c.elementos.items():
        tag = _tag(e)
        attrs = f'id="{ids[eid]}"'
        if e['nome']:
            attrs += f' name="{_a(e["nome"])}"'
        if tag == 'subProcess':
            attrs += ' triggeredByEvent="false"'
        if tag == 'boundaryEvent':
            attrs += f' attachedToRef="{ids[e["anexo"]]}"' + ('' if e['interrompe'] else ' cancelActivity="false"')
        L.append(f'    <bpmn:{tag} {attrs}>')
        doc = _documentacao(c, e)
        if doc:
            L.append(f'      <bpmn:documentation>{_a(doc)}</bpmn:documentation>')
        if e['tipo'] != 'borda':                     # a borda viaja dentro da atividade ("bordas")
            L.append(f'      <bpmn:extensionElements><senku:dados>{_json(_dados_elemento(e, doc))}</senku:dados>'
                     '</bpmn:extensionElements>')
        for f in validos:
            if f['para'] == eid:
                L.append(f'      <bpmn:incoming>{fid[f["id"]]}</bpmn:incoming>')
        for f in validos:
            if f['de'] == eid:
                L.append(f'      <bpmn:outgoing>{fid[f["id"]]}</bpmn:outgoing>')
        if e['tipo'] == 'fim' and e['encerra']:
            L.append(f'      <bpmn:terminateEventDefinition id="{ids[eid]}.def"/>')
        elif e['tipo'] in ('inicio', 'evento', 'fim', 'borda') and e['gatilho'] in DEF_EVENTO:
            d = DEF_EVENTO[e['gatilho']]
            # o que vale em cada evento (BPMN 2.0, tabela 10.93): fim não espera tempo nem condição; erro só
            # existe no fim (o validar já recusa erro em início e no meio)
            if e['tipo'] == 'fim' and d in ('timerEventDefinition', 'conditionalEventDefinition'):
                pass
            elif d == 'errorEventDefinition' and e['tipo'] not in ('fim', 'borda'):
                pass
            elif d == 'conditionalEventDefinition':
                L.append(f'      <bpmn:{d} id="{ids[eid]}.def"><bpmn:condition xsi:type="bpmn:tFormalExpression"/>'
                         f'</bpmn:{d}>')
            elif d == 'timerEventDefinition':
                if e['espera']:
                    L.append(f'      <bpmn:{d} id="{ids[eid]}.def"><bpmn:timeDuration '
                             f'xsi:type="bpmn:tFormalExpression">{_iso(e["espera"], e["tempo_texto"].get("espera"))}'
                             f'</bpmn:timeDuration></bpmn:{d}>')
                else:
                    L.append(f'      <bpmn:{d} id="{ids[eid]}.def"/>')
            elif d == 'messageEventDefinition':
                L.append(f'      <bpmn:{d} id="{ids[eid]}.def" messageRef="{mensagens[eid]}"/>')
            else:
                L.append(f'      <bpmn:{d} id="{ids[eid]}.def"/>')
        L.append(f'    </bpmn:{tag}>')
    for f in validos:
        attrs = f'id="{fid[f["id"]]}" sourceRef="{ids[f["de"]]}" targetRef="{ids[f["para"]]}"'
        if f['rotulo']:
            attrs += f' name="{_a(f["rotulo"])}"'
        if f['percentual'] is not None or f['condicao']:
            L.append(f'    <bpmn:sequenceFlow {attrs}>')
            if f['percentual'] is not None:
                L.append(f'      <bpmn:documentation>{f["percentual"]:g}% dos casos</bpmn:documentation>')
                L.append(f'      <bpmn:extensionElements><senku:dados>{_json({"percentual": f["percentual"]})}'
                         '</senku:dados></bpmn:extensionElements>')
        if f['condicao']:
            L.append(f'      <bpmn:conditionExpression xsi:type="bpmn:tFormalExpression">{_a(f["condicao"])}'
                     '</bpmn:conditionExpression>')
        if f['percentual'] is not None or f['condicao']:
            L.append('    </bpmn:sequenceFlow>')
        else:
            L.append(f'    <bpmn:sequenceFlow {attrs}/>')
    L.append('  </bpmn:process>')
    # ------------------------------------------------------------ diagrama
    largura = POOL_CAB + RAIA_CAB + lay.largura
    L.append(f'  <bpmndi:BPMNDiagram id="Diagrama.{pid}">')
    L.append(f'    <bpmndi:BPMNPlane id="Plano.{pid}" bpmnElement="Colaboracao.{pid}">')
    L.append(f'      <bpmndi:BPMNShape id="Pool.{pid}.di" bpmnElement="Pool.{pid}" isHorizontal="true">'
             f'<dc:Bounds x="{MARGEM}" y="{y0}" width="{largura:.0f}" height="{lay.altura:.0f}"/>'
             '</bpmndi:BPMNShape>')
    for r in lay.raias:
        rid = raia_id[r['id']]
        L.append(f'      <bpmndi:BPMNShape id="{rid}.di" bpmnElement="{rid}" isHorizontal="true">'
                 f'<dc:Bounds x="{MARGEM + POOL_CAB}" y="{y0 + r["y"]:.0f}" width="{largura - POOL_CAB:.0f}" '
                 f'height="{r["h"]:.0f}"/></bpmndi:BPMNShape>')
    for eid, n in lay.nos.items():
        e = c.elementos[eid]
        extra = ' isExpanded="false"' if e['tipo'] == 'subprocesso' else ''
        extra += ' isMarkerVisible="true"' if e['tipo'] == 'decisao' else ''
        L.append(f'      <bpmndi:BPMNShape id="{ids[eid]}.di" bpmnElement="{ids[eid]}"{extra}>'
                 f'<dc:Bounds x="{x0 + n["x"]:.0f}" y="{y0 + n["y"]:.0f}" width="{n["w"]}" height="{n["h"]}"/>')
        if e['tipo'] in ('inicio', 'fim', 'evento', 'borda', 'decisao', 'paralelo', 'inclusivo', 'corrida') and e['nome']:
            if e['tipo'] in ('decisao', 'inclusivo', 'corrida'):
                lx, ly = x0 + n['x'] - 70, y0 + n['y'] - 34
            else:
                lx, ly = x0 + n['cx'] - 50, y0 + n['y'] + n['h'] + 4
            L.append(f'<bpmndi:BPMNLabel><dc:Bounds x="{lx:.0f}" y="{ly:.0f}" width="100" height="27"/>'
                     '</bpmndi:BPMNLabel>')
        L.append('</bpmndi:BPMNShape>')
    for f in validos:
        pts = lay.arestas.get(f['id'], [])
        L.append(f'      <bpmndi:BPMNEdge id="{fid[f["id"]]}.di" bpmnElement="{fid[f["id"]]}">')
        for x, y in pts:
            L.append(f'        <di:waypoint x="{x0 + x:.0f}" y="{y0 + y:.0f}"/>')
        if f['rotulo'] and f['id'] in lay.rotulos:
            lx, ly, ancora = lay.rotulos[f['id']]
            largura_rot = max(30, 6 * len(f['rotulo']) + 8)
            if ancora == 'end':
                lx -= largura_rot
            L.append(f'        <bpmndi:BPMNLabel><dc:Bounds x="{x0 + lx:.0f}" y="{y0 + ly - 12:.0f}" '
                     f'width="{largura_rot}" height="14"/></bpmndi:BPMNLabel>')
        L.append('      </bpmndi:BPMNEdge>')
    for k, p in enumerate(pools):
        yp = MARGEM + k * (ALT_POOL_EXT + 40)
        L.append(f'      <bpmndi:BPMNShape id="{pool_id[p["id"]]}.di" bpmnElement="{pool_id[p["id"]]}" '
                 f'isHorizontal="true"><dc:Bounds x="{MARGEM}" y="{yp}" width="{largura:.0f}" '
                 f'height="{ALT_POOL_EXT}"/></bpmndi:BPMNShape>')
    for k, m in enumerate(msg_ext, 1):
        no = lay.nos.get(m['de'] or m['para'])
        if not no:
            continue
        idx = [p['id'] for p in pools].index(m['pool'])
        y_pool = MARGEM + idx * (ALT_POOL_EXT + 40) + ALT_POOL_EXT
        x = x0 + no['cx'] + (-12 if m['de'] else 12)          # a que sai e a que volta lado a lado
        y_no = y0 + no['y']
        a, b = ((x, y_no), (x, y_pool)) if m['de'] else ((x, y_pool), (x, y_no))
        L.append(f'      <bpmndi:BPMNEdge id="MsgFlow.{k}.di" bpmnElement="MsgFlow.{k}">'
                 f'<di:waypoint x="{a[0]:.0f}" y="{a[1]:.0f}"/><di:waypoint x="{b[0]:.0f}" y="{b[1]:.0f}"/>'
                 '</bpmndi:BPMNEdge>')
    L += ['    </bpmndi:BPMNPlane>', '  </bpmndi:BPMNDiagram>', '</bpmn:definitions>', '']
    return '\n'.join(L)
