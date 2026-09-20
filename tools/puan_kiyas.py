#!/usr/bin/env python3
"""Kör puanlama + ölçüt çıpaları.

Neden: puanlayan ile değişikliği yapan aynı ajan. "Yeni" olduğunu bilerek bakmak
puanı yukarı çeker; loop-puan.md'de kabul edilen her satır bu yanlılığı taşıyor.
Bu araç iki görüntüyü rastgele A/B'ye karıştırır, hangisinin yeni olduğunu
puanlama bitene kadar saklar.

    python3 tools/puan_kiyas.py olcut
    python3 tools/puan_kiyas.py hazirla eski.png yeni.png --etiket hp_rozet
    #   -> runlog/puan/hp_rozet_A.png, _B.png, _kor.png   (A/B hangisi belli değil)
    #   -> ajan YALNIZ bu dosyalara bakıp iki puan seti verir
    python3 tools/puan_kiyas.py ac --etiket hp_rozet --a 7,8,8,7,8,8 --b 8,8,8,7,8,8
    #   -> eşleme açılır, karar yazılır, runlog/loop-puan.md'ye satır eklenir

En güçlü biçimi: `hazirla`yı çalıştıran ajan puanlamayı KENDİ yapmaz; yalnız
_A.png/_B.png gören taze bir ajan puanlar. Tek ajan koşusunda bile A/B karışımı
"yeni olan bu" çapasını kırar.
"""
from __future__ import annotations

import argparse
import json
import pathlib
import random
import sys

from PIL import Image, ImageDraw

KOK = pathlib.Path(__file__).resolve().parent.parent
PUAN_DIZIN = KOK / "runlog" / "puan"
KAYIT = KOK / "runlog" / "loop-puan.md"

OLCUTLER = ["hiyerarşi", "okunabilirlik", "tutarlılık", "orantı", "renk-stil", "temizlik"]

# Çıpa: her ölçüt için puan seviyesinin tek satırlık karşılığı. Çıpasız 0–10
# ölçeği turdan tura kayar — aynı ekran bir tur 7, sonraki tur 5 alır.
CIPALAR = {
    "hiyerarşi": {
        10: "1 sn'de ne yapacağım belli; birincil eylem tek ve tartışmasız",
        8: "odak net, ikincil öğeler bastırmıyor",
        6: "odak var ama iki öğe dikkat için yarışıyor",
        4: "her şey aynı ağırlıkta, gözün tutunacağı yer yok",
        2: "ikincil bir öğe birincil eylemi bastırıyor",
        0: "kare okunamıyor, nereye bakılacağı belirsiz",
    },
    "okunabilirlik": {
        10: "her sayı/ikon ilk bakışta doğru okunuyor, yanlış eşleşme yok",
        8: "hepsi okunuyor; bir öğe için bir an duraksama",
        6: "bir öğe yanlış şeye aitmiş gibi okunuyor ya da kontrast zayıf",
        4: "bir bilgi ancak arayarak bulunuyor",
        2: "birden çok öğe zeminde kayboluyor",
        0: "temel bilgi (can, kaynak, sıra) okunmuyor",
    },
    "tutarlılık": {
        10: "aynı anlam her yerde aynı ikon/renk/ölçek",
        8: "tek küçük sapma (bir ikon biraz farklı ölçek)",
        6: "iki öğe aynı sistemden değilmiş gibi duruyor",
        4: "ikon ailesi karışık (farklı çizgi kalınlığı/palet)",
        2: "aynı anlam iki farklı sembolle gösteriliyor",
        0: "ekranda ortak bir stil yok",
    },
    "orantı": {
        10: "her kutu içeriğine göre; boşluk ritmi düzenli",
        8: "bir kutu biraz geniş/dar ama göze batmıyor",
        6: "şişmiş kutu veya nokta ikon var; ölçüm eşiği sınırda",
        4: "panel oyunu gereksiz örtüyor ya da ikon cılız",
        2: "öğe ekran kenarından taşıyor / kırpılıyor",
        0: "yerleşim bozuk, öğeler üst üste",
    },
    "renk-stil": {
        10: "04-style.md paletine tam uyum; kare bir bütün",
        8: "palet içinde, bir ton hafif dışarıda",
        6: "bir varlık farklı stilden (AI çamuru / yanlış doygunluk)",
        4: "palet dışı renk göze çarpıyor",
        2: "birden çok stil karışmış",
        0: "rastgele renkler, stil yok",
    },
    "temizlik": {
        10: "artefakt yok, hayalet UI yok, kırpık kenar yok",
        8: "yakın planda hafif tırtık; oyun ölçeğinde görünmüyor",
        6: "bir kenar/kontur kopuk ya da tek artefakt var",
        4: "önceki durumdan kalan öğe veya gözle görülür artefakt",
        2: "hayalet UI / placeholder görünüyor",
        0: "ekran kirli, birden çok artefakt",
    },
}

ETIKET_YUK = 44


def _goster(p: pathlib.Path) -> str:
    """Köke göre yol; köke bağlı değilse mutlak (öz-testte tmp dizin)."""
    try:
        return str(p.relative_to(KOK))
    except ValueError:
        return str(p)


def olcut_yazdir() -> None:
    print("Ölçütler (her biri 0–10) → toplam /60")
    print("Kural: yeni tasarım YALNIZCA toplam puanı yükseldiyse kabul.\n")
    for ad in OLCUTLER:
        print(f"## {ad}")
        for p in sorted(CIPALAR[ad], reverse=True):
            print(f"  {p:>2}  {CIPALAR[ad][p]}")
        print()


def _kirp(im: Image.Image, kirp: str | None) -> Image.Image:
    if not kirp:
        return im
    x, y, w, h = (int(v) for v in kirp.split(","))
    return im.crop((x, y, x + w, y + h))


def hazirla(eski: pathlib.Path, yeni: pathlib.Path, etiket: str, kirp: str | None) -> None:
    for p in (eski, yeni):
        if not p.exists():
            sys.exit(f"yok: {p}")
    PUAN_DIZIN.mkdir(parents=True, exist_ok=True)
    a_yeni = random.SystemRandom().choice([True, False])  # A yeni mi?
    esle = {"A": yeni if a_yeni else eski, "B": eski if a_yeni else yeni}

    gorseller = {}
    for harf, yol in esle.items():
        im = _kirp(Image.open(yol).convert("RGB"), kirp)
        # Kaynak dosya adı/metadata sızmasın: yeniden kodla.
        hedef = PUAN_DIZIN / f"{etiket}_{harf}.png"
        im.save(hedef)
        gorseller[harf] = im

    w = max(g.width for g in gorseller.values())
    h = max(g.height for g in gorseller.values())
    sayfa = Image.new("RGB", (w * 2 + 24, h + ETIKET_YUK), (18, 18, 26))
    d = ImageDraw.Draw(sayfa)
    for i, harf in enumerate("AB"):
        x = i * (w + 24)
        sayfa.paste(gorseller[harf], (x, ETIKET_YUK))
        d.text((x + 8, 14), harf, fill=(232, 232, 240))
    kor = PUAN_DIZIN / f"{etiket}_kor.png"
    sayfa.save(kor)

    anahtar = PUAN_DIZIN / f".{etiket}_anahtar.json"
    anahtar.write_text(json.dumps({
        "a_yeni": a_yeni, "eski": str(eski), "yeni": str(yeni), "kirp": kirp,
    }), encoding="utf-8")

    print(f"KOR {_goster(kor)}")
    print(f"A   {_goster(PUAN_DIZIN / (etiket + '_A.png'))}")
    print(f"B   {_goster(PUAN_DIZIN / (etiket + '_B.png'))}")
    print("Hangisinin yeni olduğu saklı. Puanla, sonra `ac` ile çöz.")
    print(f"Ölçüt sırası: {','.join(OLCUTLER)}")


def _puan_coz(s: str) -> list[int]:
    p = [int(v) for v in s.split(",")]
    if len(p) != len(OLCUTLER):
        sys.exit(f"{len(OLCUTLER)} puan bekleniyor ({','.join(OLCUTLER)}), {len(p)} geldi")
    if any(v < 0 or v > 10 for v in p):
        sys.exit("puanlar 0–10 aralığında olmalı")
    return p


def ac(etiket: str, a: str, b: str, not_: str | None) -> int:
    anahtar = PUAN_DIZIN / f".{etiket}_anahtar.json"
    if not anahtar.exists():
        sys.exit(f"anahtar yok: {anahtar} — önce `hazirla`")
    k = json.loads(anahtar.read_text(encoding="utf-8"))
    pa, pb = _puan_coz(a), _puan_coz(b)
    yeni_p, eski_p = (pa, pb) if k["a_yeni"] else (pb, pa)
    yeni_t, eski_t = sum(yeni_p), sum(eski_p)
    kabul = yeni_t > eski_t

    print(f"A = {'YENI' if k['a_yeni'] else 'ESKI'}   B = {'ESKI' if k['a_yeni'] else 'YENI'}")
    print(f"{'ölçüt':<14}{'eski':>6}{'yeni':>6}")
    for ad, e, y in zip(OLCUTLER, eski_p, yeni_p):
        isaret = "" if y == e else ("  ↑" if y > e else "  ↓")
        print(f"{ad:<14}{e:>6}{y:>6}{isaret}")
    print(f"{'TOPLAM':<14}{eski_t:>6}{yeni_t:>6}")
    print(f"KARAR: {'KABUL' if kabul else 'RET — geri al, gerekçeyi koda yorum düş'}")

    satir = [
        f"\n## {etiket}\n",
        f"Kıyas: `{_goster(PUAN_DIZIN / (etiket + '_kor.png'))}`",
        f" (A={'yeni' if k['a_yeni'] else 'eski'}, kör puanlandı)\n\n",
        "| ölçüt | " + " | ".join(OLCUTLER) + " | toplam |\n",
        "|---|" + "---|" * (len(OLCUTLER) + 1) + "\n",
        "| eski | " + " | ".join(str(v) for v in eski_p) + f" | **{eski_t}** |\n",
        "| yeni | " + " | ".join(str(v) for v in yeni_p) + f" | **{yeni_t}** |\n",
        f"\n→ **{'KABUL' if kabul else 'RET'}**",
        f" ({not_})" if not_ else "",
        "\n",
    ]
    with KAYIT.open("a", encoding="utf-8") as f:
        f.write("".join(satir))
    print(f"KAYIT {_goster(KAYIT)}")
    return 0 if kabul else 1


def oz_test() -> None:
    """Aracın kendi kontrolü: karıştırma ve karar mantığı doğru mu."""
    import contextlib
    import io
    import tempfile

    sessiz = contextlib.redirect_stdout(io.StringIO())  # öz-test gürültü yapmasın
    with tempfile.TemporaryDirectory() as t, sessiz:
        d = pathlib.Path(t)
        e, y = d / "e.png", d / "y.png"
        Image.new("RGB", (40, 30), (10, 10, 10)).save(e)
        Image.new("RGB", (40, 30), (200, 200, 200)).save(y)
        global PUAN_DIZIN, KAYIT
        PUAN_DIZIN, KAYIT = d / "puan", d / "kayit.md"
        KAYIT.write_text("", encoding="utf-8")
        # Karıştırma gerçekten iki yöne de düşüyor mu
        goruldu = set()
        for i in range(40):
            hazirla(e, y, f"t{i}", None)
            goruldu.add(json.loads((PUAN_DIZIN / f".t{i}_anahtar.json").read_text())["a_yeni"])
        assert goruldu == {True, False}, "karıştırma tek yöne saplanmış"
        # Karar: yeni yüksekse kabul, düşükse ret — A/B eşlemesinden bağımsız
        k = json.loads((PUAN_DIZIN / ".t0_anahtar.json").read_text())
        yuksek, dusuk = "9,9,9,9,9,9", "1,1,1,1,1,1"
        a, b = (yuksek, dusuk) if k["a_yeni"] else (dusuk, yuksek)
        assert ac("t0", a, b, None) == 0, "yeni yüksekken KABUL bekleniyordu"
        assert ac("t0", b, a, None) == 1, "yeni düşükken RET bekleniyordu"
        assert "TOPLAM" not in KAYIT.read_text()
        assert KAYIT.read_text().count("KABUL") == 1
    print("puan_kiyas oz_test: YESIL")


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__,
                                formatter_class=argparse.RawDescriptionHelpFormatter)
    alt = p.add_subparsers(dest="komut", required=True)
    alt.add_parser("olcut")
    alt.add_parser("oz-test")
    h = alt.add_parser("hazirla")
    h.add_argument("eski", type=pathlib.Path)
    h.add_argument("yeni", type=pathlib.Path)
    h.add_argument("--etiket", required=True)
    h.add_argument("--kirp", help="x,y,w,h — iki görüntüde de aynı bölge")
    a = alt.add_parser("ac")
    a.add_argument("--etiket", required=True)
    a.add_argument("--a", required=True, help=",".join(OLCUTLER))
    a.add_argument("--b", required=True)
    a.add_argument("--not", dest="not_", help="karar gerekçesi")
    n = p.parse_args()

    if n.komut == "olcut":
        olcut_yazdir()
    elif n.komut == "oz-test":
        oz_test()
    elif n.komut == "hazirla":
        hazirla(n.eski, n.yeni, n.etiket, n.kirp)
    elif n.komut == "ac":
        return ac(n.etiket, n.a, n.b, n.not_)
    return 0


if __name__ == "__main__":
    sys.exit(main())
