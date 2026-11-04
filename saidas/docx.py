"""
O mapeamento em Word (.docx), só com a biblioteca padrão: o arquivo é um zip de XML (Office Open XML).

Tem as mesmas seções e os mesmos números do HTML, em estilos do próprio Word (Título 1, Título 2, tabela com
grade), para a pessoa editar e aplicar o modelo da empresa. Cabeçalho com o título e a situação (RASCUNHO até
o aceite), rodapé com "página X de Y", sumário (o Word atualiza ao abrir). O fluxograma entra como SVG
(Word 2016/365 e LibreOffice 7+) com uma imagem PNG do desenho como reserva para quem não lê SVG; cada parte
cabe numa página A4 paisagem.
"""

import zipfile
from xml.sax.saxutils import escape

from carta.analise import pct_txt
from carta.gestao import nivel_risco, plano, riscos_ordenados
from carta.modelo import PORTAS, VALORES
from carta.util import como_lista, formatar_minutos, numero_br

from . import png as png_saida
from .documento import LEGENDA, aceites, caminho_txt, comparacao_asis
from . import svg as svg_saida

EMU_POR_PX = 9525
EMU_POR_POL = 914400
LARGURA_UTIL = 9.9                               # polegadas: A4 paisagem com margem de 2 cm
ALTURA_UTIL = 6.2                                # idem, descontando cabeçalho, rodapé e a legenda da figura
_NS = ('xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main" '
       'xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships" '
       'xmlns:wp="http://schemas.openxmlformats.org/drawingml/2006/wordprocessingDrawing"')
_REL = 'http://schemas.openxmlformats.org/officeDocument/2006/relationships'


def _t(x):
    # vale para texto e para atributo (descr="..."): as aspas também viram entidade
    return escape(str(x if x is not None else ''), {'"': '&quot;'})


def _run(texto, negrito=False, cor=None, tamanho=None):
    rpr = ''
    if negrito or cor or tamanho:
        rpr = '<w:rPr>' + ('<w:b/>' if negrito else '') + (f'<w:color w:val="{cor}"/>' if cor else '') + \
              (f'<w:sz w:val="{tamanho}"/>' if tamanho else '') + '</w:rPr>'
    return f'<w:r>{rpr}<w:t xml:space="preserve">{_t(texto)}</w:t></w:r>'


def _campo(codigo, mostrado='1'):
    return (f'<w:r><w:fldChar w:fldCharType="begin"/></w:r><w:r><w:instrText xml:space="preserve"> {codigo} '
            f'</w:instrText></w:r><w:r><w:fldChar w:fldCharType="separate"/></w:r><w:r><w:t>{mostrado}</w:t></w:r>'
            '<w:r><w:fldChar w:fldCharType="end"/></w:r>')


def _secao(orient):
    """Propriedades de seção (página A4, margens, cabeçalho e rodapé) em paisagem ou retrato."""
    tam = ('<w:pgSz w:w="16838" w:h="11906" w:orient="landscape"/>' if orient == 'paisagem'
           else '<w:pgSz w:w="11906" w:h="16838"/>')
    return ('<w:sectPr><w:headerReference w:type="default" r:id="rCab"/>'
            '<w:footerReference w:type="default" r:id="rRod"/>' + tam +
            '<w:pgMar w:top="1134" w:right="1134" w:bottom="1134" w:left="1134" w:header="567" w:footer="567" '
            'w:gutter="0"/></w:sectPr>')


class _Doc:
    def __init__(self):
        self.corpo = []
        self.titulos = []
        self.orient = 'paisagem'
        self.imagens = []                       # (n, svg bytes, png bytes)

    def p(self, texto, estilo=None, negrito=False, cor=None, tamanho=None):
        if estilo == 'Heading1':
            self.titulos.append(texto)
        ppr = f'<w:pPr><w:pStyle w:val="{estilo}"/></w:pPr>' if estilo else ''
        self.corpo.append(f'<w:p>{ppr}{_run(texto, negrito, cor, tamanho)}</w:p>')

    def lista(self, itens):
        for x in itens:
            self.p(f'• {x}')

    def sumario(self):
        self.corpo.append('<w:p><w:pPr><w:pStyle w:val="TOCHeading"/></w:pPr>' + _run('Sumário') + '</w:p>')
        # o campo já sai com as seções escritas (sem número de página): o Word abre sem perguntar nada, e
        # "Atualizar campo" põe as páginas
        self.corpo.append('@@SUMARIO@@')

    def tabela(self, cab, linhas, larguras=None):
        n = len(cab)
        larguras = larguras or [int(14000 / n)] * n
        grade = ''.join(f'<w:gridCol w:w="{w}"/>' for w in larguras)

        def cel(texto, w, titulo=False):
            sombra = '<w:shd w:val="clear" w:color="auto" w:fill="E3E9F2"/>' if titulo else ''
            rpr = '<w:rPr><w:b/><w:sz w:val="18"/></w:rPr>' if titulo else '<w:rPr><w:sz w:val="18"/></w:rPr>'
            partes = str(texto if texto is not None else '').split('\n')
            ps = ''.join(f'<w:p><w:r>{rpr}<w:t xml:space="preserve">{_t(x)}</w:t></w:r></w:p>' for x in partes)
            return f'<w:tc><w:tcPr><w:tcW w:w="{w}" w:type="dxa"/>{sombra}</w:tcPr>{ps}</w:tc>'
        linhas_xml = ['<w:tr><w:trPr><w:tblHeader/></w:trPr>' + ''.join(cel(c, w, True) for c, w in
                                                                        zip(cab, larguras)) + '</w:tr>']
        for ln in linhas:
            linhas_xml.append('<w:tr><w:trPr><w:cantSplit/></w:trPr>' +
                              ''.join(cel(c, w) for c, w in zip(ln, larguras)) + '</w:tr>')
        self.corpo.append('<w:tbl><w:tblPr><w:tblStyle w:val="TabelaSenku"/><w:tblW w:w="0" w:type="auto"/>'
                          f'</w:tblPr><w:tblGrid>{grade}</w:tblGrid>{"".join(linhas_xml)}</w:tbl>')
        self.p('')

    def figura(self, svg_texto, png_bytes, largura_px, altura_px, descricao):
        """A figura cabe na página: limita largura E altura, mantendo a proporção."""
        n = len(self.imagens) + 1
        self.imagens.append((n, svg_texto.encode('utf-8'), png_bytes))
        pol_w, pol_h = largura_px / 96, altura_px / 96
        larg, alt = (LARGURA_UTIL, ALTURA_UTIL) if self.orient == 'paisagem' else (6.5, 9.2)
        fator = min(1.0, larg / pol_w, alt / pol_h)
        cx, cy = int(pol_w * fator * EMU_POR_POL), int(pol_h * fator * EMU_POR_POL)
        self.corpo.append(
            '<w:p><w:pPr><w:keepNext/></w:pPr><w:r><w:drawing><wp:inline distT="0" distB="0" distL="0" distR="0">'
            f'<wp:extent cx="{cx}" cy="{cy}"/><wp:docPr id="{n}" name="Fluxograma {n}" descr="{_t(descricao)}"/>'
            '<a:graphic xmlns:a="http://schemas.openxmlformats.org/drawingml/2006/main">'
            '<a:graphicData uri="http://schemas.openxmlformats.org/drawingml/2006/picture">'
            '<pic:pic xmlns:pic="http://schemas.openxmlformats.org/drawingml/2006/picture">'
            f'<pic:nvPicPr><pic:cNvPr id="{n}" name="fluxograma{n}.png"/><pic:cNvPicPr/></pic:nvPicPr>'
            f'<pic:blipFill><a:blip r:embed="rPng{n}"><a:extLst>'
            '<a:ext uri="{96DAC541-7B7A-43D3-8B79-37D633B846F1}">'
            f'<asvg:svgBlip xmlns:asvg="http://schemas.microsoft.com/office/drawing/2016/SVG/main" r:embed="rSvg{n}"/>'
            '</a:ext></a:extLst></a:blip><a:stretch><a:fillRect/></a:stretch></pic:blipFill>'
            f'<pic:spPr><a:xfrm><a:off x="0" y="0"/><a:ext cx="{cx}" cy="{cy}"/></a:xfrm>'
            '<a:prstGeom prst="rect"><a:avLst/></a:prstGeom></pic:spPr></pic:pic></a:graphicData></a:graphic>'
            '</wp:inline></w:drawing></w:r></w:p>')

    def orientacao(self, nova):
        """Muda a orientação a partir daqui (fecha a seção atual: o Word começa página nova)."""
        if nova != self.orient:
            self.corpo.append(f'<w:p><w:pPr>{_secao(self.orient)}</w:pPr></w:p>')
            self.orient = nova

    def quebra(self):
        self.corpo.append('<w:p><w:r><w:br w:type="page"/></w:r></w:p>')

    def gravar(self, caminho, titulo, situacao, rascunho):
        sect = _secao(self.orient)
        itens = ''.join(f'<w:r><w:t xml:space="preserve">{_t(x)}</w:t></w:r><w:r><w:br/></w:r>' for x in self.titulos)
        sumario = ('<w:p><w:r><w:fldChar w:fldCharType="begin"/></w:r><w:r><w:instrText xml:space="preserve"> '
                   'TOC \\o "1-1" \\h \\z \\u </w:instrText></w:r><w:r><w:fldChar w:fldCharType="separate"/></w:r>'
                   + itens + '<w:r><w:fldChar w:fldCharType="end"/></w:r></w:p>')
        documento = (f'<?xml version="1.0" encoding="UTF-8" standalone="yes"?><w:document {_NS}><w:body>'
                     + ''.join(sumario if x == '@@SUMARIO@@' else x for x in self.corpo) + sect
                     + '</w:body></w:document>')
        cor_sit = 'B3261E' if rascunho else '2E7D32'
        cabecalho = (f'<?xml version="1.0" encoding="UTF-8" standalone="yes"?><w:hdr {_NS}><w:p><w:pPr>'
                     '<w:tabs><w:tab w:val="right" w:pos="14570"/></w:tabs></w:pPr>'
                     + _run(titulo, cor='5B6878', tamanho=16) + '<w:r><w:tab/></w:r>'
                     + _run(situacao, negrito=True, cor=cor_sit, tamanho=16) + '</w:p></w:hdr>')
        rodape = (f'<?xml version="1.0" encoding="UTF-8" standalone="yes"?><w:ftr {_NS}><w:p><w:pPr><w:jc '
                  'w:val="right"/></w:pPr>' + _run('Página ', cor='5B6878', tamanho=16) + _campo('PAGE') +
                  _run(' de ', cor='5B6878', tamanho=16) + _campo('NUMPAGES') + '</w:p></w:ftr>')
        estilos = (
            '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
            '<w:styles xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main">'
            '<w:docDefaults><w:rPrDefault><w:rPr><w:rFonts w:ascii="Calibri" w:hAnsi="Calibri" w:cs="Calibri"/>'
            '<w:sz w:val="21"/><w:lang w:val="pt-BR"/></w:rPr></w:rPrDefault>'
            '<w:pPrDefault><w:pPr><w:spacing w:after="80"/></w:pPr></w:pPrDefault></w:docDefaults>'
            '<w:style w:type="paragraph" w:default="1" w:styleId="Normal"><w:name w:val="Normal"/></w:style>'
            '<w:style w:type="paragraph" w:styleId="Title"><w:name w:val="Title"/><w:basedOn w:val="Normal"/>'
            '<w:pPr><w:spacing w:after="120"/></w:pPr><w:rPr><w:b/><w:sz w:val="40"/><w:color w:val="1D2733"/></w:rPr>'
            '</w:style>'
            '<w:style w:type="paragraph" w:styleId="Heading1"><w:name w:val="heading 1"/><w:basedOn w:val="Normal"/>'
            '<w:next w:val="Normal"/><w:pPr><w:keepNext/><w:spacing w:before="320" w:after="120"/>'
            '<w:outlineLvl w:val="0"/></w:pPr><w:rPr><w:b/><w:sz w:val="30"/><w:color w:val="2F4A6D"/></w:rPr>'
            '</w:style>'
            '<w:style w:type="paragraph" w:styleId="Heading2"><w:name w:val="heading 2"/><w:basedOn w:val="Normal"/>'
            '<w:next w:val="Normal"/><w:pPr><w:keepNext/><w:spacing w:before="200" w:after="80"/>'
            '<w:outlineLvl w:val="1"/></w:pPr><w:rPr><w:b/><w:sz w:val="24"/></w:rPr></w:style>'
            '<w:style w:type="paragraph" w:styleId="TOCHeading"><w:name w:val="TOC Heading"/>'
            '<w:basedOn w:val="Normal"/><w:rPr><w:b/><w:sz w:val="26"/></w:rPr></w:style>'
            '<w:style w:type="table" w:styleId="TabelaSenku"><w:name w:val="Tabela Senku"/><w:tblPr>'
            '<w:tblBorders><w:top w:val="single" w:sz="4" w:color="C5CFDC"/>'
            '<w:left w:val="single" w:sz="4" w:color="C5CFDC"/><w:bottom w:val="single" w:sz="4" w:color="C5CFDC"/>'
            '<w:right w:val="single" w:sz="4" w:color="C5CFDC"/>'
            '<w:insideH w:val="single" w:sz="4" w:color="C5CFDC"/>'
            '<w:insideV w:val="single" w:sz="4" w:color="C5CFDC"/></w:tblBorders>'
            '<w:tblCellMar><w:left w:w="80" w:type="dxa"/><w:right w:w="80" w:type="dxa"/></w:tblCellMar>'
            '</w:tblPr></w:style></w:styles>')
        config = ('<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
                  '<w:settings xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main">'
                  '<w:defaultTabStop w:val="708"/></w:settings>')
        rels = [f'<Relationship Id="rEstilos" Type="{_REL}/styles" Target="styles.xml"/>',
                f'<Relationship Id="rConfig" Type="{_REL}/settings" Target="settings.xml"/>',
                f'<Relationship Id="rCab" Type="{_REL}/header" Target="header1.xml"/>',
                f'<Relationship Id="rRod" Type="{_REL}/footer" Target="footer1.xml"/>']
        for n, _, _ in self.imagens:
            rels.append(f'<Relationship Id="rPng{n}" Type="{_REL}/image" Target="media/fluxograma{n}.png"/>')
            rels.append(f'<Relationship Id="rSvg{n}" Type="{_REL}/image" Target="media/fluxograma{n}.svg"/>')
        wml = 'application/vnd.openxmlformats-officedocument.wordprocessingml'
        tipos = ('<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
                 '<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">'
                 '<Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>'
                 '<Default Extension="xml" ContentType="application/xml"/>'
                 '<Default Extension="png" ContentType="image/png"/>'
                 '<Default Extension="svg" ContentType="image/svg+xml"/>'
                 f'<Override PartName="/word/document.xml" ContentType="{wml}.document.main+xml"/>'
                 f'<Override PartName="/word/styles.xml" ContentType="{wml}.styles+xml"/>'
                 f'<Override PartName="/word/settings.xml" ContentType="{wml}.settings+xml"/>'
                 f'<Override PartName="/word/header1.xml" ContentType="{wml}.header+xml"/>'
                 f'<Override PartName="/word/footer1.xml" ContentType="{wml}.footer+xml"/>'
                 '<Override PartName="/docProps/core.xml" ContentType="application/'
                 'vnd.openxmlformats-package.core-properties+xml"/></Types>')
        raiz_rels = ('<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
                     '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
                     f'<Relationship Id="rDoc" Type="{_REL}/officeDocument" Target="word/document.xml"/>'
                     '<Relationship Id="rCore" Type="http://schemas.openxmlformats.org/package/2006/relationships/'
                     'metadata/core-properties" Target="docProps/core.xml"/></Relationships>')
        core = ('<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
                '<cp:coreProperties xmlns:cp="http://schemas.openxmlformats.org/package/2006/metadata/'
                'core-properties" xmlns:dc="http://purl.org/dc/elements/1.1/">'
                f'<dc:title>{_t(titulo)}</dc:title><dc:creator>Senku</dc:creator></cp:coreProperties>')
        with zipfile.ZipFile(caminho, 'w', zipfile.ZIP_DEFLATED) as z:
            z.writestr('[Content_Types].xml', tipos)
            z.writestr('_rels/.rels', raiz_rels)
            z.writestr('docProps/core.xml', core)
            z.writestr('word/document.xml', documento)
            z.writestr('word/styles.xml', estilos)
            z.writestr('word/settings.xml', config)
            z.writestr('word/header1.xml', cabecalho)
            z.writestr('word/footer1.xml', rodape)
            z.writestr('word/_rels/document.xml.rels',
                       '<?xml version="1.0" encoding="UTF-8" standalone="yes"?><Relationships '
                       'xmlns="http://schemas.openxmlformats.org/package/2006/relationships">' + ''.join(rels) +
                       '</Relationships>')
            for n, svg_b, png_b in self.imagens:
                z.writestr(f'word/media/fluxograma{n}.svg', svg_b)
                z.writestr(f'word/media/fluxograma{n}.png', png_b)


def gerar(c, d, caminho):
    """Grava o .docx do mapeamento. `d` é o documento.montar(c): os números são os mesmos do HTML."""
    from .documento import _linhas_atividades, _raci, _sipoc_processo
    p, an = c.processo, d['an']
    t = an['tempos']
    doc = _Doc()
    doc.p(c.titulo(), 'Title')
    doc.p(f'Mapeamento de processo · {c.cenario().upper()} · versão {p.get("versao", "—")}', cor='5B6878')
    doc.p(d['texto_status'], negrito=True, cor='2E7D32' if d['status'] == 'aprovada' else 'B3261E')
    doc.sumario()
    erros = [a for a in d['achados'] if a.nivel == 'erro']
    if erros:
        doc.p(f'{len(erros)} erro(s) de fluxo ainda sem correção: o desenho pode estar incompleto.', negrito=True,
              cor='B3261E')

    doc.p('1. Ficha do processo', 'Heading1')
    ficha = [('Código', p.get('codigo')), ('Processo', p.get('nome')), ('Macroprocesso', p.get('macroprocesso')),
             ('Nível', p.get('nivel')), ('Área', p.get('area')), ('Dono do processo', p.get('dono')),
             ('Objetivo', p.get('objetivo')), ('Gatilho', p.get('gatilho')), ('Resultado esperado', p.get('resultado')),
             ('Frequência / volume', ' · '.join(x for x in (p.get('frequencia'), p.get('volume')) if x)),
             ('Prazo (informado)', p.get('prazo_informado')), ('Cenário', c.cenario().upper()),
             ('Versão', p.get('versao'))]
    doc.tabela(['Campo', 'Valor'], [(k, v or 'a definir') for k, v in ficha], [3200, 10800])

    doc.p('2. Escopo', 'Heading1')
    esc = p.get('escopo') or {}
    doc.tabela(['Começa em', 'Termina em'], [(esc.get('inicio') or '—', esc.get('fim') or '—')], [7000, 7000])
    for chave, rot in (('inclui', 'Inclui'), ('nao_inclui', 'Não inclui')):
        if esc.get(chave):
            doc.p(rot, 'Heading2')
            doc.lista(como_lista(esc[chave]))
    if p.get('premissas'):
        doc.p('Premissas', 'Heading2')
        doc.lista(como_lista(p['premissas']))

    doc.p('3. SIPOC', 'Heading1')
    s = c.sipoc
    cols = [como_lista(s.get('fornecedores')), como_lista(s.get('entradas')), _sipoc_processo(c, d),
            como_lista(s.get('saidas')), como_lista(s.get('clientes'))]
    doc.tabela(['Fornecedores', 'Entradas', 'Processo', 'Saídas', 'Clientes'],
               [['\n'.join(col) or 'a definir' for col in cols]])

    doc.p('4. Fluxograma', 'Heading1')
    cortes, retrato = svg_saida.faixas_impressao(c, d['lay'])
    if len(cortes) > 1:
        doc.p(f'O mapa aparece em {len(cortes)} partes, uma por página (a última coluna de uma parte repete na '
              'seguinte). O desenho inteiro está no arquivo .svg da mesma pasta.', cor='5B6878')
    for i, faixa in enumerate(cortes, 1):
        parte = (i, len(cortes)) if len(cortes) > 1 else None
        texto = svg_saida.desenhar(c, d['lay'], titulo=True, faixa=faixa if parte else None, parte=parte)
        largura = float(texto.split('width="', 1)[1].split('"', 1)[0])
        altura = float(texto.split('height="', 1)[1].split('"', 1)[0])
        reserva = png_saida.desenhar(c, d['lay'], faixa if parte else None)
        nova = 'retrato' if retrato[i - 1] else 'paisagem'
        if nova != doc.orient:
            doc.orientacao(nova)                          # parte com muitas raias: página em pé, letra maior
        elif i > 1:
            doc.quebra()
        doc.figura(texto, reserva, largura, altura, f'Fluxograma {c.titulo()}' +
                   (f', parte {i} de {len(cortes)}' if parte else '') + '. Se a figura aparecer simplificada (sem cores), '
                   'abra o arquivo .svg da mesma pasta.')
    doc.p('Legenda: ' + LEGENDA, cor='5B6878', tamanho=16)
    doc.orientacao('paisagem')

    doc.p('5. Descrição das atividades', 'Heading1')
    linhas = list(_linhas_atividades(c, d))
    doc.tabela(['Nº', 'Atividade', 'Responsável', 'Sistema', 'Entradas', 'Saídas', 'Regras', 'Tempo', 'Valor'],
               [(x['n'], x['atividade'], x['responsavel'], x['sistema'], x['entradas'], x['saidas'], x['regras'],
                 x['tempo'], x['valor']) for x in linhas],
               [600, 2600, 1700, 1500, 1700, 1700, 900, 2000, 1300])
    for x in linhas:
        if x['descricao'] or x['como'] or x['excecoes'] or x['documentos']:
            doc.p(f'{x["n"]} · {x["atividade"]}', 'Heading2')
            if x['descricao']:
                doc.p(x['descricao'])
            for i, y in enumerate(x['como'], 1):
                doc.p(f'{i}. {y}')
            for y in x['excecoes']:
                doc.p(f'Exceção: {y}')
            if x['documentos']:
                doc.p('Documentos e modelos: ' + ', '.join(x['documentos']))

    doc.p('6. Decisões e regras de negócio', 'Heading1')
    decs = [e for e in c.de_tipo('decisao', 'inclusivo', 'corrida') if len(c.saidas[e['id']]) > 1]
    if decs:
        doc.tabela(['Decisão', 'Quem decide', 'Caminhos', 'Regras'], [
            (e['nome'], c.nome_papel(e['papel']),
             '\n'.join(caminho_txt(c, e, f) for f in c.saidas[e['id']]),
             ', '.join(e['regras']) or '—') for e in decs], [3500, 2500, 6000, 2000])
    if c.regras:
        doc.tabela(['Regra', 'Texto', 'Fonte', 'Onde se aplica'],
                   [(rid, r.get('texto', ''), r.get('fonte', ''),
                     ', '.join(c.nome(e['id']) for e in c.elementos.values() if rid in e['regras']))
                    for rid, r in c.regras.items()], [1000, 7000, 3000, 3000])
    if not decs and not c.regras:
        doc.p('Nenhuma decisão ou regra registrada.')

    doc.p('7. Matriz RACI', 'Heading1')
    cab, linhas_raci = _raci(c, d)
    doc.tabela(['Nº', 'Atividade'] + cab, [[n, nome] + cel for n, nome, cel in linhas_raci])
    doc.p('R = executa · A = responde pelo resultado · C = consultado antes · I = informado depois. Uma atividade '
          'tem um só A.', cor='5B6878')
    sem_a = [e for e in d['ativ'] if not e['raci']['A']]
    if sem_a:
        doc.p(f'{len(sem_a)} atividade(s) sem "A" declarado: pendência para o dono do processo.', cor='5B6878')

    doc.p('8. Indicadores', 'Heading1')
    if c.indicadores:
        doc.tabela(['Indicador', 'Fórmula', 'Hoje', 'Meta', 'Polaridade', 'Periodicidade', 'Fonte', 'Dono'],
                   [(i.get('nome'), i.get('formula'), i.get('atual') or 'a medir', i.get('meta'), i.get('polaridade'),
                     i.get('periodicidade'), i.get('fonte'), i.get('dono')) for i in c.indicadores],
                   [2100, 3300, 1300, 1300, 1400, 1400, 1400, 1800])
    else:
        doc.p('Nenhum indicador definido ainda.')

    doc.p('9. Análise do processo', 'Heading1')
    doc.tabela(['Medida', 'Valor'], [
        ('Lead time do caminho feliz', formatar_minutos(t['lead_time'])),
        ('Lead time esperado (com exceções, retrabalho e todos os desfechos)', formatar_minutos(t['lead_time_esperado'])),
        ('Prazo em que terminam 50% / 80% / 90% dos casos',
         ' / '.join(formatar_minutos(t['percentis'][k]) for k in ('p50', 'p80', 'p90')) if t.get('percentis')
         else '—'),
        ('Esforço (execução)', formatar_minutos(t['execucao'])), ('Eficiência do ciclo', pct_txt(t)),
        ('Passagens de bastão no caso típico', len(an['passagens_caminho'])),
        ('Laços de retrabalho', len(an['retrabalho'])), ('Atividades', an['contagem']['atividades'])],
        [7000, 7000])
    if t.get('espera_sem_tempo'):
        doc.p('Sem tempo de resposta (a espera por quem está de fora conta zero; o lead time real é maior): '
              + ', '.join(c.nome(x) for x in t['espera_sem_tempo']))
    passos = [x for x in an['caminho_feliz'] if c.elementos[x]['tipo'] not in PORTAS]
    doc.p('Caminho feliz (o caso mais comum)', 'Heading2')
    doc.p(' → '.join(f'{d["nums"][x]} {c.nome(x)}' if x in d['nums'] else c.nome(x) for x in passos))
    if an['passagens_caminho']:
        doc.p('Passagens de bastão no caso típico: ' + '; '.join(
            f'{c.nome_papel(c.raia_de(a))} → {c.nome_papel(c.raia_de(b))} ({c.nome(b)})'
            for a, b in an['passagens_caminho']))
    if an['gargalos']:
        doc.p('Maiores esperas: ' + '; '.join(f'{c.nome(eid)}: {formatar_minutos(m)}' for eid, m in an['gargalos']))
    cg = an.get('carga')
    if cg:
        doc.p('Carga de trabalho (capacidade)', 'Heading2')
        doc.tabela(['Papel', 'Horas por mês', 'Pessoas (160 h/mês)'],
                   [(c.nome_papel(p), numero_br(h), numero_br(n, 1)) for p, h, n in cg['por_papel']] +
                   [('Total', numero_br(cg['horas_mes']), numero_br(cg['pessoas'], 1))], [7000, 3500, 3500])
    v = an['valor']
    total = sum(x['atividades'] for x in v.values()) or 1
    doc.tabela(['Classificação', 'Atividades', '%', 'Tempo de execução'],
               [(f'{k}: {VALORES.get(k, "sem classificação")}', v[k]['atividades'], f'{v[k]["atividades"] / total:.0%}',
                 formatar_minutos(v[k]['execucao'])) for k in ('VA', 'NAV-N', 'NAV', 'sem') if v[k]['atividades']],
               [6000, 2500, 2000, 3500])
    doc.p('Os tempos são estimativas da entrevista, não medição.', cor='5B6878')
    if an['oportunidades']:
        doc.p('Oportunidades, da maior para a menor', 'Heading2')
        doc.tabela(['#', 'Desperdício', 'Oportunidade'], [(i, o['desperdicio'], o['texto']) for i, o in
                                                          enumerate(an['oportunidades'], 1)], [600, 2600, 10800])

    cmp_ = comparacao_asis(c)
    if cmp_:
        doc.p(f'AS-IS x TO-BE (contra {cmp_[0]})', 'Heading2')
        doc.tabela(['Medida', 'AS-IS', 'TO-BE', 'Diferença'], cmp_[2], [5000, 3000, 3000, 3000])
        if cmp_[1]:
            doc.p('O que muda no fluxo:', negrito=True)
            doc.lista(cmp_[1])
    doc.p('10. Dores, melhorias e riscos', 'Heading1')
    if c.dores:
        doc.tabela(['Id', 'Dor', 'Onde', 'Impacto', 'Frequência'],
                   [(x.get('id'), x.get('descricao'), ', '.join(c.nome(r) for r in x.get('elementos') or []),
                     x.get('impacto'), x.get('frequencia')) for x in c.dores], [900, 6500, 3600, 1500, 1500])
    if c.melhorias:
        doc.p('Plano de ação (melhorias)', 'Heading2')
        doc.tabela(['Id', 'Ação', 'Resolve', 'Impacto', 'Esforço', 'Responsável', 'Prazo', 'Situação'],
                   [(x['id'], x['acao'], x['resolve'], x['impacto'], x['esforco'], x['responsavel'], x['prazo'],
                     x['situacao']) for x in plano(c)], [700, 5000, 1100, 1100, 1100, 2000, 1500, 1500])
    if c.riscos:
        doc.p('Riscos e controles', 'Heading2')
        doc.tabela(['Id', 'Risco', 'Onde', 'P × I', 'Nível', 'Controle', 'Tipo'],
                   [(x.get('id'), x.get('descricao'), ', '.join(c.nome(r) for r in x.get('elementos') or []),
                     f'{x.get("probabilidade") or "?"} × {x.get("impacto") or "?"}', nivel_risco(x)[1],
                     x.get('controle') or 'SEM CONTROLE', x.get('tipo_controle')) for x in riscos_ordenados(c)],
                   [700, 3600, 2200, 1100, 1700, 3500, 1200])
    if not (c.dores or c.melhorias or c.riscos):
        doc.p('Nada registrado ainda.')

    doc.p('11. Glossário, normas e pendências', 'Heading1')
    if c.glossario:
        doc.tabela(['Termo', 'Definição'], [(g.get('termo'), g.get('definicao')) for g in c.glossario], [3500, 10500])
    if p.get('normas'):
        doc.p('Normas e referências', 'Heading2')
        doc.lista(como_lista(p['normas']))
    if c.sistemas:
        doc.p('Sistemas', 'Heading2')
        doc.lista(f'{s["nome"]} {s["descricao"]}'.strip() for s in c.sistemas.values())
    pend = [(x.get('pergunta') or x.get('descricao', ''), x.get('para', '')) for x in c.pendencias]
    if pend:
        doc.p('Pendências', 'Heading2')
        doc.tabela(['Pendência', 'Com quem'], pend, [10500, 3500])
    abertas = [q for q in d['lacunas'] if q.prioridade in (1, 3)]
    if abertas:
        doc.p('Ainda sem resposta na carta', 'Heading2')
        doc.lista(q.texto for q in abertas)

    doc.p('12. Participantes, histórico e aprovação', 'Heading1')
    if c.participantes:
        doc.tabela(['Nome', 'Papel', 'Data'], [(x.get('nome'), x.get('papel'), x.get('data'))
                                               for x in c.participantes], [5000, 6000, 3000])
    if c.historico:
        doc.tabela(['Versão', 'Data', 'Autor', 'Mudança'], [(x.get('versao'), x.get('data'), x.get('autor'),
                                                             x.get('mudanca')) for x in c.historico],
                   [1500, 2000, 3000, 7500])
    if aceites(c):
        doc.p('Aceites do dono do processo', 'Heading2')
        doc.tabela(['Versão', 'Quando', 'Por', 'Observação'], aceites(c), [1500, 2500, 4000, 6000])
    doc.p(d['texto_status'], negrito=True)
    doc.p('Gerado pelo Senku a partir do carta.json: para mudar, edite a carta e gere de novo.', cor='5B6878')
    doc.gravar(caminho, c.titulo(), 'APROVADO' if d['status'] == 'aprovada' else 'RASCUNHO',
               d['status'] != 'aprovada')


__all__ = ['gerar']
