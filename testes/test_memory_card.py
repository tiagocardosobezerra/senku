"""Memory Card: salvar o processo aprovado num cartão local (git sem remoto), sem rede nem GitHub."""

import io
import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from contextlib import redirect_stderr, redirect_stdout

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, RAIZ)

import senku  # noqa: E402
from carta import memory_card as mc  # noqa: E402

EXEMPLO = os.path.join(RAIZ, 'exemplos', 'compras', 'carta.json')
GIT_ID = {'GIT_AUTHOR_NAME': 'Teste', 'GIT_AUTHOR_EMAIL': 'teste@exemplo.invalid',
          'GIT_COMMITTER_NAME': 'Teste', 'GIT_COMMITTER_EMAIL': 'teste@exemplo.invalid'}


def _rodar(*args):
    out, err = io.StringIO(), io.StringIO()
    with redirect_stdout(out), redirect_stderr(err):
        cod = senku.main(list(args))
    return cod, out.getvalue(), err.getvalue()


@unittest.skipIf(shutil.which('git') is None, 'sem git')
class TestMemoryCard(unittest.TestCase):

    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        self.cartao = os.path.join(self.tmp, 'cartao')
        os.makedirs(self.cartao)
        subprocess.run(['git', 'init', '-q'], cwd=self.cartao, check=True)
        self.env_antes = {k: os.environ.get(k) for k in list(GIT_ID) + ['SENKU_MEMORY_CARD_DIR',
                                                                         'SENKU_MEMORY_CARD_REPO']}
        os.environ.update(GIT_ID)
        os.environ['SENKU_MEMORY_CARD_DIR'] = self.cartao
        os.environ['SENKU_MEMORY_CARD_REPO'] = '-'
        self.proc = os.path.join(self.tmp, 'proc')
        os.makedirs(self.proc)
        self.carta = os.path.join(self.proc, 'carta.json')
        shutil.copyfile(EXEMPLO, self.carta)

    def tearDown(self):
        for k, v in self.env_antes.items():
            if v is None:
                os.environ.pop(k, None)
            else:
                os.environ[k] = v
        shutil.rmtree(self.tmp, ignore_errors=True)

    def _ref(self, cenario='as-is'):
        return f'senku/suprimentos/gestao-de-suprimentos/sup-01-compra-de-materiais-indiretos-{cenario}'

    def test_sem_aceite_recusa(self):
        cod, out, _ = _rodar('cartao', 'enviar', self.carta, '--confirmar')
        self.assertEqual(cod, 1)
        self.assertIn('aceite', out)
        self.assertFalse(os.path.exists(os.path.join(self.cartao, 'saves')))

    def test_aprovar_lembra_e_enviar_salva(self):
        cod, _, err = _rodar('aprovar', self.carta, '--por', 'Ana (Gerente)')
        self.assertEqual(cod, 0)
        self.assertIn('LEMBRETE', err)
        self.assertIn('cartao enviar', err)
        cod, out, _ = _rodar('cartao', 'enviar', self.carta)
        self.assertEqual(cod, 0)
        self.assertIn('prévia', out)
        self.assertFalse(os.path.exists(os.path.join(self.cartao, 'saves')), 'prévia não grava')
        cod, out, _ = _rodar('cartao', 'enviar', self.carta, '--confirmar')
        self.assertEqual(cod, 0, out)
        d = os.path.join(self.cartao, 'saves', *self._ref().split('/'))
        for nome in ('README.md', 'ficha.json', 'carta.json', 'carta.aprovacao.json'):
            self.assertTrue(os.path.exists(os.path.join(d, nome)), nome)
        self.assertTrue(any(n.endswith('.bpmn') for n in os.listdir(d)))
        self.assertTrue(any(n.endswith('.docx') for n in os.listdir(d)))
        ficha = json.load(open(os.path.join(d, 'ficha.json'), encoding='utf-8'))
        self.assertEqual(ficha['solucao'], 'Senku')
        self.assertEqual(ficha['status'], 'em-uso')
        self.assertEqual(ficha['aceite']['por'], 'Ana (Gerente)')
        readme = open(os.path.join(d, 'README.md'), encoding='utf-8').read()
        self.assertIn('<!-- corpo -->', readme)
        self.assertIn('## Fluxograma', readme)
        catalogo = open(os.path.join(self.cartao, 'CATALOGO.md'), encoding='utf-8').read()
        self.assertIn('## Senku', catalogo)
        log = subprocess.run(['git', 'log', '--oneline'], cwd=self.cartao, capture_output=True, text=True).stdout
        self.assertIn('save: Senku', log)
        _, out, _ = _rodar('situacao', self.carta)
        self.assertIn('salvo no cartão', out)

    def test_versao_nova_pede_motivo(self):
        _rodar('aprovar', self.carta, '--por', 'Ana (Gerente)')
        _rodar('cartao', 'enviar', self.carta, '--confirmar')
        cod, out, _ = _rodar('cartao', 'enviar', self.carta, '--confirmar')
        self.assertEqual(cod, 1)
        self.assertIn('--motivo', out)
        cod, out, _ = _rodar('cartao', 'enviar', self.carta, '--motivo', 'nova rodada', '--confirmar')
        self.assertEqual(cod, 0, out)
        ficha = mc.ler_ficha(self.cartao, self._ref())
        self.assertEqual(ficha['versao'], 2)
        self.assertEqual(ficha['historico'][-1]['motivo'], 'nova rodada')

    def test_tobe_liga_ao_asis_e_busca_acha(self):
        _rodar('aprovar', self.carta, '--por', 'Ana (Gerente)')
        _rodar('cartao', 'enviar', self.carta, '--confirmar')
        _rodar('tobe', self.carta)
        tobe = os.path.join(self.proc, 'carta-tobe.json')
        cod, out, _ = _rodar('cartao', 'enviar', tobe, '--sem-aceite', '--confirmar')
        self.assertEqual(cod, 0, out)
        asis = mc.ler_ficha(self.cartao, self._ref())
        self.assertIn(self._ref('to-be'), asis['relacionados'])
        self.assertEqual(mc.ler_ficha(self.cartao, self._ref('to-be'))['status'], 'rascunho')
        achados = mc.buscar(self.cartao, ['compra', 'de', 'materiais'])
        self.assertTrue(achados)
        self.assertEqual(mc.buscar(self.cartao, ['ponto', 'eletronico', 'crachas']), [])

    def test_nao_toca_em_outra_solucao(self):
        outra = os.path.join(self.cartao, 'saves', 'vegapunk', 'rh', 'func', 'relatorio-x')
        os.makedirs(outra)
        ficha = {'solucao': 'Vegapunk', 'categoria': 'RH', 'secao': 'Func', 'artigo': 'Relatório X',
                 'versao': 1, 'status': 'rascunho', 'tabelas': ['T1'], 'relacionados': [], 'historico': []}
        with open(os.path.join(outra, 'ficha.json'), 'w', encoding='utf-8') as f:
            json.dump(ficha, f)
        with open(os.path.join(outra, 'pendente.txt'), 'w', encoding='utf-8') as f:
            f.write('não é do Senku')
        _rodar('aprovar', self.carta, '--por', 'Ana (Gerente)')
        cod, out, _ = _rodar('cartao', 'enviar', self.carta, '--confirmar')
        self.assertEqual(cod, 0, out)
        status = subprocess.run(['git', 'status', '--porcelain'], cwd=self.cartao, capture_output=True,
                                text=True).stdout
        self.assertIn('vegapunk', status, 'o save de outra solução não entra no commit do Senku')
        catalogo = open(os.path.join(self.cartao, 'CATALOGO.md'), encoding='utf-8').read()
        self.assertIn('## Vegapunk', catalogo)
        self.assertIn('## Por tabela', catalogo)
        cod, out, _ = _rodar('cartao', 'marcar', 'vegapunk/rh/func/relatorio-x', '--status', 'em-uso', '--confirmar')
        self.assertEqual(cod, 1)

    def test_catalogo_igual_ao_do_vegapunk(self):
        fichas = [{'solucao': 'Vegapunk', 'categoria': 'RH', 'secao': 'Funcionários', 'artigo': 'A', 'ref':
                   'vegapunk/rh/funcionarios/a', 'versao': 2, 'status': 'em-uso', 'descricao': 'd',
                   'tabelas': ['T1'], 'conferencia': {'ok': False}}]
        md = mc.gerar_catalogo_md(fichas)
        self.assertIn('- [A](saves/vegapunk/rh/funcionarios/a/) — d · v2 · em-uso · **conferir: schema mudou**', md)
        self.assertIn('- `T1`: [A](saves/vegapunk/rh/funcionarios/a/)', md)

    def test_sem_cartao_status_diz_como_ligar(self):
        os.environ['SENKU_MEMORY_CARD_DIR'] = '-'
        _, out, _ = _rodar('status')
        self.assertIn('não configurado', out)
        _, _, err = _rodar('aprovar', self.carta, '--por', 'Ana (Gerente)')
        self.assertNotIn('LEMBRETE', err)


if __name__ == '__main__':
    unittest.main()
