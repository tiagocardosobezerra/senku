"""
Arquivo .drawio (diagrams.net): abre no app desktop, no navegador (app.diagrams.net), na extensão do VS Code e
no Confluence; o Lucidchart importa; o draw.io exporta para Visio (.vsdx), PDF e PNG.

Usa as formas BPMN do draw.io (mxgraph.bpmn) e as mesmas posições do layout, então o desenho editável é
igual ao do documento. As raias são formas de raia (swimlane) e os elementos ficam dentro delas.
"""

from xml.sax.saxutils import escape

from carta.layout import calcular, numerar

from .bpmn import ids_unicos

CAB = 40
MARGEM = 20
ESTILO = {
    'atividade': 'rounded=1;whiteSpace=wrap;html=1;arcSize=12;fillColor=#ffffff;strokeColor=#2f4a6d;fontSize=11;',
    'subprocesso': 'rounded=1;whiteSpace=wrap;html=1;arcSize=12;fillColor=#ffffff;strokeColor=#2f4a6d;fontSize=11;'
                   'shape=ext;double=1;',
    'decisao': 'shape=mxgraph.bpmn.gateway2;html=1;verticalLabelPosition=top;labelBackgroundColor=#ffffff;'
               'verticalAlign=bottom;align=center;perimeter=rhombusPerimeter;outlineConnect=0;outline=none;'
               'symbol=none;gwType=exclusive;fillColor=#fff8e1;strokeColor=#a86b00;fontSize=11;',
    'corrida': 'shape=mxgraph.bpmn.gateway2;html=1;verticalLabelPosition=top;verticalAlign=bottom;'
               'perimeter=rhombusPerimeter;outlineConnect=0;outline=standard;symbol=multiple;gwType=eventBased;'
               'fillColor=#fff8e1;strokeColor=#a86b00;fontSize=11;',
    'paralelo': 'shape=mxgraph.bpmn.gateway2;html=1;verticalLabelPosition=bottom;verticalAlign=top;'
                'perimeter=rhombusPerimeter;outlineConnect=0;outline=none;symbol=none;gwType=parallel;'
                'fillColor=#fff8e1;strokeColor=#a86b00;',
    'inclusivo': 'shape=mxgraph.bpmn.gateway2;html=1;verticalLabelPosition=top;verticalAlign=bottom;'
                 'perimeter=rhombusPerimeter;outlineConnect=0;outline=end;symbol=general;'
                 'fillColor=#fff8e1;strokeColor=#a86b00;fontSize=11;',
    'inicio': 'shape=mxgraph.bpmn.event;html=1;verticalLabelPosition=bottom;labelBackgroundColor=#ffffff;'
              'verticalAlign=top;align=center;perimeter=ellipsePerimeter;outlineConnect=0;aspect=fixed;'
              'outline=standard;symbol={simbolo};strokeColor=#2e7d32;fontSize=11;',
    'fim': 'shape=mxgraph.bpmn.event;html=1;verticalLabelPosition=bottom;labelBackgroundColor=#ffffff;'
           'verticalAlign=top;align=center;perimeter=ellipsePerimeter;outlineConnect=0;aspect=fixed;outline=end;'
           'symbol={simbolo};strokeColor=#b3261e;fontSize=11;',
    'evento': 'shape=mxgraph.bpmn.event;html=1;verticalLabelPosition=bottom;labelBackgroundColor=#ffffff;'
              'verticalAlign=top;align=center;perimeter=ellipsePerimeter;outlineConnect=0;aspect=fixed;'
              'outline=catching;symbol={simbolo};strokeColor=#a86b00;fontSize=11;',
    'borda': 'shape=mxgraph.bpmn.event;html=1;verticalLabelPosition=bottom;labelPosition=right;align=left;'
             'labelBackgroundColor=#ffffff;verticalAlign=top;perimeter=ellipsePerimeter;outlineConnect=0;'
             'aspect=fixed;outline={contorno};symbol={simbolo};strokeColor=#a86b00;fontSize=9;',
}
SIMBOLO = {'nenhum': 'general', 'tempo': 'timer', 'mensagem': 'message', 'condicao': 'conditional',
           'sinal': 'signal', 'erro': 'error'}


def _a(x):
    return escape(str(x), {'"': '&quot;', '\n': '&#xa;'})


def gerar(c, lay=None):
    lay = lay or calcular(c)
    nums = numerar(c, lay)
    largura = CAB + lay.largura
    cel = ['<mxCell id="0"/>', '<mxCell id="1" parent="0"/>']
    pool = 'pool'
    cel.append(f'<mxCell id="{pool}" value="{_a(c.titulo())}" style="swimlane;horizontal=0;html=1;startSize={CAB};'
               f'fillColor=#e3e9f2;strokeColor=#9fb0c6;fontStyle=1;" vertex="1" parent="1">'
               f'<mxGeometry x="{MARGEM}" y="{MARGEM}" width="{largura + CAB}" height="{lay.altura:.0f}" '
               'as="geometry"/></mxCell>')
    raia_cel = {}
    for i, r in enumerate(lay.raias):
        rid = f'raia_{i}'
        raia_cel[r['id']] = (rid, r['y'])
        fundo = '#eef0f3' if r['tipo'] == 'externo' else ('#f6f8fb' if i % 2 == 0 else '#ffffff')
        cel.append(f'<mxCell id="{rid}" value="{_a(r["nome"])}" style="swimlane;horizontal=0;html=1;'
                   f'startSize={CAB};fillColor=#e3e9f2;swimlaneFillColor={fundo};strokeColor=#c5cfdc;'
                   f'fontStyle=1;whiteSpace=wrap;" vertex="1" parent="{pool}"><mxGeometry x="{CAB}" '
                   f'y="{r["y"]:.0f}" width="{largura}" height="{r["h"]:.0f}" as="geometry"/></mxCell>')
    ids = {}
    cel_id = ids_unicos(lay.nos, 'n_')
    for eid, n in lay.nos.items():
        e = c.elementos[eid]
        rid, ry = raia_cel[n['raia']]
        cid = cel_id[eid]
        ids[eid] = cid
        simbolo = 'terminate' if e['tipo'] == 'fim' and e['encerra'] else SIMBOLO.get(e['gatilho'], 'general')
        estilo = ESTILO[e['tipo']].replace('{simbolo}', simbolo).replace(
            '{contorno}', 'boundInt' if e.get('interrompe', True) else 'boundNonint')
        if e['tipo'] in ('atividade', 'subprocesso'):
            sis = ', '.join(c.nome_sistema(s) for s in e['sistema'])
            valor = f'<b>{nums.get(eid, "")}</b> {_a(e["nome"])}'
            if sis:
                valor += f'<br><font style="font-size:9px;color:#5b6878">{_a(sis)}</font>'
            valor = escape(valor, {'"': '&quot;'})
        else:
            valor = _a(e['nome'])
        if e['tipo'] == 'borda' and e['anexo'] in ids:
            # a borda é filha da atividade: move junto quando a pessoa arrasta a caixa no draw.io
            host = lay.nos[e['anexo']]
            irmas = [x for x in c.elementos if c.elementos[x].get('anexo') == e['anexo']]
            # rótulos das bordas da mesma atividade em degraus: um não cobre o outro
            estilo += f'spacingTop={11 * irmas.index(eid)};'
            cel.append(f'<mxCell id="{cid}" value="{valor}" style="{estilo}" vertex="1" parent="{ids[e["anexo"]]}">'
                       f'<mxGeometry x="{n["x"] - host["x"]:.0f}" y="{n["y"] - host["y"]:.0f}" width="{n["w"]}" '
                       f'height="{n["h"]}" as="geometry"/></mxCell>')
            continue
        cel.append(f'<mxCell id="{cid}" value="{valor}" style="{estilo}" vertex="1" parent="{rid}">'
                   f'<mxGeometry x="{CAB + n["x"]:.0f}" y="{n["y"] - ry:.0f}" width="{n["w"]}" height="{n["h"]}" '
                   'as="geometry"/></mxCell>')
    for f in c.fluxos:
        if f['de'] not in ids or f['para'] not in ids or f['borda']:
            continue
        pts = lay.arestas.get(f['id'], [])
        rot = f['rotulo'] + (f' ({f["percentual"]:.0f}%)' if f['percentual'] is not None else '')
        tracejado = 'dashed=1;' if f['id'] in lay.volta else ''
        # os pontos do meio guiam a linha; as pontas o draw.io recalcula ao mover as formas
        meio = ''.join(f'<mxPoint x="{MARGEM + CAB + CAB + x:.0f}" y="{MARGEM + y:.0f}"/>' for x, y in pts[1:-1])
        cel.append(f'<mxCell id="e_{_a(f["id"])}" value="{_a(rot)}" style="edgeStyle=orthogonalEdgeStyle;rounded=0;'
                   f'html=1;endArrow=block;endFill=1;strokeColor=#44546a;fontSize=10;{tracejado}" edge="1" '
                   f'parent="1" source="{ids[f["de"]]}" target="{ids[f["para"]]}"><mxGeometry relative="1" '
                   f'as="geometry"><Array as="points">{meio}</Array></mxGeometry></mxCell>')
    modelo = ('<mxGraphModel dx="1200" dy="800" grid="1" gridSize="10" guides="1" tooltips="1" connect="1" '
              'arrows="1" fold="1" page="0" pageScale="1" math="0" shadow="0"><root>' + ''.join(cel) +
              '</root></mxGraphModel>')
    nome = _a(c.processo.get('codigo') or c.processo.get('nome') or 'Processo')
    return (f'<mxfile host="Senku" type="device"><diagram id="senku" name="{nome}">{modelo}</diagram></mxfile>\n')
