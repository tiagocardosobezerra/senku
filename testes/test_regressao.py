"""
Regressão: os casos que já quebraram o Senku (revisões independentes), em testes/casos/.
Cada caso roda por todos os comandos sem traceback, e os defeitos achados ficam travados aqui.

    python -m unittest discover -s testes
"""

import io
import json
import os
import shutil
import sys
import tempfile
import unittest
import xml.etree.ElementTree as ET
from collections import Counter
from contextlib import redirect_stderr, redirect_stdout

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, RAIZ)

import senku  # noqa: E402
from carta import analise, aprovacao, layout, modelo, validacao  # noqa: E402
from carta.importar import importar  # noqa: E402
from carta.util import ErroDeUso, formatar_minutos, minutos  # noqa: E402
from saidas import bpmn, mermaid, svg  # noqa: E402

CASOS = os.path.join(RAIZ, 'testes', 'casos')


def _caso(nome, arq='carta.json'):
    return os.path.join(CASOS, nome, arq)


def _ler(arq):
    with open(arq, encoding='utf-8') as f:
        return json.load(f)


def _carta(nome):
    return modelo.carregar(_caso(nome))


def _codigos(c, nivel=None):
    return {a.codigo for a in validacao.validar(c) if nivel is None or a.nivel == nivel}


def _rodar(*args):
    buf = io.StringIO()
    with redirect_stdout(buf), redirect_stderr(io.StringIO()):
        try:
            cod = senku.main(list(args))
        except ErroDeUso as e:
            print(f'✗ {e}')
            cod = 1
        except SystemExit as e:
            cod = e.code
    return cod, buf.getvalue()


class TestNenhumCasoQuebra(unittest.TestCase):
    """Todos os casos (inclusive os de tipo errado) passam por todos os comandos sem exceção."""

    def test_todos_os_comandos_em_todos_os_casos(self):
        tmp = tempfile.mkdtemp(prefix='senku-reg')
        try:
            cartas = []
            for nome in sorted(os.listdir(CASOS)):
                for arq in sorted(os.listdir(os.path.join(CASOS, nome))):
                    if arq.endswith('.json') and not arq.endswith('.aprovacao.json'):
                        cartas.append(os.path.join(CASOS, nome, arq))
            cartas += [os.path.join(RAIZ, 'exemplos', x, 'carta.json') for x in ('compras', 'credito')]
            self.assertGreater(len(cartas), 30)
            for i, carta in enumerate(cartas):
                for cmd in (['validar'], ['lacunas', '--todas'], ['analisar'], ['situacao'],
                            ['desenhar', '-o', os.path.join(tmp, str(i))],
                            ['documentar', '-o', os.path.join(tmp, str(i))]):
                    with self.subTest(carta=os.path.relpath(carta, RAIZ), cmd=cmd[0]):
                        try:
                            _rodar(cmd[0], carta, *cmd[1:])
                        except Exception as e:                      # noqa: BLE001
                            self.fail(f'{type(e).__name__}: {e}')
        finally:
            shutil.rmtree(tmp, ignore_errors=True)

    def test_tipo_errado_vira_erro_de_validacao(self):
        for nome in ('raci_str', 'raci_list', 'processo_str', 'escopo_str'):
            with self.subTest(nome):
                self.assertIn('tipo_invalido', _codigos(_carta(nome), 'erro'))

    def test_texto_no_lugar_de_lista_nao_vira_letras(self):
        c = _carta('dores_elem_str')
        textos = ' '.join(a.texto for a in validacao.validar(c))
        self.assertNotIn('"D"', textos)
        self.assertNotIn('"1"', textos)


class TestFluxoQueTrava(unittest.TestCase):
    def test_decisao_fechada_em_paralelo_trava(self):
        cods = _codigos(_carta('dead'), 'erro')
        self.assertIn('travamento', cods)
        self.assertNotIn('laco_sem_saida', cods)                    # o travamento não é contado duas vezes

    def test_paralelo_fechado_em_atividade_roda_duas_vezes(self):
        self.assertIn('sem_sincronia', _codigos(_carta('lack'), 'erro'))

    def test_aprovar_recusa_fluxo_que_trava(self):
        tmp = tempfile.mkdtemp()
        try:
            shutil.copy(_caso('dead'), os.path.join(tmp, 'carta.json'))
            cod, out = _rodar('aprovar', os.path.join(tmp, 'carta.json'), '--por', 'X')
            self.assertEqual(cod, 1, out)
        finally:
            shutil.rmtree(tmp)

    def test_fim_terminal_resolve_o_travamento(self):
        with open(os.path.join(RAIZ, 'exemplos', 'credito', 'carta.json'), encoding='utf-8') as f:
            d = json.load(f)
        self.assertEqual(_codigos(modelo.Carta(d), 'erro'), set())
        for e in d['elementos']:
            e.pop('encerra', None)
        self.assertIn('travamento', _codigos(modelo.Carta(d), 'erro'))

    def test_exemplos_passam_na_prova(self):
        for x in ('compras', 'credito'):
            c = modelo.carregar(os.path.join(RAIZ, 'exemplos', x, 'carta.json'))
            self.assertEqual([a for a in validacao.validar(c) if a.nivel in ('erro', 'aviso')], [], x)


class TestTempo(unittest.TestCase):
    def test_tabela(self):
        casos = {'15min': 15, '1:30': 90, '2h30': 150, '1 hora e meia': 90, '2h e 30min': 150, 'meia hora': 30,
                 '1 dia e meio': 720, '2 a 3 dias úteis': 1200, '15–30 min': 22.5, '2 ou 3 dias': 1200,
                 '1 semana': 2400, 'até 2h': 120}
        for t, esperado in casos.items():
            with self.subTest(t):
                self.assertAlmostEqual(minutos(t), esperado)
        for t in ('-2h', 'rapidinho', '2 dias e pouco', True):
            self.assertIsNone(minutos(t), t)

    def test_dia_corrido_nao_vira_tres_dias_uteis(self):
        self.assertLess(minutos('3dc'), minutos('3d'))
        self.assertEqual(formatar_minutos(minutos('7dc')), '5 d úteis')
        self.assertEqual(formatar_minutos(480), '1 d útil')

    def test_horas_longas_pedem_confirmacao(self):
        d = {'processo': {'nome': 'x'}, 'papeis': ['A'], 'elementos': [
            {'id': 'i', 'tipo': 'inicio', 'nome': 'Pedido', 'papel': 'A', 'segue': 'a'},
            {'id': 'a', 'nome': 'Analisar pedido', 'papel': 'A', 'tempo': {'espera': '48h'}, 'segue': 'f'},
            {'id': 'f', 'tipo': 'fim', 'nome': 'Fim'}]}
        self.assertIn('horas_ambiguas', _codigos(modelo.Carta(d), 'aviso'))


class TestAnalise(unittest.TestCase):
    def test_pergunta_negativa_nao_quebra_o_caminho_feliz(self):
        c = _carta('neg')
        r = analise.analisar(c)
        self.assertTrue(r['caminho_completo'])
        nomes = [c.nome(x) for x in r['caminho_feliz']]
        self.assertIn('Arquivar documento', nomes)
        self.assertNotIn('Corrigir documento', nomes)

    def test_percentual_nao_vem_de_decisao_alheia(self):
        c = _carta('estrutura')
        for x in analise.analisar(c)['retrabalho']:
            if x['percentual'] is not None:
                origem = analise.percentual_do_laco(c, next(f for f in c.fluxos if f['de'] == x['de']
                                                             and f['para'] == x['para']))
                self.assertEqual(origem, x['percentual'])

    def test_lead_time_esperado_conta_retrabalho(self):
        c = modelo.carregar(os.path.join(RAIZ, 'exemplos', 'credito', 'carta.json'))
        t = analise.analisar(c)['tempos']
        self.assertGreater(t['lead_time_esperado'], t['lead_time'] * 0.9)

    def test_externo_nao_vira_vai_e_volta(self):
        c = modelo.carregar(os.path.join(RAIZ, 'exemplos', 'compras', 'carta.json'))
        for a, b, z in analise.analisar(c)['vai_e_volta']:
            self.assertNotEqual((c.papeis.get(c.raia_de(b)) or {}).get('tipo'), 'externo')

    def test_controle_obrigatorio_nao_e_sugerido_para_corte(self):
        c = modelo.carregar(os.path.join(RAIZ, 'exemplos', 'credito', 'carta.json'))
        textos = ' '.join(o['texto'] for o in analise.analisar(c)['oportunidades'])
        self.assertNotIn('KYC', textos)
        self.assertNotIn('uma basta', textos)

    def test_criterio_no_nome_da_decisao(self):
        d = {'processo': {'nome': 'x'}, 'papeis': ['A'], 'elementos': [
            {'id': 'i', 'tipo': 'inicio', 'nome': 'Pedido', 'papel': 'A', 'segue': 'a'},
            {'id': 'a', 'nome': 'Analisar pedido', 'papel': 'A', 'segue': 'd'},
            {'id': 'd', 'tipo': 'decisao', 'nome': 'Valor acima de R$ 10 mil?', 'papel': 'A',
             'segue': [{'para': 'f1', 'rotulo': 'Sim'}, {'para': 'f2', 'rotulo': 'Não'}]},
            {'id': 'f1', 'tipo': 'fim', 'nome': 'Vai ao diretor'}, {'id': 'f2', 'tipo': 'fim', 'nome': 'Aprovado'}]}
        self.assertFalse(analise.decisao_sem_criterio(modelo.Carta(d), modelo.Carta(d).elementos['d']))

    def test_oportunidades_em_ordem_de_peso(self):
        c = modelo.carregar(os.path.join(RAIZ, 'exemplos', 'credito', 'carta.json'))
        pesos = [o['peso'] for o in analise.analisar(c)['oportunidades']]
        self.assertEqual(pesos, sorted(pesos, reverse=True))


class TestComparar(unittest.TestCase):
    def test_troca_de_destino_aparece(self):
        a, b = modelo.carregar(_caso('cmp', 'a.json')), modelo.carregar(_caso('cmp', 'b.json'))
        linhas, _ = aprovacao.comparar(a, b)
        self.assertTrue(any('ia para' in t for _, t in linhas), linhas)

    def test_desvio_aparece(self):
        a, c = modelo.carregar(_caso('cmp', 'a.json')), modelo.carregar(_caso('cmp', 'c.json'))
        linhas, _ = aprovacao.comparar(a, c)
        self.assertTrue(linhas)


class TestDesenho(unittest.TestCase):
    def _cruzamentos(self, c, lay):
        n = 0
        for fid, pts in lay.arestas.items():
            f = next(x for x in c.fluxos if x['id'] == fid)
            for (x1, y1), (x2, y2) in zip(pts, pts[1:]):
                for eid, no in lay.nos.items():
                    if eid in (f['de'], f['para']):
                        continue
                    if (min(x1, x2) < no['x'] + no['w'] and max(x1, x2) > no['x'] and
                            min(y1, y2) < no['y'] + no['h'] and max(y1, y2) > no['y']):
                        n += 1
        return n

    def test_nenhuma_linha_atravessa_caixa(self):
        for nome in ('hub', 'grande', 'estrutura', 'neg', 'lack'):
            c = _carta(nome)
            self.assertEqual(self._cruzamentos(c, layout.calcular(c)), 0, nome)
        for x in ('compras', 'credito'):
            c = modelo.carregar(os.path.join(RAIZ, 'exemplos', x, 'carta.json'))
            self.assertEqual(self._cruzamentos(c, layout.calcular(c)), 0, x)

    def test_rotulos_de_decisao_nao_se_escondem(self):
        c = _carta('hub')
        lay = layout.calcular(c)
        pos = [lay.rotulos[f['id']][:2] for f in c.fluxos if f['rotulo']]
        self.assertEqual(len(pos), len(set(pos)), 'dois rótulos no mesmo lugar')

    def test_mapa_longo_sai_em_partes(self):
        c = _carta('grande')
        lay = layout.calcular(c)
        partes = svg.faixas(lay)
        self.assertGreater(len(partes), 1)
        for i, f in enumerate(partes, 1):
            ET.fromstring(svg.desenhar(c, lay, faixa=f, parte=(i, len(partes))).encode('utf-8'))

    def test_sem_raia_fantasma(self):
        c = _carta('dc')
        self.assertNotIn(modelo.SEM_PAPEL, c.raias())


class TestInterop(unittest.TestCase):
    def test_ids_unicos(self):
        c = _carta('acento_ids')
        raiz = ET.fromstring(bpmn.gerar(c).encode('utf-8'))
        ids = [e.get('id') for e in raiz.iter() if e.get('id')]
        self.assertEqual([k for k, v in Counter(ids).items() if v > 1], [])
        m = mermaid.gerar(c)
        nos = [ln.split('[')[0].split('(')[0].split('{')[0].strip() for ln in m.splitlines()
               if ln.startswith('    ') and ':::' in ln]
        self.assertEqual(len(nos), len(set(nos)))

    def test_eventos_validos(self):
        d = {'processo': {'nome': 'x'}, 'papeis': ['A'], 'elementos': [
            {'id': 'i', 'tipo': 'inicio', 'gatilho': 'erro', 'papel': 'A', 'segue': 'f'},
            {'id': 'f', 'tipo': 'fim', 'nome': 'Fim'}]}
        self.assertIn('erro_fora_do_fim', _codigos(modelo.Carta(d), 'erro'))
        c = modelo.carregar(os.path.join(RAIZ, 'exemplos', 'credito', 'carta.json'))
        xml = bpmn.gerar(c)
        self.assertIn('terminateEventDefinition', xml)
        self.assertIn('timeDuration', xml)
        self.assertIn('messageRef=', xml)

    def test_importa_camunda_sem_erro(self):
        carta, avisos = importar(_caso('import', 'camunda.bpmn'))
        c = modelo.Carta(carta)
        self.assertEqual([a for a in validacao.validar(c) if a.nivel == 'erro'], [])
        self.assertTrue(any(e.get('bordas') for e in carta['elementos']))
        self.assertTrue(any('Mensagem' in p['pergunta'] for p in carta['pendencias']))


class TestRodada2(unittest.TestCase):
    """Achados da segunda revisão independente."""

    def test_ou_inclusivo_bem_formado_passa(self):
        cods = _codigos(_carta('r1_incl_ok'), 'erro')
        self.assertEqual(cods, set())

    def test_chamado_encerrado_e_fim_bom(self):
        c = _carta('r1_sem_chamado')
        nomes = [c.nome(x) for x in analise.analisar(c)['caminho_feliz']]
        self.assertEqual(nomes[-1], 'Chamado encerrado')

    def test_espera_do_evento_de_prazo(self):
        t = analise.analisar(_carta('r1_sem_timer'))['tempos']
        self.assertGreater(t['espera'], 5 * 480)

    def test_rotulos_de_decisao_perto_da_porta(self):
        for p in (os.path.join(RAIZ, 'exemplos', 'credito', 'carta.json'), _caso('r1_loops'), _caso('hub')):
            c = modelo.carregar(p)
            lay = layout.calcular(c)
            pos = []
            for f in c.fluxos:
                if f['rotulo'] and c.elementos[f['de']]['tipo'] in ('decisao', 'inclusivo'):
                    x, y, _ = lay.rotulos[f['id']]
                    n = lay.nos[f['de']]
                    if f['id'] not in lay.volta:
                        self.assertLess(abs(x - n['cx']) + abs(y - n['cy']), 160, (p, f))
                    pos.append((x, y))
            self.assertEqual(len(pos), len(set(pos)), p)

    def test_sem_trechos_sobrepostos(self):
        sys.path.insert(0, os.path.join(RAIZ, 'ferramentas'))
        import geometria
        for p in (os.path.join(RAIZ, 'exemplos', 'credito', 'carta.json'),
                  os.path.join(RAIZ, 'exemplos', 'compras', 'carta.json'), _caso('estrutura'), _caso('r1_mix'),
                  _caso('r1_big66'), _caso('hub')):
            r = geometria.check(p)
            self.assertEqual(r['edge_over_node'], [], p)
            self.assertEqual(r['edge_overlap'], [], p)
            self.assertEqual(r['label_label'], [], p)

    def test_comparar_ve_raci_valor_e_indicador(self):
        tmp = tempfile.mkdtemp()
        try:
            carta = os.path.join(tmp, 'carta.json')
            shutil.copy(os.path.join(RAIZ, 'exemplos', 'credito', 'carta.json'), carta)
            _rodar('aprovar', carta, '--por', 'X (Y)')
            with open(carta, encoding='utf-8') as f:
                d = json.load(f)
            next(e for e in d['elementos'] if e['id'] == 'a4')['raci'] = {'A': 'comite'}
            d['indicadores'][0]['meta'] = 'outra'
            d['riscos'] = []
            with open(carta, 'w', encoding='utf-8') as f:
                json.dump(d, f, ensure_ascii=False)
            _, out = _rodar('comparar', carta)
            self.assertIn('RACI', out)
            self.assertIn('meta', out)
            self.assertIn('risco removido', out)
            self.assertNotIn('valor (vazio)', out)
        finally:
            shutil.rmtree(tmp)

    def test_campo_numerico_nao_quebra_documentar(self):
        tmp = tempfile.mkdtemp()
        try:
            cod, out = _rodar('documentar', _caso('r1_volume_num'), '-o', tmp)
            self.assertEqual(cod, 0, out)
        finally:
            shutil.rmtree(tmp)

    def test_ida_e_volta_pelo_bpmn_nao_perde_nada(self):
        tmp = tempfile.mkdtemp()
        try:
            c = modelo.carregar(os.path.join(RAIZ, 'exemplos', 'credito', 'carta.json'))
            arq = os.path.join(tmp, 'x.bpmn')
            with open(arq, 'w', encoding='utf-8') as f:
                f.write(bpmn.gerar(c))
            carta, _ = importar(arq)
            linhas, _ = aprovacao.comparar(c, modelo.Carta(carta))
            self.assertEqual(linhas, [])
        finally:
            shutil.rmtree(tmp)

    def test_importa_colaboracao_camunda(self):
        carta, avisos = importar(_caso('r1_import_camunda_collab', 'camunda_collab.bpmn'))
        self.assertEqual([a for a in validacao.validar(modelo.Carta(carta)) if a.nivel == 'erro'], [])

    def test_percentuais(self):
        self.assertIn('percentual_soma', _codigos(_carta('r1_val_pct_sum_150'), 'erro'))
        self.assertIn('percentual_soma', _codigos(_carta('r1_val_pct_sum_40'), 'erro'))

    def test_ids_tecnicos_nao_colidem(self):
        x = bpmn.gerar(_carta('r1_idclash'))
        import re as _re
        ids = _re.findall(r'id="([^"]+)"', x)
        self.assertEqual(len(ids), len(set(ids)))

    def test_timer_em_tempo_de_relogio(self):
        x = bpmn.gerar(modelo.carregar(os.path.join(RAIZ, 'exemplos', 'credito', 'carta.json')))
        self.assertIn('<bpmn:timeDuration xsi:type="bpmn:tFormalExpression">P7D<', x)
        self.assertNotIn('PT0H', x)

    def test_tempo_brasileiro(self):
        for t, esperado in {'imediato': 0, 'D+1': 480, 'mesmo dia': 240, '~1h': 60, 'de 2 a 3 semanas': 6000,
                            '90 seg': 1.5}.items():
            self.assertAlmostEqual(minutos(t), esperado, msg=t)

    def test_fluxograma_rapido_sem_processo_nao_e_erro(self):
        self.assertNotIn('processo_sem_nome', _codigos(_carta('r1_quick'), 'erro'))

    def test_word(self):
        import zipfile
        from saidas import docx, documento
        tmp = tempfile.mkdtemp()
        try:
            c = modelo.carregar(os.path.join(RAIZ, 'exemplos', 'credito', 'carta.json'))
            arq = os.path.join(tmp, 'x.docx')
            docx.gerar(c, documento.montar(c), arq)
            with zipfile.ZipFile(arq) as z:
                for n in z.namelist():
                    if n.endswith(('.xml', '.rels')):
                        ET.fromstring(z.read(n))
                self.assertIn('word/media/fluxograma1.svg', z.namelist())
        finally:
            shutil.rmtree(tmp)


class TestRodada3(unittest.TestCase):
    """Achados da terceira revisão independente."""

    def test_caractere_de_controle_nao_quebra_xml(self):
        import zipfile
        tmp = tempfile.mkdtemp()
        try:
            _rodar('documentar', _caso('r2_01_ctrlchar'), '-o', tmp)
            for n in os.listdir(tmp):
                if n.endswith(('.bpmn', '.svg', '.drawio')):
                    with open(os.path.join(tmp, n), encoding='utf-8') as f:
                        ET.fromstring(f.read().encode('utf-8'))
            docx = [n for n in os.listdir(tmp) if n.endswith('.docx')][0]
            with zipfile.ZipFile(os.path.join(tmp, docx)) as z:
                ET.fromstring(z.read('word/document.xml'))
        finally:
            shutil.rmtree(tmp)
        self.assertIn('caractere_invisivel', _codigos(_carta('r2_01_ctrlchar')))

    def test_corrida_com_fim_terminal(self):
        c = _carta('r2_02_terminate_happy_path')
        r = analise.analisar(c)
        self.assertEqual(c.nome(r['caminho_feliz'][-1]), 'Contrato assinado')
        self.assertLess(r['tempos']['lead_time'], minutos('5d'))

    def test_ids_originais_voltam_do_bpmn(self):
        tmp = tempfile.mkdtemp()
        try:
            c = _carta('r2_03_roundtrip_ids')
            arq = os.path.join(tmp, 'x.bpmn')
            with open(arq, 'w', encoding='utf-8') as f:
                f.write(bpmn.gerar(c))
            carta, _ = importar(arq)
            self.assertEqual(sorted(e['id'] for e in carta['elementos']), sorted(c.elementos))
        finally:
            shutil.rmtree(tmp)

    def test_duas_ligacoes_para_o_mesmo_destino(self):
        carta, _ = importar(_caso('r2_04_import_two_link_throws', '04_import_two_link_throws.bpmn'))
        self.assertEqual([a for a in validacao.validar(modelo.Carta(carta)) if a.nivel == 'erro'], [])

    def test_borda_de_erro_importa_valida(self):
        carta, _ = importar(_caso('r2_05_import_camunda_full', '05_import_camunda_full.bpmn'))
        self.assertEqual([a for a in validacao.validar(modelo.Carta(carta)) if a.nivel == 'erro'], [])

    def test_sistema_em_branco_ainda_e_pergunta(self):
        from carta import lacunas
        c = _carta('r2_08_blank_sistema')
        self.assertTrue(any('sistema' in q.texto for q in lacunas.levantar(c)))

    def test_texto_booleano(self):
        c = _carta('r2_12_string_bool')
        self.assertFalse(any(e['encerra'] for e in c.elementos.values()
                             if str(e['bruto'].get('encerra')).lower() in ('false', 'não', 'nao')))
        self.assertIn('papel_repetido', _codigos(c, 'erro'))

    def test_comparar_sem_fantasma(self):
        tmp = tempfile.mkdtemp()
        try:
            carta = os.path.join(tmp, 'carta.json')
            shutil.copy(_caso('r2_09_cmp_phantom'), carta)
            _rodar('aprovar', carta, '--por', 'X (Y)')
            _, out = _rodar('comparar', carta)
            self.assertIn('nenhuma diferença', out)
            linhas = [ln for ln in out.splitlines() if 'lead time esperado' in ln]
            self.assertTrue(linhas and linhas[0].rstrip().endswith('='), linhas)
        finally:
            shutil.rmtree(tmp)

    def test_figura_do_word_cabe_na_pagina(self):
        import re as _re
        import zipfile
        from saidas import docx, documento
        tmp = tempfile.mkdtemp()
        try:
            c = _carta('r2_15_big10')
            arq = os.path.join(tmp, 'x.docx')
            docx.gerar(c, documento.montar(c), arq)
            with zipfile.ZipFile(arq) as z:
                xml = z.read('word/document.xml').decode('utf-8')
                self.assertIn('word/header1.xml', z.namelist())
                self.assertGreater(len(z.read('word/media/fluxograma1.png')), 500)   # não é mais 1 pixel
            for cx, cy in _re.findall(r'<wp:extent cx="(\d+)" cy="(\d+)"', xml):
                self.assertLessEqual(int(cy), 6.3 * 914400)
                self.assertLessEqual(int(cx), 10 * 914400)
        finally:
            shutil.rmtree(tmp)

    def test_word_e_html_contam_igual(self):
        import zipfile
        from saidas import docx, documento
        tmp = tempfile.mkdtemp()
        try:
            c = modelo.carregar(os.path.join(RAIZ, 'exemplos', 'compras', 'carta.json'))
            d = documento.montar(c)
            arq = os.path.join(tmp, 'x.docx')
            docx.gerar(c, d, arq)
            with zipfile.ZipFile(arq) as z:
                xml = z.read('word/document.xml').decode('utf-8')
            self.assertIn(f'>{len(d["an"]["passagens_caminho"])}<', xml)
            for secao in ('Decisões e regras', 'Participantes', 'Caminho feliz', 'Normas'):
                self.assertIn(secao, xml)
        finally:
            shutil.rmtree(tmp)

    def test_lacunas_comecam_pelo_mapa(self):
        from carta import lacunas
        qs = lacunas.levantar(_carta('r2_13_nested_sim_heuristic'))
        self.assertTrue(all(q.prioridade <= 2 for q in qs[:3]), [q.prioridade for q in qs[:3]])

    def test_frases_de_tempo(self):
        for t, esperado in {'uma hora': 60, 'duas horas': 120, 'dez minutos': 10, 'entre 2 e 3 dias': 1200,
                            '2h e meia': 150, '45min.': 45, 'quinzena': 4800, 'uma quinzena': 4800,
                            'dia seguinte': 480}.items():
            self.assertAlmostEqual(minutos(t), esperado, msg=t)

    def test_limite_na_pergunta(self):
        c = _carta('r2_13_nested_sim_heuristic')
        nomes = [c.nome(x) for x in analise.analisar(c)['caminho_feliz']]
        self.assertFalse(any('comit' in n.lower() for n in nomes), nomes)

    def test_csv_sem_formula(self):
        from saidas import documento
        d = {'processo': {'nome': 'x'}, 'papeis': ['A'], 'elementos': [
            {'id': 'i', 'tipo': 'inicio', 'nome': 'In', 'papel': 'A', 'segue': 'a'},
            {'id': 'a', 'nome': '=HYPERLINK("x")', 'papel': 'A', 'segue': 'f'},
            {'id': 'f', 'tipo': 'fim', 'nome': 'Fim'}]}
        self.assertNotIn(';=HYPERLINK', documento.csv_atividades(modelo.Carta(d)))

    def test_bpmn_sem_nomes_de_pessoas(self):
        x = bpmn.gerar(modelo.carregar(os.path.join(RAIZ, 'exemplos', 'credito', 'carta.json')))
        self.assertNotIn('Marina Lopes', x)

    def test_estresse_do_desenho(self):
        import random as _r
        sys.path.insert(0, os.path.join(RAIZ, 'ferramentas'))
        import estresse
        ruins = 0
        for semente in range(40):
            R = _r.Random(semente)
            c = modelo.Carta(estresse.gerar(semente, R.randint(3, 8), _r.Random(semente + 1).randint(10, 30)))
            r = estresse.medir(c, layout.calcular(c))
            self.assertEqual(r['caixa'], 0, semente)
            self.assertEqual([a for a in validacao.validar(c) if a.nivel == 'erro'], [], semente)
            ruins += 1 if r['sobrepostas'] else 0
        self.assertLessEqual(ruins, 4)


class TestRodada4(unittest.TestCase):
    """Recursos de profissional: corrida, bordas, pools, subprocesso ligado, risco e plano de ação."""

    def test_corrida(self):
        c = _carta('corrida')
        self.assertEqual([a for a in validacao.validar(c) if a.nivel in ('erro', 'aviso')], [])
        x = bpmn.gerar(c)
        self.assertIn('eventBasedGateway', x)
        r = analise.analisar(c)
        self.assertIn('Aceite do cliente recebido', [c.nome(i) for i in r['caminho_feliz']])
        d = _ler(_caso('corrida'))
        d['elementos'][2]['segue'][0]['para'] = 'a2'           # corrida tem de começar com evento
        self.assertIn('corrida_sem_evento', _codigos(modelo.Carta(d), 'erro'))

    def test_bordas(self):
        c = _carta('bordas')
        self.assertEqual([a for a in validacao.validar(c) if a.nivel in ('erro', 'aviso')], [])
        x = bpmn.gerar(c)
        self.assertEqual(x.count('<bpmn:boundaryEvent'), 2)
        self.assertIn('cancelActivity="false"', x)
        r = analise.analisar(c)
        self.assertNotIn('Escalar para supervisor', [c.nome(i) for i in r['caminho_feliz']])
        self.assertGreater(r['tempos']['lead_time_esperado'], r['tempos']['lead_time'])
        lay = layout.calcular(c)
        host = lay.nos['a1']
        for b in c.de_tipo('borda'):
            n = lay.nos[b['id']]
            self.assertAlmostEqual(n['cy'], host['y'] + host['h'])
        from saidas import documento
        self.assertIn('Prazo de 8h estourado', documento.html_documento(c))

    def test_bordas_na_ida_e_volta(self):
        tmp = tempfile.mkdtemp()
        try:
            c = _carta('bordas')
            arq = os.path.join(tmp, 'x.bpmn')
            with open(arq, 'w', encoding='utf-8') as f:
                f.write(bpmn.gerar(c))
            carta, _ = importar(arq)
            self.assertEqual(aprovacao.comparar(c, modelo.Carta(carta))[0], [])
        finally:
            shutil.rmtree(tmp)

    def test_borda_importada_de_camunda(self):
        carta, _ = importar(_caso('r2_05_import_camunda_full', '05_import_camunda_full.bpmn'))
        bordas = [b for e in carta['elementos'] for b in e.get('bordas', [])]
        self.assertEqual(len(bordas), 3)
        self.assertTrue(any(b.get('interrompe') is False for b in bordas))

    def test_pools(self):
        c = modelo.carregar(os.path.join(RAIZ, 'exemplos', 'compras', 'carta.json'))
        x, aviso = bpmn.gerar_com_pools(c)
        self.assertEqual(aviso, '')
        raiz = ET.fromstring(x.encode('utf-8'))
        ns = '{http://www.omg.org/spec/BPMN/20100524/MODEL}'
        self.assertEqual(len(list(raiz.iter(ns + 'participant'))), 2)
        self.assertGreater(len(list(raiz.iter(ns + 'messageFlow'))), 0)
        nomes = {e.get('name') for e in raiz.iter(ns + 'task')} | {e.get('name') for e in raiz.iter(ns + 'userTask')}
        self.assertNotIn('Enviar proposta', nomes)             # atividade do fornecedor fica no pool dele
        c2 = modelo.carregar(os.path.join(RAIZ, 'exemplos', 'credito', 'carta.json'))
        _, aviso = bpmn.gerar_com_pools(c2)
        self.assertIn('raias', aviso)

    def test_subprocesso_ligado(self):
        c = modelo.carregar(os.path.join(RAIZ, 'exemplos', 'credito', 'carta.json'))
        self.assertNotIn('detalhe_nao_existe', _codigos(c))
        d = _ler(os.path.join(RAIZ, 'exemplos', 'credito', 'carta.json'))
        next(e for e in d['elementos'] if e['id'] == 's1')['detalhe'] = 'nao/existe.json'
        c2 = modelo.Carta(d, os.path.join(RAIZ, 'exemplos', 'credito', 'carta.json'))
        self.assertIn('detalhe_nao_existe', _codigos(c2, 'aviso'))

    def test_risco_e_plano(self):
        from carta.gestao import nivel_risco, plano
        self.assertEqual(nivel_risco({'probabilidade': 'alta', 'impacto': 'muito alto', 'controle': 'x'}),
                         (20, 'crítico'))
        self.assertEqual(nivel_risco({'probabilidade': 2, 'impacto': 2, 'controle': 'x'})[1], 'baixo')
        self.assertIn('sem controle', nivel_risco({'probabilidade': 2, 'impacto': 2})[1])
        c = modelo.carregar(os.path.join(RAIZ, 'exemplos', 'credito', 'carta.json'))
        self.assertTrue(all(x['responsavel'] != 'a definir' for x in plano(c)))
        from saidas import documento
        h = documento.html_documento(c)
        self.assertIn('Plano de ação', h)
        self.assertIn('linha de base', h)


class TestRodada5(unittest.TestCase):
    """Achados da quinta revisão: bordas, corrida, pools, comparação e análise."""

    def test_borda_nao_vira_lacuna_de_divisao(self):
        from carta import lacunas
        c = modelo.carregar(os.path.join(RAIZ, 'exemplos', 'credito', 'carta.json'))
        self.assertFalse(any('lugares' in q.texto for q in lacunas.levantar(c)))
        _, out = _rodar('situacao', os.path.join(RAIZ, 'exemplos', 'credito', 'carta.json'))
        self.assertNotIn('Etapa: entrevista', out)

    def test_comparar_logo_depois_do_aceite(self):
        tmp = tempfile.mkdtemp()
        try:
            shutil.copytree(os.path.join(RAIZ, 'exemplos', 'credito'), os.path.join(tmp, 'c'),
                            ignore=shutil.ignore_patterns('saida'))
            carta = os.path.join(tmp, 'c', 'carta.json')
            _rodar('aprovar', carta, '--por', 'X (Y)')
            d = _ler(carta)
            d['historico'].append({'versao': '1.0', 'mudanca': 'aprovado'})
            with open(carta, 'w', encoding='utf-8') as f:
                json.dump(d, f, ensure_ascii=False)
            _, out = _rodar('comparar', carta)
            self.assertIn('nenhuma diferença', out)
            self.assertNotIn('-', ''.join(ln.split()[-1] for ln in out.splitlines() if 'lead time' in ln))
            _, out = _rodar('situacao', carta)
            self.assertIn('aprovado', out)
        finally:
            shutil.rmtree(tmp)

    def test_lembrete_dentro_de_laco(self):
        self.assertEqual(_codigos(_carta('r4_r03_nonint_loop'), 'erro'), set())

    def test_prazo_da_borda_nao_soma_a_atividade(self):
        t = analise.analisar(_carta('r4_r01_borda_tempo'))['tempos']
        self.assertLess(t['lead_time_esperado'], minutos('4d'))
        self.assertIn('horas_ambiguas', _codigos(_carta('r4_r01_borda_tempo'), 'aviso'))

    def test_tipo_borda_solto_nao_quebra(self):
        tmp = tempfile.mkdtemp()
        try:
            cod, _ = _rodar('desenhar', _caso('r4_r15_tipo_borda'), '-o', tmp)
            self.assertIn(cod, (0, 1))
        finally:
            shutil.rmtree(tmp)

    def test_corrida_com_evento_compartilhado(self):
        self.assertIn('corrida_evento_compartilhado', _codigos(_carta('r4_r12_corrida_bad'), 'erro'))

    def test_pools_mensagem_nunca_em_porta(self):
        ns = '{http://www.omg.org/spec/BPMN/20100524/MODEL}'
        for nome in ('r4_r05_pools', 'r4_r06_pools_gateway'):
            x, aviso = bpmn.gerar_com_pools(_carta(nome))
            self.assertEqual(aviso, '', nome)
            raiz = ET.fromstring(x.encode('utf-8'))
            tipos = {e.get('id'): e.tag.replace(ns, '') for e in raiz.iter() if e.get('id')}
            for m in raiz.iter(ns + 'messageFlow'):
                for ref in (m.get('sourceRef'), m.get('targetRef')):
                    self.assertFalse(tipos.get(ref, '').endswith('Gateway'), (nome, ref))
                self.assertNotEqual(tipos.get(m.get('sourceRef')), 'startEvent')
            from saidas.pools import transformar
            interna, _, _ = transformar(_carta(nome))
            self.assertEqual([a for a in validacao.validar(interna) if a.nivel == 'erro'], [], nome)

    def test_inclusivo_nao_normaliza(self):
        c = _carta('r4_r14_inclusivo')
        v = analise.analisar(c)['visitas']
        por_nome = {c.nome(e): v[e] for e in c.elementos}
        self.assertAlmostEqual(por_nome['Emitir parecer financeiro'], 0.8, places=2)
        self.assertAlmostEqual(por_nome['Emitir parecer de auditoria'], 0.6, places=2)

    def test_iso_sem_hora_quebrada(self):
        from saidas.bpmn import _iso
        self.assertEqual(_iso(90), 'PT1H30M')

    def test_carga_por_papel(self):
        r = analise.analisar(modelo.carregar(os.path.join(RAIZ, 'exemplos', 'credito', 'carta.json')))
        self.assertIsNotNone(r['carga'])
        self.assertGreater(r['carga']['pessoas'], 1)
        self.assertEqual(analise.casos_por_mes('15 por dia'), 300)

    def test_numeracao_pelo_caminho_feliz(self):
        c = modelo.carregar(os.path.join(RAIZ, 'exemplos', 'compras', 'carta.json'))
        nums = layout.numerar(c, layout.calcular(c))
        caminho = [x for x in analise.caminho_feliz(c)[0] if x in nums]
        self.assertEqual([nums[x] for x in caminho], sorted(nums[x] for x in caminho))
        self.assertGreater(nums['a1b'], nums['a11'])                 # exceção depois do caminho principal

    def test_png_de_reserva_tem_texto(self):
        from saidas import png
        c = modelo.carregar(os.path.join(RAIZ, 'exemplos', 'compras', 'carta.json'))
        self.assertGreater(len(png.desenhar(c, layout.calcular(c))), 8000)

    def test_importa_signavio(self):
        carta, avisos = importar(_caso('r4_r09_import', 'signavio.bpmn'))
        self.assertEqual([a for a in validacao.validar(modelo.Carta(carta)) if a.nivel == 'erro'], [])
        self.assertTrue(any('escalation' in a for a in avisos))


class TestRodada6(unittest.TestCase):
    """Achados da 5ª revisão cega."""

    def test_pools_sem_mensagem_saindo_de_evento_de_espera(self):
        xml, _ = bpmn.gerar_com_pools(_carta('r5_r07_grande'))
        raiz = ET.fromstring(xml.encode('utf-8'))
        tipo = {e.get('id'): e.tag.split('}')[1] for e in raiz.iter() if e.get('id')}
        for m in raiz.iter():
            if m.tag.endswith('messageFlow'):
                self.assertNotIn(tipo[m.get('sourceRef')], ('intermediateCatchEvent', 'exclusiveGateway',
                                                            'parallelGateway', 'eventBasedGateway'))
                self.assertNotIn(tipo[m.get('targetRef')], ('exclusiveGateway', 'parallelGateway', 'endEvent'))

    def test_espera_de_mensagem_sem_tempo_nao_da_100(self):
        c = _carta('r5_r03_corrida')
        t = analise.analisar(c)['tempos']
        if t['espera_sem_tempo']:
            self.assertIn('—', analise.pct_txt(t))
        from carta import lacunas
        self.assertTrue(any('costuma levar' in q.texto for q in lacunas.levantar(c)))

    def test_comparar_ids_renomeados_sem_mudanca_falsa(self):
        a, b = _carta('r5_r11_aprov'), modelo.carregar(_caso('r5_r11_aprov', 'carta-tobe.json'))
        linhas, _ = aprovacao.comparar(a, b)
        self.assertEqual(linhas, [])

    def test_comparar_papel_herdado_nao_repete(self):
        pasta = tempfile.mkdtemp()
        try:
            shutil.copy(_caso('r5_r10_comparar'), pasta)
            shutil.copy(_caso('r5_r10_comparar', 'carta.aprovacao.json'), pasta)
            cod, out = _rodar('comparar', os.path.join(pasta, 'carta.json'))
            self.assertEqual(cod, 0)
            self.assertEqual(out.count('responsável'), 1)
        finally:
            shutil.rmtree(pasta, ignore_errors=True)

    def test_aceite_diz_o_que_mudou_fora_do_fluxo(self):
        pasta = tempfile.mkdtemp()
        try:
            arq = os.path.join(pasta, 'carta.json')
            shutil.copy(os.path.join(RAIZ, 'exemplos', 'compras', 'carta.json'), arq)
            self.assertEqual(_rodar('aprovar', arq, '--por', 'Ana (Gerente)')[0], 0)
            d = _ler(arq)
            d.setdefault('pendencias', []).append({'pergunta': 'Qual a alçada?', 'para': 'Controladoria'})
            with open(arq, 'w', encoding='utf-8') as f:
                json.dump(d, f, ensure_ascii=False)
            cod, out = _rodar('comparar', arq)
            self.assertIn('pendências', out)
            cod, out = _rodar('situacao', arq)
            self.assertIn('mudou depois do aceite', out)
        finally:
            shutil.rmtree(pasta, ignore_errors=True)

    def test_borda_rara_nao_lidera_oportunidades(self):
        ops = analise.analisar(_carta('r5_r02_bordas'))['oportunidades']
        self.assertNotIn('Catástrofe', ops[0]['texto'])

    def test_avisos_novos(self):
        self.assertIn('paralelo_de_esperas', _codigos(_carta('r5_corrida_after_and')))
        self.assertIn('borda_divide', _codigos(_carta('r5_r05_tipos')))
        self.assertIn('corrida_juntando', _codigos(_carta('r5_r03_corrida'), 'erro'))

    def test_detalhe_confere_tempo_da_carta_filha(self):
        pasta = tempfile.mkdtemp()
        try:
            destino = os.path.join(pasta, 'credito')
            shutil.copytree(os.path.join(RAIZ, 'exemplos', 'credito'), destino,
                            ignore=shutil.ignore_patterns('saida'))
            self.assertNotIn('detalhe_tempo_diferente', _codigos(modelo.carregar(os.path.join(destino, 'carta.json'))))
            d = _ler(os.path.join(destino, 'carta.json'))
            for e in d['elementos']:
                if e.get('id') == 's1':
                    e['tempo'] = {'execucao': '3h', 'espera': '2d'}
            with open(os.path.join(destino, 'carta.json'), 'w', encoding='utf-8') as f:
                json.dump(d, f, ensure_ascii=False)
            self.assertIn('detalhe_tempo_diferente', _codigos(modelo.carregar(os.path.join(destino, 'carta.json'))))
        finally:
            shutil.rmtree(pasta, ignore_errors=True)

    def test_faixa_comprime_raias_vazias(self):
        c = _carta('r5_r07_grande')
        lay = layout.calcular(c)
        cortes = svg.faixas(lay)
        alturas = [float(svg.desenhar(c, lay, faixa=f, parte=(i + 1, len(cortes))).split('height="', 1)[1]
                         .split('"', 1)[0]) for i, f in enumerate(cortes)]
        self.assertLess(max(alturas), lay.altura)

    def test_modelador_vale_mais_no_tipo_do_evento(self):
        c = modelo.carregar(os.path.join(RAIZ, 'exemplos', 'credito', 'carta.json'))
        xml = bpmn.gerar(c)
        # no modelador, um fim terminal virou fim comum
        xml2 = xml.replace('<bpmn:terminateEventDefinition', '<bpmn:x_removido', 1)
        pasta = tempfile.mkdtemp()
        try:
            arq = os.path.join(pasta, 'x.bpmn')
            with open(arq, 'w', encoding='utf-8') as f:
                f.write(xml2)
            carta, _ = importar(arq)
            enc_antes = sum(1 for e in c.elementos.values() if e['encerra'])
            enc_depois = sum(1 for e in carta['elementos'] if e.get('encerra'))
            if enc_antes:
                self.assertEqual(enc_depois, enc_antes - 1)
        finally:
            shutil.rmtree(pasta, ignore_errors=True)


class TestRodada7(unittest.TestCase):
    """Achados da 6ª revisão cega."""

    def test_importar_pela_linha_de_comando(self):
        pasta = tempfile.mkdtemp()
        try:
            cod, out = _rodar('importar', _caso('r6_roundtrip', 'signavio.bpmn'), '-o', os.path.join(pasta, 'c.json'))
            self.assertEqual(cod, 0, out)
        finally:
            shutil.rmtree(pasta, ignore_errors=True)

    def test_sem_quebra_em_casos_ruins(self):
        for nome in ('r6_par_typo', 'r6_borda_pct_str'):
            for cmd in ('validar', 'analisar'):
                cod, out = _rodar(cmd, _caso(nome))
                self.assertIn(cod, (0, 1), f'{cmd} {nome}: {out}')
        c = _carta('r6_borda_pct_str')
        self.assertTrue(all(isinstance(e['percentual_borda'], (float, type(None)))
                            for e in c.elementos.values() if e['tipo'] == 'borda'))

    def test_png_de_parte_tem_tamanho_certo(self):
        import struct
        import zlib
        from saidas import png
        c = modelo.carregar(os.path.join(RAIZ, 'exemplos', 'credito', 'carta.json'))
        lay = layout.calcular(c)
        for faixa in svg.faixas(lay)[1:]:
            b = png.desenhar(c, lay, faixa)
            w, h = struct.unpack('>II', b[16:24])
            i, dados = 8, b''
            while i < len(b):
                n, tipo = struct.unpack('>I4s', b[i:i + 8])
                if tipo == b'IDAT':
                    dados += b[i + 8:i + 8 + n]
                i += 12 + n
            self.assertEqual(len(zlib.decompress(dados)), h * (w * 3 + 1))

    def test_borda_no_ramo_paralelo_nao_desvia(self):
        c = _carta('r6_v28_border_in_parallel')
        caminho, _ = analise.caminho_feliz(c)
        self.assertEqual(c.elementos[caminho[-1]]['tipo'], 'fim')

    def test_pools_cai_para_raias_quando_nao_da(self):
        from saidas.pools import transformar
        for nome in ('r6_p1_corrida_ext', 'r6_p2_borda_ext'):
            interna, motivo, _ = transformar(_carta(nome))
            self.assertIsNone(interna, nome)
            self.assertIsInstance(motivo, str)
        interna, pools, msgs = transformar(_carta('r6_p3_par_ext'))
        self.assertIsNotNone(interna)
        # "Receber orçamento" do cliente: só ida, ninguém espera resposta dele
        self.assertFalse(any(m['de'] is None and 'orçamento' in m['nome'].lower() for m in msgs))

    def test_validacoes_novas(self):
        casos = {'r6_v17_nonint_rejoin': 'lembrete_volta_ao_fluxo', 'r6_v19_fim_timer': 'fim_de_tempo',
                 'r6_v20_corrida_envia': 'corrida_sem_evento', 'r6_v26_borders_sum': 'bordas_mais_de_100',
                 'r6_v29_flow_into_border': 'fluxo_para_borda'}
        for nome, codigo in casos.items():
            self.assertIn(codigo, _codigos(_carta(nome)), nome)

    def test_modelador_vale_no_prazo_e_na_raia(self):
        carta, _ = importar(_caso('r6_roundtrip', 'editado.bpmn'))
        papeis = {p['id']: p['nome'] for p in carta['papeis']}
        self.assertEqual(len(papeis), len(carta['papeis']))
        self.assertFalse(any(str(i).startswith('Raia_') for i in papeis))
        original, _ = importar(_caso('r6_roundtrip', 'original.bpmn'))
        t_ed = {e['id']: e.get('tempo') for e in carta['elementos']}
        t_or = {e['id']: e.get('tempo') for e in original['elementos']}
        self.assertNotEqual(t_ed, t_or)

    def test_volume_brasileiro(self):
        f = analise.casos_por_mes
        self.assertEqual(f('dez mil por mês'), 10000)
        self.assertEqual(f('2.5 mil por mês'), 2500)
        self.assertEqual(f('entre 100 e 150 por mês'), 125)
        self.assertEqual(f('R$ 2 milhões por mês em 300 pedidos'), 300)
        self.assertEqual(f('1.200 pedidos por mês'), 1200)

    def test_numeracao_segue_o_tempo(self):
        c = modelo.carregar(os.path.join(RAIZ, 'exemplos', 'credito', 'carta.json'))
        lay = layout.calcular(c)
        nums = layout.numerar(c, lay)
        normais = sorted((int(n), lay.nos[e]['coluna']) for e, n in nums.items())
        primeiros = [col for _, col in normais][:10]
        self.assertEqual(primeiros, sorted(primeiros))

    def test_docx_sem_prompt_e_md_completo(self):
        pasta = tempfile.mkdtemp()
        try:
            destino = os.path.join(pasta, 'credito')
            shutil.copytree(os.path.join(RAIZ, 'exemplos', 'credito'), destino, ignore=shutil.ignore_patterns('saida'))
            self.assertEqual(_rodar('documentar', destino)[0], 0)
            import glob
            import zipfile
            with zipfile.ZipFile(glob.glob(os.path.join(destino, 'saida', '*.docx'))[0]) as z:
                self.assertNotIn('updateFields', z.read('word/settings.xml').decode('utf-8'))
                ET.fromstring(z.read('word/document.xml'))
            with open(glob.glob(os.path.join(destino, 'saida', '*.md'))[0], encoding='utf-8') as f:
                md = f.read()
            for trecho in ('linha de base', 'Carga de trabalho', 'Normas e referências'):
                self.assertIn(trecho, md)
            with open(glob.glob(os.path.join(destino, 'saida', '*.html'))[0], encoding='utf-8') as f:
                html_txt = f.read()
            self.assertNotIn('sem sem', html_txt)
        finally:
            shutil.rmtree(pasta, ignore_errors=True)

    def test_nota_de_risco_arredonda(self):
        from carta.gestao import nivel_risco
        self.assertEqual(nivel_risco({'probabilidade': '4.7', 'impacto': 1, 'controle': 'x'})[0], 5)


class TestRodada8(unittest.TestCase):
    """Achados da 7ª revisão cega."""

    def _ida_e_volta(self, carta_json, editar=None):
        pasta = tempfile.mkdtemp()
        try:
            c = modelo.carregar(carta_json)
            xml = bpmn.gerar(c)
            if editar:
                xml = editar(xml)
            arq = os.path.join(pasta, 'x.bpmn')
            with open(arq, 'w', encoding='utf-8') as f:
                f.write(xml)
            dados, _ = importar(arq)
            return c, modelo.Carta(dados)
        finally:
            shutil.rmtree(pasta, ignore_errors=True)

    def test_ida_e_volta_sem_edicao_nao_muda_nada(self):
        for nome in ('compras', 'credito'):
            antes, depois = self._ida_e_volta(os.path.join(RAIZ, 'exemplos', nome, 'carta.json'))
            self.assertEqual(aprovacao.comparar(antes, depois)[0], [], nome)
        antes, depois = self._ida_e_volta(_caso('r7_roundtrip'))
        self.assertEqual(aprovacao.comparar(antes, depois)[0], [])

    def test_descricao_editada_no_modelador_vale(self):
        import re
        def editar(xml):
            return re.sub(r'(<bpmn:documentation>)', r'\1TEXTO NOVO. ', xml, count=1)
        _, depois = self._ida_e_volta(_caso('r7_roundtrip'), editar)
        self.assertTrue(any('TEXTO NOVO' in (e['descricao'] or '') for e in depois.elementos.values()))

    def test_comparar_percentual_sem_rotulo(self):
        c = _carta('r7_aprov')
        antes, reg = aprovacao.carregar_retrato_aprovado(c)
        linhas, _ = aprovacao.comparar(antes, c, reg['retrato'])
        self.assertTrue(any('60% -> 30%' in t for _, t in linhas))

    def test_pools_mensagem_valida(self):
        xml, _ = bpmn.gerar_com_pools(_carta('r7_pools'))
        raiz = ET.fromstring(xml.encode('utf-8'))
        elems = {e.get('id'): e for e in raiz.iter() if e.get('id')}
        alvos, fontes = set(), set()
        for m in raiz.iter():
            if m.tag.endswith('messageFlow'):
                alvo = elems[m.get('targetRef')]
                defs = [d.tag.split('}')[1] for d in alvo]
                self.assertNotIn('timerEventDefinition', defs)
                alvos.add(alvo.get('name'))
                fontes.add(elems[m.get('sourceRef')].get('name'))
        self.assertIn('Documentos recebidos', alvos)
        self.assertIn('Pedir documentos', fontes)

    def test_importa_subprocesso_de_evento_e_escolhe_pool(self):
        carta, avisos = importar(_caso('r7_import', 'signavio.bpmn'))
        self.assertEqual([a for a in validacao.validar(modelo.Carta(carta)) if a.nivel == 'erro'], [])
        self.assertTrue(any('subprocesso de evento' in a for a in avisos))
        loja, _ = importar(_caso('r7_import', 'bizagi_2pools.bpmn'), pool='loja')
        dc, _ = importar(_caso('r7_import', 'bizagi_2pools.bpmn'))
        self.assertNotEqual({e['nome'] for e in loja['elementos']}, {e['nome'] for e in dc['elementos']})
        with self.assertRaises(ErroDeUso):
            importar(_caso('r7_import', 'bizagi_2pools.bpmn'), pool='nao existe')

    def test_fim_terminal_desenhado_diferente(self):
        c = _carta('r7_terminate')
        texto = svg.desenhar(c)
        terminal = [e for e in c.elementos.values() if e['tipo'] == 'fim' and e['encerra']]
        self.assertTrue(terminal)
        self.assertIn('fill="#b3261e"/>', texto)

    def test_id_digitado_errado_sugere_e_nao_cascateia(self):
        achados = validacao.validar(_carta('r7_typos'))
        textos = ' '.join(a.texto for a in achados)
        self.assertIn('quis dizer "a1"', textos)
        self.assertFalse({'nunca_termina', 'sem_entrada', 'inalcancavel'} & {a.codigo for a in achados})

    def test_inclusivo_que_pode_nao_seguir(self):
        d = _ler(_caso('r4_r14_inclusivo'))
        for e in d['elementos']:
            for s in e.get('segue') or [] if isinstance(e.get('segue'), list) else []:
                if isinstance(s, dict) and s.get('percentual') is not None:
                    s['percentual'] = 30
        c = modelo.Carta(d)
        if any(e['tipo'] == 'inclusivo' and len(c.saidas[e['id']]) > 1 and
               all(f['percentual'] is not None for f in c.saidas[e['id']]) for e in c.elementos.values()):
            self.assertIn('inclusivo_pode_nao_seguir', _codigos(c))

    def test_word_em_faixas_de_cinco_colunas(self):
        c = modelo.carregar(os.path.join(RAIZ, 'testes', 'casos', 'r5_r07_grande', 'carta.json'))
        lay = layout.calcular(c)
        for i, f in enumerate(svg.faixas(lay, por_faixa=5)):
            t = svg.desenhar(c, lay, faixa=f, parte=(i + 1, 9))
            w = float(t.split('width="', 1)[1].split('"', 1)[0])
            h = float(t.split('height="', 1)[1].split('"', 1)[0])
            self.assertGreater(min(9.9 * 96 / w, 6.2 * 96 / h), 0.55)


class TestRodada9(unittest.TestCase):
    """Achados da 8ª revisão cega."""

    def test_caminho_feliz_com_retrabalho_majoritario_chega_ao_fim(self):
        c = _carta('r8_retrabalho60')
        caminho, _ = analise.caminho_feliz(c)
        self.assertEqual(c.elementos[caminho[-1]]['tipo'], 'fim')
        self.assertIn('a3', caminho)
        self.assertNotIn('a4', caminho)

    def test_paralelo_com_ramo_que_encerra(self):
        c = _carta('r8_sem_join')
        r = analise.analisar(c)
        self.assertAlmostEqual(r['visitas']['t3'], 0.5, delta=0.03)          # simulação: margem de sorteio
        self.assertAlmostEqual(r['tempos']['lead_time_esperado'], 6 * 60, delta=30)

    def test_volume_por_extenso(self):
        f = analise.casos_por_mes
        self.assertEqual(f('2 mil e quinhentos por mês'), 2500)
        self.assertEqual(f('cento e vinte por mês'), 120)
        self.assertEqual(f('de 2 a 3 mil por mês'), 2500)
        self.assertEqual(f('entre 100 e 150 por mês'), 125)
        self.assertAlmostEqual(f('4 a cada 2 semanas'), 2 * 4)
        self.assertIsNotNone(f('50/sem'))

    def test_plausibilidade(self):
        cods = _codigos(_carta('r8_sem_race'))
        self.assertIn('corrida_espera_maior_que_prazo', cods)
        self.assertIn('prazo_menor_que_atividade', cods)
        self.assertIn('laco_sempre', _codigos(_carta('r8_laco100'), 'erro'))

    def test_carta_ansi_nao_quebra(self):
        cod, out = _rodar('validar', _caso('r8_ansi'))
        self.assertIn(cod, (0, 1), out)

    def test_pools_acha_o_parceiro_da_mensagem(self):
        xml, _ = bpmn.gerar_com_pools(_carta('r8_pools'))
        raiz = ET.fromstring(xml.encode('utf-8'))
        elems = {e.get('id'): e for e in raiz.iter() if e.get('id')}
        pares = set()
        for m in raiz.iter():
            if m.tag.endswith('messageFlow'):
                pares.add((elems[m.get('sourceRef')].get('name'), elems[m.get('targetRef')].get('name')))
        self.assertIn(('Solicitar cotação', 'Fornecedor'), pares)
        self.assertIn(('Fornecedor', 'Cotação recebida'), pares)

    def test_lean_excecao_nao_vira_checklist(self):
        ops = analise.analisar(_carta('r8_bordas'))['oportunidades']
        self.assertFalse(any('Sistema fora' in o['texto'] and 'checklist' in o['texto'] for o in ops))

    def test_comparar_detalha_risco_e_aceites_no_documento(self):
        pasta = tempfile.mkdtemp()
        try:
            arq = os.path.join(pasta, 'carta.json')
            shutil.copy(os.path.join(RAIZ, 'exemplos', 'credito', 'carta.json'), arq)
            self.assertEqual(_rodar('aprovar', arq, '--por', 'Ana')[0], 0)
            d = _ler(arq)
            d['riscos'][0]['impacto'] = 'baixo'
            with open(arq, 'w', encoding='utf-8') as f:
                json.dump(d, f, ensure_ascii=False)
            _, out = _rodar('comparar', arq)
            self.assertIn('impacto', out)
            self.assertEqual(_rodar('aprovar', arq, '--por', 'Ana')[0], 0)
            self.assertEqual(_rodar('documentar', arq)[0], 0)
            import glob
            with open(glob.glob(os.path.join(pasta, 'saida', '*.md'))[0], encoding='utf-8') as f:
                self.assertIn('Aceites do dono', f.read())
        finally:
            shutil.rmtree(pasta, ignore_errors=True)

    def test_bordas_numeradas(self):
        texto = svg.desenhar(_carta('r5_r02_bordas'))
        self.assertIn('>1 ', texto)


class TestRodada10(unittest.TestCase):
    """Achados da 9ª revisão cega."""

    def test_lead_time_com_laco_nos_ramos_paralelos(self):
        # dois ramos de "2d + 50% de refazer": a média do mais longo é ~5,8 d úteis (simulação independente)
        esperado = analise.analisar(_carta('r9_par_loops'))['tempos']['lead_time_esperado'] / 480
        self.assertGreater(esperado, 5.5)
        self.assertLess(esperado, 6.1)

    def test_carga_do_subprocesso_vai_para_a_carta_filha(self):
        r = analise.analisar(_carta('r9_big'))
        c = _carta('r9_big')
        papeis = {c.nome_papel(p) for p, _, _ in r['carga']['por_papel']}
        self.assertIn('Fábrica', papeis)

    def test_avalanche_vira_um_erro_com_causa(self):
        d = _ler(_caso('r9_big'))
        for e in d['elementos']:
            for b in e.get('bordas') or []:
                if isinstance(b, dict) and b.get('nome') == 'Cliente pede alteração':
                    b['interrompe'] = False
        c = modelo.Carta(d, _caso('r9_big'))
        erros = [a for a in validacao.validar(c) if a.nivel == 'erro']
        self.assertLessEqual(len(erros), 5, [a.codigo for a in erros])

    def test_decisao_de_prazo_e_raci(self):
        d = _ler(_caso('r8_retrabalho60'))
        for e in d['elementos']:
            if e['id'] == 'd1':
                e['nome'] = 'Documentos chegaram em até 5 dias?'
            if e['id'] == 'a2':
                e['raci'] = {'A': ['com', 'cad'], 'R': ['cad']}
        c = modelo.Carta(d)
        cods = _codigos(c)
        self.assertIn('decisao_de_prazo', cods)
        self.assertIn('raci_dois_a', cods)
        self.assertIn('raci_r', cods)

    def test_tempo_por_extenso(self):
        self.assertEqual(minutos('cinquenta minutos'), 50)
        self.assertEqual(minutos('quarenta e cinco minutos'), 45)
        self.assertEqual(minutos('cem minutos'), 100)
        self.assertEqual(minutos("45'"), 45)
        self.assertEqual(minutos('meio expediente'), 240)
        self.assertEqual(analise.casos_por_mes('10k por mês'), 10000)

    def test_word_e_html_com_as_mesmas_partes_e_letra_minima(self):
        c = _carta('r9_big')
        lay = layout.calcular(c)
        cortes, retratos = svg.faixas_impressao(c, lay)
        self.assertEqual(len(cortes), len(retratos))
        for (ini, fim), em_pe in zip(cortes, retratos):
            t = svg.desenhar(c, lay, faixa=(ini, fim), parte=(1, 2))
            w = float(t.split('width="', 1)[1].split('"', 1)[0])
            h = float(t.split('height="', 1)[1].split('"', 1)[0])
            larg, alt = (6.5, 9.2) if em_pe else (9.9, 6.2)
            self.assertGreater(min(1.0, larg * 96 / w, alt * 96 / h), 0.65)

    def test_importa_camunda8_call_activity(self):
        carta, _ = importar(_caso('r7_import', 'camunda8.bpmn'))
        self.assertTrue(any(e.get('detalhe') for e in carta['elementos']))

    def test_tempo_editado_na_documentacao_vale(self):
        import re
        c = modelo.carregar(os.path.join(RAIZ, 'exemplos', 'credito', 'carta.json'))
        xml = bpmn.gerar(c)
        m = re.search(r'<bpmn:documentation>([^<]*Tempo: execução 20min[^<]*)</bpmn:documentation>', xml)
        self.assertIsNotNone(m)
        xml = xml.replace(m.group(1), 'Texto novo. ' + m.group(1).replace('execução 20min', 'execução 45min'), 1)
        pasta = tempfile.mkdtemp()
        try:
            arq = os.path.join(pasta, 'x.bpmn')
            with open(arq, 'w', encoding='utf-8') as f:
                f.write(xml)
            carta, _ = importar(arq)
            alvo = [e for e in carta['elementos'] if 'Texto novo' in str(e.get('descricao'))]
            self.assertTrue(alvo)
            self.assertEqual(alvo[0]['tempo']['execucao'], '45min')
            self.assertNotIn('Tempo:', alvo[0]['descricao'])
        finally:
            shutil.rmtree(pasta, ignore_errors=True)

    def test_exemplo_credito_sem_decisao_de_prazo(self):
        c = modelo.carregar(os.path.join(RAIZ, 'exemplos', 'credito', 'carta.json'))
        self.assertNotIn('decisao_de_prazo', _codigos(c))
        self.assertTrue(c.de_tipo('borda'))


class TestRodada11(unittest.TestCase):
    """Achados da 10ª revisão cega: simulação de fichas, desenho, volume, importação."""

    def test_simulacao_borda_que_encerra_no_paralelo(self):
        t = analise.analisar(_carta('r10_r01_encerra_borda'))['tempos']
        self.assertAlmostEqual(t['lead_time_esperado'] / 480, 10.5, delta=0.6)    # simulação independente: 10,5
        self.assertIsNotNone(t['percentis'])
        self.assertLessEqual(t['percentis']['p50'], t['percentis']['p80'])

    def test_simulacao_borda_de_prazo_no_ramo_com_laco(self):
        t = analise.analisar(_carta('r10_r02_borda_mc'))['tempos']
        self.assertAlmostEqual(t['lead_time_esperado'] / 480, 4.2, delta=0.25)    # simulação independente: 4,2

    def test_simulacao_igual_entre_versoes_da_mesma_carta(self):
        c = modelo.carregar(os.path.join(RAIZ, 'exemplos', 'credito', 'carta.json'))
        d = json.loads(json.dumps(c.dados))
        d['elementos'] = list(reversed(d['elementos']))            # mesma carta, outra ordem
        a = analise.analisar(c)['tempos']['lead_time_esperado']
        b = analise.analisar(modelo.Carta(d, c.caminho))['tempos']['lead_time_esperado']
        self.assertAlmostEqual(a, b, delta=a * 0.03)

    def test_atividade_sem_id_com_borda_nao_quebra(self):
        pasta = tempfile.mkdtemp()
        try:
            shutil.copy(_caso('r10_r17_crash_borda_sem_id'), pasta)
            for cmd in ('validar', 'desenhar', 'documentar'):
                cod, out = _rodar(cmd, os.path.join(pasta, 'carta.json'))
                self.assertIn(cod, (0, 1), f'{cmd}: {out}')
                self.assertNotIn('erro interno', out)
            self.assertIn('sem_id', _codigos(_carta('r10_r17_crash_borda_sem_id')))
        finally:
            shutil.rmtree(pasta, ignore_errors=True)

    def test_volume_ano_e_reais(self):
        f = analise.casos_por_mes
        self.assertEqual(f('Em 2025 foram 14.400 requisições no ano'), 1200)
        self.assertEqual(f('20 mil reais por mês em 50 requisições'), 50)
        self.assertEqual(f('100 por semana'), 400)

    def test_tempos_iso_e_milhar(self):
        self.assertEqual(minutos('1.000 min'), 1000)
        self.assertIsNotNone(minutos('PT2H'))
        self.assertIsNotNone(minutos('P3D'))

    def test_desenho_sem_t_e_sem_rotulo_cortado(self):
        sys.path.insert(0, os.path.join(RAIZ, 'ferramentas'))
        import estresse
        import juncoes
        com_t = 0
        for semente in range(40):
            c = modelo.Carta(estresse.gerar(semente))
            if any(a.nivel == 'erro' for a in validacao.validar(c)):
                continue
            com_t += bool(juncoes.juncoes(c, layout.calcular(c)))
        self.assertLessEqual(com_t, 2)
        for nome in ('compras', 'credito'):
            c = modelo.carregar(os.path.join(RAIZ, 'exemplos', nome, 'carta.json'))
            lay = layout.calcular(c)
            for f in c.fluxos:
                if f['id'] in lay.rotulos and (f['rotulo'] or f['percentual'] is not None):
                    caixa = layout._caixa_rotulo(c, f, lay.rotulos[f['id']])
                    for g in c.fluxos:
                        if g['id'] != f['id'] and g['id'] in lay.arestas:
                            pts = lay.arestas[g['id']]
                            self.assertFalse(any(layout._corta(caixa, a, b) for a, b in zip(pts, pts[1:])),
                                             f'{nome}: rótulo de {f["id"]} cortado por {g["id"]}')

    def test_parte_da_faixa_nao_sai_por_cima(self):
        import re
        c = modelo.carregar(os.path.join(RAIZ, 'exemplos', 'credito', 'carta.json'))
        lay = layout.calcular(c)
        cortes, _ = svg.faixas_impressao(c, lay)
        for i, f in enumerate(cortes):
            t = svg.desenhar(c, lay, faixa=f, parte=(i + 1, len(cortes)))
            topo = min(float(y) for y in re.findall(r'<rect x="[\d.]+" y="([\d.]+)" width="[\d.]+" height="[\d.]+" '
                                                    r'fill="#(?:f|e)', t))
            caixas = [float(y) for y in re.findall(r'<rect x="[\d.]+" y="([\d.]+)" width="130" height="70"', t)]
            self.assertTrue(all(y >= topo - 1 for y in caixas), f'parte {i + 1}')

    def test_tobe_traz_comparacao_com_as_is(self):
        pasta = tempfile.mkdtemp()
        try:
            arq = os.path.join(pasta, 'carta.json')
            shutil.copy(os.path.join(RAIZ, 'exemplos', 'compras', 'carta.json'), arq)
            self.assertEqual(_rodar('tobe', arq)[0], 0)
            self.assertEqual(_rodar('documentar', os.path.join(pasta, 'carta-tobe.json'))[0], 0)
            import glob
            with open([g for g in glob.glob(os.path.join(pasta, 'saida', '*.md')) if 'to-be' in g][0],
                      encoding='utf-8') as f:
                self.assertIn('AS-IS x TO-BE', f.read())
        finally:
            shutil.rmtree(pasta, ignore_errors=True)

    def test_importa_pool_sem_raias_e_nome_do_processo(self):
        carta, avisos = importar(_caso('r10_import', 'camunda2pools.bpmn'))
        self.assertTrue(all(e.get('papel') for e in carta['elementos']
                            if e.get('tipo', 'atividade') == 'atividade'))
        self.assertTrue(any('não tem raias' in a for a in avisos))
        sig, _ = importar(_caso('r10_import', 'signavio.bpmn'))
        self.assertTrue(any(' / ' in p['nome'] for p in sig['papeis']))

    def test_conferencias_em_cadeia_viram_um_item(self):
        ops = analise.analisar(_carta('r10_r16_big70'))['oportunidades']
        self.assertLessEqual(sum(1 for o in ops if o['tipo'] == 'aprovacao_em_serie'), 2)


class TestRodada11b(unittest.TestCase):
    """Fuzz da 11ª revisão: carta com fichas que se multiplicam deixava o analisar em 25 s."""

    def test_simulacao_desiste_cedo_em_fluxo_que_nao_fecha(self):
        import time
        c = _carta('r11_lento')
        t0 = time.monotonic()
        analise.analisar(c)
        self.assertLess(time.monotonic() - t0, 6)


class TestRodada12(unittest.TestCase):
    """Achados da 11ª revisão cega."""

    def test_varios_inicios_dividem_os_casos(self):
        r = analise.analisar(_carta('r11_simM2'))
        self.assertAlmostEqual(r['tempos']['lead_time_esperado'] / 60, 7, delta=0.5)
        gestor = {p: h for p, h, _ in r['carga']['por_papel']}
        self.assertTrue(any(abs(h - 553) < 40 for h in gestor.values()), gestor)

    def test_ou_com_ramo_que_nao_volta(self):
        r = analise.analisar(_carta('r11_simJ'))
        self.assertGreater(r['visitas']['w'], 0.85)          # antes: 0,50

    def test_carga_do_subprocesso_igual_a_da_filha(self):
        pai = analise.analisar(_carta('r11_pai'))['carga']['horas_mes']
        filha = analise.analisar(modelo.carregar(_caso('r11_pai', 'filho/carta.json')))['carga']['horas_mes']
        self.assertAlmostEqual(pai, filha, delta=filha * 0.05)

    def test_fluxo_com_erro_avisa_antes_dos_numeros(self):
        r = analise.analisar(_carta('r11_simM'))
        self.assertTrue(any('erro' in a for a in r['alertas']))
        self.assertIsNone(r['tempos']['percentis'])

    def test_trabalho_cortado_pelo_prazo_conta_so_a_parte_feita(self):
        cg = analise.analisar(_carta('r11_simB'))['carga']
        horas = {p: h for p, h, _ in cg['por_papel']}
        self.assertLess(max(horas.values()), 16500)          # antes: 17.709 (atividade inteira)

    def test_alertas_de_prazo_e_carga(self):
        alertas = ' '.join(analise.analisar(_carta('r11_plaus'))['alertas'])
        self.assertIn('prazo', alertas)
        self.assertIn('pessoas', alertas)

    def test_faixa_de_tempo_da_percentis_diferentes(self):
        d = _ler(_caso('r8_retrabalho60'))
        for e in d['elementos']:
            if e['id'] == 'a2':
                e['tempo'] = {'execucao': '30min', 'espera': '1 a 5 dias'}
        t = analise.analisar(modelo.Carta(d))['tempos']
        self.assertLess(t['percentis']['p50'], t['percentis']['p90'])

    def test_mapa_grande_sem_seta_por_dentro_de_caixa(self):
        sys.path.insert(0, os.path.join(RAIZ, 'ferramentas'))
        import geometria
        r = geometria.check(_caso('r11_big11'))
        self.assertEqual(len(r['edge_over_node']), 0)

    def test_risco_tempo_e_volume_em_portugues(self):
        from carta.gestao import _nota
        self.assertEqual(_nota('70%'), 4)
        self.assertEqual(_nota(0.5), 3)
        self.assertEqual(_nota('3 - média'), 3)
        self.assertEqual(_nota('remota'), 1)
        self.assertEqual(_nota('médio-alto'), 4)
        self.assertEqual(minutos('uma hora e quinze'), 75)
        self.assertEqual(minutos('10 d.u.'), 4800)
        self.assertEqual(minutos('+/- 2h'), 120)
        self.assertIsNotNone(minutos('um trimestre'))
        self.assertEqual(analise.casos_por_mes('30 por dia corrido'), 900)

    def test_importar_com_base_traz_participantes(self):
        pasta = tempfile.mkdtemp()
        try:
            base = os.path.join(RAIZ, 'exemplos', 'credito', 'carta.json')
            xml = bpmn.gerar(modelo.carregar(base))
            arq = os.path.join(pasta, 'x.bpmn')
            with open(arq, 'w', encoding='utf-8') as f:
                f.write(xml)
            destino = os.path.join(pasta, 'nova.json')
            self.assertEqual(_rodar('importar', arq, '-o', destino, '--base', base)[0], 0)
            self.assertEqual(_ler(destino).get('participantes'), _ler(base).get('participantes'))
        finally:
            shutil.rmtree(pasta, ignore_errors=True)


class TestRodada13(unittest.TestCase):
    """Achados da 12ª revisão cega."""

    def test_juncao_ou_espera_so_quem_ainda_pode_chegar(self):
        t = analise.analisar(_carta('r12_r_ou_corrida'))['tempos']
        self.assertIsNotNone(t['percentis'])

    def test_travamento_que_a_prova_nao_alcanca_vira_alerta(self):
        r = analise.analisar(_carta('r12_r_g001_trava_nao_detectada'))
        self.assertTrue(any('não terminam' in a for a in r['alertas']))

    def test_simulacao_nao_depende_do_relogio(self):
        from carta import simulacao
        c = _carta('r12_cx')
        a = simulacao.simular(c)
        b = simulacao.simular(c)
        self.assertEqual(a['media'], b['media'])
        self.assertEqual(a['casos'], b['casos'])

    def test_subprocesso_usa_o_tempo_da_carta_filha(self):
        c = _carta('r12_r_detalhe')
        from carta.validacao import tempos_do_detalhe
        sub = [e for e in c.de_tipo('subprocesso') if e['bruto'].get('detalhe')][0]
        _, lead_filha = tempos_do_detalhe(c, sub)
        t = analise.analisar(c)['tempos']['lead_time_esperado']
        self.assertGreaterEqual(t, lead_filha - 1)

    def test_timer_volta_igual_do_bpmn(self):
        from carta.importar import _iso_para_texto
        from saidas.bpmn import _iso
        for texto in ('4h', '2d', '5d', '10dc', '48hc', '30min'):
            m = minutos(texto)
            de_volta = minutos(_iso_para_texto(_iso(m, texto)))
            self.assertAlmostEqual(de_volta, m, delta=max(10, m * 0.01), msg=texto)
        self.assertEqual(minutos('4 horas corridas'), 240)          # prazo curto: hora a hora no expediente

    def test_volta_do_bizagi_com_base(self):
        pasta = tempfile.mkdtemp()
        try:
            destino = os.path.join(pasta, 'b.json')
            cod, out = _rodar('importar', _caso('r12_rt', 'editado_bizagi.bpmn'), '-o', destino,
                              '--base', _caso('r12_rt'))
            self.assertEqual(cod, 0, out)
            d = _ler(destino)
            self.assertTrue(any(e.get('tempo') for e in d['elementos']))
            self.assertFalse(any(str(e.get('descricao') or '').startswith(('Sistema:', 'Tempo:'))
                                 for e in d['elementos']))
            self.assertTrue(any(p.get('tipo') == 'externo' for p in d['papeis']))
        finally:
            shutil.rmtree(pasta, ignore_errors=True)

    def test_espera_de_evento_entra_no_lean(self):
        ops = analise.analisar(_carta('r12_cx'))['oportunidades']
        self.assertIn('Aceite recebido', ops[0]['texto'])

    def test_alerta_so_para_erro_de_fluxo(self):
        d = _ler(os.path.join(RAIZ, 'exemplos', 'compras', 'carta.json'))
        d['riscos'][0]['elementos'] = ['nao_existe']
        r = analise.analisar(modelo.Carta(d))
        self.assertFalse(any('erro' in a and 'não valem' in a for a in r['alertas']))
        d['melhorias'][0]['prazo'] = '31/02/2027'
        self.assertIn('data_invalida', _codigos(modelo.Carta(d)))

    def test_volume_parte_pico_e_meio_milhao(self):
        f = analise.casos_por_mes
        self.assertEqual(f('10% dos 500 pedidos por mês'), 50)
        self.assertEqual(f('pico de 300, normal 100 por mês'), 100)
        self.assertIsNotNone(f('meio milhão por ano'))


if __name__ == '__main__':
    unittest.main()
