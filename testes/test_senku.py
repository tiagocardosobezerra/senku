"""
Testes do Senku sobre o exemplo fictício de compras e cartas pequenas montadas aqui.

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
from contextlib import redirect_stdout

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, RAIZ)

import senku  # noqa: E402
from carta import analise, aprovacao, lacunas, layout, modelo, validacao  # noqa: E402
from carta.importar import importar  # noqa: E402
from carta.util import ErroDeUso, minutos  # noqa: E402
from saidas import bpmn, documento, drawio, mermaid, svg  # noqa: E402

EXEMPLO = os.path.join(RAIZ, 'exemplos', 'compras', 'carta.json')


def _exemplo():
    with open(EXEMPLO, encoding='utf-8') as f:
        return json.load(f)


def _mini(**extra):
    d = {'processo': {'nome': 'Mini'},
         'papeis': [{'id': 'a', 'nome': 'Analista'}, {'id': 'g', 'nome': 'Gestor'}],
         'elementos': [
             {'id': 'i', 'tipo': 'inicio', 'nome': 'Pedido recebido', 'papel': 'a', 'segue': 'x1'},
             {'id': 'x1', 'nome': 'Analisar pedido', 'papel': 'a', 'segue': 'd'},
             {'id': 'd', 'tipo': 'decisao', 'nome': 'Pedido aprovado?', 'papel': 'a',
              'segue': [{'para': 'x2', 'rotulo': 'Sim'}, {'para': 'f2', 'rotulo': 'Não'}]},
             {'id': 'x2', 'nome': 'Emitir pedido', 'papel': 'g', 'segue': 'f1'},
             {'id': 'f1', 'tipo': 'fim', 'nome': 'Pedido emitido'},
             {'id': 'f2', 'tipo': 'fim', 'nome': 'Pedido recusado'}]}
    d.update(extra)
    return d


def _codigos(dados, nivel=None):
    c = modelo.Carta(dados)
    return {a.codigo for a in validacao.validar(c) if nivel is None or a.nivel == nivel}


def _el(dados, eid):
    return next(e for e in dados['elementos'] if e['id'] == eid)


def _rodar(*args):
    buf = io.StringIO()
    with redirect_stdout(buf):
        try:
            cod = senku.main(list(args))
        except ErroDeUso as e:
            print(f'✗ {e}')
            cod = 1
    return cod, buf.getvalue()


class TestTempos(unittest.TestCase):
    def test_unidades(self):
        self.assertEqual(minutos('15min'), 15)
        self.assertEqual(minutos('2h'), 120)
        self.assertEqual(minutos('2h30'), 150)
        self.assertEqual(minutos('1,5d'), 720)
        self.assertEqual(minutos('3 dias úteis'), 1440)
        self.assertAlmostEqual(minutos('1dc'), 480 * 5 / 7)
        self.assertEqual(minutos('2 a 4h'), 180)
        self.assertEqual(minutos(45), 45)
        self.assertEqual(minutos('0'), 0)
        self.assertIsNone(minutos('rapidinho'))
        self.assertIsNone(minutos(''))

    def test_tempo_ilegivel_vira_erro(self):
        d = _mini()
        _el(d, 'x1')['tempo'] = {'execucao': 'rapidinho'}
        self.assertIn('tempo_ilegivel', _codigos(d, 'erro'))


class TestModelo(unittest.TestCase):
    def test_papel_por_nome_e_sinonimo_de_tipo(self):
        d = _mini()
        _el(d, 'x1')['papel'] = 'analista'
        _el(d, 'd')['tipo'] = 'gateway'
        c = modelo.Carta(d)
        self.assertEqual(c.elementos['x1']['papel'], 'a')
        self.assertEqual(c.elementos['d']['tipo'], 'decisao')

    def test_fluxos_no_topo(self):
        d = _mini()
        for e in d['elementos']:
            e.pop('segue', None)
        d['fluxos'] = [{'de': 'i', 'para': 'x1'}, {'de': 'x1', 'para': 'd'}, {'de': 'd', 'para': 'x2', 'rotulo': 'Sim'},
                       {'de': 'd', 'para': 'f2', 'rotulo': 'Não'}, {'de': 'x2', 'para': 'f1'}]
        self.assertEqual(_codigos(d, 'erro'), set())

    def test_exemplo_sem_erro_nem_aviso(self):
        c = modelo.carregar(EXEMPLO)
        achados = validacao.validar(c)
        self.assertEqual([a for a in achados if a.nivel in ('erro', 'aviso')], [])

    def test_json_quebrado_diz_a_linha(self):
        d = tempfile.mkdtemp()
        try:
            arq = os.path.join(d, 'carta.json')
            with open(arq, 'w', encoding='utf-8') as f:
                f.write('{\n "processo": {"nome": "x"},\n "elementos": [,]\n}')
            with self.assertRaises(ErroDeUso) as ctx:
                modelo.carregar(arq)
            self.assertIn('linha 3', str(ctx.exception))
        finally:
            shutil.rmtree(d)


class TestValidacao(unittest.TestCase):
    def test_mini_limpo(self):
        self.assertEqual(_codigos(_mini(), 'erro'), set())
        self.assertEqual(_codigos(_mini(), 'aviso'), set())

    def test_beco_sem_saida(self):
        d = _mini()
        del _el(d, 'x2')['segue']
        cods = _codigos(d, 'erro')
        self.assertIn('beco_sem_saida', cods)
        self.assertIn('sem_entrada', cods)       # f1 ficou sem ninguém chegando

    def test_destino_inexistente(self):
        d = _mini()
        _el(d, 'x2')['segue'] = 'nao_existe'
        self.assertIn('destino_inexistente', _codigos(d, 'erro'))

    def test_sem_inicio_e_sem_fim(self):
        d = _mini()
        d['elementos'] = [e for e in d['elementos'] if e.get('tipo') != 'inicio']
        self.assertIn('sem_inicio', _codigos(d, 'erro'))
        d = _mini()
        d['elementos'] = [e for e in d['elementos'] if e.get('tipo') != 'fim']
        _el(d, 'x2').pop('segue')
        _el(d, 'd')['segue'] = [{'para': 'x2', 'rotulo': 'Sim'}, {'para': 'x1', 'rotulo': 'Não'}]
        self.assertIn('sem_fim', _codigos(d, 'erro'))

    def test_decisao_sem_rotulo_e_rotulo_repetido(self):
        d = _mini()
        _el(d, 'd')['segue'] = ['x2', 'f2']
        self.assertIn('saida_sem_rotulo', _codigos(d, 'erro'))
        d = _mini()
        _el(d, 'd')['segue'] = [{'para': 'x2', 'rotulo': 'Sim'}, {'para': 'f2', 'rotulo': 'sim'}]
        self.assertIn('rotulo_repetido', _codigos(d, 'erro'))

    def test_decisao_de_outro_papel_sem_analise(self):
        d = _mini()
        _el(d, 'd')['papel'] = 'g'
        self.assertIn('decisao_sem_trabalho', _codigos(d, 'aviso'))

    def test_decisao_sem_pergunta(self):
        d = _mini()
        _el(d, 'd')['nome'] = 'Aprovação'
        self.assertIn('decisao_sem_interrogacao', _codigos(d, 'aviso'))

    def test_porta_inutil(self):
        d = _mini()
        _el(d, 'd')['segue'] = [{'para': 'x2', 'rotulo': 'Sim'}]
        d['elementos'] = [e for e in d['elementos'] if e['id'] != 'f2']
        self.assertIn('porta_inutil', _codigos(d, 'erro'))

    def test_nome_sem_verbo_com_sugestao(self):
        d = _mini()
        _el(d, 'x1')['nome'] = 'Análise do pedido'
        c = modelo.Carta(d)
        av = [a for a in validacao.validar(c) if a.codigo == 'nome_sem_verbo']
        self.assertEqual(len(av), 1)
        self.assertIn('Analisar ...', av[0].texto)

    def test_verbos_reconhecidos(self):
        for nome in ('Aprovar requisição', 'Compor kit', 'Emitir NF', 'Conferir material', 'Ler contrato',
                     'Repor estoque'):
            self.assertTrue(validacao.parece_verbo(validacao.primeira_palavra(nome)), nome)
        for nome in ('Fornecedor escolhido', 'Lugar de entrega', 'Valor do pedido', 'Requisição'):
            self.assertFalse(validacao.parece_verbo(validacao.primeira_palavra(nome)), nome)

    def test_duas_atividades(self):
        d = _mini()
        _el(d, 'x1')['nome'] = 'Conferir e aprovar pedido'
        self.assertIn('duas_atividades', _codigos(d, 'aviso'))

    def test_divisao_implicita(self):
        d = _mini()
        _el(d, 'x1')['segue'] = ['d', 'x2']
        self.assertIn('divisao_implicita', _codigos(d, 'aviso'))

    def test_papel_sistema_regra_inexistentes(self):
        d = _mini()
        _el(d, 'x1').update({'papel': 'diretor', 'sistema': 'sap', 'regras': ['R9']})
        d['sistemas'] = [{'id': 'erp', 'nome': 'ERP'}]           # com lista de sistemas, "sap" fora dela é erro
        cods = _codigos(d, 'erro')
        self.assertTrue({'papel_inexistente', 'sistema_inexistente', 'regra_inexistente'} <= cods, cods)

    def test_fins_sem_estado(self):
        d = _mini()
        _el(d, 'f1')['nome'] = 'Fim'
        self.assertIn('fins_sem_estado', _codigos(d, 'aviso'))

    def test_laco_sem_saida(self):
        d = _mini()
        _el(d, 'd')['segue'] = [{'para': 'x2', 'rotulo': 'Sim'}, {'para': 'x1', 'rotulo': 'Não'}]
        _el(d, 'x2')['segue'] = 'x1'                        # sem saída para nenhum fim
        cods = _codigos(d, 'erro')
        self.assertIn('nunca_termina', cods)

    def test_inclusivo_e_mapa_grande(self):
        d = _mini()
        _el(d, 'd')['tipo'] = 'inclusivo'
        self.assertIn('inclusivo', _codigos(d, 'aviso'))
        d = _mini()
        extra = [{'id': f'z{i}', 'nome': f'Executar passo {i}', 'papel': 'a', 'segue': f'z{i + 1}'} for i in range(50)]
        extra[-1]['segue'] = 'x1'
        _el(d, 'i')['segue'] = 'z0'
        d['elementos'] += extra
        self.assertIn('mapa_grande', _codigos(d, 'aviso'))

    def test_paralelo_que_termina_em_dois_fins_e_valido(self):
        d = _mini()
        _el(d, 'x2')['segue'] = 'p'
        d['elementos'] += [{'id': 'p', 'tipo': 'paralelo', 'papel': 'g', 'segue': ['f1', 'x3']},
                           {'id': 'x3', 'nome': 'Avisar cliente', 'papel': 'g', 'segue': 'f1'}]
        self.assertEqual(_codigos(d, 'erro'), set())        # cada ramo consome a sua ficha num fim

    def test_referencia_de_dor_e_melhoria(self):
        d = _mini(dores=[{'id': 'D1', 'elementos': ['zz']}], melhorias=[{'id': 'M1', 'resolve': ['D9']}])
        cods = _codigos(d, 'erro')
        self.assertIn('referencia_inexistente', cods)
        self.assertIn('dor_inexistente', cods)


class TestLacunas(unittest.TestCase):
    def test_carta_vazia_pergunta_inicio_e_objetivo(self):
        c = modelo.Carta(modelo.esqueleto('Novo'))
        qs = lacunas.levantar(c)
        self.assertEqual(qs[0].prioridade, 1)
        self.assertTrue(any(q.onde == 'processo.objetivo' for q in qs))
        self.assertTrue(any(q.onde == 'processo.dono' for q in qs))

    def test_decisao_com_um_caminho(self):
        d = _mini()
        _el(d, 'd')['segue'] = [{'para': 'x2', 'rotulo': 'Sim'}]
        qs = lacunas.levantar(modelo.Carta(d))
        self.assertTrue(any(q.elemento == 'd' and 'resposta é outra' in q.texto for q in qs))

    def test_quem_faz_e_retrabalho(self):
        d = _mini()
        del _el(d, 'x2')['papel']
        _el(d, 'd')['segue'] = [{'para': 'x2', 'rotulo': 'Sim'}, {'para': 'x1', 'rotulo': 'Não'}]
        qs = lacunas.levantar(modelo.Carta(d))
        self.assertTrue(any(q.elemento == 'x2' and q.texto.startswith('Quem faz') for q in qs))
        self.assertTrue(any('de cada 100' in q.texto.lower() for q in qs))

    def test_ordenadas_por_prioridade(self):
        qs = lacunas.levantar(modelo.Carta(_mini()))
        self.assertEqual([q.prioridade for q in qs], sorted(q.prioridade for q in qs))


class TestLayout(unittest.TestCase):
    def test_sem_sobreposicao_e_dentro_da_raia(self):
        c = modelo.carregar(EXEMPLO)
        lay = layout.calcular(c)
        nos = list(lay.nos.values())
        for i, a in enumerate(nos):
            for b in nos[i + 1:]:
                sobrepoe = not (a['x'] + a['w'] <= b['x'] or b['x'] + b['w'] <= a['x'] or
                                a['y'] + a['h'] <= b['y'] or b['y'] + b['h'] <= a['y'])
                self.assertFalse(sobrepoe, (a, b))
        raias = {r['id']: r for r in lay.raias}
        for n in nos:
            r = raias[n['raia']]
            self.assertTrue(r['y'] <= n['y'] and n['y'] + n['h'] <= r['y'] + r['h'], n)

    def test_fluxo_para_frente_vai_para_a_direita(self):
        c = modelo.carregar(EXEMPLO)
        lay = layout.calcular(c)
        for f in c.fluxos:
            if f['id'] not in lay.volta:
                self.assertLess(lay.nos[f['de']]['coluna'], lay.nos[f['para']]['coluna'], f)

    def test_numeracao(self):
        c = modelo.carregar(EXEMPLO)
        nums = layout.numerar(c, layout.calcular(c))
        self.assertEqual(nums['a1'], '01')
        self.assertEqual(len(set(nums.values())), len(c.atividades()))


class TestAnalise(unittest.TestCase):
    def test_exemplo(self):
        c = modelo.carregar(EXEMPLO)
        r = analise.analisar(c)
        self.assertEqual(r['caminho_feliz'][0], 'inicio')
        self.assertEqual(r['caminho_feliz'][-1], 'fim')
        self.assertNotIn('a1b', r['caminho_feliz'])          # retrabalho fica fora
        self.assertIn('a9', r['caminho_feliz'] + r['paralelos'])
        self.assertEqual(len(r['retrabalho']), 2)
        t = r['tempos']
        self.assertGreater(t['lead_time'], t['execucao'] - 1)
        tipos = {o['tipo'] for o in r['oportunidades']}
        # o vai e volta de compras (Solicitante -> Gestor -> "Corrigir requisição") é o próprio laço de correção:
        # aparece uma vez só, como retrabalho
        self.assertTrue({'retrabalho', 'espera', 'desperdicio'} <= tipos, tipos)
        self.assertNotIn('vai_e_volta', tipos)

    def test_paralelo_conta_o_ramo_mais_longo(self):
        d = _mini()
        _el(d, 'x2')['segue'] = 'p1'
        d['elementos'] += [
            {'id': 'p1', 'tipo': 'paralelo', 'papel': 'g', 'segue': ['r1', 'r2']},
            {'id': 'r1', 'nome': 'Separar material', 'papel': 'g', 'tempo': {'execucao': '1h'}, 'segue': 'p2'},
            {'id': 'r2', 'nome': 'Emitir nota', 'papel': 'g', 'tempo': {'execucao': '3h'}, 'segue': 'p2'},
            {'id': 'p2', 'tipo': 'paralelo', 'papel': 'g', 'segue': 'f1'}]
        r = analise.analisar(modelo.Carta(d))
        self.assertEqual(r['tempos']['lead_time'], 180)
        self.assertEqual(r['tempos']['execucao'], 240)

    def test_digitacao_dupla(self):
        d = _mini(sistemas=[{'id': 's1', 'nome': 'ERP'}, {'id': 's2', 'nome': 'Planilha'}])
        _el(d, 'x1').update({'nome': 'Registrar pedido', 'sistema': 's1'})
        _el(d, 'x2').update({'nome': 'Lançar pedido', 'sistema': 's2'})
        r = analise.analisar(modelo.Carta(d))
        self.assertIn('digitacao_dupla', {o['tipo'] for o in r['oportunidades']})


class TestSaidas(unittest.TestCase):
    def setUp(self):
        self.c = modelo.carregar(EXEMPLO)

    def test_bpmn_valido_e_completo(self):
        xml = bpmn.gerar(self.c)
        raiz = ET.fromstring(xml.encode('utf-8'))
        ns = {'b': 'http://www.omg.org/spec/BPMN/20100524/MODEL', 'di': 'http://www.omg.org/spec/BPMN/20100524/DI'}
        ids = {e.get('id') for e in raiz.iter() if e.get('id')}
        for f in raiz.iter('{%s}sequenceFlow' % ns['b']):
            self.assertIn(f.get('sourceRef'), ids)
            self.assertIn(f.get('targetRef'), ids)
        formas = {s.get('bpmnElement') for s in raiz.iter('{%s}BPMNShape' % ns['di'])}
        arestas = {s.get('bpmnElement') for s in raiz.iter('{%s}BPMNEdge' % ns['di'])}
        for eid in self.c.elementos:
            self.assertIn(bpmn.xml_id(eid), formas)
        self.assertEqual(len(arestas), len(self.c.fluxos))
        self.assertEqual(len(list(raiz.iter('{%s}lane' % ns['b']))), len(self.c.raias()))
        self.assertEqual(len(list(raiz.iter('{%s}parallelGateway' % ns['b']))), 2)

    def test_bpmn_id_seguro(self):
        self.assertEqual(bpmn.xml_id('1 passo'), 'Id_1_passo')
        self.assertEqual(bpmn.xml_id('a1'), 'a1')

    def test_ida_e_volta_pelo_bpmn(self):
        d = tempfile.mkdtemp()
        try:
            arq = os.path.join(d, 'x.bpmn')
            with open(arq, 'w', encoding='utf-8') as f:
                f.write(bpmn.gerar(self.c))
            carta, avisos = importar(arq)
            c2 = modelo.Carta(carta)
            self.assertEqual(len(c2.elementos), len(self.c.elementos))
            self.assertEqual(len(c2.fluxos), len(self.c.fluxos))
            self.assertEqual([a for a in validacao.validar(c2) if a.nivel == 'erro'], [])
            self.assertEqual(sorted(e['nome'] for e in c2.elementos.values()),
                             sorted(e['nome'] for e in self.c.elementos.values()))
        finally:
            shutil.rmtree(d)

    def test_importar_recusa_o_que_nao_e_bpmn(self):
        d = tempfile.mkdtemp()
        try:
            arq = os.path.join(d, 'x.bpmn')
            with open(arq, 'w', encoding='utf-8') as f:
                f.write('<html></html>')
            with self.assertRaises(ErroDeUso):
                importar(arq)
        finally:
            shutil.rmtree(d)

    def test_drawio_e_svg_sao_xml(self):
        raiz = ET.fromstring(drawio.gerar(self.c).encode('utf-8'))
        celulas = list(raiz.iter('mxCell'))
        self.assertEqual(sum(1 for x in celulas if x.get('edge') == '1'), len(self.c.fluxos))
        ET.fromstring(svg.desenhar(self.c, cores_valor=True).encode('utf-8'))

    def test_mermaid(self):
        m = mermaid.gerar(self.c)
        self.assertTrue(m.startswith('flowchart LR'))
        self.assertIn('d1 -->|"Sim (85%)"| a3', m)
        self.assertIn('-.->', m)                          # retrabalho tracejado
        self.assertEqual(m.count('subgraph'), len(self.c.raias()))

    def test_texto_com_caractere_especial(self):
        d = _mini()
        _el(d, 'x1')['nome'] = 'Analisar <pedido> & "anexo"'
        c = modelo.Carta(d)
        ET.fromstring(bpmn.gerar(c).encode('utf-8'))
        ET.fromstring(drawio.gerar(c).encode('utf-8'))
        ET.fromstring(svg.desenhar(c).encode('utf-8'))
        self.assertNotIn('<pedido>', mermaid.gerar(c))

    def test_documento(self):
        d = documento.montar(self.c)
        h = documento.html_documento(self.c, d)
        for s in ('Ficha do processo', 'SIPOC', 'Matriz RACI', 'Indicadores', 'Riscos e controles', '<svg'):
            self.assertIn(s, h)
        self.assertIn('RASCUNHO', h)
        md = documento.markdown_documento(self.c, d)
        self.assertIn('```mermaid', md)
        csv = documento.csv_atividades(self.c, d)
        self.assertEqual(len(csv.strip().splitlines()), len(self.c.atividades()) + 1)
        self.assertTrue(csv.startswith('Nº;Id;Atividade'))


class TestAprovacaoECli(unittest.TestCase):
    def setUp(self):
        self.d = tempfile.mkdtemp(prefix='senku')
        self.carta = os.path.join(self.d, 'carta.json')
        shutil.copy(EXEMPLO, self.carta)

    def tearDown(self):
        shutil.rmtree(self.d, ignore_errors=True)

    def test_aprovar_e_mudar(self):
        cod, out = _rodar('aprovar', self.carta, '--por', 'Dono (Gerente)')
        self.assertEqual(cod, 0, out)
        c = modelo.carregar(self.carta)
        self.assertEqual(aprovacao.situacao_aprovacao(c)[0], 'aprovada')
        dados = _exemplo()
        _el(dados, 'a4')['papel'] = 'gestor'
        with open(self.carta, 'w', encoding='utf-8') as f:
            json.dump(dados, f, ensure_ascii=False)
        c = modelo.carregar(self.carta)
        self.assertEqual(aprovacao.situacao_aprovacao(c)[0], 'mudou')
        cod, out = _rodar('comparar', self.carta)
        self.assertIn('responsável Comprador -> Gestor da área', out)

    def test_aprovar_recusa_carta_com_erro(self):
        dados = _exemplo()
        _el(dados, 'a6')['segue'] = 'nada'
        with open(self.carta, 'w', encoding='utf-8') as f:
            json.dump(dados, f, ensure_ascii=False)
        cod, out = _rodar('aprovar', self.carta, '--por', 'X')
        self.assertEqual(cod, 1)
        self.assertIn('erro', out)

    def test_documentar_gera_tudo(self):
        cod, out = _rodar('documentar', self.carta, '-o', os.path.join(self.d, 'saida'))
        self.assertEqual(cod, 0, out)
        nomes = os.listdir(os.path.join(self.d, 'saida'))
        for ext in ('.html', '.md', '-atividades.csv', '.svg', '.bpmn', '.drawio', '.mmd'):
            self.assertTrue(any(n.endswith(ext) for n in nomes), (ext, nomes))

    def test_tobe_e_comparar(self):
        cod, out = _rodar('tobe', self.carta)
        self.assertEqual(cod, 0, out)
        tobe = os.path.join(self.d, 'carta-tobe.json')
        with open(tobe, encoding='utf-8') as f:
            dados = json.load(f)
        self.assertEqual(dados['processo']['cenario'], 'to-be')
        # TO-BE: a cotação entra direto no ERP (sai o "Lançar cotação no ERP")
        dados['elementos'] = [e for e in dados['elementos'] if e['id'] != 'a5']
        _el(dados, 'a4')['segue'] = 'a6'
        with open(tobe, 'w', encoding='utf-8') as f:
            json.dump(dados, f, ensure_ascii=False)
        cod, out = _rodar('comparar', self.carta, '--contra', tobe)
        self.assertIn('atividade removida: "Lançar cotação no ERP"', out)
        self.assertRegex(out, r'atividades\s+14\s+13\s+-1')

    def test_novo_situacao_validar(self):
        pasta = os.path.join(self.d, 'novo')
        cod, _ = _rodar('novo', pasta, '--processo', 'Admissão')
        self.assertEqual(cod, 0)
        cod, out = _rodar('situacao', pasta)
        self.assertIn('Etapa: entrevista', out)
        cod, out = _rodar('validar', os.path.join(pasta, 'carta.json'))
        self.assertEqual(cod, 1)
        cod, out = _rodar('novo', pasta, '--processo', 'Admissão')
        self.assertEqual(cod, 1)                          # não sobrescreve

    def test_lacunas_json(self):
        cod, out = _rodar('lacunas', self.carta, '--json')
        self.assertEqual(cod, 0)
        self.assertIsInstance(json.loads(out), list)

    def test_entrevista(self):
        cod, out = _rodar('entrevista', 'decisoes')
        self.assertEqual(cod, 0)
        self.assertIn('De cada 100 casos', out)
        cod, _ = _rodar('entrevista', 'xyz')
        self.assertEqual(cod, 1)


if __name__ == '__main__':
    unittest.main()
