#!/usr/bin/env python3
"""Varlık doğrulama harness'i — Faz 4C. studio.py ve pipeline aynı kodu kullanır.

Tekniği makine onaylar, estetiği insan: burada yalnızca ölçülebilen şeyler var.

    python3 assets/pipeline/harness.py <id> [<id>...]   # manifest + 04-style.md'ye göre
    python3 assets/pipeline/harness.py --hepsi           # durumu taslak/spec olan her varlık
"""
import json
import re
import struct
import sys
from pathlib import Path

from PIL import Image

KOK = Path(__file__).resolve().parents[2]
PALET_DISI_TAVAN = 0.01  # ponytail: sabit %1; stil kılavuzuna 'palet toleransı' alanı gerekirse oradan oku


def palet_oku(stil_yolu=KOK / "04-style.md"):
    if not stil_yolu.exists():
        return set()
    metin = stil_yolu.read_text(encoding="utf-8")
    return {tuple(int(h[i:i + 2], 16) for i in (0, 2, 4))
            for h in re.findall(r"#([0-9a-fA-F]{6})\b", metin)}


def spec_boyut(spec):
    m = re.search(r"(\d+)\s*[x×]\s*(\d+)", spec or "")  # 48x48 ve 48×48
    return (int(m.group(1)), int(m.group(2))) if m else None


def spec_kare(spec):
    m = re.search(r"(\d+)\s*kare", spec or "")
    return int(m.group(1)) if m else None


def png_kontrol(yol, spec="", palet=None):
    """Boyut, kare sayısı, format, şeffaflık, palet dışı renk."""
    hata = []
    try:
        im = Image.open(yol)
    except Exception as e:
        return [f"PNG açılamadı: {e}"]
    if im.format != "PNG":
        hata.append(f"format {im.format}, PNG bekleniyor")
    hucre, kare = spec_boyut(spec), spec_kare(spec)
    if hucre:
        beklenen = (hucre[0] * (kare or 1), hucre[1])
        if im.size != beklenen and im.size != hucre:
            hata.append(f"boyut {im.size}, spec {beklenen} ({hucre} x {kare or 1} kare)")
    if "A" not in im.getbands() and re.search(r"şeffaf|transparan|alpha", spec or "", re.I):
        hata.append("alfa kanalı yok, spec şeffaflık istiyor")
    if palet:
        rgba = im.convert("RGBA")
        pikseller = [p[:3] for p in rgba.getdata() if p[3] > 0]
        if pikseller:
            disi = sum(1 for p in pikseller if p not in palet)
            oran = disi / len(pikseller)
            if oran > PALET_DISI_TAVAN:
                hata.append(f"palet dışı piksel %{oran * 100:.1f} (tavan %{PALET_DISI_TAVAN * 100:.0f})")
    return hata


def wav_kontrol(yol, hiz=None, bit=None, hedef_dbfs=None):
    """Başlık + tepe seviye + kırpılma. Yalnızca PCM."""
    d = Path(yol).read_bytes()
    if d[:4] != b"RIFF" or d[8:12] != b"WAVE":
        return ["geçerli WAV değil"]
    i = d.find(b"fmt ")
    if i < 0:
        return ["fmt bloğu yok"]
    fmt_tipi, kanal = struct.unpack("<HH", d[i + 8:i + 12])
    ornekleme = struct.unpack("<I", d[i + 12:i + 16])[0]
    derinlik = struct.unpack("<H", d[i + 22:i + 24])[0]
    hata = []
    if fmt_tipi != 1:
        return [f"PCM değil (format {fmt_tipi})"]
    if hiz and ornekleme != hiz:
        hata.append(f"örnekleme {ornekleme}, spec {hiz}")
    if bit and derinlik != bit:
        hata.append(f"bit derinliği {derinlik}, spec {bit}")
    j = d.find(b"data")
    if j < 0 or derinlik not in (16, 24):
        return hata + (["data bloğu yok"] if j < 0 else [])
    ham = d[j + 8:]
    if derinlik == 16:
        n = len(ham) // 2
        ornekler = struct.unpack(f"<{n}h", ham[:n * 2])
        tam = 32767
    else:
        ornekler = [int.from_bytes(ham[k:k + 3], "little", signed=True) for k in range(0, len(ham) - 2, 3)]
        tam = 8388607
    if not ornekler:
        return hata + ["ses verisi boş"]
    tepe = max(abs(o) for o in ornekler)
    kirpik = sum(1 for o in ornekler if abs(o) >= tam - 1)
    if kirpik > 2:
        hata.append(f"kırpılma: {kirpik} örnek tam ölçekte")
    if hedef_dbfs is not None and tepe > 0:
        import math
        dbfs = 20 * math.log10(tepe / tam)
        if abs(dbfs - hedef_dbfs) > 1.5:
            hata.append(f"tepe {dbfs:.1f} dBFS, hedef {hedef_dbfs} (±1.5)")
    return hata


def atlas_sizma(png_yolu, tablo_yolu):
    """Her karenin dışındaki extrude halkası kenar pikselini tekrarlıyor mu."""
    tablo = json.loads(Path(tablo_yolu).read_text(encoding="utf-8"))
    extrude = int(tablo.get("extrude", 0))
    if not extrude:
        return ["atlas tablosunda extrude yok ya da 0"]
    im = Image.open(png_yolu).convert("RGBA")
    W, H = im.size
    px = im.load()
    hata = []
    for k in tablo.get("kareler", []):
        x, y, w, h = k["x"], k["y"], k["w"], k["h"]
        if x - extrude < 0 or y - extrude < 0 or x + w + extrude > W or y + h + extrude > H:
            hata.append(f"{k.get('id', '?')}: extrude payı atlas dışına taşıyor")
            continue
        for e in range(1, extrude + 1):
            for cx in range(x, x + w):
                if px[cx, y - e] != px[cx, y] or px[cx, y + h - 1 + e] != px[cx, y + h - 1]:
                    hata.append(f"{k.get('id', '?')}: dikey extrude sızıyor")
                    break
            for cy in range(y, y + h):
                if px[x - e, cy] != px[x, cy] or px[x + w - 1 + e, cy] != px[x + w - 1, cy]:
                    hata.append(f"{k.get('id', '?')}: yatay extrude sızıyor")
                    break
    return sorted(set(hata))


def paket_olcumu(dizin):
    """(toplam bayt, doku belleği bayt = Σ w*h*4)"""
    toplam = doku = 0
    for p in Path(dizin).rglob("*"):
        if not p.is_file():
            continue
        toplam += p.stat().st_size
        if p.suffix.lower() in (".png", ".webp", ".jpg", ".jpeg"):
            try:
                w, h = Image.open(p).size
                doku += w * h * 4
            except Exception:
                pass
    return toplam, doku


def ogg_kontrol(yol):
    """OGG = Ogg Vorbis olmalı (Godot yalnız Vorbis import eder; Ogg FLAC/Opus geçmez)."""
    d = Path(yol).read_bytes()[:512]
    if d[:4] != b"OggS":
        return ["geçerli Ogg değil"]
    if b"vorbis" not in d:
        kodek = "FLAC" if b"FLAC" in d else ("Opus" if b"Opus" in d else "bilinmeyen")
        return [f"Ogg içinde Vorbis yok ({kodek}); Godot bunu import etmez"]
    return []


def isim_kontrol(kimlik, yol):
    return [] if Path(yol).stem == kimlik and kimlik == kimlik.lower() else \
        [f"dosya adı '{Path(yol).stem}' id ile aynı ve küçük harf olmalı"]


def tech_spec():
    """02-tech.md'den ses hedeflerini çek."""
    p = KOK / "02-tech.md"
    if not p.exists():
        return {}
    m = p.read_text(encoding="utf-8")
    hiz = re.search(r"\b(44100|48000|22050)\b", m)
    bit = re.search(r"\b(16|24)\s*[- ]?bit", m, re.I)
    db = re.search(r"(-\d+(?:\.\d+)?)\s*dBFS", m)
    return {"hiz": int(hiz.group(1)) if hiz else None,
            "bit": int(bit.group(1)) if bit else None,
            "dbfs": float(db.group(1)) if db else None}


def varlik_kontrol(kimlik, spec, yol):
    """Tek varlık için tüm hata listesi."""
    yol = Path(yol)
    hata = isim_kontrol(kimlik, yol)
    if yol.suffix.lower() == ".png":
        # Çizgi film varlıkları sabit paletle çizilmez; spec 'palet serbest' derse palet kontrolü atlanır.
        palet = None if re.search(r"palet serbest", spec or "", re.I) else (palet_oku() or None)
        hata += png_kontrol(yol, spec, palet)
    elif yol.suffix.lower() == ".wav":
        t = tech_spec()
        hata += wav_kontrol(yol, t.get("hiz"), t.get("bit"), t.get("dbfs"))
    elif yol.suffix.lower() == ".ogg":
        hata += ogg_kontrol(yol)
    return hata


def _cli(argv):
    import yaml
    kayitlar = yaml.safe_load((KOK / "assets/manifest.yaml").read_text(encoding="utf-8")) or []
    if "--hepsi" in argv:
        hedef = [k for k in kayitlar if str(k.get("durum")) in ("spec", "revizyon", "taslak")]
    else:
        hedef = [k for k in kayitlar if k.get("id") in argv]
    kod = 0
    for k in hedef:
        yol = next((p for p in (KOK / "assets/raw").rglob("*") if p.is_file() and p.stem == k["id"]), None)
        hata = [f"ham dosya yok"] if not yol else varlik_kontrol(k["id"], k.get("spec", ""), yol)
        print(f"{'GEÇTİ' if not hata else 'KALDI'}  {k['id']}" + "".join(f"\n        - {h}" for h in hata))
        kod |= bool(hata)
    return kod


if __name__ == "__main__":
    sys.exit(_cli(sys.argv[1:]))
