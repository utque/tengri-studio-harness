#!/usr/bin/env python3
"""Varlık sınıfı ön/son koşulları — fal üretiminden ÖNCE ve SONRA.

Neden: fal turları pahalı ve yavaş. Reddedilen denemelerin çoğu üretimden önce
bilinebilir bir kural ihlaliydi (prompt 1000 karakteri aşınca kuyruğu — yani
`yasak` kısıtları — sessizce kesiliyordu; magenta zemin model tarafından yok
sayılıyordu; karakter sprite'ı ikon boru hattından geçince ayak pivotu
bozuluyordu). Bu dosya o dersleri kurala çevirir: ihlal varsa tur hiç harcanmaz.

Kullanım (fal aracından):

    sys.path.insert(0, str(KOK / "assets" / "pipeline"))
    import varlik_kural
    varlik_kural.dur_veya_gec(
        varlik_kural.on_kosul(vid, VARLIKLAR[vid], final_prompt), f"{vid} ön koşul")
    ...
    varlik_kural.dur_veya_gec(
        varlik_kural.son_kosul(vid, VARLIKLAR[vid], islenmis), f"{vid} son koşul")

Doğrudan koşturulunca öz-testi çalışır: python3 assets/pipeline/varlik_kural.py
"""
from __future__ import annotations

import pathlib
import sys

# fal prompt sınırı. Aşılınca kuyruk kesiliyor ve kesilen kısım genelde
# `yasak` maddeleri oluyor → model yasaklı şeyi üretiyor.
PROMPT_MAX = 1000
# Model magenta zemini yok sayıyor; beyaz zemin kesme aşamasında güvenilir.
YASAK_ZEMIN = ("magenta", "#ff00ff", "chroma key", "green screen")
ZORUNLU_ZEMIN = "white"
# Recraft stil adları — ikon sınıfında başka stil izole ikon yerine manzara veriyor.
IKON_STIL = "vector_illustration/cutout"
# Üretilmiş ama görünmez varlık (pilotta 246 opak piksel ile geçmişti).
OPAK_MIN = 400
# İçerik tuvalin en az bu kadarını doldurmalı — 96×96 karede 8×8 çizilmiş
# ikonlar harness'ten geçmişti.
BBOX_DOLULUK_MIN = 0.35
# Karakter ayak pivotu: kurulmuş atlas'ta pivot kaynak tuvalin alt-ortasında
# olmalı (96x96 için (48,96)); içerik alt kenarı pivotun bu kadar üstünde durabilir.
# Ölçüldü: kurulu altı chr_ atlasının hepsinde pivot=(48,96), içerik altı 93.
KARAKTER_PIVOT_PAY = 6


def sinif(vid: str, tanim: dict) -> str:
    """Varlık sınıfı: kural kümesini bu seçer."""
    if vid.startswith("chr_"):
        return "karakter"
    mod = tanim.get("mod", "")
    if mod == "arazi":
        return "arazi"
    if mod == "fx":
        return "fx"
    if mod in ("ikon", "ikon_tohum"):
        return "ikon"
    return "bilinmeyen"


def on_kosul(vid: str, tanim: dict, prompt: str, stil: str = None) -> list:
    """Üretimden ÖNCE — ihlal varsa fal turu hiç harcanmaz."""
    h = []
    s = sinif(vid, tanim)

    if s == "bilinmeyen":
        h.append(f"sınıf çıkarılamadı (mod={tanim.get('mod')!r}) — kural uygulanamıyor")

    if len(prompt) > PROMPT_MAX:
        kesilen = prompt[PROMPT_MAX:]
        h.append(f"prompt {len(prompt)} karakter (sınır {PROMPT_MAX}); "
                 f"kesilecek kuyruk: …{kesilen[:60]!r}")

    dusuk = prompt.lower()
    for kelime in YASAK_ZEMIN:
        if kelime in dusuk:
            h.append(f"promptta yasak zemin ifadesi {kelime!r} — {ZORUNLU_ZEMIN} kullan")
    if s in ("ikon", "karakter") and ZORUNLU_ZEMIN not in dusuk:
        h.append(f"{s} promptunda {ZORUNLU_ZEMIN!r} zemin yok — kesme adımı zemine dayanıyor")

    if s == "ikon":
        if stil is not None and stil != IKON_STIL:
            h.append(f"ikon stili {stil!r} — {IKON_STIL!r} olmalı")
        if not tanim.get("hedef_px"):
            h.append("hedef_px yok — ikon ölçeği varlık başına belirlenir")

    # tohum (img2img şablonu) ve tohum_maske (siluet kilidi) AYRI knob'lar:
    # tohum tek başına meşru. Tersi değil — maske tohumu indekslerken patlar.
    if tanim.get("tohum_maske") and not tanim.get("tohum"):
        h.append("tohum_maske var ama tohum yok — maskelenecek siluet yok")

    return h


def son_kosul(vid: str, tanim: dict, png: pathlib.Path) -> list:
    """Üretimden SONRA, kuruluma girmeden önce."""
    from PIL import Image

    h = []
    s = sinif(vid, tanim)
    if not png.exists():
        return [f"çıktı yok: {png}"]
    im = Image.open(png).convert("RGBA")
    w, hgt = im.size

    alfa = im.getchannel("A")
    opak = sum(1 for v in alfa.getdata() if v > 0)
    if opak < OPAK_MIN:
        h.append(f"yalnız {opak} opak piksel — görünmez varlık (eşik {OPAK_MIN})")

    bb = alfa.getbbox()
    if bb is None:
        h.append("tamamen şeffaf")
        return h
    doluluk = ((bb[2] - bb[0]) * (bb[3] - bb[1])) / float(w * hgt)
    if doluluk < BBOX_DOLULUK_MIN:
        h.append(f"içerik tuvalin %{doluluk * 100:.0f}'ini dolduruyor "
                 f"(en az %{BBOX_DOLULUK_MIN * 100:.0f}); küçük çizilmiş varlık")

    bekle = tanim.get("beklenen_boyut")
    if bekle and tuple(bekle) != (w, hgt):
        h.append(f"boyut {w}×{hgt}, beklenen {bekle[0]}×{bekle[1]}")

    return h


def atlas_kosul(vid: str, json_yolu: pathlib.Path) -> list:
    """Kurulum SONRASI — atlas json'undaki pivot hâlâ ayakta mı.

    Karakterlerde ayak pivotu (kaynak tuvalin alt-ortası) oyunun hex hizalaması
    için tek dayanak. İçerik tuvalin ortasına alınırsa sprite hexin üstünde
    asılı kalıyor — denendi, puan 42→17, reddedildi. Ara 96x96 çıktısı bilerek
    ortalanır; kırmızı olan yalnızca KURULMUŞ atlas'ın pivotudur.
    """
    import json

    h = []
    if not vid.startswith("chr_"):
        return h
    if not json_yolu.exists():
        return [f"atlas json yok: {json_yolu}"]
    d = json.loads(json_yolu.read_text(encoding="utf-8"))
    for alan in ("pivot", "trim_ofset", "kaynak_boyut", "kareler"):
        if alan not in d:
            return [f"atlas json'unda {alan} yok"]
    kw, kh = d["kaynak_boyut"]
    px = d["trim_ofset"][0] + d["pivot"][0]
    py = d["trim_ofset"][1] + d["pivot"][1]
    if abs(px - kw / 2.0) > 1.0:
        h.append(f"pivot x={px}, kaynak ortası {kw / 2.0:.0f} olmalı")
    if py != kh:
        h.append(f"pivot y={py}, kaynak tabanı {kh} olmalı (ayak pivotu)")
    alt = d["trim_ofset"][1] + d["kareler"][0]["h"]
    if py - alt > KARAKTER_PIVOT_PAY:
        h.append(f"içerik alt kenarı pivotun {py - alt} px üstünde "
                 f"(pay {KARAKTER_PIVOT_PAY}) — sprite hexin üstünde asılı kalır")
    return h


def dur_veya_gec(hatalar: list, baslik: str) -> None:
    if not hatalar:
        print(f"KURAL YESIL {baslik}")
        return
    for e in hatalar:
        print(f"KURAL KIRMIZI {baslik}: {e}", file=sys.stderr)
    sys.exit(f"{baslik}: {len(hatalar)} kural ihlali — üretim durdu")


def oz_test() -> None:
    import tempfile

    from PIL import Image

    ikon = {"mod": "ikon_tohum", "tohum": "arma", "tohum_maske": True, "hedef_px": 78}
    iyi = "ONE gold shield icon, thick dark outline, plain solid WHITE background, isolated"
    assert on_kosul("ico_arma", ikon, iyi, IKON_STIL) == [], on_kosul("ico_arma", ikon, iyi, IKON_STIL)

    # Prompt sınırı
    uzun = iyi + " x" * 600
    assert any("sınır" in e for e in on_kosul("ico_arma", ikon, uzun, IKON_STIL))
    # Magenta zemin
    assert any("magenta" in e for e in
               on_kosul("ico_arma", ikon, iyi + " solid magenta background", IKON_STIL))
    # Beyaz zemin yok
    assert any("zemin yok" in e for e in on_kosul("ico_arma", ikon, "ONE gold shield", IKON_STIL))
    # Yanlış stil
    assert any("stili" in e for e in on_kosul("ico_arma", ikon, iyi, "digital_illustration/pixel_art"))
    # hedef_px yok
    assert any("hedef_px" in e for e in
               on_kosul("ico_x", {"mod": "ikon", "hedef_px": 0}, iyi, IKON_STIL))
    # tohum tek başına meşru (img2img şablonu), maske tek başına değil
    assert on_kosul("ico_y", {"mod": "ikon_tohum", "tohum": "a", "hedef_px": 40}, iyi, IKON_STIL) == []
    assert any("tohum yok" in e for e in
               on_kosul("ico_z", {"mod": "ikon_tohum", "tohum_maske": True, "hedef_px": 40},
                        iyi, IKON_STIL))
    # Karakter ikon boru hattından geçebilir: pivot kurulumda türetiliyor.
    krk = {"mod": "ikon_tohum", "tohum": "piyade", "tohum_maske": True, "hedef_px": 62}
    assert on_kosul("chr_piyade", krk, iyi, IKON_STIL) == []
    # Bilinmeyen sınıf sessizce geçmemeli
    assert any("sınıf" in e for e in on_kosul("xx_a", {"mod": "?"}, iyi, IKON_STIL))
    # Arazi/fx beyaz zemin şartı aranmaz (img2img hex şablonu)
    assert on_kosul("env_ova", {"mod": "arazi"}, "ONE flat-top hex, solid fill") == []

    with tempfile.TemporaryDirectory() as t:
        d = pathlib.Path(t)
        # Sağlam ikon: 96×96'nın ortasında 70×70 blok
        im = Image.new("RGBA", (96, 96), (0, 0, 0, 0))
        im.paste((200, 180, 60, 255), (13, 13, 83, 83))
        im.save(d / "iyi.png")
        assert son_kosul("ico_arma", ikon, d / "iyi.png") == []

        # Görünmez varlık
        bos = Image.new("RGBA", (96, 96), (0, 0, 0, 0))
        bos.paste((255, 255, 255, 255), (0, 0, 10, 10))
        bos.save(d / "az.png")
        h = son_kosul("ico_arma", ikon, d / "az.png")
        assert any("opak piksel" in e for e in h), h
        assert any("dolduruyor" in e for e in h), h

        # Ara çıktı ortalanmış olabilir — karakter için bu kırmızı DEĞİL.
        # (Pivot yalnız KURULMUŞ atlas'ta aranır; aşağıdaki atlas_kosul testi.)
        k = Image.new("RGBA", (96, 96), (0, 0, 0, 0))
        k.paste((120, 120, 160, 255), (13, 5, 83, 75))
        k.save(d / "krk.png")
        assert not any("pivot" in e for e in son_kosul("chr_piyade", krk, d / "krk.png"))

        # Kurulmuş atlas pivotu: ayakta olan geçer, ortalanan kırmızı
        import json as _j
        saglam = {"pivot": [14, 54], "trim_ofset": [34, 42], "kaynak_boyut": [96, 96],
                  "kareler": [{"w": 22, "h": 51}]}
        (d / "iyi.json").write_text(_j.dumps(saglam))
        assert atlas_kosul("chr_piyade", d / "iyi.json") == []
        ortali = {"pivot": [11, 25], "trim_ofset": [37, 22], "kaynak_boyut": [96, 96],
                  "kareler": [{"w": 22, "h": 51}]}
        (d / "kotu.json").write_text(_j.dumps(ortali))
        assert any("ayak pivotu" in e for e in atlas_kosul("chr_piyade", d / "kotu.json"))
        # Karakter olmayan varlıkta kural aranmaz
        assert atlas_kosul("ico_altin", d / "kotu.json") == []
        # Eksik json sessizce geçmemeli
        assert atlas_kosul("chr_piyade", d / "yok.json")

        # Beklenen boyut
        assert any("boyut" in e for e in
                   son_kosul("ico_arma", dict(ikon, beklenen_boyut=[64, 64]), d / "iyi.png"))

        # Olmayan dosya sessizce geçmemeli
        assert son_kosul("ico_arma", ikon, d / "yok.png")

    print("varlik_kural oz_test: YESIL")


if __name__ == "__main__":
    oz_test()
