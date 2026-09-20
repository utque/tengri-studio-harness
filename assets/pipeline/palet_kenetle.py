#!/usr/bin/env python3
"""Palet dışı pikselleri en yakın palet rengine kenetler.

Paleti kilitli projeler içindir: AI üretimi varlıklarda kalan kenar
yumuşatma/gölge renkleri bu adımla palete oturur. Palet 04-style.md'den
okunur (harness.palet_oku). Alfa korunur; şeffaf pikseller değişmez.

Projen paleti kilitlemiyorsa (04-style.md "renk aileleri" diyorsa) bu araç
yanlış alettir — varlık spec'ine "palet serbest" yaz, harness atlar.

    python3 assets/pipeline/palet_kenetle.py assets/taslak/ico_oyna_96.png ...
    python3 assets/pipeline/palet_kenetle.py --test
"""
import colorsys
import sys
from pathlib import Path

from PIL import Image

sys.path.insert(0, str(Path(__file__).parent))
import harness  # noqa: E402

# ponytail: uzaklık eşiği yok — 04-style.md muafiyet tanımıyor, her renk kenetlenir.
# Görünür kayma olursa palet eksiktir; çözüm eşik değil 04-style.md'ye renk eklemek.


def _uzaklik(a, b):
    """Ton ağırlıklı uzaklık. Düz RGB koyu altını bataklık yeşiline kenetliyordu:
    RGB'de yakın olan iki renk farklı tonda olabilir, göz tonu affetmez."""
    ha, sa, va = colorsys.rgb_to_hsv(*(x / 255 for x in a))
    hb, sb, vb = colorsys.rgb_to_hsv(*(x / 255 for x in b))
    dh = min(abs(ha - hb), 1 - abs(ha - hb)) * 2  # dairesel; doygunluk düşükse ton anlamsız
    return (dh * min(sa, sb)) ** 2 * 6 + (sa - sb) ** 2 + (va - vb) ** 2


def kenetle(yol, palet=None, yaz=True):
    """Palet dışı her rengi en yakın palet rengine taşır. (değişen_piksel, renk_haritası)"""
    palet = palet or harness.palet_oku()
    if not palet:
        raise SystemExit("04-style.md'de palet yok.")
    im = Image.open(yol).convert("RGBA")
    harita, degisen = {}, 0
    for rgba in {p for p in im.getdata() if p[3] > 0 and p[:3] not in palet}:
        harita[rgba[:3]] = min(palet, key=lambda q, c=rgba[:3]: _uzaklik(c, q))
    if harita:
        px = list(im.getdata())
        for i, p in enumerate(px):
            if p[3] > 0 and p[:3] in harita:
                px[i] = harita[p[:3]] + (p[3],)
                degisen += 1
        im.putdata(px)
        if yaz:
            im.save(yol)
    return degisen, harita


def oz_test():
    palet = {(0, 0, 0), (255, 255, 255)}
    p = Path("/tmp/_kenetle_test.png")
    im = Image.new("RGBA", (2, 2))
    im.putdata([(250, 250, 250, 255), (5, 5, 5, 255), (120, 0, 0, 0), (255, 255, 255, 255)])
    im.save(p)
    degisen, _ = kenetle(p, palet)
    son = list(Image.open(p).convert("RGBA").getdata())
    assert degisen == 2, degisen
    assert son[0] == (255, 255, 255, 255) and son[1] == (0, 0, 0, 255), son
    assert son[2] == (120, 0, 0, 0), "şeffaf piksel korunmalı"
    assert son[3] == (255, 255, 255, 255), "palet içi piksel değişmemeli"
    assert kenetle(p, palet)[0] == 0, "idempotent değil"
    p.unlink()
    print("palet_kenetle öz-test: geçti")


if __name__ == "__main__":
    if "--test" in sys.argv:
        oz_test()
    else:
        for y in sys.argv[1:]:
            n, h = kenetle(y)
            print(f"{y}: {n} piksel kenetlendi, {len(h)} renk")
