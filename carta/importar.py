"""
Importa um mapa que já existe em BPMN 2.0 XML (Bizagi, bpmn.io, Camunda, ARIS, Signavio, Visual Paradigm,
Enterprise Architect exportam) para uma carta, para revisar, documentar ou redesenhar no padrão do Senku.

Lê: pools e raias (lanes), tarefas, subprocessos, eventos (com o tipo de gatilho), portas, fluxos de
sequência (nome e condição) e a documentação de cada elemento. Fluxo de mensagem entre pools vira
pendência (a carta é um processo só; o outro pool vira papel externo). O que não é lido vira aviso,
nunca adivinhação.
"""

import json
import re
import xml.etree.ElementTree as ET

from .modelo import esqueleto
from .util import ErroDeUso, sem_acento


def _xml_id(x):
    from saidas.bpmn import xml_id
    return xml_id(x)

MODEL = 'http://www.omg.org/spec/BPMN/20100524/MODEL'
TIPOS = {
    'task': 'atividade', 'userTask': 'atividade', 'manualTask': 'atividade', 'serviceTask': 'atividade',
    'scriptTask': 'atividade', 'businessRuleTask': 'atividade', 'sendTask': 'atividade', 'receiveTask': 'atividade',
    'subProcess': 'subprocesso', 'callActivity': 'subprocesso', 'transaction': 'subprocesso',
    'startEvent': 'inicio', 'endEvent': 'fim', 'intermediateCatchEvent': 'evento',
    'intermediateThrowEvent': 'evento', 'boundaryEvent': 'evento',
    'exclusiveGateway': 'decisao', 'eventBasedGateway': 'corrida', 'complexGateway': 'inclusivo',
    'parallelGateway': 'paralelo', 'inclusiveGateway': 'inclusivo',
}
GATILHO = {'timerEventDefinition': 'tempo', 'messageEventDefinition': 'mensagem',
           'conditionalEventDefinition': 'condicao', 'signalEventDefinition': 'sinal',
           'errorEventDefinition': 'erro'}


def _local(tag):
    return tag.split('}', 1)[-1]


def _texto(x):
    return re.sub(r'\s+', ' ', (x or '')).strip()


def _iso_para_texto(iso):
    """Duração ISO 8601 (relógio) -> texto da carta em tempo corrido: P2D -> "2dc", PT48H -> "48hc"."""
    m = re.fullmatch(r'P(?:(\d+(?:[.,]\d+)?)W)?(?:(\d+(?:[.,]\d+)?)D)?(?:T(?:(\d+(?:[.,]\d+)?)H)?'
                     r'(?:(\d+(?:[.,]\d+)?)M)?(?:\d+(?:[.,]\d+)?S)?)?', (iso or '').strip().upper())
    if not m or not any(m.groups()):
        return None
    sem, dias, horas, mins = (float(x.replace(',', '.')) if x else 0 for x in m.groups())
    dias += sem * 7
    total_h = dias * 24 + horas + mins / 60
    if total_h >= 24:
        return f'{round(total_h / 24, 2):g}dc'          # P2DT19H -> 2.79dc (a mesma conta do relógio)
    if total_h >= 1:
        return f'{round(total_h, 2):g}hc'
    return f'{mins:g}min'


_CAMPOS_DA_CARTA = ('tempo', 'sistema', 'regras', 'raci', 'valor', 'automatizada', 'como', 'entradas', 'saidas',
                    'excecoes', 'documentos', 'detalhe', 'frequencia')


def completar_com_base(carta, base):
    """Volta de um modelador que apaga as extensões (Bizagi, por exemplo): o que o BPMN não guarda vem da carta
    de antes, pelo id (ou pelo nome) de cada elemento. Nome, tipo, raia e ligações continuam os do modelador.
    Devolve avisos."""
    avisos = []
    for chave in ('participantes', 'historico'):
        if base.get(chave):
            carta[chave] = base[chave]
    if carta.get('_extensao_senku'):
        return avisos
    antigos = [e for e in base.get('elementos') or [] if isinstance(e, dict)]
    por_id = {str(e.get('id')): e for e in antigos if e.get('id')}
    por_nome = {sem_acento(str(e.get('nome') or '')).lower(): e for e in antigos if e.get('nome')}
    recuperados = 0
    for e in carta.get('elementos') or []:
        velho = por_id.get(str(e.get('id'))) or por_nome.get(sem_acento(str(e.get('nome') or '')).lower())
        if not velho:
            continue
        for k in _CAMPOS_DA_CARTA:
            if k in velho and (k not in e or k == 'tempo' and not _tempo_editado(e, velho)):
                e[k] = velho[k]
        if velho.get('descricao') is not None:
            e['descricao'] = velho['descricao']
        elif _so_texto_gerado(e.get('descricao')):
            e.pop('descricao', None)
        # percentual das saídas: mesma saída (mesmo destino), mesmo percentual
        segue_velho = velho.get('segue')
        if isinstance(segue_velho, list) and isinstance(e.get('segue'), list):
            pct = {str(s.get('para')): s.get('percentual') for s in segue_velho if isinstance(s, dict)}
            for s in e['segue']:
                if isinstance(s, dict) and s.get('percentual') is None and pct.get(str(s.get('para'))) is not None:
                    s['percentual'] = pct[str(s.get('para'))]
        recuperados += 1
    # papel externo continua externo
    tipos = {sem_acento(str(p.get('nome') or '')).lower(): p.get('tipo') for p in base.get('papeis') or []
             if isinstance(p, dict)}
    for p in carta.get('papeis') or []:
        t = tipos.get(sem_acento(str(p.get('nome') or '')).lower())
        if t and p.get('tipo') != t:
            p['tipo'] = t
    for k in ('processo', 'regras', 'sistemas', 'indicadores', 'riscos', 'dores', 'melhorias', 'glossario', 'sipoc'):
        if base.get(k) and not carta.get(k) or k == 'processo' and base.get(k):
            if k == 'processo':
                nome_novo = carta.get('processo', {}).get('nome')
                carta['processo'] = dict(base['processo'], **({'nome': nome_novo} if nome_novo else {}))
            else:
                carta[k] = base[k]
    if recuperados:
        avisos.append(f'{recuperados} elemento(s) receberam da carta de antes o que o BPMN não guarda (tempos, '
                      'sistemas, regras, RACI, percentuais)')
    return avisos


def _tempo_editado(e, velho):
    """O modelador mudou o prazo do temporizador? (então o tempo do BPMN vale)"""
    novo = (e.get('tempo') or {}).get('espera') if isinstance(e.get('tempo'), dict) else None
    antigo = (velho.get('tempo') or {}).get('espera') if isinstance(velho.get('tempo'), dict) else None
    if not novo or not antigo:
        return False
    from .util import minutos
    try:
        a, b = minutos(novo), minutos(antigo)
    except Exception:
        return False
    return a is not None and b is not None and abs(a - b) > max(30, 0.1 * b)


def _so_texto_gerado(texto):
    return bool(texto) and bool(re.match(r'\s*(Sistema|Tempo|Regra \S+|Valor):\s', str(texto)))


def _prazo_mudou(texto_carta, iso_bpmn):
    """O prazo da carta, exportado de novo, dá o mesmo ISO que está no BPMN? Se não, foi editado no modelador."""
    from saidas.bpmn import _iso
    from .util import minutos
    try:
        m = minutos(texto_carta)
    except Exception:
        return False
    return m is not None and _iso(m, texto_carta) != (iso_bpmn or '').strip()


def _restaurar_senku(carta, principal, elementos, ordem):
    """O BPMN veio do Senku (com as extensões senku:): volta tudo que a carta tinha e o BPMN não guarda
    (sistemas, tempos, regras, RACI, valor, indicadores...). O que foi editado no modelador vale mais: nome,
    tipo, raia e ligações vêm do BPMN."""
    dados_carta = None
    for x in principal:
        if _local(x.tag) == 'extensionElements':
            for y in x:
                if _local(y.tag) == 'carta' and (y.text or '').strip():
                    try:
                        dados_carta = json.loads(y.text)
                    except ValueError:
                        dados_carta = None
    if not dados_carta and not any('_senku' in e for e in elementos.values()):
        return
    lanes = {p['id']: p['nome'] for p in carta['papeis']}
    if dados_carta:
        nome_bpmn = carta['processo'].get('nome')
        for k, v in dados_carta.items():
            carta[k] = v
        papeis_orig = {sem_acento(str(p.get('nome') if isinstance(p, dict) else p)).lower():
                       (p.get('id') or p.get('nome')) if isinstance(p, dict) else p
                       for p in dados_carta.get('papeis') or []}
        for e in elementos.values():
            nome_raia = lanes.get(e.get('papel'))
            # a raia exportada pelo Senku tem id "Raia_<id do papel>": se o nome mudou, é o mesmo papel renomeado
            # (o id fica, e o RACI continua apontando certo)
            lid = str(e.get('papel') or '')
            renomeado = next((p for p in carta.get('papeis') or [] if isinstance(p, dict) and p.get('id') not in
                              (None, '') and lid in ('Raia_' + _xml_id(str(p['id'])), _xml_id(str(p['id'])))), None)
            if nome_raia and sem_acento(nome_raia).lower() in papeis_orig:
                e['papel'] = papeis_orig[sem_acento(nome_raia).lower()]
            elif nome_raia and renomeado:
                renomeado['nome'] = nome_raia
                e['papel'] = renomeado['id']
            elif nome_raia and not any(isinstance(p, dict) and p.get('id') == e['papel']
                                       for p in carta.get('papeis') or []):
                # raia nova ou renomeada no modelador: entra uma vez; o papel antigo sem ninguém sai
                carta.setdefault('papeis', []).append({'id': e['papel'], 'nome': nome_raia})
        if nome_bpmn and not carta['processo'].get('nome'):
            carta['processo']['nome'] = nome_bpmn
    mapa = {}
    for eid, e in elementos.items():
        orig = e.pop('_senku', None)
        if not orig:
            continue
        e['_tinha_senku'] = True
        for k, v in orig.items():
            if k in ('id', 'nome', 'tipo', 'papel', 'segue', 'proximo', 'bordas', 'descricao', '_doc'):
                continue
            if k in ('gatilho', 'encerra', 'automatizada', 'recebe', 'envia'):
                # o BPMN guarda isso no próprio tipo (timer, terminate, serviceTask, receiveTask...): o que
                # o modelador mostra vale mais que a cópia guardada
                continue
            if k == 'tempo' and isinstance(v, dict) and e.get('_iso') and _prazo_mudou(v.get('espera'), e['_iso']):
                e['tempo'] = dict(v, espera=e['tempo']['espera'])   # o prazo editado no modelador vale
                continue
            e[k] = v
        # bordas: valem as do modelador (apagada some, renomeada fica com o nome novo); da carta voltam só o que
        # o BPMN não guarda (percentual, o texto do prazo)
        host_id = str(orig.get('id') or eid)
        antigas = {}
        for k, b in enumerate(orig.get('bordas') or [], 1):
            if isinstance(b, dict):
                # sem id na carta, a borda ganhou "atividade~N" e o XML virou "atividade_N"
                antigas[str(b.get('id') or _xml_id(f'{host_id}~{k}'))] = (b, b.get('id'))
        for b in e.get('bordas') or []:
            velha = antigas.get(str(b.get('id')))
            if not velha:
                continue
            for k in ('percentual', 'tempo'):
                if k == 'tempo' and b.get('_iso') and _prazo_mudou(velha[0].get('tempo'), b['_iso']):
                    continue                                  # o prazo editado no modelador vale
                if velha[0].get(k) not in (None, ''):
                    b[k] = velha[0][k]
            if velha[1] is None:
                b.pop('id', None)                         # volta a ser "atividade~N", como era
        if 'tempo' not in orig and e.get('_iso'):
            # o prazo saiu do nome do evento ("Aguardar 3 dias corridos"): se o BPMN ainda tem esse prazo, a
            # carta continua sem "tempo", como era
            from saidas.bpmn import _iso
            from .util import minutos
            from .modelo import prazo_no_nome
            texto = prazo_no_nome(orig.get('nome'))
            m = minutos(texto) if texto else None
            if m is not None and _iso(m, texto) == e['_iso'].strip():
                e.pop('tempo', None)
        doc_antes = orig.get('_doc')
        doc_agora = ' '.join(str(e.get('descricao') or '').split())
        if doc_antes is not None and doc_agora != doc_antes:
            # a documentação foi editada no modelador: vale o texto novo, sem a parte que o Senku gera
            # (sistema, tempo, regras, valor), que continua vindo da carta
            # a parte gerada começa em "Sistema:", "Tempo:", "Regra X:" ou "Valor:": antes dela, a descrição
            corte = re.search(r'\s*\b(Sistema|Tempo|Regra \S+|Valor):\s', doc_agora)
            novo = doc_agora[:corte.start()].strip() if corte else doc_agora
            tempo_doc = re.search(r'\bTempo:\s*(.*?)(?=\s+\b(?:Regra \S+|Valor):\s|$)', doc_agora)
            if tempo_doc:
                # o tempo também pode ter sido editado no texto: "execução 30min, espera 2d"
                partes = dict(re.findall(r'(execu[cç][aã]o|espera)\s+([^,]+)', tempo_doc.group(1)))
                novo_tempo = {('execucao' if k.startswith('exec') else 'espera'): v.strip() for k, v in partes.items()}
                antigo = orig.get('tempo') if isinstance(orig.get('tempo'), dict) else {}
                if novo_tempo and any(str(antigo.get(k, '')).strip() != v for k, v in novo_tempo.items()):
                    e['tempo'] = dict(antigo, **novo_tempo)
            if novo:
                e['descricao'] = novo
            else:
                e.pop('descricao', None)
        elif 'descricao' in orig:
            e['descricao'] = orig['descricao']
        else:
            e.pop('descricao', None)                              # o texto gerado na documentação não é descrição
        e.pop('_doc', None)
        if orig.get('id') not in (None, '') and str(orig['id']) != eid:
            mapa[eid] = str(orig['id'])
    # o id volta a ser o da carta ("ação 1" virou "a__o_1" no XML): dores, riscos e melhorias apontam para ele
    usados = set(elementos) - set(mapa)
    if any(v in usados for v in mapa.values()) or len(set(mapa.values())) != len(mapa):
        return                                                    # colidiria com outro: fica o id do BPMN
    for velho, novo in mapa.items():
        elementos[novo] = elementos.pop(velho)
        elementos[novo]['id'] = novo
        ordem[ordem.index(velho)] = novo
    for e in elementos.values():
        segue = e.get('segue')
        for s in (segue if isinstance(segue, list) else []):
            if isinstance(s, dict) and s.get('para') in mapa:
                s['para'] = mapa[s['para']]


def importar(caminho, pool=None):
    try:
        raiz = ET.parse(caminho).getroot()
    except ET.ParseError as e:
        raise ErroDeUso(f'{caminho} não é um XML válido: {e}')
    except FileNotFoundError:
        raise ErroDeUso(f'arquivo não encontrado: {caminho}')
    if _local(raiz.tag) != 'definitions':
        raise ErroDeUso(f'{caminho} não parece BPMN 2.0 (a raiz é <{_local(raiz.tag)}>, esperado <definitions>)')
    avisos = []
    processos = [p for p in raiz.iter() if _local(p.tag) == 'process']
    if not processos:
        raise ErroDeUso('o arquivo não tem nenhum <process>')
    participantes = {p.get('processRef') or f'__caixa_preta__{p.get("id")}': p.get('name')
                     for p in raiz.iter() if _local(p.tag) == 'participant'}
    # o processo principal é o que tem mais elementos; os outros pools viram papéis externos
    def tamanho(p):
        return sum(1 for x in p.iter() if _local(x.tag) in TIPOS)
    processos.sort(key=tamanho, reverse=True)
    if pool:
        # a pessoa escolheu o pool (pelo nome do participante ou id do processo)
        alvo = sem_acento(str(pool)).lower().strip()
        escolhidos = [p for p in processos if alvo in sem_acento(str(participantes.get(p.get('id')) or
                                                                     p.get('name') or p.get('id'))).lower()
                      or alvo == str(p.get('id')).lower()]
        if not escolhidos:
            nomes = ', '.join(f'"{participantes.get(p.get("id")) or p.get("name") or p.get("id")}"' for p in processos)
            raise ErroDeUso(f'nenhum pool com "{pool}"; os pools do arquivo são: {nomes}')
        processos.remove(escolhidos[0])
        processos.insert(0, escolhidos[0])
    principal = processos[0]
    # o nome do processo é o do <process>; o do pool (participante) costuma ser a empresa ou a área
    nome = _texto(principal.get('name')) or participantes.get(principal.get('id')) or 'Processo importado'
    nome_pool = participantes.get(principal.get('id'))
    carta = esqueleto(nome)
    carta['processo']['premissas'] = [f'Importado de {caminho.replace(chr(92), "/").split("/")[-1]}: confira '
                                      'papéis, regras e tempos com o dono do processo']
    papeis, raia_de = [], {}
    for lane in principal.iter():
        if _local(lane.tag) != 'lane':
            continue
        lid = lane.get('id')
        filhas = [y for y in lane.iter() if _local(y.tag) == 'lane' and y is not lane]
        if filhas:                                  # raia que só agrupa outras: o papel é de cada filha
            continue
        # raia exportada pelo Senku tem id "Raia_<papel>": o papel volta com o id curto
        pid_curto = lid[5:] if lid.startswith('Raia_') and len(lid) > 5 else lid
        # raia dentro de raia (Bizagi, Signavio): o nome leva o da raia de fora ("Compras / Comprador")
        pais = [p for p in principal.iter() if _local(p.tag) == 'lane' and p is not lane
                and any(y is lane for y in p.iter())]
        nome_raia = _texto(lane.get('name')) or lid
        if pais and _texto(pais[-1].get('name')):
            nome_raia = f'{_texto(pais[-1].get("name"))} / {nome_raia}'
        papeis.append({'id': pid_curto, 'nome': nome_raia, 'tipo': 'interno'})
        for ref in lane:
            if _local(ref.tag) == 'flowNodeRef':
                raia_de[_texto(ref.text)] = pid_curto
    for p in processos[1:]:
        pid = p.get('id')
        papeis.append({'id': pid, 'nome': participantes.get(pid) or p.get('name') or pid, 'tipo': 'externo'})
        avisos.append(f'o pool "{participantes.get(pid) or pid}" virou papel externo; as atividades dele não '
                      f'foram importadas (para trazê-lo: importar ... --pool "{participantes.get(pid) or pid}", '
                      'numa carta própria)')
    for pid, nomep in participantes.items():
        if pid.startswith('__caixa_preta__') and nomep:     # pool sem processo (caixa-preta): papel externo
            papeis.append({'id': re.sub(r'\W+', '_', nomep), 'nome': nomep, 'tipo': 'externo'})
    if not any(p['tipo'] == 'interno' for p in papeis):
        papeis.insert(0, {'id': 'executor', 'nome': nome_pool or nome, 'tipo': 'interno'})
        avisos.append(f'o pool não tem raias: tudo foi para um papel só ("{nome_pool or nome}"); diga quem faz '
                      'cada atividade')
    carta['papeis'] = papeis
    internos = [p['id'] for p in papeis if p['tipo'] == 'interno']
    unico = internos[0] if len(internos) == 1 else None

    elementos, ordem, bordas = {}, [], []
    padrao = {}                                     # fluxo padrão de cada porta ("default"): vira "Senão"
    ligacoes, portas_evento, dados_ass = {}, set(), []
    notas, ligadas = {}, []
    for x in principal.iter():
        if _local(x.tag) == 'textAnnotation':
            notas[x.get('id')] = ' '.join(_texto(t.text) for t in x if _local(t.tag) == 'text')
        if _local(x.tag) == 'association':
            ligadas.append((x.get('sourceRef'), x.get('targetRef')))
    objetos = {x.get('id'): _texto(x.get('name')) or x.get('id') for x in principal.iter()
               if _local(x.tag) in ('dataObjectReference', 'dataStoreReference', 'dataObject')}

    def visitar(container):
        for x in container:
            tag = _local(x.tag)
            if tag == 'subProcess' and str(x.get('triggeredByEvent')).lower() in ('true', '1'):
                # subprocesso de evento (dispara a qualquer momento, sem fluxo chegando): na carta, é exceção
                nome_ev = _texto(x.get('name')) or x.get('id')
                avisos.append(f'o subprocesso de evento "{nome_ev}" ficou de fora (não tem fluxo de entrada); '
                              'ele virou pendência: decida se vira borda numa atividade ou "excecoes"')
                carta['pendencias'].append({'pergunta': f'Subprocesso de evento "{nome_ev}" no mapa original: '
                                            'em que atividade ele pode acontecer (borda) ou é só exceção?'})
                continue
            if tag in TIPOS:
                eid = x.get('id')
                e = {'id': eid, 'tipo': TIPOS[tag], 'nome': _texto(x.get('name'))}
                papel = raia_de.get(eid) or unico
                if papel:
                    e['papel'] = papel
                doc = [_texto(d.text) for d in x if _local(d.tag) == 'documentation' and _texto(d.text)]
                if doc:
                    e['descricao'] = ' '.join(doc)
                for d in x:
                    if _local(d.tag) in GATILHO:
                        e['gatilho'] = GATILHO[_local(d.tag)]
                    if _local(d.tag) == 'timerEventDefinition':
                        dur = [_texto(y.text) for y in d.iter() if _local(y.tag) in ('timeDuration', 'timeCycle')]
                        texto_dur = _iso_para_texto(dur[0]) if dur else None
                        if texto_dur:
                            e['tempo'] = {'espera': texto_dur}
                            e['_iso'] = dur[0]                 # para saber se o modelador mudou o prazo
                    if _local(d.tag) == 'linkEventDefinition':
                        par = ligacoes.setdefault(_texto(d.get('name')) or _texto(x.get('name')),
                                                  {'lanca': [], 'recebe': []})
                        par['lanca' if tag == 'intermediateThrowEvent' else 'recebe'].append(eid)
                    if _local(d.tag) == 'multiInstanceLoopCharacteristics':
                        e['descricao'] = ((e.get('descricao') or '') + ' (repete para cada item)').strip()
                    if _local(d.tag) == 'standardLoopCharacteristics':
                        e['descricao'] = ((e.get('descricao') or '') + ' (repete até concluir)').strip()
                    if _local(d.tag) == 'extensionElements':
                        for y in d:
                            if _local(y.tag) == 'dados' and (y.text or '').strip():
                                try:
                                    e['_senku'] = json.loads(y.text)
                                except ValueError:
                                    pass
                    if _local(d.tag) in ('dataInputAssociation', 'dataOutputAssociation'):
                        refs = [_texto(y.text) for y in d if _local(y.tag) in ('sourceRef', 'targetRef')]
                        dados_ass.append((eid, _local(d.tag), refs))
                lanca_outro = any(_local(d.tag) in ('escalationEventDefinition', 'compensateEventDefinition')
                                  for d in x)
                if tag == 'intermediateThrowEvent' and e.get('gatilho') == 'mensagem' and not lanca_outro:
                    e['envia'] = True                      # evento que manda a mensagem (a carta tem esse evento)
                elif tag == 'intermediateThrowEvent' and (e.get('gatilho') == 'sinal' or lanca_outro):
                    # lançar uma mensagem é uma ação de quem está no processo: na carta, uma atividade
                    e['tipo'] = 'atividade'
                    e['nome'] = e['nome'] or 'Enviar mensagem'
                    e['descricao'] = ((e.get('descricao') or '') + ' (envia mensagem)').strip()
                    e.pop('gatilho', None)
                if tag == 'eventBasedGateway':
                    portas_evento.add(eid)
                if tag == 'serviceTask':
                    e['automatizada'] = True
                if tag == 'receiveTask':
                    e['recebe'] = True                     # atividade que espera uma mensagem (vale depois da corrida)
                if tag == 'sendTask':
                    e['envia'] = True
                chamado = x.get('calledElement') or next(
                    (y.get('processId') for y in x.iter() if _local(y.tag) == 'calledElement' and y.get('processId')),
                    None)                                  # Camunda 8 guarda em <zeebe:calledElement processId>
                if tag == 'callActivity' and chamado:
                    e['detalhe'] = chamado
                    avisos.append(f'"{e["nome"] or eid}" chama o processo "{chamado}": ficou em '
                                  '"detalhe"; aponte o caminho da carta dele')
                for d in x:
                    if _local(d.tag) in ('escalationEventDefinition', 'compensateEventDefinition',
                                         'cancelEventDefinition'):
                        avisos.append(f'"{e["nome"] or eid}" é um evento de {_local(d.tag)[:-15]} (BPMN), que a carta '
                                      'não tem: ficou como erro; confira o significado')
                        e['gatilho'] = 'erro'
                    if _local(d.tag) == 'timerEventDefinition' and tag == 'startEvent':
                        ciclo = [_texto(y.text) for y in d.iter() if _local(y.tag) in ('timeCycle', 'timeDate')]
                        if ciclo:
                            e['descricao'] = ((e.get('descricao') or '') + f' (agenda: {ciclo[0]})').strip()
                if tag == 'endEvent' and any(_local(d.tag) == 'terminateEventDefinition' for d in x):
                    e['encerra'] = True
                if tag == 'boundaryEvent':
                    bordas.append((eid, x.get('attachedToRef'), x.get('cancelActivity') != 'false'))
                if x.get('default'):
                    padrao[x.get('default')] = True
                if tag == 'subProcess' and any(_local(y.tag) in TIPOS for y in x):
                    avisos.append(f'o subprocesso "{e["nome"] or eid}" tem detalhe dentro: ficou recolhido; '
                                  'importe o detalhe numa carta própria')
                elementos[eid] = e
                ordem.append(eid)
    visitar(principal)
    nomes = {}
    for eid in ordem:
        e = elementos[eid]
        if e['tipo'] in ('atividade', 'subprocesso') and not e['nome']:
            avisos.append(f'a atividade {eid} não tem nome')
        nomes[eid] = e['nome']
    for f in principal.iter():
        if _local(f.tag) != 'sequenceFlow':
            continue
        de, para = f.get('sourceRef'), f.get('targetRef')
        if de not in elementos and para not in elementos:
            continue                                # fluxo dentro de um subprocesso expandido
        if de not in elementos or para not in elementos:
            avisos.append(f'fluxo {f.get("id")} liga {de} -> {para}, fora do processo principal: ignorado')
            continue
        saida = {'para': para}
        cond = [c for c in f if _local(c.tag) == 'conditionExpression' and _texto(c.text)]
        if cond:
            saida['condicao'] = _texto(cond[0].text)
        if f.get('name'):
            saida['rotulo'] = _texto(f.get('name'))
        elif f.get('id') in padrao:
            saida['rotulo'] = 'Senão'
        elif cond:
            rot = re.sub(r'^\$\{|\}$|^#\{', '', saida['condicao']).strip()
            saida['rotulo'] = rot if len(rot) <= 40 else rot[:39] + '…'
        for ext in f:
            if _local(ext.tag) == 'extensionElements':
                for y in ext:
                    if _local(y.tag) == 'dados' and (y.text or '').strip():
                        try:
                            pct = json.loads(y.text).get('percentual')
                        except (ValueError, AttributeError):
                            pct = None
                        if pct is not None:
                            saida['percentual'] = pct
        elementos[de].setdefault('segue', []).append(saida)
    # evento de borda (prazo estourado, erro, mensagem que chega durante a atividade): vira "bordas" da atividade
    for bid, alvo, interrompe in bordas:
        if alvo not in elementos or bid not in elementos:
            avisos.append(f'evento de borda {bid} preso a {alvo}, que não foi importado: ficou de fora')
            elementos.pop(bid, None)
            if bid in ordem:
                ordem.remove(bid)
            continue
        ev = elementos.pop(bid)
        ordem.remove(bid)
        borda = {'id': bid, 'nome': ev.get('nome', ''), 'gatilho': ev.get('gatilho') or 'erro',
                 'segue': ev.get('segue') or []}
        if (ev.get('tempo') or {}).get('espera'):
            borda['tempo'] = ev['tempo']['espera']
            borda['_iso'] = ev.get('_iso')
        if not interrompe:
            borda['interrompe'] = False
        elementos[alvo].setdefault('bordas', []).append(borda)
        if not borda['segue']:
            avisos.append(f'a borda "{borda["nome"] or bid}" em "{elementos[alvo]["nome"]}" não segue para nada')
    # evento de ligação (link): o par "vai para A" / "vem de A" é só um atalho de desenho; vira ligação direta
    for nome_lig, par in ligacoes.items():
        lancas, recebe = par['lanca'], par['recebe']
        if not lancas or len(recebe) != 1:
            avisos.append(f'evento de ligação "{nome_lig}": {len(lancas)} lança(m) e {len(recebe)} recebe(m); '
                          'precisa de um "recebe" para ligar: ligue à mão')
            continue
        destinos = elementos[recebe[0]].get('segue') or []
        for e in elementos.values():
            novo = []
            for s in e.get('segue') or []:
                if s['para'] in lancas:
                    novo.extend(dict(d, **({'rotulo': s['rotulo']} if s.get('rotulo') else {})) for d in destinos)
                else:
                    novo.append(s)
            if e.get('segue'):
                e['segue'] = novo
        for x in lancas + recebe:
            elementos.pop(x, None)
            ordem.remove(x)
    # objetos de dados ligados a uma atividade: entradas e saídas dela; anotação de texto: nota na descrição
    for eid, tipo_ass, refs in dados_ass:
        if eid not in elementos:
            continue
        nomes_obj = [objetos[r] for r in refs if r in objetos]
        chave = 'entradas' if tipo_ass == 'dataInputAssociation' else 'saidas'
        elementos[eid].setdefault(chave, []).extend(n for n in nomes_obj if n not in elementos[eid].get(chave, []))
    for a, b in ligadas:
        nota, alvo = (notas.get(a), b) if a in notas else (notas.get(b), a)
        if nota and alvo in elementos:
            elementos[alvo]['descricao'] = ((elementos[alvo].get('descricao') or '') + f' Nota: {nota}').strip()
    ignorados = sorted({_local(x.tag) for x in principal.iter()} & {'callChoreography', 'choreographyTask', 'group'})
    if ignorados:
        avisos.append('não lidos (sem equivalente na carta): ' + ', '.join(ignorados))
    _restaurar_senku(carta, principal, elementos, ordem)
    # fim implícito (o BPMN deixa um caminho só parar): na carta todo caminho termina num fim com nome
    tem_borda_saindo = {b.get('id') for e in elementos.values() for b in e.get('bordas') or []}
    for eid in list(ordem):
        e = elementos[eid]
        if e['tipo'] != 'fim' and not e.get('segue') and eid not in tem_borda_saindo:
            fid = f'{eid}_fim'
            elementos[fid] = {'id': fid, 'tipo': 'fim', 'nome': f'Fim após {e.get("nome") or eid}'}
            if e.get('papel'):
                elementos[fid]['papel'] = e['papel']
            ordem.insert(ordem.index(eid) + 1, fid)
            e['segue'] = [{'para': fid}]
            avisos.append(f'"{e.get("nome") or eid}" não seguia para nada (fim implícito no BPMN): ganhou um fim; '
                          'dê a ele o nome do resultado')
    for e in elementos.values():
        for b in e.get('bordas') or []:
            if not b.get('segue'):
                fid = f'{b["id"]}_fim'
                elementos[fid] = {'id': fid, 'tipo': 'fim', 'nome': f'Fim após {b.get("nome") or b["id"]}'}
                ordem.append(fid)
                b['segue'] = [{'para': fid}]
    for e in elementos.values():
        segue = e.get('segue')
        if segue and len(segue) == 1 and set(segue[0]) == {'para'}:
            e['segue'] = segue[0]['para']
    nomes_de = {x.get('id'): _texto(x.get('name')) for x in raiz.iter() if x.get('id')}
    for m in raiz.iter():
        if _local(m.tag) != 'messageFlow':
            continue
        de, para = nomes_de.get(m.get('sourceRef')) or m.get('sourceRef'), \
            nomes_de.get(m.get('targetRef')) or m.get('targetRef')
        rot = f' "{_texto(m.get("name"))}"' if m.get('name') else ''
        carta['pendencias'].append({'pergunta': f'Mensagem{rot} de "{de}" para "{para}" no mapa original: '
                                    'confira se a troca está nas atividades da carta.'})
    carta['_extensao_senku'] = any(e.get('_tinha_senku') for e in elementos.values())
    for e in elementos.values():
        e.pop('_iso', None)
        if not e.pop('_tinha_senku', None) and not carta['_extensao_senku'] and e.get('descricao'):
            # sem a extensão do Senku, a parte gerada da documentação ("Sistema: ... Tempo: ...") não é descrição
            corte = re.search(r'\s*\b(Sistema|Tempo|Regra \S+|Valor):\s', str(e['descricao']))
            if corte:
                resto = str(e['descricao'])[:corte.start()].strip()
                if resto:
                    e['descricao'] = resto
                else:
                    e.pop('descricao', None)
        for b in e.get('bordas') or []:
            if isinstance(b, dict):
                b.pop('_iso', None)
    carta['elementos'] = [elementos[i] for i in ordem]
    return carta, avisos
