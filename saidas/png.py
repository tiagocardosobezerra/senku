"""
PNG do fluxograma, só com a biblioteca padrão: raias, caixas, losangos, círculos, linhas com seta e texto
numa fonte de bitmap 5x7 embutida (maiúsculas, sem acento). Serve de imagem de reserva no Word: quem abre
num programa sem SVG vê o desenho do fluxo, e o texto alternativo da figura diz para abrir o .svg.
"""

import struct
import zlib

from carta.layout import COLUNA, numerar
from carta.util import quebrar, sem_acento

from .fonte import ALTURA, FONTE, LARGURA

CAB = 150
MARGEM = 16
BRANCO = (255, 255, 255)
CORES = {'raia_a': (246, 248, 251), 'raia_b': (255, 255, 255), 'externa': (238, 240, 243), 'cab': (227, 233, 242),
         'borda': (197, 207, 220), 'linha': (68, 84, 106), 'caixa': (47, 74, 109), 'porta': (168, 107, 0),
         'inicio': (46, 125, 50), 'fim': (179, 38, 30)}


class _Tela:
    def __init__(self, w, h):
        self.w, self.h = w, h
        self.px = bytearray(BRANCO * (w * h))

    def ponto(self, x, y, cor):
        x, y = int(round(x)), int(round(y))
        if 0 <= x < self.w and 0 <= y < self.h:
            i = (y * self.w + x) * 3
            self.px[i:i + 3] = bytes(cor)

    def retangulo(self, x0, y0, x1, y1, cor):
        x0, x1 = max(0, int(x0)), min(self.w, int(x1))
        if x1 <= x0:                                     # fora da tela (caixa antes desta parte do mapa)
            return
        for y in range(max(0, int(y0)), min(self.h, int(y1))):
            i = (y * self.w + x0) * 3
            self.px[i:i + (x1 - x0) * 3] = bytes(cor) * max(0, x1 - x0)

    def linha(self, x0, y0, x1, y1, cor, esp=1):
        n = int(max(abs(x1 - x0), abs(y1 - y0))) + 1
        for k in range(n + 1):
            x = x0 + (x1 - x0) * k / n
            y = y0 + (y1 - y0) * k / n
            for d in range(esp):
                self.ponto(x + (d if abs(y1 - y0) > abs(x1 - x0) else 0),
                           y + (d if abs(x1 - x0) >= abs(y1 - y0) else 0), cor)

    def contorno(self, pts, cor, esp=2):
        for a, b in zip(pts, pts[1:] + pts[:1]):
            self.linha(a[0], a[1], b[0], b[1], cor, esp)

    def circulo(self, cx, cy, r, cor, esp=2):
        import math
        for k in range(int(8 * r) + 8):
            t = 2 * math.pi * k / (8 * r + 8)
            for d in range(esp):
                self.ponto(cx + (r - d) * math.cos(t), cy + (r - d) * math.sin(t), cor)

    def texto(self, x, y, s, cor, centro=True):
        """Escreve em maiúsculas sem acento (a fonte 5x7 não tem acento); x é o centro ou o início."""
        s = sem_acento(str(s)).upper()
        if centro:
            x -= len(s) * LARGURA / 2
        for i, ch in enumerate(s):
            g = FONTE.get(ch, FONTE['?'] if ch.strip() else FONTE[' '])
            for lin, bits in enumerate(g):
                for col in range(5):
                    if bits & (1 << (4 - col)):
                        self.ponto(x + i * LARGURA + col, y + lin, cor)

    def seta(self, x0, y0, x1, y1, cor):
        """Ponta de seta no fim do segmento (x0,y0)->(x1,y1)."""
        import math
        a = math.atan2(y1 - y0, x1 - x0)
        for d in (-0.45, 0.45):
            self.linha(x1, y1, x1 - 6 * math.cos(a + d), y1 - 6 * math.sin(a + d), cor, 2)

    def png(self):
        linhas = b''.join(b'\x00' + bytes(self.px[y * self.w * 3:(y + 1) * self.w * 3]) for y in range(self.h))

        def bloco(tipo, dados):
            return (struct.pack('>I', len(dados)) + tipo + dados +
                    struct.pack('>I', zlib.crc32(tipo + dados) & 0xffffffff))
        cab = struct.pack('>IIBBBBB', self.w, self.h, 8, 2, 0, 0, 0)
        return (b'\x89PNG\r\n\x1a\n' + bloco(b'IHDR', cab) + bloco(b'IDAT', zlib.compress(linhas, 9)) +
                bloco(b'IEND', b''))


def desenhar(c, lay, faixa=None, escala=0.8):
    """PNG (bytes) do fluxograma inteiro ou das colunas de `faixa`, na mesma geometria do SVG."""
    ini, fim = faixa or (0, round(lay.largura / COLUNA))
    if faixa:
        from .svg import _comprimir                     # mesma compressão das raias vazias do SVG
        lay = _comprimir(lay, ini, fim)
    s = escala
    ox, oy = MARGEM + CAB - ini * COLUNA, MARGEM
    largura = int((MARGEM + CAB + (fim - ini) * COLUNA + MARGEM) * s)
    altura = int((MARGEM + lay.altura + MARGEM) * s)
    t = _Tela(max(1, largura), max(1, altura))
    for i, r in enumerate(lay.raias):
        fundo = CORES['externa'] if r['tipo'] == 'externo' else CORES['raia_a' if i % 2 == 0 else 'raia_b']
        y0, y1 = (oy + r['y']) * s, (oy + r['y'] + r['h']) * s
        t.retangulo((MARGEM + CAB) * s, y0, largura - MARGEM * s, y1, fundo)
        t.linha(MARGEM * s, y0, largura - MARGEM * s, y0, CORES['borda'])
    nums = numerar(c, lay)
    for fid, pts in lay.arestas.items():
        p = [((x + ox) * s, (y + oy) * s) for x, y in pts]
        for a, b in zip(p, p[1:]):
            t.linha(a[0], a[1], b[0], b[1], CORES['linha'])
        if len(p) > 1:
            t.seta(p[-2][0], p[-2][1], p[-1][0], p[-1][1], CORES['linha'])
    # rótulos das saídas ("SIM (80%)"): sem eles, a figura de reserva não diz qual caminho é qual
    for f in c.fluxos:
        rot = f['rotulo'] + (f' ({f["percentual"]:.0f}%)' if f['percentual'] is not None else '')
        if rot and f['id'] in lay.rotulos:
            x, y, ancora = lay.rotulos[f['id']]
            rot = rot[:24]
            xx = (x + ox) * s - (len(rot) * LARGURA if ancora == 'end' else 0)
            t.texto(xx, (y + oy) * s - ALTURA, rot, CORES['linha'], centro=(ancora == 'middle'))
    for eid, n in lay.nos.items():
        if faixa and not (ini <= n['coluna'] < fim):
            continue                                    # só os elementos das colunas desta parte
        x, y, w, h = (n['x'] + ox) * s, (n['y'] + oy) * s, n['w'] * s, n['h'] * s
        cx, cy = (n['cx'] + ox) * s, (n['cy'] + oy) * s
        tipo = n['tipo']
        if tipo in ('atividade', 'subprocesso'):
            t.retangulo(x, y, x + w, y + h, BRANCO)
            t.contorno([(x, y), (x + w, y), (x + w, y + h), (x, y + h)], CORES['caixa'])
            caber = max(4, int((w - 6) // LARGURA))
            linhas = quebrar(c.nome(eid), caber)[:3]
            for i, ln in enumerate(linhas):
                t.texto(cx, cy - len(linhas) * ALTURA / 2 + i * ALTURA + 2, ln[:caber], CORES['caixa'])
            if eid in nums:
                t.texto(x + 3, y + 3, nums[eid], CORES['linha'], centro=False)
        elif tipo in ('decisao', 'paralelo', 'inclusivo', 'corrida'):
            t.contorno([(cx, y), (x + w, cy), (cx, y + h), (x, cy)], CORES['porta'])
            if tipo == 'paralelo':
                t.texto(cx, cy - 3, '+', CORES['porta'])
            elif c.elementos[eid]['nome']:
                t.texto(cx, y - ALTURA - 2, quebrar(c.nome(eid), 22)[0], CORES['linha'])
        else:
            cor = CORES['inicio'] if tipo == 'inicio' else CORES['fim'] if tipo == 'fim' else CORES['porta']
            t.circulo(cx, cy, w / 2, cor, 3 if tipo == 'fim' else 2)
            if tipo == 'fim' and c.elementos[eid]['encerra']:
                for raio in range(1, int(w / 2) - 6):             # fim terminal: disco cheio
                    t.circulo(cx, cy, raio, cor, 1)
            if c.elementos[eid]['nome'] and tipo != 'borda':
                t.texto(cx, y + h + 3, quebrar(c.nome(eid), 22)[0], CORES['linha'])
    # cabeçalho das raias por cima (no corte de uma faixa, o que vem antes some atrás dele)
    t.retangulo(0, 0, (MARGEM + CAB) * s, altura, BRANCO)
    for r in lay.raias:
        y0, y1 = (oy + r['y']) * s, (oy + r['y'] + r['h']) * s
        t.retangulo(MARGEM * s, y0, (MARGEM + CAB) * s, y1, CORES['cab'])
        t.contorno([(MARGEM * s, y0), ((MARGEM + CAB) * s, y0), ((MARGEM + CAB) * s, y1), (MARGEM * s, y1)],
                   CORES['borda'], 1)
        nome = quebrar(r['nome'], int(CAB * s // LARGURA) - 1)[:3]
        for i, ln in enumerate(nome):
            t.texto((MARGEM + CAB / 2) * s, (y0 + y1) / 2 - len(nome) * ALTURA / 2 + i * ALTURA, ln, CORES['linha'])
    return t.png()
