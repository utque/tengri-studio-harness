#!/usr/bin/env python3
"""Piksel diff + değişen bölge kutuları.

Neden: iki QA turu arasında neyin DEĞİŞTİĞİ gözle aranıyordu. 26 ekran × 2 tur
= 52 kare; göz yalnız baktığı yeri görür, bakmadığı yerdeki sessiz regresyonu
kaçırır. Bu araç farkı sayar ve nerede olduğunu kutuyla söyler.

    python3 tools/gorsel_diff.py runlog/z10 runlog/z11
    python3 tools/gorsel_diff.py runlog/z10/05_baslangic.png runlog/z11/05_baslangic.png \\
        --ciz runlog/diff/05.png
    # Bitiş ölçütü kontrolü: yalnız amaçlanan bölge değişmiş mi?
    python3 tools/gorsel_diff.py runlog/z10 runlog/z11 --beklenen 10b_tur2_gelir.png

Çıkış 0 = beklenen dışında değişiklik yok. 1 = var (ya da eşleşmeyen dosya).
"""
from __future__ import annotations

import argparse
import pathlib
import sys

from PIL import Image, ImageChops, ImageDraw

# Sıkıştırma/anti-alias gürültüsü: kanal farkı bunun altındaysa değişim sayılmaz.
ESIK = 12
# Kutu birleştirme: bu kadar yakın bölgeler tek kutu olur (px).
YAKINLIK = 24
# Gürültü kutusu: bundan küçük bölgeler raporlanmaz.
MIN_ALAN = 64


def _maske(a: Image.Image, b: Image.Image, esik: int):
    """Farkın ikili maskesi + değişen piksel sayısı."""
    if a.size != b.size:
        return None, -1
    fark = ImageChops.difference(a.convert("RGB"), b.convert("RGB"))
    # Kanalların en büyüğü: tek kanaldaki kayma ortalamada kayboluyordu.
    kanallar = fark.split()
    en = kanallar[0]
    for k in kanallar[1:]:
        en = ImageChops.lighter(en, k)
    # "1" moduna çevirme: point LUT'u 0/1 üretip convert 255'e şişiriyor ve
    # sayım 255 katı çıkıyor. L modunda kal, doğrudan say.
    m = en.point(lambda v: 255 if v >= esik else 0, mode="L")
    return m, sum(1 for v in m.getdata() if v)


def _kutular(maske: Image.Image, yakinlik: int, min_alan: int) -> list:
    """Değişen pikselleri satır-koşusu ile toplayıp yakın olanları birleştirir.

    ponytail: O(bölge²) birleştirme. Kare başına birkaç düzine bölge oluyor,
    hızlı. Yüzlerce bölgeye çıkarsa union-find'a geç.
    """
    w, h = maske.size
    px = maske.load()
    kutular = []
    for y in range(h):
        x = 0
        while x < w:
            if not px[x, y]:
                x += 1
                continue
            bas = x
            while x < w and px[x, y]:
                x += 1
            kutular.append([bas, y, x - 1, y])

    degisti = True
    while degisti:
        degisti = False
        i = 0
        while i < len(kutular):
            j = i + 1
            while j < len(kutular):
                if _yakin(kutular[i], kutular[j], yakinlik):
                    kutular[i] = [
                        min(kutular[i][0], kutular[j][0]), min(kutular[i][1], kutular[j][1]),
                        max(kutular[i][2], kutular[j][2]), max(kutular[i][3], kutular[j][3])]
                    kutular.pop(j)
                    degisti = True
                else:
                    j += 1
            i += 1
    return [k for k in kutular
            if (k[2] - k[0] + 1) * (k[3] - k[1] + 1) >= min_alan]


def _yakin(a: list, b: list, d: int) -> bool:
    return not (a[0] - d > b[2] or b[0] - d > a[2] or a[1] - d > b[3] or b[1] - d > a[3])


def kiyasla(eski: pathlib.Path, yeni: pathlib.Path, esik: int, yakinlik: int,
            min_alan: int, ciz: pathlib.Path = None) -> dict:
    a = Image.open(eski)
    b = Image.open(yeni)
    maske, sayi = _maske(a, b, esik)
    if maske is None:
        return {"ad": yeni.name, "hata": f"boyut farklı {a.size} vs {b.size}",
                "piksel": -1, "kutular": []}
    kutular = _kutular(maske, yakinlik, min_alan) if sayi else []
    sonuc = {
        "ad": yeni.name, "piksel": sayi,
        "oran": sayi / float(a.size[0] * a.size[1]),
        "kutular": kutular,
    }
    if ciz is not None and kutular:
        ciz.parent.mkdir(parents=True, exist_ok=True)
        im = b.convert("RGB")
        d = ImageDraw.Draw(im)
        for k in kutular:
            d.rectangle([k[0] - 2, k[1] - 2, k[2] + 2, k[3] + 2], outline=(255, 60, 60), width=3)
        im.save(ciz)
        sonuc["ciz"] = str(ciz)
    return sonuc


def _yazdir(r: dict) -> None:
    if r.get("hata"):
        print(f"  {r['ad']:<28} HATA {r['hata']}")
        return
    if r["piksel"] == 0:
        print(f"  {r['ad']:<28} aynı")
        return
    print(f"  {r['ad']:<28} {r['piksel']:>8} px  %{r['oran'] * 100:.2f}  "
          f"{len(r['kutular'])} bölge")
    for k in r["kutular"][:6]:
        print(f"      kutu x{k[0]}..{k[2]} y{k[1]}..{k[3]} "
              f"({k[2] - k[0] + 1}×{k[3] - k[1] + 1})")
    if len(r["kutular"]) > 6:
        print(f"      … {len(r['kutular']) - 6} kutu daha")


def oz_test() -> None:
    import tempfile

    with tempfile.TemporaryDirectory() as t:
        d = pathlib.Path(t)
        a = Image.new("RGB", (200, 120), (20, 20, 30))
        b = a.copy()
        ImageDraw.Draw(b).rectangle([10, 10, 29, 29], fill=(240, 60, 60))
        ImageDraw.Draw(b).rectangle([150, 90, 169, 109], fill=(60, 240, 60))
        a.save(d / "a.png")
        b.save(d / "b.png")

        r = kiyasla(d / "a.png", d / "b.png", ESIK, YAKINLIK, MIN_ALAN)
        assert r["piksel"] == 800, f"800 px bekleniyordu, {r['piksel']}"
        assert len(r["kutular"]) == 2, f"2 bölge bekleniyordu, {len(r['kutular'])}"
        kutular = sorted(r["kutular"])
        assert kutular[0] == [10, 10, 29, 29], kutular[0]
        assert kutular[1] == [150, 90, 169, 109], kutular[1]

        # Aynı görüntü sıfır fark vermeli
        assert kiyasla(d / "a.png", d / "a.png", ESIK, YAKINLIK, MIN_ALAN)["piksel"] == 0

        # Eşiğin altındaki gürültü sayılmamalı
        c = Image.new("RGB", (200, 120), (26, 26, 36))  # her kanalda +6
        c.save(d / "c.png")
        assert kiyasla(d / "a.png", d / "c.png", ESIK, YAKINLIK, MIN_ALAN)["piksel"] == 0

        # Boyut uyuşmazlığı hata olarak dönmeli, sessizce "aynı" değil
        Image.new("RGB", (100, 60)).save(d / "k.png")
        assert kiyasla(d / "a.png", d / "k.png", ESIK, YAKINLIK, MIN_ALAN)["hata"]
    print("gorsel_diff oz_test: YESIL")


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__,
                                formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("eski", type=pathlib.Path, nargs="?")
    p.add_argument("yeni", type=pathlib.Path, nargs="?")
    p.add_argument("--esik", type=int, default=ESIK)
    p.add_argument("--yakinlik", type=int, default=YAKINLIK)
    p.add_argument("--min-alan", type=int, default=MIN_ALAN)
    p.add_argument("--ciz", type=pathlib.Path, help="kutulu görüntü (dosya) / dizin (dizin modu)")
    p.add_argument("--beklenen", nargs="*", default=None,
                   help="değişmesi BEKLENEN dosya adları; başkası değiştiyse çıkış 1")
    p.add_argument("--oz-test", action="store_true")
    n = p.parse_args()

    if n.oz_test:
        oz_test()
        return 0
    if n.eski is None or n.yeni is None:
        p.error("eski ve yeni gerekli")

    if n.eski.is_dir():
        adlar = sorted({f.name for f in n.eski.glob("*.png")} |
                       {f.name for f in n.yeni.glob("*.png")})
        print(f"── {n.eski} → {n.yeni}  ({len(adlar)} kare)")
        beklenmeyen = []
        for ad in adlar:
            e, y = n.eski / ad, n.yeni / ad
            if not e.exists() or not y.exists():
                print(f"  {ad:<28} EKSIK ({'eski' if not e.exists() else 'yeni'} turda yok)")
                beklenmeyen.append(ad)
                continue
            ciz = (n.ciz / ad) if n.ciz else None
            r = kiyasla(e, y, n.esik, n.yakinlik, n.min_alan, ciz)
            _yazdir(r)
            if r["piksel"] != 0 and n.beklenen is not None and ad not in n.beklenen:
                beklenmeyen.append(ad)
        if n.beklenen is not None:
            if beklenmeyen:
                print(f"── KIRMIZI: beklenmeyen değişiklik — {', '.join(beklenmeyen)}")
                return 1
            print("── YESIL: yalnız beklenen bölgeler değişti")
        return 0

    r = kiyasla(n.eski, n.yeni, n.esik, n.yakinlik, n.min_alan, n.ciz)
    _yazdir(r)
    return 1 if r["piksel"] != 0 else 0


if __name__ == "__main__":
    sys.exit(main())
