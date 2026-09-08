#!/usr/bin/env python3
"""Faz kapılı stüdyo koşucusu — 8 faz, kapılar yazılımda.

Her düğüm koddur: ön koşulu, izinli kapsamı, makine doğrulaması ve kapısı
vardır. Ajanın "yaptım" demesi hiçbir yerde kanıt sayılmaz; her şey dosya
sisteminden, git'ten ve harness'ten ölçülür. Onay, hash, idempotens, merge ve
limitler ajanın değil bu scriptin işi.

İnsan yalnızca oyun tipi ve varlık (asset) sorularına cevap verir. Yazılım
adımlarında studio 10 seviyeli öz-yargı iterasyonu ile kendini yargılar;
oynanır demo'ya (ilk playtest kapısı) kadar bu döngüyle ilerler.

    python3 studio.py                    # kaldığın yerden devam et (demo'ya kadar)
    python3 studio.py --agac             # ağacı çiz
    python3 studio.py --onayla X...      # kapı aç / varlık onayla (adım, id ya da "taslak")
    python3 studio.py --reddet id not    # varlığı revizyona düşür
    python3 studio.py --sec kisa_liste a,b,c | --sec secilen a
    python3 studio.py --test             # kendi kendini test et
    python3 studio.py --kok <dizin> ...  # başka bir proje kökünde koş (tek kopya, çok proje)

Limitler: STUDIO_BUTCE=10 STUDIO_SURE=1800 STUDIO_PARTI=20  STUDIO_PARALEL=4
          STUDIO_IZIN=bypassPermissions  STUDIO_TEST_KOMUT=tests/run.sh
          STUDIO_GODOT=godot  STUDIO_PLAYTEST_ARALIK=10
          STUDIO_NICE=10 (ajan ve dış komutların öncelik düşürmesi)
          STUDIO_YUK=<çekirdek×1.5> (bu load average'ın üstünde adım BAŞLATILMAZ, beklenir)
          STUDIO_YUK_BEKLE=900 (yük düşmezse bu kadar saniye sonra DUR)
          STUDIO_AI=claude|cursor  (ajan motoru; cursor = Cursor CLI `agent`)
          STUDIO_MODEL=  (cursor için --model, örn. sonnet-4 / gpt-5)
          STUDIO_YARGI=10 (yazılım adımı öz-yargı seviyesi)
          STUDIO_YARGI_MOD=ai|deterministik|claude|cursor  (ai = STUDIO_AI; testte deterministik)
          STUDIO_DEMO=playtest-1  (oynanır demo kapısı; buraya kadar otonom yazılım)
"""
import concurrent.futures
import datetime
import fnmatch
import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
import time
from pathlib import Path

import jsonschema
import yaml

def _kok_ayikla(argv):
    """--kok <dizin>: stüdyoyu başka bir proje kökünde koştur. Tek kopya, çok proje.
    Varsayılan bu betiğin dizini. Bayrak argv'den ayıklanır ki diğer bayrakların
    argümanlarına karışmasın."""
    if "--kok" not in argv:
        return Path(__file__).resolve().parent, argv
    i = argv.index("--kok")
    if i + 1 >= len(argv):
        sys.exit("\033[31m■ DUR:\033[0m --kok bir dizin ister.")
    k = Path(argv[i + 1]).expanduser().resolve()
    if not (k / ".git").is_dir():
        sys.exit(f"\033[31m■ DUR:\033[0m {k} bir git deposu değil — stüdyo dal ve worktree ile çalışır.")
    return k, argv[:i] + argv[i + 2:]


KOK, ARGV = _kok_ayikla(sys.argv[1:])

# harness.py stüdyo altyapısıdır (faz çıktısı DEĞİL) ama kendi konumundan kök hesaplar
# (parents[2]), o yüzden stüdyodan import edilemez — yanlış projenin dosyalarını okur.
# Eksikse projeye tohumlanır; sonrası projenin kendi kopyası, Faz 5'te değişebilir.
_HARNESS = KOK / "assets" / "pipeline" / "harness.py"
if not _HARNESS.exists():
    _kaynak = Path(__file__).resolve().parent / "assets" / "pipeline" / "harness.py"
    if _kaynak.exists():
        _HARNESS.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(_kaynak, _HARNESS)
        print(f"\033[33m   harness.py projeye tohumlandı:\033[0m {_HARNESS.relative_to(KOK)}")
sys.path.insert(0, str(KOK / "assets" / "pipeline"))
try:
    import harness  # noqa: E402  — Faz 4C, pipeline ile paylaşılan kod
    HARNESS_VAR = True
except ModuleNotFoundError:  # Faz 4C'den önce yok; Faz 1–4A harness'siz koşar
    HARNESS_VAR = False

    class _HarnessYok:
        def __getattr__(self, ad):
            raise Dur(f"{KOK}/assets/pipeline/harness.py yok — harness.{ad} Faz 4C çıktısıdır.")
    harness = _HarnessYok()

# Tur promptları stüdyonun kendi .claude/commands'ında; proje kendi sürümünü koyarsa o kazanır.
KOMUTLAR = KOK / ".claude" / "commands"
if not KOMUTLAR.is_dir():
    KOMUTLAR = Path(__file__).resolve().parent / ".claude" / "commands"
RUNLOG = KOK / "runlog"
DURUM = RUNLOG / "durum.json"
MANIFEST = KOK / "assets" / "manifest.yaml"
HAM = KOK / "assets" / "raw"
SECIM = KOK / "01-secim.yaml"
YAYIN_LISTE = KOK / "07-yayin.yaml"
WT = KOK / ".wt"

BUTCE = os.environ.get("STUDIO_BUTCE", "10")
SURE = int(os.environ.get("STUDIO_SURE", "1800"))
PARTI_BOYUT = int(os.environ.get("STUDIO_PARTI", "20"))
PARALEL = int(os.environ.get("STUDIO_PARALEL", "4"))
IZIN = os.environ.get("STUDIO_IZIN", "bypassPermissions")
TEST_KOMUT = os.environ.get("STUDIO_TEST_KOMUT", "tests/run.sh")
GODOT = os.environ.get("STUDIO_GODOT", "godot")
PLAYTEST_ARALIK = int(os.environ.get("STUDIO_PLAYTEST_ARALIK", "10"))  # kaç dilimde bir playtest; ilk playtest ilk oynanabilir sahneden sonra
NICE = int(os.environ.get("STUDIO_NICE", "10"))
CEKIRDEK = os.cpu_count() or 4
YUK_TAVAN = float(os.environ.get("STUDIO_YUK", str(CEKIRDEK * 1.5)))
YUK_BEKLE = int(os.environ.get("STUDIO_YUK_BEKLE", "900"))
REVIZYON_TAVAN = 3
DILIM_DENEME = 3
YARGI_SEVIYE = int(os.environ.get("STUDIO_YARGI", "10"))
YARGI_MOD = os.environ.get("STUDIO_YARGI_MOD", "ai")  # ai | deterministik | claude | cursor
DEMO_ADIM = os.environ.get("STUDIO_DEMO", "playtest-1")  # oynanır demo: buraya kadar yazılım otonom
STUDIO_AI = os.environ.get("STUDIO_AI", "claude").strip().lower()  # claude | cursor
STUDIO_MODEL = os.environ.get("STUDIO_MODEL", "").strip()  # cursor --model

# İnsan kapısı türleri — yazılım sorusu ASLA kullanıcıya gitmez.
INSAN_OYUN_TIPI = "oyun_tipi"
INSAN_ASSET = "asset"
INSAN_DEMO = "demo"  # oynanır build hazır; his/onay sende
YAZILIM = "yazilim"

YASAK = ["CLAUDE.md", "studio.py", "00-charter.md", "01-secim.yaml", "07-yayin.yaml",
         ".claude/*", ".git/*", "tests/*", "06-slices/*", "assets/pipeline/harness.py", "tools/*",
         "runlog/durum.json", "runlog/ai-beyani.md", "runlog/*.log", "runlog/gece-gunlugu.md"]
# Anlık görüntüden yalnızca gerçekten ölçülemeyecek şeyler dışarıda kalır; "gürültü" diye
# dizin atlanmaz — atlanan dizin ajanın gizli yazım alanıdır. Motor çıktıları (.godot, .import)
# ilgili adımların kapsamına girer, görünmez olmaz.
ATLA = [".git/*", ".wt/*", ".DS_Store", "*/.DS_Store", "*/__pycache__/*", "runlog/.yedek*"]
MOTOR = ["game/.godot/*", "game/*.import", "game/*.uid", "game/*.translation"]  # Godot yan ürünleri: önbellek, .import, .uid, CSV→.translation
ONAYLI = ("onaylı", "onayli")
# Ajanın gelecekteki oturumları zehirleyebileceği yerler — her adımda önce/sonra ölçülür.
YETKI_YOLLARI = [Path.home() / ".claude" / ad for ad in
                 ("CLAUDE.md", "settings.json", "settings.local.json", "commands", "agents", "skills")]
YASAK_ARACLAR = ["Task", "Bash(git:*)", "Bash(rm:*)", "Write(~/.claude/**)", "Edit(~/.claude/**)"]
ID_KALIP = re.compile(r"^(chr|env|fx|ui|ico|sfx|mus|fnt|dat|mkt)_[a-z0-9]+(_[a-z0-9]+)*$")
ID_ARA = re.compile(r"\b(?:chr|env|fx|ui|ico|sfx|mus|fnt|dat|mkt)_[a-z0-9_]+")
ZORUNLU = ("id", "tip", "spec", "kaynak", "lisans", "oncelik", "durum", "revizyon")
CHARTER_BASLIKLAR = ("bütçe tavanı", "kapsam tavanı", "varlık bütçesi", "kırmızı çizgi",
                     "başarı tanımı", "kapasite")
SISTEM_EK = ("Türkçe yaz ve Türkçe karakterleri kullan (ş ı ğ ü ö ç İ); ASCII'ye düşürme. "
             "Tek adım yapıyorsun. Kapsamındaki dosyaları yaz ve bitir. Özet, sonraki adım "
             "önerisi, kutlama yazma. Kapsam dışı dosyaya dokunma. Bitince yalnızca şemadaki JSON "
             "raporu döndür: adim = görevdeki adım adı; yazilan = dokunduğun HER dosyanın repo köküne "
             "göre yolu (eksik ya da fazla bildirirsen tur reddedilir); kanit = çalıştırdığın her "
             "komut ve gerçek çıkış kodu; iddialar = yazdığın her sayısal iddia, kaynak URL'i ya da "
             "'tahmin'; durus = yalnız oyun tipi veya varlık (asset) kararı gerekiyorsa neden+soru, "
             "yazılım/kod/test/layout sorusu SORMA — kendin çöz veya revizyon notu bırak; yoksa null.")


class Dur(Exception):
    """Koşu durdu — genelde insan kapısı veya tavan."""


class Sor(Dur):
    """Ajan boşluk buldu. Yalnızca oyun tipi / asset soruları kullanıcıya gider; yazılım öz-yargıya düşer."""
    def __init__(self, msg, neden="", soru=""):
        super().__init__(msg)
        self.neden = neden
        self.soru = soru


class RaporYok(Dur):
    """Ajan işi yapmış olabilir ama şemalı JSON rapor döndürmedi — geri bildirimle tekrar denenir."""


# ================================================================== şemalar
# Ajanın dönüşü: CLI --json-schema ile zorlanır, studio jsonschema ile bir daha doğrular.
RAPOR_SEMA = {
    "type": "object", "additionalProperties": False,
    "required": ["adim", "yazilan", "kanit", "iddialar", "durus"],
    "properties": {
        "adim": {"type": "string"},
        "yazilan": {"type": "array", "items": {"type": "string", "pattern": "^[^/\\s][^\\s]*$"}},
        "kanit": {"type": "array", "items": {
            "type": "object", "additionalProperties": False, "required": ["komut", "cikis_kodu"],
            "properties": {"komut": {"type": "string", "minLength": 1}, "cikis_kodu": {"type": "integer"},
                           "sure_s": {"type": "number", "minimum": 0}}}},
        "iddialar": {"type": "array", "items": {
            "type": "object", "additionalProperties": False, "required": ["iddia", "kaynak"],
            "properties": {"iddia": {"type": "string", "minLength": 1},
                           "kaynak": {"type": "string", "pattern": "^(https?://\\S+|tahmin)$"}}}},
        "durus": {"oneOf": [{"type": "null"}, {
            "type": "object", "additionalProperties": False, "required": ["neden", "soru"],
            "properties": {"neden": {"type": "string", "minLength": 1}, "soru": {"type": "string", "minLength": 1}}}]},
    },
}
YARGI_SEMA = {
    "type": "object", "additionalProperties": False,
    "required": ["seviye", "yapilan", "yapilmasi_gereken", "dogru", "yanlis", "karar", "revizyon_notu", "skor"],
    "properties": {
        "seviye": {"type": "integer", "minimum": 1, "maximum": 10},
        "yapilan": {"type": "array", "items": {"type": "string", "minLength": 1}, "minItems": 1},
        "yapilmasi_gereken": {"type": "array", "items": {"type": "string", "minLength": 1}},
        "dogru": {"type": "array", "items": {"type": "string", "minLength": 1}},
        "yanlis": {"type": "array", "items": {"type": "string", "minLength": 1}},
        "karar": {"enum": ["onay", "revizyon"]},
        "revizyon_notu": {"oneOf": [{"type": "null"}, {"type": "string", "minLength": 1}]},
        "skor": {"type": "integer", "minimum": 1, "maximum": 10},
    },
}
ID_DESEN = "^(chr|env|fx|ui|ico|sfx|mus|fnt|dat|mkt)_[a-z0-9]+(_[a-z0-9]+)*$"
KATEGORI = ["chr", "env", "fx", "ui", "ico", "sfx", "mus", "fnt", "dat", "mkt"]
MANIFEST_SEMA = {"type": "array", "minItems": 1, "items": {
    "type": "object",
    "required": ["id", "tip", "spec", "kaynak", "lisans", "oncelik", "durum", "revizyon", "hash", "onay_tarihi"],
    "properties": {
        "id": {"type": "string", "pattern": ID_DESEN},
        "tip": {"type": "string", "minLength": 1},
        "spec": {"type": "string", "minLength": 3},
        "kaynak": {"enum": ["ai-üretim", "komisyon", "satın-alma", "cc0", "kendi"]},
        "lisans": {"type": "string"},
        "bagimli": {"type": "array", "items": {"type": "string"}},
        "kullanan": {"type": "array", "items": {"type": "string"}},
        "oncelik": {"type": "integer", "minimum": 1},
        "durum": {"enum": ["spec", "taslak", "revizyon", "onaylı", "kilitli"]},
        "revizyon": {"type": "integer", "minimum": 0},
        "revizyon_notu": {"type": "string"},
        "hash": {"type": "string"},
        "onay_tarihi": {"type": "string"},
    }}}
DILLER_VARSAYILAN = ["tr", "en"]


def strings_sema(diller=None):
    """Metin tablosu şeması. Grup adları (menu, hud, …) oyuna göre değişir: stüdyo sözlük dayatmaz.
    Zorunlu diller charter'ın 'Diller:' satırından gelir; charter susarsa tr+en."""
    diller = list(diller or DILLER_VARSAYILAN)
    alanlar = {d: {"type": "string", "minLength": 1} for d in diller}
    alanlar["not"] = {"type": "string"}
    return {"type": "object", "minProperties": 1, "additionalProperties": False,
            "patternProperties": {"^[a-z][a-z0-9_]*(\\.[a-z0-9_]+)+$": {
                "type": "object", "additionalProperties": False, "required": diller,
                "properties": alanlar}}}
VARLIKLAR_SEMA = {"type": "object", "required": ["kategoriler"], "additionalProperties": False, "properties": {
    "kategoriler": {"type": "array", "minItems": 1, "items": {
        "type": "object", "required": ["ad", "adet"], "additionalProperties": False,
        "properties": {"ad": {"enum": KATEGORI}, "adet": {"type": "integer", "minimum": 0},
                       "aciklama": {"type": "string"}}}}}}
BOLUMLER_SEMA = {"type": "array", "minItems": 1, "items": {
    "type": "object", "required": ["sira", "ad", "sure_dk"], "additionalProperties": False,
    "properties": {"sira": {"type": "integer", "minimum": 1}, "ad": {"type": "string", "minLength": 1},
                   "sure_dk": {"type": "integer", "minimum": 1}, "mekanik": {"type": "string"},
                   "notlar": {"type": "string"}}}}
EKRANLAR_SEMA = {"type": "array", "minItems": 1, "items": {
    "type": "object", "required": ["ad", "gecisler"], "additionalProperties": False,
    "properties": {"ad": {"type": "string", "minLength": 1}, "butonlar": {"type": "array", "items": {"type": "string"}},
                   "gecisler": {"type": "array", "items": {"type": "string"}}}}}
DENGE_SEMA = {"type": "object", "minProperties": 1}
SECIM_SEMA = {"type": "object", "additionalProperties": False, "properties": {
    "kisa_liste": {"type": "array", "minItems": 3, "maxItems": 4, "items": {"type": "string", "minLength": 1}},
    "secilen": {"type": "string", "minLength": 1}}}


def sema_dogrula(veri, sema, ad):
    try:
        jsonschema.validate(veri, sema)
    except jsonschema.ValidationError as e:
        yol = "/".join(str(x) for x in e.absolute_path) or "(kök)"
        raise Dur(f"{ad} şemaya uymuyor → {yol}: {e.message}")


# ================================================================== ölçüm

def eslesir(yol, kaliplar):
    for k in kaliplar:
        if k == "runlog/*.log":
            # Yalnızca stüdyonun kendi adım günlükleri (runlog/<adım>.log). Alt dizinlerdeki
            # bot/playtest günlükleri (runlog/playtest-bot-6/bolum1.log) yasak değildir;
            # fnmatch'te * bölü işaretini de yuttuğu için burada derinlik denetlenir.
            if yol.startswith("runlog/") and yol.endswith(".log") and yol.count("/") == 1:
                return True
            continue
        if fnmatch.fnmatch(yol, k):
            return True
    return False


def anlik_goruntu(kok=None):
    """{yol: (boyut, mtime)}; sembolik bağlar ("link", hedef) olarak ayrı işaretlenir."""
    kok = kok or KOK
    g = {}
    for p in kok.rglob("*"):
        yol = p.relative_to(kok).as_posix()
        if eslesir(yol, ATLA):
            continue
        if p.is_symlink():
            g[yol] = ("link", os.readlink(p))
        elif p.is_file():
            # İçerik hash'i: aynı içerikle yeniden yazılan dosya (pipeline yeniden koşusu) "değişti" sayılmaz.
            g[yol] = (p.stat().st_size, dosya_hash(p))
    return g


def bag_denetle(ad, once, sonra):
    """Sembolik bağ = repo dışına yazma kapısı. Ajanın yarattığı her bağ ret."""
    yeni = [y for y, v in sonra.items() if v[0] == "link" and once.get(y) != v]
    if yeni:
        raise Dur(f"{ad}: ajan sembolik bağ yarattı (repo dışına yazım kapısı): {yeni[:5]}")


def yetki_goruntusu():
    g = {}
    for kok in YETKI_YOLLARI:
        for p in ([kok] if kok.is_file() else kok.rglob("*") if kok.is_dir() else []):
            if p.is_file():
                st = p.stat()
                g[str(p)] = (st.st_size, st.st_mtime_ns)
    return g


def yetki_denetle(ad, once):
    degisen, silinen = fark(once, yetki_goruntusu())
    if degisen or silinen:
        raise Dur(f"{ad}: ajan yetki dosyalarına dokundu (sonraki oturumları zehirler): "
                  f"{(degisen + silinen)[:5]}. Elle geri al, sonra devam et.")


def git_goruntusu(kok=None):
    return (git("rev-parse", "HEAD", kok=kok, kontrol=False),
            git("stash", "list", kok=kok, kontrol=False),
            git("branch", "--show-current", kok=kok, kontrol=False))


def git_denetle(ad, once, kok=None):
    if once != git_goruntusu(kok):
        raise Dur(f"{ad}: ajan git durumunu değiştirdi (HEAD/stash/dal). Elle geri al, sonra devam et.")


def yuk():
    return os.getloadavg()[0]


def yuk_bekle(ad, tavan=None, bekle=None):
    """İşlemci nöbeti: load average tavanın üstündeyse adım başlatılmaz; düşene kadar 30 sn'de bir
    bakılır, süre dolarsa DUR. Yüklü makinede koşan ajan hem yavaş hem pahalıdır (zaman aşımı = $)."""
    tavan = YUK_TAVAN if tavan is None else tavan
    bekle = YUK_BEKLE if bekle is None else bekle
    baslangic = time.time()
    uyardi = False
    while yuk() > tavan:
        if time.time() - baslangic >= bekle:
            raise Dur(f"{ad}: makine yüklü (load {yuk():.0f} > tavan {tavan:.0f}, {CEKIRDEK} çekirdek) ve "
                      f"{bekle}s içinde düşmedi. Diğer süreçleri kapat ya da STUDIO_YUK'u büyüt.")
        if not uyardi:
            print(f"   \033[33myük {yuk():.0f} > {tavan:.0f}; düşmesi bekleniyor (≤{bekle}s)\033[0m")
            uyardi = True
        time.sleep(30)


def paralel_genislik():
    """Yük tavanın yarısını aştıysa paralellik 1'e iner."""
    return 1 if yuk() > YUK_TAVAN / 2 else PARALEL


def komut_kos(cmd, kok=None, sure=None, ortam=None):
    """Dış komut koşucusu: stdout/stderr DOSYAYA (pipe değil), stdin kapalı, kendi süreç grubu,
    zaman aşımında grup SIGKILL. Godot macOS'ta stdout pipe olunca alt süreç bırakıp asılı
    kalıyor; pipe ile bekleyen her çağrı 30 dk'yı yer. Döner: (çıkış_kodu | 'zaman aşımı', çıktı)."""
    import signal
    import tempfile
    with tempfile.TemporaryFile("w+", encoding="utf-8", errors="replace") as f:
        p = subprocess.Popen(["nice", "-n", str(NICE), *cmd], cwd=kok or KOK, stdout=f, stderr=subprocess.STDOUT,
                             stdin=subprocess.DEVNULL, start_new_session=True, env=ortam)
        try:
            kod = p.wait(timeout=sure or SURE)
        except subprocess.TimeoutExpired:
            try:
                os.killpg(p.pid, signal.SIGKILL)
            except ProcessLookupError:
                pass
            p.wait()
            kod = "zaman aşımı"
        f.seek(0)
        return kod, f.read()


def korumali_kos(ad, kapsam, fn):
    """Ajan yazımı bir komutu (pipeline, kanıt) studio koşarken yan etkisini ölç: kapsam dışına
    yazan/silen ya da yetki dosyasına dokunan komut = ret. Ajanın eli studio'nun eliyle uzamaz."""
    once_g, once_y = anlik_goruntu(), yetki_goruntusu()
    sonuc = fn()
    yetki_denetle(ad, once_y)
    sonra_g = anlik_goruntu()
    bag_denetle(ad, once_g, sonra_g)
    degisen, silinen = fark(once_g, sonra_g)
    disari = [y for y in degisen + silinen if eslesir(y, YASAK) or not eslesir(y, kapsam)]
    if disari:
        raise Dur(f"{ad}: koşulan komut kapsam dışına yazdı/sildi: {disari[:6]}")
    return sonuc


def fark(once, sonra):
    return (sorted(y for y, v in sonra.items() if once.get(y) != v),
            sorted(set(once) - set(sonra)))


def dosya_hash(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()[:16]


def agac_hash(kok):
    """Motor yan ürünleri (*.import, .godot/) hariç — pipeline'ın değil Godot'un yazdığı dosyalar."""
    return {p.relative_to(kok).as_posix(): dosya_hash(p) for p in Path(kok).rglob("*")
            if p.is_file() and not eslesir("game/" + p.relative_to(kok).as_posix(), MOTOR)} if Path(kok).exists() else {}


def oku(yol, kok=None):
    try:
        return ((kok or KOK) / yol).read_text(encoding="utf-8")
    except FileNotFoundError:
        raise Dur(f"{yol} yok.")


def yaml_oku(yol, sema=None):
    try:
        veri = yaml.safe_load(oku(yol))
    except yaml.YAMLError as e:
        raise Dur(f"{yol}: YAML ayrıştırılamadı → {e}")
    if sema is not None:
        sema_dogrula(veri, sema, yol)
    return veri


def git(*args, kok=None, kontrol=True):
    s = subprocess.run(["git", "-C", str(kok or KOK), *args], capture_output=True, text=True)
    if kontrol and s.returncode != 0:
        raise Dur(f"git {' '.join(args)} → {s.stderr.strip() or s.stdout.strip()}")
    return s.stdout.rstrip("\n")  # porcelain satırlarının baştaki boşluğu anlamlı


# ----------------------------------------------------------------- manifest

def manifest_kayitlari(metin=None):
    if metin is None:
        if not MANIFEST.exists():
            return []
        metin = MANIFEST.read_text(encoding="utf-8")
    try:
        veri = yaml.safe_load(metin) or []
    except yaml.YAMLError:
        return []
    return [k for k in veri if isinstance(k, dict) and "id" in k] if isinstance(veri, list) else []


def manifest_alanlari(metin=None):
    """{id: (durum, hash, onay_tarihi)} — onay alanlarının nöbeti."""
    return {k["id"]: (str(k.get("durum")), str(k.get("hash")), str(k.get("onay_tarihi")))
            for k in manifest_kayitlari(metin)}


def manifest_guncelle(kimlik, **alanlar):
    """Satır bazlı düzenleme — yorumlar ve sıralama korunur."""
    satirlar = MANIFEST.read_text(encoding="utf-8").splitlines()
    bas = next((n for n, s in enumerate(satirlar)
                if re.match(rf"\s*-\s*id:\s*{re.escape(kimlik)}\s*(#.*)?$", s)), None)
    if bas is None:
        raise Dur(f"manifest'te bulunamadı: {kimlik}")
    son = next((n for n in range(bas + 1, len(satirlar))
                if satirlar[n].lstrip().startswith("- id:")), len(satirlar))
    for alan, deger in alanlar.items():
        for n in range(bas, son):
            if re.match(rf"\s*{alan}:", satirlar[n]):
                girinti = " " * (len(satirlar[n]) - len(satirlar[n].lstrip()))
                satirlar[n] = f"{girinti}{alan}: {deger}"
                break
        else:
            satirlar.insert(son, f"  {alan}: {deger}")
            son += 1
    MANIFEST.write_text("\n".join(satirlar) + "\n", encoding="utf-8")


def ham_dosya(kimlik):
    """Tam olarak bir ham dosya: aynı gövde adlı ikinci dosya belirsizlik = ret."""
    if not HAM.exists():
        return None
    adaylar = [p for p in HAM.rglob("*") if p.is_file() and p.stem == kimlik and "_style" not in p.parts]
    if len(adaylar) > 1:
        raise Dur(f"{kimlik}: birden fazla ham dosya var {[a.name for a in adaylar]} — hangisi doğrulanacak belirsiz.")
    return adaylar[0] if adaylar else None


def hash_kilidi():
    """5D: onaylı ham dosya arkadan değişmişse her adımda yakala."""
    bozuk = []
    for kimlik, (durum, h, _t) in manifest_alanlari().items():
        if durum not in ONAYLI or h in ("-", "None", ""):
            continue
        p = ham_dosya(kimlik)
        if p and dosya_hash(p) != h:
            manifest_guncelle(kimlik, durum="revizyon")
            bozuk.append(kimlik)
    if bozuk:
        raise Dur(f"Hash kilidi: onaydan sonra değişmiş ham dosya → {bozuk}. "
                  "'revizyon'a düşürüldü; yeniden onayına gelecek.")


# ----------------------------------------------------------------- charter

def charter_bilgi():
    p = KOK / "00-charter.md"
    if not p.exists():
        return None
    m = p.read_text(encoding="utf-8")
    kucuk = m.lower()

    def sayi(kalip):
        r = re.search(kalip, kucuk)
        return int(r.group(1)) if r else None

    kirmizi = []
    blok = re.split(r"^#+ .*kırmızı çizgi.*$", m, flags=re.M | re.I)
    if len(blok) > 1:
        for s in blok[1].splitlines():
            if re.match(r"^#+ ", s):
                break
            if s.strip().startswith(("-", "*")):
                kirmizi.append(s.strip().lstrip("-* ").strip())
    tarih = re.search(r"yayın tarihi\D{0,20}(\d{4}-\d{2}-\d{2})", kucuk)
    diller = re.search(r"diller\s*[:=]\s*([a-z]{2}(?:\s*[,+/]\s*[a-z]{2})*)", kucuk)
    return {"eksik": [b for b in CHARTER_BASLIKLAR if b not in kucuk],
            "diller": re.split(r"[,+/]\s*", diller.group(1).replace(" ", "")) if diller else list(DILLER_VARSAYILAN),
            "varlik": sayi(r"varlık bütçesi\D{0,20}(\d+)"),
            "paket_mb": sayi(r"paket (?:bütçesi|boyutu)\D{0,20}(\d+)\s*mb"),
            "doku_mb": sayi(r"doku belleği\D{0,20}(\d+)\s*mb"),
            "saat_hafta": sayi(r"haftada\s*(\d+)\s*saat"),
            "kirmizi": kirmizi,
            "yayin": datetime.date.fromisoformat(tarih.group(1)) if tarih else None}


def kirmizi_tarama(dosyalar):
    """Kırmızı çizgideki anahtar kelime sonraki dokümanlarda geçiyor mu (uyarı)."""
    bilgi = charter_bilgi() or {}
    uyari = []
    for cizgi in bilgi.get("kirmizi", []):
        anahtar = re.split(r"\s+(yok|olmayacak|yasak)", cizgi.lower())[0].strip()
        if len(anahtar) < 3:
            continue
        for d in dosyalar:
            if (KOK / d).exists() and anahtar in oku(d).lower():
                uyari.append(f"kırmızı çizgi '{cizgi}' → '{anahtar}' {d} içinde geçiyor")
    return uyari


def secim_oku():
    if not SECIM.exists():
        return {}
    veri = yaml.safe_load(SECIM.read_text(encoding="utf-8")) or {}
    sema_dogrula(veri, SECIM_SEMA, "01-secim.yaml")
    return veri


def secim_yaz(alan, deger):
    veri = secim_oku()
    veri[alan] = deger
    SECIM.write_text(yaml.safe_dump(veri, allow_unicode=True, sort_keys=False), encoding="utf-8")


def komut_metni(ad, arg="", ek=""):
    metin = (KOMUTLAR / f"{ad}.md").read_text(encoding="utf-8")
    if metin.startswith("---"):
        p = metin.split("---", 2)
        metin = p[2] if len(p) == 3 else metin
    metin = metin.replace("$ARGUMENTS", arg).strip()
    return f"{metin}\n\n{ek}".strip() if ek else metin


# ============================================================ doğrulayıcılar

def dg_market(_):
    metin = oku("01-market.md")
    if len(re.findall(r"^\|", metin, re.M)) < 5:
        raise Dur("01-market.md: skor tablosu yok.")
    supheli = [s.strip() for s in metin.splitlines()
               if re.search(r"\d{2,}", s) and "http" not in s and "[tahmin]" not in s
               and not s.lstrip().startswith(("#", "|"))]
    return [f"kaynaksız olabilecek {len(supheli)} satır (ilk: {supheli[0][:60]})"] if supheli else []


TR_DUZ = str.maketrans("çğıöşüÇĞİÖŞÜ", "cgiosuCGIOSU")


def duz(s):
    """Türkçe karakterleri düzle + küçült: 'Sıra Tabanlı' ≡ 'sira tabanli' (seçim adı eşleşmesi)."""
    return s.translate(TR_DUZ).lower()


def dg_derin(_):
    metin = oku("01-market.md")
    if "derin analiz" not in metin.lower():
        raise Dur("01-market.md: 'Derin analiz' bölümü yok.")
    derin = duz(metin.split("Derin Analiz", 1)[1] if "Derin Analiz" in metin else metin.lower().split("derin analiz", 1)[1])
    eksik = [k for k in secim_oku().get("kisa_liste", []) if duz(k) not in derin]
    if eksik:
        raise Dur(f"Derin analizde kısa listedeki konsept yok: {eksik}")
    for baslik in ("teardown", "inceleme", "ölü oyun", "varlık say"):
        if duz(baslik) not in derin:
            raise Dur(f"Derin analizde '{baslik}' bölümü yok.")
    return dg_market(_)


def dg_tech(_):
    metin = oku("02-tech.md")
    for baslik in ("salt referans", "bağımlılık"):
        if baslik not in metin.lower():
            raise Dur(f"02-tech.md: '{baslik}' kutusu yok.")
    # Bağımlılık kutusu = "bağımlılık" geçen başlıktan sonraki, aynı ya da üst seviye başlığa kadarki metin
    # (salt referans kutusu hemen ardından gelir ve orada GPL geçmesi normaldir).
    kutu = re.search(r"^(#+)[^\n]*bağımlılık[^\n]*\n(.*?)(?=^\1 |^#{1,2} |\Z)", metin, re.M | re.S | re.I)
    if not kutu:
        raise Dur("02-tech.md: 'Bağımlılık' başlıklı kutu yok.")
    if re.search(r"\b[al]?gpl\b", kutu.group(2), re.I):
        raise Dur("02-tech.md: bağımlılık kutusunda GPL/AGPL/LGPL geçiyor — oraya giremez.")
    if not re.search(r"\b(44100|48000|22050)\b", metin):
        raise Dur("02-tech.md: ses örnekleme hızı sayı olarak yazılmamış.")
    if not re.search(r"\b\d+\s*[x×]\s*\d+\b", metin):
        raise Dur("02-tech.md: sprite hücre boyutu sayı olarak yazılmamış.")
    # Pilot dersi: çözünürlük Faz 6'da değişti, 3 dilim ve 14 test iddiası kırıldı. Burada kilitlenir.
    kucuk = metin.lower()
    if not re.search(r"çözünürlük\D{0,40}\d{3,4}\s*[x×]\s*\d{3,4}", kucuk):
        raise Dur("02-tech.md: taban çözünürlük yazılmamış (ör. 'Taban çözünürlük: 1920×1080'). "
                  "Pilotta bu Faz 6'da değişti ve 3 dilim + 14 test iddiası kırdı.")
    if not re.search(r"karo\D{0,40}\d{2,4}\s*(px|piksel)", kucuk):
        raise Dur("02-tech.md: karo boyutu piksel olarak yazılmamış (ör. 'Karo: 96 px').")
    if not re.search(r"ölçek modu\s*[:=]", kucuk):
        raise Dur("02-tech.md: 'Ölçek modu:' satırı yok (tam sayı / kesirli / kapalı).")
    kanit = oku("runlog/faz2-kanit.md").lower()
    if "çıkış kodu" not in kanit and "exit" not in kanit:
        raise Dur("runlog/faz2-kanit.md: test/build çıkış kodu yazılmamış — kanıt yok.")
    if not (KOK / "runlog/faz2-kanit/project.godot").exists():
        raise Dur("runlog/faz2-kanit/project.godot yok — kanıt prototipi kapsam içinde üretilmemiş.")
    uyari = kirmizi_tarama(["02-tech.md"])
    sure = re.search(r"build[^\n]{0,60}?(\d+)\s*(sn|saniye|s)\b", kanit)
    if sure and int(sure.group(1)) > 120:
        uyari.append(f"build süresi {sure.group(1)}s > 120s — yapım fazı acı verir")
    return uyari


def adet_topla(veri):
    return sum(k["adet"] for k in veri["kategoriler"])


def dg_gdd(_):
    for ad, sema in (("ekranlar", EKRANLAR_SEMA), ("bolumler", BOLUMLER_SEMA), ("denge", DENGE_SEMA)):
        yaml_oku(f"gdd/{ad}.yaml", sema)
    butce = (charter_bilgi() or {}).get("varlik")
    toplam = adet_topla(yaml_oku("gdd/varliklar.yaml", VARLIKLAR_SEMA))
    if butce and toplam > butce:
        raise Dur(f"Varlık envanteri {toplam} > charter bütçesi {butce}. Kararı sen ver.")
    onayli = durum_oku().get("ornek_hash", {}).get("gdd/varliklar.yaml")
    if onayli and dosya_hash(KOK / "gdd/varliklar.yaml") != onayli:
        raise Dur("gdd/varliklar.yaml onayladığın örnekten farklı — envanter değişikliğine sen karar ver.")
    metin = oku("03-gdd.md")
    for kacamak in ("sonra netleştir", "tbd", "belirlenecek"):
        if kacamak in metin.lower():
            raise Dur(f"03-gdd.md'de boşluk bırakılmış: '{kacamak}'")
    if len(re.findall(r"^#{1,3} ", metin, re.M)) < 10:
        raise Dur("03-gdd.md: 10 açının hepsi başlık olarak yok.")
    kapsam_disi = re.split(r"^#+ .*kapsam disi.*$", duz(metin), flags=re.M)  # 'Dışı' ve ASCII 'Disi' ikisi de
    madde = len(re.findall(r"^\s*(?:[-*]|\d+[.)])\s+\S", kapsam_disi[1], re.M)) if len(kapsam_disi) > 1 else 0
    if madde < 15:
        raise Dur(f"03-gdd.md: kapsam dışı listesi {madde} madde, en az 15 gerekli.")
    return kirmizi_tarama(["03-gdd.md"])


def dg_bolum(arg):
    yol = f"03-levels/bolum-{arg}.md"
    metin = oku(yol)
    if len(metin) < 200:
        raise Dur(f"{yol}: içerik yok denecek kadar kısa.")
    kategoriler = {k["ad"] for k in yaml_oku("gdd/varliklar.yaml", VARLIKLAR_SEMA)["kategoriler"] if k["adet"] > 0}
    bilinmeyen = [i for i in set(ID_ARA.findall(metin)) if i.split("_")[0] not in kategoriler]
    if bilinmeyen:
        raise Dur(f"{yol}: envanterde adedi olmayan kategoriden id: {sorted(bilinmeyen)[:8]}")
    if not re.search(r"\d+\s*(dk|dakika)", metin, re.I):
        raise Dur(f"{yol}: tahmini süre yazılmamış.")
    return []


def bolum_sure(metin):
    m = re.search(r"(\d+)\s*(dk|dakika)", metin, re.I)
    return int(m.group(1)) if m else 0


def k_bolum_toplam():
    """Kapı 3B: bölümlerin toplam süresi GDD'deki iddiayla uyuşuyor mu."""
    dosyalar = sorted((KOK / "03-levels").glob("bolum-*.md"))
    if not dosyalar:
        return None
    gercek = sum(bolum_sure(p.read_text(encoding="utf-8")) for p in dosyalar)
    iddia = sum(k["sure_dk"] for k in yaml_oku("gdd/bolumler.yaml", BOLUMLER_SEMA))
    if abs(gercek - iddia) > iddia * 0.2:
        return (f"Bölüm süreleri toplamı {gercek} dk, gdd/bolumler.yaml iddiası {iddia} dk "
                "(sapma >%20). GDD ya da bölümler değişmeli — kararı sen ver.")
    return None


def charter_diller():
    return (charter_bilgi() or {}).get("diller") or list(DILLER_VARSAYILAN)


def dg_strings(_):
    diller = charter_diller()
    yaml_oku("03-strings.yaml", strings_sema(diller))
    return [f"metin tablosu {len(diller)} dilde: {', '.join(diller)}"]


def palet_oku():
    """04-style.md'deki hex renkler. harness aynısını yapar ama o Faz 4C çıktısı ve Faz 4A
    ondan önce koşuyor — bu yüzden studio kendi okur."""
    return {h.lower() for h in re.findall(r"#([0-9a-fA-F]{6})\b", oku("04-style.md"))}


def dg_stil(_):
    metin = oku("04-style.md")
    if len(palet_oku()) < 3:
        raise Dur("04-style.md: palet hex değerleriyle yazılmamış (en az 3).")
    if "uygulanmayacak" not in metin.lower():
        raise Dur("04-style.md: 'uygulanmayacaklar' listesi yok.")
    gorseller = [p for p in (KOK / "assets/raw/_style").glob("*") if p.is_file()] \
        if (KOK / "assets/raw/_style").exists() else []
    if len(gorseller) < 3:
        raise Dur(f"assets/raw/_style/: en az 3 anahtar görsel bekleniyor, {len(gorseller)} var.")
    if not HARNESS_VAR:
        # Piksel düzeyi denetim harness'e muhtaç; o Faz 4C çıktısı. Palet, 'uygulanmayacaklar'
        # ve 3 görsel şartı burada tutuyor, piksel kontrolü Faz 5 kapısında yapılıyor.
        return [f"harness.py henüz yok — {len(gorseller)} stil görseli piksel düzeyinde palet "
                "denetiminden GEÇMEDİ; Faz 5'te denetlenecek."]
    hatalar = {p.name: harness.png_kontrol(p, "", harness.palet_oku())
               for p in gorseller if p.suffix == ".png"}
    hatalar = {k: v for k, v in hatalar.items() if v}
    if hatalar:
        raise Dur(f"_style görselleri kendi paletine uymuyor: {hatalar}")
    return []


def dg_manifest(_):
    kayitlar = yaml_oku("assets/manifest.yaml", MANIFEST_SEMA)
    for k in kayitlar:
        if str(k["durum"]) != "spec":
            raise Dur(f"manifest '{k['id']}': durum '{k['durum']}' — 4B'de hepsi 'spec' olmalı.")
        if not harness.spec_boyut(k["spec"]) and k["id"].split("_")[0] in ("chr", "env", "fx", "ui", "ico", "mkt"):
            raise Dur(f"manifest '{k['id']}': spec'te boyut (WxH) yok.")
    idler = [k["id"] for k in kayitlar]
    if len(set(idler)) != len(idler):
        raise Dur("manifest: tekrar eden id var.")
    if not any(i.startswith("mkt_") for i in idler):
        raise Dur("manifest: Steam pazarlama varlıkları (mkt_*) yok.")
    if (KOK / "gdd/varliklar.yaml").exists():
        envanter = {k["ad"]: k["adet"] for k in yaml_oku("gdd/varliklar.yaml", VARLIKLAR_SEMA)["kategoriler"]}
        for kat in set(i.split("_")[0] for i in idler):
            n = sum(1 for i in idler if i.startswith(kat + "_"))
            if n > envanter.get(kat, 0):
                raise Dur(f"manifest'te {kat}_* {n} adet, gdd/varliklar.yaml envanteri {envanter.get(kat, 0)}. "
                          "Envanter değişikliğine sen karar ver.")
    bilgi = charter_bilgi() or {}
    if bilgi.get("varlik") and len(kayitlar) > bilgi["varlik"]:
        raise Dur(f"manifest {len(kayitlar)} satır > charter bütçesi {bilgi['varlik']}.")
    for bolum in sorted((KOK / "03-levels").glob("bolum-*.md")):
        eksik = [i for i in set(ID_ARA.findall(bolum.read_text(encoding="utf-8"))) if i not in idler]
        if eksik:
            raise Dur(f"{bolum.name} kullanıyor ama manifest'te yok: {sorted(eksik)[:8]}")
    kategori = {}
    for i in idler:
        kategori[i.split("_")[0]] = kategori.get(i.split("_")[0], 0) + 1
    onay_saat = len(idler) * 90 / 3600
    uyari = [f"{len(idler)} varlık {dict(sorted(kategori.items()))}, onay yükü ~{onay_saat:.1f} saat"]
    if bilgi.get("saat_hafta") and onay_saat > bilgi["saat_hafta"] * 3:  # Faz 4 takvimde 3 hafta
        uyari.append(f"onay yükü {onay_saat:.1f} saat > kapasiten {bilgi['saat_hafta']} saat/hafta x 3 hafta")
    return uyari


def dg_parti(arg):
    rapor = KOK / f"runlog/parti-{arg}.html"
    metin = rapor.read_text(encoding="utf-8", errors="ignore")
    kayitlar = manifest_kayitlari()
    taslak = [k for k in kayitlar if str(k.get("durum")) == "taslak"]  # önceki parti kararsız olamaz (k_parti_on)
    # Kullanıcı kapıdan önce --onayla ile onayladıysa o varlıklar da bu partinindir (sayfada geçenler);
    # aksi halde "taslak yok" diye düşer ve adım boşuna yeniden koşar.
    taslak += [k for k in kayitlar if str(k.get("durum")) in ONAYLI and k["id"] in metin]
    if not taslak:
        raise Dur(f"parti-{arg}: 'taslak' durumuna geçen varlık yok.")
    gorunmeyen = [k["id"] for k in taslak if k["id"] not in metin]
    if gorunmeyen:
        raise Dur(f"parti-{arg}: kontakt sayfasında yok: {gorunmeyen[:8]}")
    # Sayfa gerçek dosyayı gömmeli — id'yi metin olarak yazmak "gösterdim" sayılmaz.
    gomulu = set()
    for src in re.findall(r'(?:src|href)="([^"]+)"', metin):
        try:
            gomulu.add((rapor.parent / src).resolve())
        except OSError:
            pass
    gommeyen = [k["id"] for k in taslak if ham_dosya(k["id"]) and ham_dosya(k["id"]).resolve() not in gomulu]
    if gommeyen:
        raise Dur(f"parti-{arg}: kontakt sayfası ham dosyayı görseli gömmüyor (<img src=\"../assets/raw/...\">): {gommeyen[:8]}")
    hatalar = {}
    for k in taslak:
        p = ham_dosya(k["id"])
        h = ["ham dosya yok"] if not p else harness.varlik_kontrol(k["id"], k.get("spec", ""), p)
        if h:
            hatalar[k["id"]] = h
    if hatalar:
        raise Dur(f"parti-{arg}: harness'ten geçmeyen varlıklar → {dict(list(hatalar.items())[:5])}")
    return []


def godot_var():
    return shutil.which(GODOT) is not None and (KOK / "game/project.godot").exists()


def dg_hazirla(_):
    reg = oku("game/assets/registry.gd")
    onayli = [k for k, v in manifest_alanlari().items() if v[0] in ONAYLI]
    eksik = [i for i in onayli if i.upper() not in reg.upper()]
    if eksik:
        raise Dur(f"registry.gd'de karşılığı yok: {eksik[:8]}")
    kayip = [y for y in re.findall(r'"(res://[^"]+)"', reg) if not (KOK / "game" / y[6:]).exists()]
    if kayip:
        raise Dur(f"registry.gd var olmayan dosyaya işaret ediyor: {kayip[:5]}")
    if "ÜRETİLMİŞ" not in reg.splitlines()[0]:
        raise Dur("registry.gd ilk satırında 'ÜRETİLMİŞ DOSYA' uyarısı yok.")
    if not (KOK / "game/assets/strings.gd").exists() and "Strings" not in reg:
        raise Dur("03-strings.yaml'dan Strings sınıfı üretilmemiş.")
    uyari = []
    for tablo in (KOK / "game/assets").rglob("*.json"):
        png = tablo.with_suffix(".png")
        if png.exists() and "kareler" in tablo.read_text(encoding="utf-8", errors="ignore"):
            h = harness.atlas_sizma(png, tablo)
            if h:
                raise Dur(f"atlas sızma testi: {tablo.name} → {h[:4]}")
    if shutil.which(GODOT) and not (KOK / "game/project.godot").exists():
        raise Dur("game/project.godot yok — registry motorda derlenmeden Faz 5 kapanmaz (pipeline üretmeli).")
    if godot_var():
        kod, cikti = komut_kos([GODOT, "--headless", "--path", "game", "--check-only",
                                "-s", "res://assets/registry.gd"], sure=300)
        if kod != 0:
            raise Dur(f"registry.gd motorda derlenmiyor (çıkış {kod}):\n{cikti[-800:]}")
        if "preload(" not in reg:
            raise Dur("registry.gd sabitleri preload(...) olmalı — yol string'i eksik dosyayı sessizce geçirir.")
        # Derlenmek yetmez: preload'lar çalışma zamanında YÜKLENMELİ (import edilmemiş PNG = parse error, 0 sabit).
        betik = RUNLOG / ".registry_yukle.gd"
        betik.write_text('extends SceneTree\nfunc _initialize():\n\tvar r = load("res://assets/registry.gd")\n'
                         '\tvar n = r.get_script_constant_map().size() if r else 0\n'
                         '\tprint("REGISTRY_SABIT=", n)\n\tquit(0 if n > 0 else 1)\n', encoding="utf-8")
        kod, cikti = komut_kos([GODOT, "--headless", "--path", "game", "-s", str(betik.resolve())], sure=300)
        m = re.search(r"REGISTRY_SABIT=(\d+)", cikti)
        sabit = int(m.group(1)) if m else 0
        # Çeviri kapısı charter'ın dillerini dolaşır; beklenen değer 03-strings.yaml'ın ilk anahtarından okunur.
        diller = charter_diller()
        tablo = yaml_oku("03-strings.yaml", strings_sema(diller))
        anahtar, beklenen = next(iter(tablo.items()))
        cev = RUNLOG / ".ceviri_yukle.gd"
        govde = "".join(f'\tTranslationServer.set_locale("{d}")\n\tprint("CEVIRI_{d.upper()}=", tr("{anahtar}"))\n'
                        for d in diller)
        cev.write_text(f'extends SceneTree\nfunc _initialize():\n{govde}\tquit(0)\n', encoding="utf-8")
        ckod, ccikti = komut_kos([GODOT, "--headless", "--path", "game", "-s", str(cev.resolve())], sure=300)
        bulunan = {d: (re.search(rf"CEVIRI_{d.upper()}=(.*)", ccikti) or [None, ""])[1].strip() for d in diller}
        eksik = [d for d in diller if bulunan[d] != beklenen[d]]
        if eksik:
            raise Dur(f"Çeviriler çalışma zamanında gelmiyor — tr(\"{anahtar}\") şu dillerde tutmadı: {eksik}\n"
                      + "\n".join(f"  {d}: beklenen {beklenen[d]!r}, bulunan {bulunan[d]!r}" for d in eksik)
                      + "\nproject.godot translations + import kontrol et.\n" + ccikti[-500:])
        if kod != 0 or sabit < len(onayli):
            raise Dur(f"registry.gd çalışma zamanında yüklenmiyor ({sabit} sabit, {len(onayli)} onaylı varlık). "
                      "Sebep çoğu zaman import edilmemiş varlıklar: pipeline sonunda 'godot --headless --path game --import' "
                      f"koşmalı.\n{cikti[-600:]}")
    else:
        uyari.append("godot bulunamadı — motor yükleme testi atlandı")
    kod = " ".join(p.read_text(encoding="utf-8", errors="ignore")
                   for p in (KOK / "game").rglob("*.gd") if "assets" not in p.parts)
    yetim = [i for i in onayli if i.upper() not in kod.upper()]
    if yetim:
        uyari.append(f"{len(yetim)} yetim varlık (üretildi, koddan referans yok)")
    bilgi = charter_bilgi() or {}
    paket, doku = harness.paket_olcumu(KOK / "game/assets")
    uyari.append(f"paket {paket / 1e6:.1f} MB, doku belleği {doku / 1e6:.1f} MB")
    # Paket boyutu sınırlanmaz (kullanıcı kararı 2026-09-04): yalnızca bilgi olarak raporlanır.
    if bilgi.get("doku_mb") and doku > bilgi["doku_mb"] * 1e6:
        raise Dur(f"doku belleği {doku / 1e6:.1f} MB > charter bütçesi {bilgi['doku_mb']} MB")
    if not bilgi.get("doku_mb"):
        uyari.append("charter'da 'doku belleği: N MB' yok, doku bütçesi ölçülmedi")
    return uyari


def dg_playtest(arg):
    if not (RUNLOG / f"playtest-{arg}-notlar.md").exists():
        raise Dur(f"runlog/playtest-{arg}-notlar.md üretilmemiş.")
    build = KOK / "build"
    if not build.exists() or not any(build.rglob("*")):
        raise Dur("build/ boş — oynanabilir build alınmamış.")
    return []


def dg_yayin(_):
    metin = oku("07-yayin.md")
    if not re.search(r"^##.*(türkçe|tr)\b", metin, re.M | re.I) or \
       not re.search(r"^##.*(english|en)\b", metin, re.M | re.I):
        raise Dur("07-yayin.md: '## Türkçe' ve '## English' başlıkları yok.")
    mkt = [k for k, v in manifest_alanlari().items() if k.startswith("mkt_")]
    eksik = [k for k in mkt if k not in metin]
    if eksik:
        raise Dur(f"07-yayin.md: capsule listesinde yok: {eksik}")
    onaysiz = [k for k in mkt if manifest_alanlari()[k][0] not in ONAYLI]
    if onaysiz:
        raise Dur(f"Onaysız pazarlama varlığı: {onaysiz}")
    if len(re.findall(r"\d{4}-\d{2}-\d{2}", metin)) < 5:
        raise Dur("07-yayin.md: takvimde 5 gerçek tarih yok.")
    kapsam_disi = re.split(r"^#+ .*kapsam dışı.*$", oku("03-gdd.md"), flags=re.M | re.I)
    if len(kapsam_disi) > 1:
        maddeler = [m.strip("-* ").strip().lower() for m in kapsam_disi[1].splitlines() if m.strip().startswith(("-", "*"))]
        vaat = [m for m in maddeler if len(m) > 4 and m.split()[0] in metin.lower()]
        return [f"kapsam dışı madde mağaza metninde geçiyor olabilir: {vaat[:5]}"] if vaat else []
    return []


def dg_dilim(adim, kok):
    komut = kok / TEST_KOMUT
    if not komut.exists():
        raise Dur(f"{TEST_KOMUT} yok — testsiz dilim merge edilmez. Test koşucusunu sen yaz.")
    kod, cikti = komut_kos(["bash", str(komut)], kok)
    (RUNLOG / f"{adim}-test.log").write_text(cikti, encoding="utf-8")
    if kod != 0:
        raise Dur(f"testler kırmızı (çıkış {kod}):\n{cikti[-1500:]}")
    return []


ORNEK_3A = ("ÖRNEK TURU: tam dokümanı yazma. 03-gdd.md'ye YALNIZCA 1. açı (çekirdek döngü) ve "
            "7. açıyı (sanat yönü ve varlık envanteri, sayıyla) yaz; gdd/varliklar.yaml'ı tam üret. "
            "Diğer açıları ve diğer yaml'ları yazma. Bu bir biçim ve ton kontrolüdür.")
TAM_3A = ("ÖRNEK ONAYLANDI: 03-gdd.md'deki mevcut 1. ve 7. açı ile gdd/varliklar.yaml'ı KORU "
          "(varliklar.yaml'ı değiştirirsen tur reddedilir); aynı biçim ve tonda kalan her şeyi tamamla.")
ORNEK_3B = ("ÖRNEK BÖLÜM: bu ilk bölüm, sonraki tüm bölümlerin biçim referansı olacak. Layout formatını "
            "(ASCII ya da JSON) burada seç; diğerleri aynısını kullanacak.")
TAM_3B = ("BİÇİM REFERANSI: 03-levels/bolum-01.md onaylandı; aynı layout formatını ve bölüm yapısını "
          "birebir kullan.")
ORNEK_3C = ("ÖRNEK TURU: 03-strings.yaml'a yalnızca menu.* ve hud.* gruplarını yaz (en az 10 anahtar). "
            "Diğer grupları yazma. Bu bir ton kontrolüdür.")
TAM_3C = ("ÖRNEK ONAYLANDI: mevcut menu.*/hud.* anahtarlarını ve tonunu koru, kalan tüm grupları tamamla.")


def dg_ornek_gdd(_):
    metin = oku("03-gdd.md").lower()
    for gerekli in ("çekirdek döngü", "envanter"):
        if gerekli not in metin:
            raise Dur(f"örnek 03-gdd.md'de '{gerekli}' yok.")
    butce = (charter_bilgi() or {}).get("varlik")
    toplam = adet_topla(yaml_oku("gdd/varliklar.yaml", VARLIKLAR_SEMA))
    if butce and toplam > butce:
        raise Dur(f"Varlık envanteri {toplam} > charter bütçesi {butce}. Kararı sen ver.")
    return [f"envanter toplamı {toplam}" + (f" / bütçe {butce}" if butce else "")]


def dg_ornek_strings(_):
    dg_strings(_)
    veri = yaml_oku("03-strings.yaml")
    if sum(1 for k in veri if k.startswith(("menu.", "hud."))) < 10:
        raise Dur("örnek 03-strings.yaml'da menu.*/hud.* altında en az 10 anahtar olmalı.")
    return []


# ================================================================ sonrası

def hash_yaz():
    uyari = []
    for kimlik, (durum, eski, _t) in manifest_alanlari().items():
        p = ham_dosya(kimlik)
        if not p:
            continue
        yeni = dosya_hash(p)
        if eski in ("-", "None", ""):
            manifest_guncelle(kimlik, hash=yeni)
        elif eski != yeni:
            manifest_guncelle(kimlik, hash=yeni, durum="revizyon")
            uyari.append(f"{kimlik}: ham dosya onaydan sonra değişmiş → revizyon")
    return uyari


def idempotens():
    giris = KOK / "assets/pipeline/hazirla.sh"
    if not giris.exists():
        raise Dur("assets/pipeline/hazirla.sh yok — idempotens ölçülemedi, giriş noktası şart.")
    hedef, yedek = KOK / "game/assets", RUNLOG / ".yedek-game-assets"
    once = agac_hash(hedef)
    if yedek.exists():
        shutil.rmtree(yedek)
    shutil.move(str(hedef), str(yedek))
    try:
        kod, cikti = korumali_kos("idempotens", ["game/assets/*", "game/project.godot"] + MOTOR,
                                  lambda: komut_kos(["bash", str(giris)]))
    except Dur:
        if hedef.exists():
            shutil.rmtree(hedef)
        shutil.move(str(yedek), str(hedef))
        raise
    sonra = agac_hash(hedef)
    if kod != 0 or once != sonra:
        if hedef.exists():
            shutil.rmtree(hedef)
        shutil.move(str(yedek), str(hedef))
        ayrik = sorted(set(once) ^ set(sonra)) or [k for k in once if once[k] != sonra.get(k)]
        raise Dur(f"İdempotens düştü (çıkış {kod}). Farklı: {ayrik[:8]}. Çıktı geri yüklendi.")
    shutil.rmtree(yedek)
    return [f"idempotens tamam ({len(sonra)} dosya birebir aynı)"]


def hazirla_sonrasi():
    return hash_yaz() + idempotens()


def ai_beyani():
    """Steam AI beyanı — manifest'in kaynak alanından, oyuncunun tükettiği kategoriler."""
    tuketilen = {"chr": "karakter görselleri", "env": "çevre görselleri", "fx": "efekt görselleri",
                 "ui": "arayüz görselleri", "ico": "ikonlar", "sfx": "ses efektleri",
                 "mus": "müzik", "fnt": "font", "mkt": "mağaza görselleri (pazarlama)"}
    grup = {}
    for k in manifest_kayitlari():
        kat = k["id"].split("_")[0]
        if str(k.get("kaynak")) == "ai-üretim" and kat in tuketilen:
            grup.setdefault(kat, []).append(k["id"])
    satirlar = ["# Steam AI beyanı (manifest'ten üretildi — elle düzenlemeyin)", "",
                "Beyana tabi: oyunla gelen ve oyuncunun tükettiği AI üretimi içerik. "
                "Geliştirme araçları (kod yazdırma vb.) kapsam dışı.", ""]
    for kat, idler in sorted(grup.items()):
        satirlar.append(f"## {tuketilen[kat]} — {len(idler)} varlık")
        satirlar += [f"- {i}" for i in idler]
        satirlar.append("")
    if not grup:
        satirlar.append("AI üretimi, oyuncuya sunulan varlık yok.")
    (RUNLOG / "ai-beyani.md").write_text("\n".join(satirlar) + "\n", encoding="utf-8")
    return [f"AI beyanı üretildi: {sum(len(v) for v in grup.values())} varlık, runlog/ai-beyani.md"]


# ================================================================== ağaç

class Adim:
    def __init__(self, ad, grup, komut=None, arg="", cikti=(), kapsam=(), dogrula=None,
                 sonrasi=None, kontrol=None, on=None, secim=None, ek="", paralel=False,
                 worktree=False, deneme=2, ornek_hash=(), kanit_min=0, iddia_zorunlu=False, not_="",
                 insan_tur=None):
        self.__dict__.update(ad=ad, grup=grup, komut=komut, arg=arg, cikti=list(cikti),
                             kapsam=list(kapsam), dogrula=dogrula, sonrasi=sonrasi, kontrol=kontrol,
                             on=on, secim=secim, ek=ek, paralel=paralel, worktree=worktree,
                             deneme=deneme, ornek_hash=list(ornek_hash), kanit_min=kanit_min,
                             iddia_zorunlu=iddia_zorunlu, not_=not_, insan_tur=insan_tur)

    @property
    def insan(self):
        return self.komut is None

    def kapi_turu(self):
        """oyun_tipi | asset | demo | yazilim — yazılım asla kullanıcıya sorulmaz."""
        if self.insan_tur:
            return self.insan_tur
        if self.komut in ("parti", "faz4a") or self.ad == "pilot-uret":
            return INSAN_ASSET
        if self.insan:
            if self.ad in ("charter", "kisa-liste", "secilen"):
                return INSAN_OYUN_TIPI
            if "onay" in self.ad or self.ad.startswith("pilot"):
                return INSAN_ASSET
            if self.ad.startswith("playtest-") or self.ad == "steam":
                return INSAN_DEMO
            return YAZILIM
        return YAZILIM


def k_charter():
    bilgi = charter_bilgi()
    if bilgi is None:
        return ("00-charter.md yok. Oyun tipini/kapsamı sen yazıyorsun (bütçe, varlık tavanı, "
                "kırmızı çizgi, başarı, kapasite). Onsuz Faz 1 başlamaz.")
    if bilgi["eksik"]:
        return f"00-charter.md'de şu başlıklar yok: {bilgi['eksik']} (altı madde şart)."
    bos = re.findall(r"<[^>!-][^>]{0,60}>", (KOK / "00-charter.md").read_text(encoding="utf-8"))
    if bos:
        return f"00-charter.md şablonu doldurulmamış: {bos[:4]}"
    if not bilgi["varlik"]:
        return "00-charter.md'de 'varlık bütçesi: N' satırı yok; bütçe kapısı ölçemiyor."
    return None


def k_kisa_liste():
    liste = secim_oku().get("kisa_liste") or []
    if not 3 <= len(liste) <= 4:
        return ("Kapı 1A · oyun tipi: 3–4 konsept seç (ilki birincil) → "
                "python3 studio.py --sec kisa_liste a,b,c")
    return None


def k_secilen():
    s = secim_oku()
    if not s.get("secilen"):
        return "Kapı 1B · oyun tipi: tek konsept seç → python3 studio.py --sec secilen <ad>"
    if s["secilen"] not in (s.get("kisa_liste") or []):
        return f"Seçilen '{s['secilen']}' kısa listede yok."
    return None


def k_varlik_onay(pilot=False):
    alanlar = manifest_alanlari()
    if not alanlar:
        return "assets/manifest.yaml boş."
    if pilot:
        return None if any(v[0] in ONAYLI for v in alanlar.values()) else \
            "Pilot kapısı · asset: kontakt sayfasını incele → python3 studio.py --onayla taslak"
    onaysiz = [k for k, v in alanlar.items() if v[0] not in ONAYLI]
    if onaysiz:
        return (f"Asset kapısı: {len(onaysiz)} varlık 'onaylı' değil ({onaysiz[:5]}). "
                "Kontakt → python3 studio.py --onayla taslak  (ya da --reddet <id> \"not\")")
    return None


def k_parti_on():
    """Parti bitmeden sonraki parti başlamaz: karar bekleyen taslak yok; 3. revizyon yok."""
    bekleyen = [k for k, v in manifest_alanlari().items() if v[0] == "taslak"]
    if bekleyen:
        return (f"Asset kapısı · taslak: {bekleyen[:6]} — kontakt: "
                "--onayla taslak | --reddet <id> \"not\"")
    return k_revizyon_tavani()


def k_revizyon_tavani():
    tavan = [k["id"] for k in manifest_kayitlari()
             if str(k.get("durum")) in ("spec", "revizyon") and int(k.get("revizyon", 0)) >= REVIZYON_TAVAN]
    return (f"{REVIZYON_TAVAN}. revizyona gelen varlıklar: {tavan}. Sorun varlıkta değil spec'te olabilir; "
            "manifest spec'ini sen düzelt, revizyon sayacını sıfırla.") if tavan else None


def k_dilim_spec():
    if not sorted((KOK / "06-slices").glob("dilim-*.md")):
        return "06-slices/dilim-*.md yok. Dilim spec'lerini sen yazıyorsun (dokunacağı dosya yollarıyla)."
    if not (KOK / TEST_KOMUT).exists():
        return f"{TEST_KOMUT} yok. Test koşucusunu sen yazarsın (ajana yasak); yeşil = çıkış 0."
    return None


def k_playtest(n):
    def kontrol():
        p = RUNLOG / f"playtest-{n}.md"
        if not p.exists() or len(p.read_text(encoding="utf-8")) < 100:
            return (f"Demo kapısı {n}: build'i oyna, notlarını runlog/playtest-{n}.md'ye yaz "
                    "(yazılım değil — eğlence/his/denge).")
        return None
    return kontrol


YAYIN_ADIMLARI = ("steam_direct_odendi", "magaza_sayfasi_gonderildi", "coming_soon_canli",
                  "build_yuklendi", "release_basildi")


def k_steam():
    if not YAYIN_LISTE.exists():
        return "07-yayin.yaml yok. Şablon:\n" + "".join(f"      {a}: false\n" for a in YAYIN_ADIMLARI)
    veri = yaml.safe_load(YAYIN_LISTE.read_text(encoding="utf-8")) or {}
    eksik = [a for a in YAYIN_ADIMLARI if not veri.get(a)]
    if eksik:
        bilgi = charter_bilgi() or {}
        takvim = ""
        if bilgi.get("yayin"):
            t = bilgi["yayin"]
            takvim = "  takvim: " + ", ".join(
                f"T−{h}h {(t - datetime.timedelta(weeks=h)).isoformat()}" for h in (6, 5, 4, 2)) + f", T {t}"
        return f"Faz 7 sende: 07-yayin.yaml'da işaretlenmemiş: {eksik}.{takvim}"
    return None


def dilim_kapsam(spec_yolu):
    metin = spec_yolu.read_text(encoding="utf-8")
    yollar = sorted(set(re.findall(r"\b(?:game|tests)/[\w./-]+\.\w+", metin)))
    return [y for y in yollar if not y.startswith("game/assets/")]


def adimlari_uret(durum):
    r = ["runlog/*"]
    a = [Adim("charter", "Faz 0 · charter", kontrol=k_charter, insan_tur=INSAN_OYUN_TIPI,
              not_="oyun tipi: 6 başlık + varlık bütçesi"),
         Adim("faz1a", "Faz 1 · pazar", "faz1a", cikti=["01-market.md"], kapsam=["01-market.md"] + r,
              dogrula=dg_market, secim=("kisa_liste", 3), iddia_zorunlu=True, not_="20 parametre → oyun tipi seç"),
         Adim("kisa-liste", "Faz 1 · pazar", kontrol=k_kisa_liste, insan_tur=INSAN_OYUN_TIPI, not_="Kapı 1A · oyun tipi"),
         Adim("faz1b", "Faz 1 · pazar", "faz1b", cikti=["01-market.md"], kapsam=["01-market.md"] + r,
              dogrula=dg_derin, secim=("secilen", 1), iddia_zorunlu=True, not_="derin analiz → 1 oyun tipi"),
         Adim("secilen", "Faz 1 · pazar", kontrol=k_secilen, insan_tur=INSAN_OYUN_TIPI, not_="Kapı 1B · oyun tipi"),
         Adim("faz2", "Faz 2 · teknik", "faz2", cikti=["02-tech.md", "runlog/faz2-kanit.md"],
              kapsam=["02-tech.md"] + r, dogrula=dg_tech, kanit_min=2, iddia_zorunlu=True,
              not_="lisans, kanıt prototipi (test+build kanıtı), kırmızı çizgi"),
         Adim("ornek-3a", "Faz 3 · tasarım", "faz3a", cikti=["03-gdd.md", "gdd/varliklar.yaml"],
              kapsam=["03-gdd.md", "gdd/*"] + r, dogrula=dg_ornek_gdd, ek=ORNEK_3A,
              ornek_hash=["gdd/varliklar.yaml"], not_="ÖRNEK: 2 açı + envanter → onay ya da döngü"),
         Adim("faz3a", "Faz 3 · tasarım", "faz3a", cikti=["03-gdd.md", "gdd/varliklar.yaml"],
              kapsam=["03-gdd.md", "gdd/*"] + r, dogrula=dg_gdd, ek=TAM_3A, not_="10 açı, ≥15 kapsam dışı")]
    if (KOK / "gdd/bolumler.yaml").exists():
        n = len(yaml_oku("gdd/bolumler.yaml", BOLUMLER_SEMA))
        for i in range(1, n + 1):
            nn = f"{i:02d}"
            a.append(Adim(f"faz3b-{nn}", "Faz 3 · tasarım", "faz3b", nn, [f"03-levels/bolum-{nn}.md"],
                          [f"03-levels/bolum-{nn}.md"] + r, dg_bolum, paralel=i > 1,
                          ek=ORNEK_3B if i == 1 else TAM_3B,
                          not_="ÖRNEK bölüm → onay ya da döngü" if i == 1 else f"≤{PARALEL} paralel oturum"))
        a.append(Adim("bolum-toplam", "Faz 3 · tasarım", kontrol=k_bolum_toplam, not_="süre ↔ GDD"))
    a += [Adim("ornek-3c", "Faz 3 · tasarım", "faz3c", cikti=["03-strings.yaml"],
               kapsam=["03-strings.yaml"] + r, dogrula=dg_ornek_strings, ek=ORNEK_3C,
               not_="ÖRNEK: menu.*/hud.* → onay ya da döngü"),
          Adim("faz3c", "Faz 3 · tasarım", "faz3c", cikti=["03-strings.yaml"],
               kapsam=["03-strings.yaml"] + r, dogrula=dg_strings, ek=TAM_3C, not_="tr+en, noktalı anahtar"),
          Adim("faz4a", "Faz 4 · varlık", "faz4a", cikti=["04-style.md"],
               kapsam=["04-style.md", "assets/raw/_style/*"] + r, dogrula=dg_stil,
               insan_tur=INSAN_ASSET, not_="stil · asset onayı"),
          Adim("faz4b", "Faz 4 · varlık", "faz4b", cikti=["assets/manifest.yaml"],
               kapsam=["assets/manifest.yaml"] + r, dogrula=dg_manifest, not_="id şeması, bütçe, kapasite")]
    if MANIFEST.exists():
        varlik_kapsam = ["assets/raw/*", "assets/manifest.yaml"] + r
        a += [Adim("pilot-uret", "Faz 4 · varlık", "parti", "00", ["runlog/parti-00.html"], varlik_kapsam,
                   dg_parti, ek="PİLOT: bu turda YALNIZCA öncelik 1 olan ilk varlığı üret, başka hiçbirini alma.",
                   not_="tek varlık, zincirin ucundan ucuna"),
              Adim("pilot-onay", "Faz 4 · varlık", kontrol=lambda: k_varlik_onay(pilot=True),
                   insan_tur=INSAN_ASSET, not_="Kapı 4D · asset (pilot)"),
              Adim("pilot-hazirla", "Faz 4 · varlık", "hazirla",
                   cikti=["game/assets/registry.gd", "runlog/hazirlama-raporu.md"],
                   kapsam=["assets/pipeline/*", "game/assets/*", "game/project.godot"] + MOTOR + r, dogrula=dg_hazirla,
                   sonrasi=hazirla_sonrasi, kanit_min=1,
                   ek="PİLOT: yalnızca 'onaylı' olan varlıkları işle, diğerleri için DURMA; ön koşulu bu tur için atla.",
                   not_="pipeline + motor yükleme, tek varlıkla")]
        kalan = sum(1 for v in manifest_alanlari().values() if v[0] in ("spec", "revizyon"))
        yapilan = len([x for x in durum["tamamlanan"] if x.startswith("parti-")])
        for i in range(-(-kalan // PARTI_BOYUT)):
            nn = f"{yapilan + i + 1:02d}"
            a.append(Adim(f"parti-{nn}", "Faz 4 · varlık", "parti", nn, [f"runlog/parti-{nn}.html"],
                          varlik_kapsam, dg_parti, on=k_parti_on,
                          ek=f"SINIR: bu turda en fazla {PARTI_BOYUT} varlık al.",
                          not_=f"≤{PARTI_BOYUT} varlık, harness ölçer"))
    a += [Adim("varlik-onay", "Faz 4 · varlık", kontrol=k_varlik_onay, insan_tur=INSAN_ASSET,
               not_="Kapı 4D · asset — onayı sen yazarsın"),
          Adim("hazirla", "Faz 5 · hazırlık", "hazirla", cikti=["game/assets/registry.gd", "runlog/hazirlama-raporu.md"],
               kapsam=["assets/pipeline/*", "game/assets/*", "game/project.godot"] + MOTOR + r, dogrula=dg_hazirla,
               sonrasi=hazirla_sonrasi, kanit_min=1, not_="registry, atlas sızma, motor, paket, hash, idempotens"),
          Adim("dilim-spec", "Faz 6 · yapım", kontrol=k_dilim_spec, not_="spec'i sen yazarsın")]
    dilimler = sorted((KOK / "06-slices").glob("dilim-*.md"))
    for i, spec in enumerate(dilimler, 1):
        nn = spec.stem.split("-", 1)[1]
        a.append(Adim(f"dilim-{nn}", "Faz 6 · yapım", "dilim", nn, kapsam=dilim_kapsam(spec) + MOTOR + r,
                      worktree=True, deneme=DILIM_DENEME, not_="worktree, spec kapsamı, test, merge"))
        if i % PLAYTEST_ARALIK == 0 or i == len(dilimler):
            n = -(-i // PLAYTEST_ARALIK)
            a += [Adim(f"playtest-hazirla-{n}", "Faz 6 · yapım", "playtest-hazirla", str(n),
                       [f"runlog/playtest-{n}-notlar.md"], ["build/*", "game/export_presets.cfg"] + MOTOR + r, dg_playtest, kanit_min=2,
                       not_="build + duman testi (kanıtlı)"),
                  Adim(f"playtest-{n}", "Faz 6 · yapım", kontrol=k_playtest(n),
                       insan_tur=INSAN_DEMO, not_="Demo kapısı — sen oynarsın")]
    a += [Adim("yayin", "Faz 7 · yayın", "yayin", cikti=["07-yayin.md"], kapsam=["07-yayin.md"] + r,
               dogrula=dg_yayin, sonrasi=ai_beyani, iddia_zorunlu=True, not_="mağaza metni, capsule, takvim, AI beyanı"),
          Adim("steam", "Faz 7 · yayın", kontrol=k_steam, insan_tur=INSAN_DEMO,
               not_="Release App'e sen basarsın")]
    return a


# ================================================================== koşum
# Ajan motoru: STUDIO_AI=claude|cursor. Cursor CLI: `agent` / `cursor-agent`.

def ai_adi():
    """Etkin motor adı (yargı modu claude/cursor ise onu kullanır)."""
    if YARGI_MOD in ("claude", "cursor"):
        return YARGI_MOD
    return STUDIO_AI if STUDIO_AI in ("claude", "cursor") else "claude"


def ai_bin():
    ad = ai_adi()
    if ad == "cursor":
        for aday in ("agent", "cursor-agent"):
            if shutil.which(aday):
                return aday
        raise Dur("STUDIO_AI=cursor ama `agent`/`cursor-agent` PATH'te yok. "
                  "https://cursor.com/docs/cli — `curl https://cursor.com/install -fsS | bash`")
    if not shutil.which("claude"):
        raise Dur("STUDIO_AI=claude ama `claude` PATH'te yok.")
    return "claude"


def json_nesne_cikar(metin, sema, ad):
    """Serbest metinden şemaya uyan son JSON nesnesini çıkar (Cursor CLI şema zorlamaz)."""
    if not metin or not metin.strip():
        raise RaporYok(f"{ad}: boş yanıt, JSON yok.")
    adaylar = []
    # ```json ... ``` çitleri
    for m in re.finditer(r"```(?:json)?\s*(\{.*?\})\s*```", metin, re.S):
        adaylar.append(m.group(1))
    # dengeli { ... } tarama (sondan)
    yigin, bas = 0, None
    for i, ch in enumerate(metin):
        if ch == "{":
            if yigin == 0:
                bas = i
            yigin += 1
        elif ch == "}" and yigin:
            yigin -= 1
            if yigin == 0 and bas is not None:
                adaylar.append(metin[bas:i + 1])
                bas = None
    hatalar = []
    for ham in reversed(adaylar):
        try:
            veri = json.loads(ham)
        except json.JSONDecodeError as e:
            hatalar.append(str(e))
            continue
        try:
            sema_dogrula(veri, sema, ad)
            return veri
        except Dur as e:
            hatalar.append(str(e))
            continue
    raise RaporYok(f"{ad}: şemalı JSON çıkarılamadı ({len(adaylar)} aday). "
                   f"Son hata: {(hatalar[-1] if hatalar else 'yok')[:200]}")


def stream_json_zarf(stdout):
    """Claude/Cursor stream-json: son type=result olayını döndür."""
    zarf = None
    for satir in (stdout or "").splitlines():
        satir = satir.strip()
        if not satir.startswith("{"):
            continue
        try:
            olay = json.loads(satir)
        except json.JSONDecodeError:
            continue
        if olay.get("type") == "result":
            zarf = olay
    return zarf


def ajan_komut(prompt, kok, sema, butce=None, salt_okunur=False):
    """Motor komut satırı + (gerekirse zenginleştirilmiş) prompt.
    salt_okunur=True → Cursor `--mode ask` (yargıç; dosya yazmaz)."""
    butce = butce if butce is not None else BUTCE
    motor = ai_adi()
    binary = ai_bin()
    if motor == "cursor":
        # Cursor --json-schema yok: şemayı prompt'a göm.
        prompt = (f"{SISTEM_EK}\n\n{prompt}\n\n"
                  "İŞ BİTİNCE: başka metin yazma. Yalnızca aşağıdaki JSON Schema'ya uyan "
                  "tek bir JSON nesnesi döndür (istersen ```json çiti içinde):\n"
                  f"{json.dumps(sema, ensure_ascii=False)}")
        cmd = ["nice", "-n", str(NICE), binary, "-p", prompt,
               "--output-format", "stream-json",
               "--trust", "--workspace", str(kok)]
        if salt_okunur:
            cmd += ["--mode", "ask"]
        else:
            cmd += ["--force"]  # yazma + shell (parti/dilim)
        # Auto / boş → Cursor varsayılanı (Auto); aksi halde --model
        if STUDIO_MODEL and STUDIO_MODEL.lower() not in ("auto", "default", "varsayilan"):
            cmd += ["--model", STUDIO_MODEL]
        return cmd, prompt, "cursor"
    cmd = ["nice", "-n", str(NICE), binary, "-p", prompt,
           "--permission-mode", IZIN, "--max-budget-usd", str(butce),
           "--disallowedTools", *YASAK_ARACLAR, "--append-system-prompt", SISTEM_EK,
           "--output-format", "stream-json", "--verbose",
           "--json-schema", json.dumps(sema, ensure_ascii=False),
           "--no-session-persistence"]
    # Auto / boş model → CLI varsayılanı; aksi halde --model
    if STUDIO_MODEL and STUDIO_MODEL.lower() not in ("auto", "default", "varsayilan"):
        cmd += ["--model", STUDIO_MODEL]
    return cmd, prompt, "claude"



def ajan_rapor_coz(zarf, sema, ad, motor):
    """Result zarfından şemalı rapor çıkar."""
    if zarf is None:
        raise Dur(f"{ad}: {motor} 'result' zarfı döndürmedi. runlog/{ad}.log")
    if zarf.get("is_error"):
        raise Dur(f"{ad}: {motor} hata ({zarf.get('subtype') or zarf.get('result', '')!s}). runlog/{ad}.log")
    if zarf.get("subtype") and zarf.get("subtype") not in ("success",):
        # Claude: error_max_budget_usd vb.
        if zarf.get("subtype") == "error_max_budget_usd":
            raise Dur(f"{ad}: {BUTCE}$ bütçe tavanına takıldı. Adımı böl ya da STUDIO_BUTCE'yi büyüt.")
        raise Dur(f"{ad}: {motor} hata ({zarf.get('subtype')}). runlog/{ad}.log")
    if motor == "claude" and zarf.get("structured_output") is not None:
        rapor = zarf["structured_output"]
        sema_dogrula(rapor, sema, f"{ad} raporu")
        return rapor
    # Cursor (ve Claude structured_output yoksa): result metninden JSON
    metin = zarf.get("result") or zarf.get("structured_output")
    if isinstance(metin, dict):
        sema_dogrula(metin, sema, f"{ad} raporu")
        return metin
    if not isinstance(metin, str):
        raise RaporYok(f"{ad}: şemalı rapor yok — iş yapılmış olabilir, rapor eksik.")
    return json_nesne_cikar(metin, sema, ad)


def ajani_calistir(adim, ek, kok=None):
    """Ajanı koştur, dönüşü RAPOR_SEMA'ya uyan tek JSON nesnesi olarak al."""
    kok = kok or KOK
    prompt = komut_metni(adim.komut, adim.arg, "\n".join(x for x in (adim.ek, ek) if x))
    RUNLOG.mkdir(exist_ok=True)
    log = RUNLOG / f"{adim.ad}.log"
    yuk_bekle(adim.ad)
    cmd, prompt, motor = ajan_komut(prompt, kok, RAPOR_SEMA)
    print(f"\n\033[1m▶ {adim.ad}\033[0m  [{motor}] (≤{BUTCE}$, ≤{SURE}s, nice {NICE}, "
          f"yük {yuk():.0f}/{YUK_TAVAN:.0f}, {kok.name}/, log: runlog/{adim.ad}.log)")
    try:
        p = subprocess.run(cmd, cwd=kok, capture_output=True, text=True, timeout=SURE)
    except subprocess.TimeoutExpired as e:
        def metin(x):
            return x.decode("utf-8", "replace") if isinstance(x, bytes) else (x or "")
        with log.open("a", encoding="utf-8") as f:
            f.write(metin(e.stdout) + metin(e.stderr))
        raise Dur(f"{adim.ad}: {SURE}s süre tavanına takıldı. Adımı böl ya da STUDIO_SURE'yi büyüt "
                  f"(yarım kalan iş dalda saklanır, sonraki koşu kaldığı yerden devam eder).")
    adim.son_cikti = getattr(adim, "son_cikti", "") + p.stdout + p.stderr

    def logu_yaz():
        log.open("a", encoding="utf-8").write(adim.son_cikti)
        adim.son_cikti = ""
    if p.returncode != 0:
        logu_yaz()
        raise Dur(f"{adim.ad}: {motor} çıkış kodu {p.returncode}. runlog/{adim.ad}.log")
    zarf = stream_json_zarf(p.stdout)
    if zarf is None:
        logu_yaz()
        raise Dur(f"{adim.ad}: {motor} 'result' zarfı döndürmedi. runlog/{adim.ad}.log")
    maliyet = float(zarf.get("total_cost_usd") or 0)
    if not hasattr(adim, "maliyet"):
        adim.maliyet = durum_oku().get("maliyet", {}).get(adim.ad, 0)
    adim.maliyet += maliyet
    print(f"   {zarf.get('num_turns', '?')} tur, {maliyet:.2f}$ (bu adımda toplam {adim.maliyet:.2f}$) [{motor}]")
    try:
        rapor = ajan_rapor_coz(zarf, RAPOR_SEMA, adim.ad, motor)
    except (Dur, RaporYok):
        logu_yaz()
        raise
    return rapor



KANIT_META = re.compile(r"[;|&<>$`\n\\]|\(\)|\{|\}")
KANIT_YASAK_BAS = {"sudo", "curl", "wget", "rm", "ssh", "scp", "nc", "eval", "exec", "-c"}


def kanit_kos(adim, kanit, kok):
    """Kanıt beyan değil: bildirilen her komutu studio tekrar koşar, çıkış kodu tutmalı.
    Komut tek ve düz olmalı: boru/zincir/yönlendirme/genişletme yok, tehlikeli başlangıç yok —
    aksi halde ajan, studio'nun eliyle keyfi komut çalıştırmış olur."""
    for k in kanit:
        if KANIT_META.search(k["komut"]):
            raise Dur(f"{adim.ad}: kanıt komutunda meta karakter (boru/zincir/yönlendirme) var, koşulmadı → `{k['komut']}`")
        parcalar = k["komut"].split()
        bas = parcalar[0].split("/")[-1] if parcalar else ""
        if bas in KANIT_YASAK_BAS or "-c" in parcalar:
            raise Dur(f"{adim.ad}: kanıt komutu '{bas}'/-c ile olamaz → `{k['komut']}`")
        if bas in ("bash", "sh", "python3", "python") and (len(parcalar) < 2 or parcalar[1].startswith(("/", "~", "-"))):
            raise Dur(f"{adim.ad}: kanıt yorumlayıcısı yalnız repo içi bir betik alabilir → `{k['komut']}`")
        gercek, _cikti = korumali_kos(f"{adim.ad} kanıt `{k['komut']}`", adim.kapsam,
                                      lambda: komut_kos(["bash", "-c", k["komut"]], kok))
        if gercek != k["cikis_kodu"]:
            raise Dur(f"{adim.ad}: kanıt tutmuyor → `{k['komut']}` bildirilen {k['cikis_kodu']}, "
                      f"gerçek {gercek}")


def rapor_denetle(adim, rapor, degisen, kok=None, onceki=()):
    """`onceki`: bu adımın önceki (yarım) denemelerinde dala girmiş dosyalar — ajan bu koşuda dokunmadıysa
    raporlamak zorunda değil, ama raporlarsa da 'yazılmamış' sayılmaz."""
    """Ajanın söylediği ile ölçülen aynı mı; kanıt tekrar koşulur; kaynak zorunlulukları."""
    if getattr(adim, "son_cikti", ""):
        (RUNLOG / f"{adim.ad}.log").open("a", encoding="utf-8").write(adim.son_cikti)
        adim.son_cikti = ""
    d = durum_oku()
    d.setdefault("maliyet", {})[adim.ad] = round(getattr(adim, "maliyet", 0), 4)
    durum_yaz(d)
    if rapor["adim"] != adim.ad:
        raise Dur(f"{adim.ad}: rapor başka adım için ({rapor['adim']}).")
    if rapor["durus"]:
        raise Sor(f"{adim.ad} DURDU — {rapor['durus']['neden']}\n  SORU: {rapor['durus']['soru']}",
                  neden=rapor["durus"]["neden"], soru=rapor["durus"]["soru"])
    # Motor önbelleği (.godot/, *.import) yan üründür: kapsamda kalır ama raporlanması istenmez.
    yan_urun = lambda y: y.startswith("runlog/") or eslesir(y, MOTOR)
    olculen = {y for y in degisen if not yan_urun(y)}
    onceki_k = {y for y in onceki if not yan_urun(y)}
    bildirilen = {y.rstrip("/") for y in rapor["yazilan"] if not yan_urun(y)}
    bildirilmeyen = olculen - bildirilen - onceki_k
    # Aynı içerikle yeniden yazılan dosya "değişmedi" görünür; bildirilmesi hata değildir. Hata: var olmayan dosyayı bildirmek.
    yazilmamis = {y for y in bildirilen - olculen - onceki_k if not ((kok or KOK) / y).exists()}
    if bildirilmeyen or yazilmamis:
        raise Dur(f"{adim.ad}: bildirilen ≠ ölçülen. Bildirilmeyen: {sorted(bildirilmeyen)[:6]}, "
                  f"yazılmamış: {sorted(yazilmamis)[:6]}")
    if adim.kanit_min:
        kanit_kos(adim, rapor["kanit"], kok or KOK)
    basarili = [k for k in rapor["kanit"] if k["cikis_kodu"] == 0]
    if len(basarili) < adim.kanit_min:
        raise Dur(f"{adim.ad}: en az {adim.kanit_min} sıfır çıkışlı kanıt gerekli, {len(basarili)} var.")
    if adim.iddia_zorunlu and not rapor["iddialar"]:
        raise Dur(f"{adim.ad}: iddialar boş — her sayısal iddia URL ya da 'tahmin' ile listelenmeli.")
    tahmin = sum(1 for i in rapor["iddialar"] if i["kaynak"] == "tahmin")
    return [f"{len(rapor['iddialar'])} iddia, {tahmin} tahmin, {len(rapor['kanit'])} kanıt"] \
        if rapor["iddialar"] or rapor["kanit"] else []


URETILMIS = ["game/assets/*"] + MOTOR  # üretilmiş çıktı: pipeline temiz üretimde silip yeniden yazar


TEST_DIZIN = ["tests/*"]


def iddia_sayisi(metin):
    """Bir test dosyasındaki ok(...) çağrısı sayısı — yorum satırındakiler sayılmaz."""
    return sum(len(re.findall(r"\bok\s*\(", s.split("#")[0])) for s in metin.splitlines())


def test_denetimi(ad, yollar, kok, taban):
    """Pilot dersi: 7 duruşun 4'ü ajanın doğru işi yapıp eski testteki sabiti güncelleyememesiydi
    (dilim-23/32/37/50). Dilim turunda tests/ artık güncellenebilir, ama iddia SAYISI azalamaz ve
    dosya eklenemez. Tavan: kapı, sabit güncellemesi ile bir iddianın içini boşaltmayı ayırt edemez
    — bu yüzden her güncelleme kapıda uyarı olarak basılır, son söz kullanıcınındır."""
    for y in yollar:
        eski_metin = git("show", f"{taban}:{y}", kok=kok, kontrol=False)
        if not eski_metin:
            raise Dur(f"{ad}: yeni test dosyası eklenemez ({y}) — testi kullanıcı yazar.")
        e, n = iddia_sayisi(eski_metin), iddia_sayisi(oku(y, kok))
        if n < e:
            raise Dur(f"{ad}: {y} içinde iddia sayısı {e} → {n} düştü. Test gevşetmek yasak; "
                      "tests/ yalnızca sabit güncellemesi için açıktır.")
        print(f"\033[33m   test güncellendi:\033[0m {y} ({e} → {n} iddia) — merge öncesi diff'e bak")


def kapsam_denetle(ad, kapsam, degisen, silinen, kok=None, taban="HEAD"):
    # Silme yasağı kaynak dosyalar içindir; üretilmiş çıktı (game/assets, motor önbelleği) temiz üretimde silinebilir —
    # ama yalnız kapsamı buraya uzanan adımlarda (hazırlama). Diğer adımlarda orada silme de rettir.
    silinen = [y for y in silinen if not (eslesir(y, URETILMIS) and eslesir(y, kapsam))]
    if silinen:
        raise Dur(f"{ad}: dosya SİLİNMİŞ (anayasa 3): {silinen[:8]}")
    testler = [y for y in degisen if eslesir(y, TEST_DIZIN)] if ad.startswith("dilim-") else []
    if testler:
        test_denetimi(ad, testler, kok, taban)
    disari = [y for y in degisen if y not in testler and (eslesir(y, YASAK) or not eslesir(y, kapsam))]
    if disari:
        raise Dur(f"{ad}: kapsam dışı yazım: {disari[:8]}\n  izinli: {kapsam}")


def onay_nobeti(ad, komut, once, sonra):
    if once and komut != "faz4b":  # liste Kapı 4B'de kilitlenir; 4B'nin kendi (tekrar) turu listeyi yazabilir
        eklenen, silinen = sorted(set(sonra) - set(once)), sorted(set(once) - set(sonra))
        if eklenen:
            raise Dur(f"{ad}: manifest'e satır eklenemez (liste Kapı 4B'de kilitlendi): {eklenen[:5]}")
        if silinen:
            raise Dur(f"{ad}: manifest'ten satır silinemez: {silinen[:5]}")
    for kimlik, (d_y, h_y, t_y) in sonra.items():
        eski = once.get(kimlik)
        if eski is None:
            continue
        d_e, h_e, t_e = eski
        if t_e != t_y:
            raise Dur(f"{ad}: '{kimlik}' onay_tarihi değiştirilmiş — yalnızca sen yazarsın.")
        if h_e != h_y:
            raise Dur(f"{ad}: '{kimlik}' hash değiştirilmiş — yalnızca studio.py yazar.")
        if d_e != d_y and not (komut == "parti" and d_e in ("spec", "revizyon") and d_y == "taslak"):
            raise Dur(f"{ad}: '{kimlik}' durum {d_e} → {d_y}. Bu geçişi ajan yapamaz.")


def duruslar(kok=None):
    r = (kok or KOK) / "runlog"
    return {p.name for p in r.glob("*durus*.md")} if r.exists() else set()


def durus_bas(ad, yeni, kok=None):
    if yeni:
        for d in sorted(yeni):
            print(f"\n\033[33m── {d} ──\033[0m\n" + ((kok or KOK) / "runlog" / d).read_text(encoding="utf-8"))
        raise Dur(f"{ad}: ajan duruş raporu yazdı (yukarıda). Cevabını ver, tekrar koş.")


def dogrula_ve_sonrasi(adim):
    eksik = [c for c in adim.cikti if not (KOK / c).exists()]
    if eksik:
        raise Dur(f"beklenen çıktı yok: {eksik}")
    uyari = list(adim.dogrula(adim.arg)) if adim.dogrula else []
    if adim.sonrasi:
        uyari += adim.sonrasi()
    return uyari


def adimi_kosun(adim, ek=""):
    taban = ek  # kullanıcı notları; tekrar denemelerde kaybolmaz, geri bildirim üstüne eklenir
    # Taban görüntü adımın BAŞINDA alınır: tekrar denemelerde "değişen" = adım boyunca değişen her şey.
    # (Deneme başına alınsaydı, ikinci denemede hiçbir şey yazmayan ve boş rapor veren ajan kapıdan geçerdi.)
    once_g, once_m, once_d = anlik_goruntu(), manifest_alanlari(), duruslar()
    for deneme in range(1, adim.deneme + 1):
        once_y, once_git = yetki_goruntusu(), git_goruntusu()
        try:
            rapor = ajani_calistir(adim, "\n".join(x for x in (ek, f"adim: {adim.ad}") if x))
        except RaporYok as e:
            if deneme == adim.deneme:
                raise
            print(f"\n\033[33m↻ rapor yok, tekrar {deneme + 1}/{adim.deneme}:\033[0m {e}")
            ek = (f"{taban}\n\nÖNCEKİ DENEME: dosyaları yazdın ama şemalı JSON raporu DÖNDÜRMEDİN. Mevcut "
                  "dosyaları koru, eksik kalan işi tamamla ve bitişte yalnızca JSON raporu döndür.").strip()
            continue
        yetki_denetle(adim.ad, once_y)
        git_denetle(adim.ad, once_git)
        sonra_g = anlik_goruntu()
        bag_denetle(adim.ad, once_g, sonra_g)
        degisen, silinen = fark(once_g, sonra_g)
        kapsam_denetle(adim.ad, adim.kapsam, degisen, silinen)
        onay_nobeti(adim.ad, adim.komut, once_m, manifest_alanlari())
        durus_bas(adim.ad, duruslar() - once_d)
        try:
            uyari = rapor_denetle(adim, rapor, degisen)
            return degisen, uyari + dogrula_ve_sonrasi(adim)
        except Sor:
            raise
        except Dur as e:
            if deneme == adim.deneme:
                raise Dur(f"{adim.ad}: {adim.deneme} denemede de doğrulamadan geçmedi → {e}")
            # Studio'nun kendi yazdıkları (adım log'u, durum.json) sonraki denemede "değişen" sayılmasın.
            simdi = anlik_goruntu()
            for y in simdi:
                if y == "runlog/durum.json" or (y.startswith("runlog/") and y.endswith(".log")):
                    once_g[y] = simdi[y]
            print(f"\n\033[33m↻ doğrulama düştü, tekrar {deneme + 1}/{adim.deneme}:\033[0m {e}")
            ek = (f"{taban}\n\nÖNCEKİ DENEME REDDEDİLDİ: {e}\nSadece bunu düzelt, baştan yazma. "
                  "JSON raporun yine TÜM adım için tam olmalı (yazilan: dokunduğun dosyalar, iddialar: "
                  "dosyadaki tüm sayısal iddialar, kanit) — yalnız bu düzeltmeyi raporlama.").strip()


def grubu_paralel_kosun(grup):
    """Aynı komutun bağımsız örnekleri (faz3b): her ajan KENDİ worktree'sinde koşar, kapsamı
    kendi worktree'sinin git durumundan ölçülür (per-ajan atıf), yalnız beklenen çıktı KOK'a döner."""
    kullanici_dosyalarini_commitle()
    kirli = git("status", "--porcelain", "--", "03-gdd.md", "gdd", "03-levels", kontrol=False)
    if kirli:
        print(f"   \033[33muyarı:\033[0m commit'lenmemiş tasarım dosyaları worktree'lerde görünmez:\n{kirli}")
    once_y, once_git = yetki_goruntusu(), git_goruntusu()
    genislik = paralel_genislik()
    print(f"\n\033[1m▶ {len(grup)} adım paralel (≤{genislik}, yük {yuk():.0f}):\033[0m " + ", ".join(a.ad for a in grup))
    wts = {}
    for a in grup:  # worktree'ler seri açılır (git kilidi), ajanlar paralel koşar
        wt = WT / a.ad
        if wt.exists():
            git("worktree", "remove", "--force", str(wt), kontrol=False)
        git("branch", "-D", f"wt-{a.ad}", kontrol=False)
        git("worktree", "add", "-q", "-b", f"wt-{a.ad}", str(wt), "HEAD")
        (wt / "runlog").mkdir(exist_ok=True)
        wts[a.ad] = wt
    hatalar, raporlar = {}, {}
    with concurrent.futures.ThreadPoolExecutor(genislik) as havuz:
        isler = [(a, havuz.submit(ajani_calistir, a, f"{notlar_ek(a.ad)}\nadim: {a.ad}", wts[a.ad])) for a in grup]
        for adim, gelecek in isler:
            try:
                raporlar[adim.ad] = gelecek.result()
            except Dur as e:
                hatalar[adim.ad] = str(e)
    yetki_denetle("paralel grup", once_y)
    git_denetle("paralel grup", once_git)
    sonuc = []
    for adim in grup:
        wt = wts[adim.ad]
        try:
            if adim.ad in hatalar:
                raise Dur(hatalar[adim.ad])
            satirlar = git("status", "--porcelain", "--untracked-files=all", kok=wt).splitlines()
            silinen = [s[3:] for s in satirlar if s[:2].strip() == "D"]
            degisen = [s[3:] for s in satirlar if s[:2].strip() != "D"]
            bag_denetle(adim.ad, {}, {y: v for y, v in anlik_goruntu(wt).items() if v[0] == "link"})
            kapsam_denetle(adim.ad, adim.kapsam, degisen, silinen, wt)
            durus_bas(adim.ad, duruslar(wt), kok=wt)
            uyari = rapor_denetle(adim, raporlar[adim.ad], degisen, wt)
            for c in adim.cikti:  # yalnız beklenen çıktı ana ağaca döner
                if (wt / c).exists():
                    (KOK / c).parent.mkdir(parents=True, exist_ok=True)
                    shutil.copy2(wt / c, KOK / c)
            sonuc.append((adim, (degisen, uyari + dogrula_ve_sonrasi(adim))))
        except Sor:
            raise
        except Dur as e:
            print(f"\n\033[33m↻ {adim.ad} düştü, tek başına tekrar:\033[0m {e}")
            sonuc.append((adim, adimi_kosun(adim, f"ÖNCEKİ DENEME REDDEDİLDİ: {e}\nSadece bunu düzelt.")))
        finally:
            git("worktree", "remove", "--force", str(wt), kontrol=False)
            git("branch", "-D", f"wt-{adim.ad}", kontrol=False)
    return sonuc


def dilim_kosun(adim, ek=""):
    """Faz 6: ayrı worktree, spec kapsamı git diff'ten, testleri studio koşar, 3 deneme."""
    if not adim.kapsam or adim.kapsam == ["runlog/*"]:
        raise Dur(f"{adim.ad}: 06-slices/{adim.ad}.md dosya yolu içermiyor; kapsam tanımsız.")
    kullanici_dosyalarini_commitle()
    if git("status", "--porcelain", "--", "game", "tests", kontrol=False):
        raise Dur(f"{adim.ad}: game/ veya tests/ altında commit'lenmemiş değişiklik var; önce onu kapat.")
    wt = WT / adim.ad
    devam = ""
    if wt.exists():  # önceki (zaman aşımı/kırmızı) deneme: kapsam içi yarım iş dalda saklanır, dışı atılır
        satirlar = git("status", "--porcelain", "--untracked-files=all", kok=wt, kontrol=False).splitlines()
        yarim = [s[3:] for s in satirlar if s[:2].strip() != "D"]
        silinmis = [s[3:] for s in satirlar if s[:2].strip() == "D"]
        # Kapsam dışı yarım dosyalar (örn. tests/_debug.gd) atılır — atılabilir worktree'de, main'e değmez;
        # kapsam içi olanlar dala commit'lenir. Silme varsa hiçbiri alınmaz.
        disari = [y for y in yarim if eslesir(y, YASAK) or not eslesir(y, adim.kapsam)]
        for y in disari:
            git("checkout", "--", y, kok=wt, kontrol=False)  # değiştirilmişse geri al
            (wt / y).unlink(missing_ok=True) if (wt / y).exists() and y not in git("ls-files", y, kok=wt, kontrol=False) else None
        if disari:
            print(f"   \033[33myarım denemeden kapsam dışı dosyalar atıldı:\033[0m {disari[:5]}")
        if silinmis:
            print(f"   \033[33myarım deneme atıldı (silme var):\033[0m {silinmis[:5]}")
            git("checkout", "--", ".", kok=wt, kontrol=False)
        elif [y for y in yarim if y not in disari]:
            git("add", "-A", kok=wt)
            git("commit", "-q", "-m", f"{adim.ad}: yarım kalan deneme", kok=wt, kontrol=False)
        git("worktree", "remove", "--force", str(wt), kontrol=False)
    if git("branch", "--list", adim.ad, kontrol=False).strip():
        git("worktree", "add", "-q", str(wt), adim.ad)  # dal var: kaldığı yerden
        # main ilerlemiş olabilir (test düzeltmesi vb.): dala main'i al; çakışırsa DUR.
        m = subprocess.run(["git", "-C", str(wt), "merge", "-q", "-m", f"{adim.ad}: main güncellemesi", "main"],
                           capture_output=True, text=True)
        if m.returncode != 0:
            git("merge", "--abort", kok=wt, kontrol=False)
            raise Dur(f"{adim.ad}: yarım dal main ile çakıştı → {m.stderr.strip()[:300]}. Çözümü sen ver.")
        if git("log", "--oneline", f"HEAD..{adim.ad}", kontrol=False).strip():
            devam = ("ÖNCEKİ DENEME YARIDA KALDI: dalda spec kapsamındaki dosyalar zaten var. Baştan yazma; "
                     "mevcut dosyaları oku, eksikleri tamamla, testi geçir.")
    else:
        git("worktree", "add", "-q", "-b", adim.ad, str(wt), "HEAD")
    taban = "\n\n".join(x for x in (ek, devam) if x)
    ek = taban
    taban_commit = git("merge-base", "HEAD", adim.ad, kontrol=False).strip() or git("rev-parse", "HEAD")  # main ile ortak taban
    for deneme in range(1, adim.deneme + 1):
        once_d, once_y, once_git, once_g = duruslar(wt), yetki_goruntusu(), git_goruntusu(wt), anlik_goruntu(wt)
        rapor = ajani_calistir(adim, f"{ek}\nadim: {adim.ad}", kok=wt)
        yetki_denetle(adim.ad, once_y)
        git_denetle(adim.ad, once_git, wt)
        bag_denetle(adim.ad, once_g, anlik_goruntu(wt))
        satirlar = git("status", "--porcelain", "--untracked-files=all", kok=wt).splitlines()
        silinen = [s[3:] for s in satirlar if s[:2].strip() == "D"]
        degisen = [s[3:] for s in satirlar if s[:2].strip() != "D"]
        # Önceki denemelerde dala commit'lenen dosyalar da bu dilimin yazımıdır (rapor kıyası için).
        dal_degisen = git("diff", "--name-only", taban_commit, kok=wt, kontrol=False).splitlines()
        bu_kosu = list(degisen)
        degisen = sorted(set(degisen) | set(dal_degisen))
        kapsam_denetle(adim.ad, adim.kapsam, degisen, silinen, wt, taban_commit)
        durus_bas(adim.ad, duruslar(wt) - once_d, kok=wt)
        rapor_denetle(adim, rapor, bu_kosu, wt, onceki=set(dal_degisen) - set(bu_kosu))
        if not degisen:
            raise Dur(f"{adim.ad}: ajan hiçbir dosyayı değiştirmedi.")
        git("add", "-A", kok=wt)
        if git("status", "--porcelain", kok=wt, kontrol=False).strip():  # sürdürülen dalda iş zaten commit'li olabilir
            git("commit", "-q", "-m", f"{adim.ad}: deneme {deneme}", kok=wt)
        try:
            dg_dilim(adim.ad, wt)
            return degisen, []
        except Dur as e:
            if deneme == adim.deneme:
                raise Dur(f"{adim.ad}: {adim.deneme} denemede de yeşile dönmedi → {e}\n"
                          f"Dal '{adim.ad}' ve worktree duruyor; teşhis için runlog/{adim.ad}-test.log")
            print(f"\n\033[33m↻ test kırmızı, deneme {deneme + 1}/{adim.deneme}\033[0m")
            ek = f"{taban}\n\nTESTLER KIRMIZI, ÇIKTI:\n{e}\nSadece bunu düzelt.".strip()


def dilim_merge(adim):
    wt = WT / adim.ad
    try:
        git("merge", "--no-ff", "-q", "-m", f"merge {adim.ad}", adim.ad)
    except Dur as e:
        git("merge", "--abort", kontrol=False)
        raise Dur(f"{adim.ad}: merge çakıştı → {e}. Dal duruyor, çözümü sen ver.")
    git("worktree", "remove", "--force", str(wt), kontrol=False)
    git("branch", "-d", adim.ad, kontrol=False)
    print(f"   merge edildi: {adim.ad}")


KULLANICI_DOSYALARI = ["00-charter.md", "01-secim.yaml", "07-yayin.yaml", "06-slices", "tests"]


def kullanici_dosyalarini_commitle():
    """Worktree'ler HEAD'den açılır: kullanıcının yazdığı spec/test/charter commit'lenmemişse ajan
    onları göremez. Kullanıcı dosyalarını kendi başına bir commit'e alır (ajan çıktısıyla karışmaz)."""
    var = [y for y in KULLANICI_DOSYALARI if (KOK / y).exists()]
    if not var:
        return
    git("add", "--", *var, kontrol=False)
    if git("diff", "--cached", "--name-only", "--", *var, kontrol=False):
        git("commit", "-q", "-m", "kullanıcı dosyaları", "--", *var, kontrol=False)


def kapi_commit(adim, degisen):
    """Her kapı bir commit: dilim worktree'leri HEAD'den açılır, HEAD kapıda büyür.
    Ölçülen değişiklik listesine ek olarak, adımın kapsamındaki commit'lenmemiş her dosya da alınır —
    --onayla yolunda degisen boş gelir; kapsamdaki üretim (game/assets, 03-levels…) yine commit'lenmeli."""
    kapsam = adim.kapsam + adim.cikti
    bekleyen = [s[3:] for s in git("status", "--porcelain", "--untracked-files=all", kontrol=False).splitlines()
                if s[:2].strip() != "D" and eslesir(s[3:], kapsam) and not eslesir(s[3:], ATLA)
                and not s[3:].startswith("game/.godot/") and not s[3:].endswith(".log")]
    yollar = sorted(set([y for y in degisen if not eslesir(y, ATLA)] + bekleyen)) + ["runlog/durum.json"]
    if SECIM.exists():
        yollar.append("01-secim.yaml")
    if MANIFEST.exists():
        yollar.append("assets/manifest.yaml")
    git("add", "--", *yollar, kontrol=False)
    git("commit", "-q", "-m", f"kapı: {adim.ad}", "--", *yollar, kontrol=False)
    kullanici_dosyalarini_commitle()


def secim_iste(adim):
    alan, n = adim.secim
    if secim_oku().get(alan) and len(secim_oku()[alan] if n > 1 else [1]) == n:
        return
    if not sys.stdin.isatty():
        raise Dur(f"{adim.ad} onaylandı; seçim gerekiyor → python3 studio.py --sec {alan} "
                  + ("a,b,c" if n > 1 else "<ad>"))
    cevap = input(f"   {alan} ({n} konsept, virgülle): ").strip()
    sec(alan, cevap)


def sec(alan, deger):
    if alan == "kisa_liste":
        liste = [x.strip() for x in deger.split(",") if x.strip()]
        if not 3 <= len(liste) <= 4:
            raise Dur("kisa_liste 3–4 konsept olmalı (ilki birincil).")
        secim_yaz("kisa_liste", liste)
    elif alan == "secilen":
        if deger.strip() not in (secim_oku().get("kisa_liste") or []):
            raise Dur(f"'{deger}' kısa listede yok: {secim_oku().get('kisa_liste')}")
        secim_yaz("secilen", deger.strip())
    else:
        raise Dur("alan: kisa_liste ya da secilen")
    print(f"seçim yazıldı: {alan}")


def onay_iste(adim, degisen, uyarilar):
    """İnsan kapısı (oyun tipi / asset / demo). True = onay."""
    tur = adim.kapi_turu()
    etiket = {"oyun_tipi": "oyun tipi", "asset": "asset", "demo": "demo"}.get(tur, tur)
    print(f"\n\033[1m⏸ İnsan kapısı ({etiket}): {adim.ad}\033[0m")
    for y in degisen[:20]:
        print(f"   yazıldı: {y}")
    for u in uyarilar:
        print(f"   \033[33muyarı:\033[0m {u}")
    if not sys.stdin.isatty():
        raise Dur(f"{adim.ad} ({etiket}) onay bekliyor:\n"
                  f"  onay → python3 studio.py --onayla {adim.ad}\n"
                  f"  ret  → python3 studio.py --reddet {adim.ad} \"düzeltme notu\"")
    if input("   onaylıyor musun? [e/h] ").strip().lower() == "e":
        return True
    not_ = input("   düzeltme notu (boş = dur): ").strip()
    if not not_:
        raise Dur(f"{adim.ad} onaylanmadı, not yok. Sonra: --reddet {adim.ad} \"not\" ya da tekrar koş.")
    not_ekle(adim.ad, not_)
    return False


def not_ekle(ad, not_):
    d = durum_oku()
    d.setdefault("notlar", {}).setdefault(ad, []).append(not_)
    durum_yaz(d)
    print(f"   not kaydedildi ({len(d['notlar'][ad])}. tur): {not_}")


def notlar_ek(ad):
    notlar = durum_oku().get("notlar", {}).get(ad, [])
    if not notlar:
        return ""
    return ("REVİZYON NOTLARI (sırayla, sonuncusu en yeni — hepsini uygula):\n" +
            "\n".join(f"{i + 1}. {n}" for i, n in enumerate(notlar)) +
            "\nMevcut çıktıyı bu notlara göre yeniden yaz.")


# --- öz-yargı (yazılım adımları; insan sorulmaz) ---

YAZILIM_ANAHTAR = re.compile(
    r"\b(test|kod|script|gd|tscn|offset|px|layout|bug|merge|commit|fonksiyon|class|"
    r"compile|derle|headless|assert|ok\(|pipeline|hash|idempotens|worktree|diff|"
    r"yaml|json|import|export|godot|registry|string tablosu|03-strings|gdd değiş|"
    r"syntax|exception|traceback|lint)\b", re.I)
ASSET_ANAHTAR = re.compile(
    r"\b(asset|varlık|sprite|palet|stil|font|görsel|ses|müzik|kontakt|taslak|"
    r"onayla|manifest|png|wav|ogg)\b", re.I)
OYUN_TIPI_ANAHTAR = re.compile(
    r"\b(oyun tipi|konsept|tür|genre|charter|kapsam tavan|kısa liste|seçilen|"
    r"market|rakipler?|wishlist)\b", re.I)


def soru_sinifi(soru, neden=""):
    metin = f"{neden}\n{soru}"
    if ASSET_ANAHTAR.search(metin) and not YAZILIM_ANAHTAR.search(metin):
        return INSAN_ASSET
    if OYUN_TIPI_ANAHTAR.search(metin) and not YAZILIM_ANAHTAR.search(metin):
        return INSAN_OYUN_TIPI
    if YAZILIM_ANAHTAR.search(metin):
        return YAZILIM
    # belirsiz yazılım sorusu: kullanıcıya gitmez
    return YAZILIM


def yargi_raporu_yaz(adim, seviye, yargi):
    RUNLOG.mkdir(exist_ok=True)
    yol = RUNLOG / f"{adim.ad}-yargi-{seviye:02d}.md"
    satirlar = [
        f"# Öz-yargı · {adim.ad} · seviye {seviye}/{YARGI_SEVIYE}",
        "",
        f"**Karar:** {yargi['karar']} · **Skor:** {yargi['skor']}/10",
        "",
        "## Yapılanlar",
        *[f"- {x}" for x in yargi["yapilan"]],
        "",
        "## Yapılması gerekenler",
        *([f"- {x}" for x in yargi["yapilmasi_gereken"]] or ["- (yok)"]),
        "",
        "## Neden doğru",
        *([f"- {x}" for x in yargi["dogru"]] or ["- (yok)"]),
        "",
        "## Neden yanlış",
        *([f"- {x}" for x in yargi["yanlis"]] or ["- (yok)"]),
    ]
    if yargi.get("revizyon_notu"):
        satirlar += ["", "## Revizyon notu", yargi["revizyon_notu"]]
    yol.write_text("\n".join(satirlar) + "\n", encoding="utf-8")
    print(f"   öz-yargı {seviye}/{YARGI_SEVIYE}: {yargi['karar']} (skor {yargi['skor']}) → {yol.name}")
    return yol


def yargi_deterministik(adim, degisen, uyarilar, seviye):
    """Test / Claude yok: uyarı yoksa onay, varsa revizyon."""
    if uyarilar:
        return {
            "seviye": seviye,
            "yapilan": [f"dosya: {y}" for y in degisen[:12]] or ["çıktı üretildi"],
            "yapilmasi_gereken": list(uyarilar),
            "dogru": ["makine doğrulaması adımı tamamladı"],
            "yanlis": list(uyarilar),
            "karar": "revizyon",
            "revizyon_notu": "Uyarıları gider: " + "; ".join(uyarilar)[:800],
            "skor": max(1, 6 - min(5, len(uyarilar))),
        }
    return {
        "seviye": seviye,
        "yapilan": [f"dosya: {y}" for y in degisen[:12]] or [f"{adim.ad} tamam"],
        "yapilmasi_gereken": [],
        "dogru": ["makine doğrulaması geçti", "kapsam ve kanıt tutarlı", "uyarı yok"],
        "yanlis": [],
        "karar": "onay",
        "revizyon_notu": None,
        "skor": 9 if degisen else 7,
    }


def yargi_ai(adim, degisen, uyarilar, seviye):
    """Ayrı yargıç oturumu (STUDIO_AI / YARGI_MOD motoruyla)."""
    ozet = []
    for y in degisen[:30]:
        try:
            boy = (KOK / y).stat().st_size if (KOK / y).is_file() else 0
            ozet.append(f"- {y} ({boy} B)")
        except OSError:
            ozet.append(f"- {y}")
    prompt = (
        f"GÖREV: Öz-yargıç. Adım `{adim.ad}` (seviye {seviye}/{YARGI_SEVIYE}) için çıktıyı yargıla.\n"
        f"NOT: {adim.not_}\n"
        f"Değişen dosyalar:\n" + ("\n".join(ozet) or "- (yok)") + "\n"
        f"Makine uyarıları:\n" + ("\n".join(f"- {u}" for u in uyarilar) or "- (yok)") + "\n\n"
        "OKU: değişen dosyaları ve ilgili spec'i. Yazılım kalitesini, spec uyumunu, eksikleri ölç.\n"
        "Estetik asset onayı VERME — o insanın işi. Burada yalnızca yazılım/tasarım dokümanı doğruluğu.\n"
        "JSON döndür: seviye, yapilan, yapilmasi_gereken, dogru, yanlis, karar (onay|revizyon), "
        "revizyon_notu (revizyonda somut düzeltme; onayda null), skor 1-10.\n"
        "Skor ≥ 8 ve yapilmasi_gereken boşsa onay; aksi halde revizyon."
    )
    yuk_bekle(f"{adim.ad}-yargi")
    cmd, prompt, motor = ajan_komut(prompt, KOK, YARGI_SEMA, butce=min(float(BUTCE), 3.0), salt_okunur=True)
    try:
        p = subprocess.run(cmd, cwd=KOK, capture_output=True, text=True, timeout=min(SURE, 600))
    except subprocess.TimeoutExpired:
        return yargi_deterministik(adim, degisen, uyarilar + ["yargı zaman aşımı"], seviye)
    zarf = stream_json_zarf(p.stdout)
    if p.returncode != 0 or zarf is None:
        return yargi_deterministik(adim, degisen, uyarilar + [f"yargıç raporu yok ({motor})"], seviye)
    try:
        yargi = ajan_rapor_coz(zarf, YARGI_SEMA, f"{adim.ad}-yargi", motor)
    except (Dur, RaporYok):
        return yargi_deterministik(adim, degisen, uyarilar + ["yargıç JSON çıkmadı"], seviye)
    yargi["seviye"] = seviye
    sema_dogrula(yargi, YARGI_SEMA, f"{adim.ad} yargı")
    return yargi


def yargi_claude(adim, degisen, uyarilar, seviye):
    """Geriye dönük takma ad."""
    return yargi_ai(adim, degisen, uyarilar, seviye)



def oz_yargi(adim, degisen, uyarilar, seviye):
    if YARGI_MOD == "deterministik":
        yargi = yargi_deterministik(adim, degisen, uyarilar, seviye)
    else:
        try:
            yargi = yargi_ai(adim, degisen, uyarilar, seviye)
        except Dur:
            yargi = yargi_deterministik(adim, degisen, uyarilar + ["yargıç hata → deterministik"], seviye)
    yargi_raporu_yaz(adim, seviye, yargi)
    return yargi


def sor_yonet(adim, exc):
    """Yazılım sorusu → revizyon notu. Oyun tipi / asset → kullanıcıya Dur."""
    soru = getattr(exc, "soru", "") or str(exc)
    neden = getattr(exc, "neden", "") or ""
    sinif = soru_sinifi(soru, neden)
    if sinif == YAZILIM:
        not_ekle(adim.ad, f"[öz-yargı · yazılım duruşu] {neden} | Çöz: {soru}")
        print(f"   \033[33myazılım sorusu kullanıcıya gitmedi → öz-yargı notu\033[0m")
        return False  # tekrar dene
    raise Dur(f"{adim.ad} · insan ({sinif}): {neden}\n  SORU: {soru}")


def kapiya_kadar(adim, kos_fn):
    """Yazılım: en fazla YARGI_SEVIYE öz-yargı. Asset/oyun tipi/demo: insan kapısı."""
    tur = adim.kapi_turu()
    for seviye in range(1, YARGI_SEVIYE + 1):
        try:
            degisen, uyari = kos_fn(adim, notlar_ek(adim.ad))
        except Sor as e:
            if sor_yonet(adim, e) is False:
                continue
            raise
        if tur in (INSAN_ASSET, INSAN_OYUN_TIPI, INSAN_DEMO):
            if onay_iste(adim, degisen, uyari):
                return degisen
            continue
        # yazılım — öz-yargı
        yargi = oz_yargi(adim, degisen, uyari, seviye)
        if yargi["karar"] == "onay" and yargi["skor"] >= 7:
            return degisen
        notu = yargi.get("revizyon_notu") or "; ".join(yargi.get("yanlis") or yargi.get("yapilmasi_gereken") or ["düzelt"])
        not_ekle(adim.ad, f"[öz-yargı {seviye}/{YARGI_SEVIYE} skor={yargi['skor']}] {notu}")
    raise Dur(f"{adim.ad}: {YARGI_SEVIYE} öz-yargı seviyesinde onaylanmadı. "
              f"runlog/{adim.ad}-yargi-*.md — yazılım tavanı; asset/oyun tipi değilse spec'i gözden geçir.")


def tamamla(adim, durum, degisen):
    if adim.worktree:
        dilim_merge(adim)
    for yol in adim.ornek_hash:
        durum.setdefault("ornek_hash", {})[yol] = dosya_hash(KOK / yol)
    durum.get("notlar", {}).pop(adim.ad, None)
    durum["tamamlanan"].append(adim.ad)
    durum_yaz(durum)
    kapi_commit(adim, degisen)


def kos():
    """Oynanır demo'ya (STUDIO_DEMO) kadar yazılım adımlarını öz-yargı ile yürüt.
    İnsan yalnızca oyun tipi ve asset kapılarında; demo kapısında build teslim edilir."""
    durum = durum_oku()
    adimlar = adimlari_uret(durum)
    i = 0
    while i < len(adimlar):
        adim = adimlar[i]
        if adim.insan:
            hata = adim.kontrol()
            if hata:
                # Demo teslim: playtest notu yoksa dur — kullanıcı oynar (yazılım sorusu değil)
                if adim.ad == DEMO_ADIM or adim.kapi_turu() == INSAN_DEMO:
                    raise Dur(f"Oynanır demo hazır · {adim.ad}. {hata}")
                raise Dur(f"{adim.ad}: {hata}")
            if adim.ad == DEMO_ADIM:
                print(f"\n\033[32m✔ Oynanır demo kapısı geçildi: {adim.ad}\033[0m")
            i += 1
            continue
        if adim.ad in durum["tamamlanan"]:
            i += 1
            continue
        hash_kilidi()
        if adim.on:
            hata = adim.on()
            if hata:
                raise Dur(f"{adim.ad}: {hata}")
        if adim.paralel:
            grup = []
            while i < len(adimlar) and adimlar[i].paralel and adimlar[i].komut == adim.komut \
                    and adimlar[i].ad not in durum["tamamlanan"]:
                grup.append(adimlar[i])
                i += 1
            for a, (degisen, uyari) in grubu_paralel_kosun(grup):
                if a.kapi_turu() == YAZILIM:
                    yargi = oz_yargi(a, degisen, uyari, 1)
                    if yargi["karar"] != "onay" or yargi["skor"] < 7:
                        degisen = kapiya_kadar(a, adimi_kosun)
                elif not onay_iste(a, degisen, uyari):
                    degisen = kapiya_kadar(a, adimi_kosun)
                tamamla(a, durum, degisen)
            continue
        degisen = kapiya_kadar(adim, dilim_kosun if adim.worktree else adimi_kosun)
        if adim.secim:
            secim_iste(adim)
        tamamla(adim, durum, degisen)
        if adim.komut in ("faz3a", "faz4b", "parti"):
            return kos()
        i += 1
    print("\n\033[32m✔ Sıradaki adım yok. Ağaç bitti.\033[0m")



# ============================================================ onay / çizim

def durum_oku():
    return json.loads(DURUM.read_text(encoding="utf-8")) if DURUM.exists() else {"tamamlanan": []}


def durum_yaz(d):
    RUNLOG.mkdir(exist_ok=True)
    DURUM.write_text(json.dumps(d, ensure_ascii=False, indent=2), encoding="utf-8")


def onayla(hedefler):
    durum = durum_oku()
    adimlar = {a.ad: a for a in adimlari_uret(durum)}
    bugun = datetime.date.today().isoformat()
    for h in hedefler:
        if h in adimlar:
            if h not in durum["tamamlanan"]:
                a = adimlar[h]
                if not a.insan:  # kapı, koşulmamış adımı atlamak için kullanılamaz
                    eksik = [c for c in a.cikti if not (KOK / c).exists()]
                    if eksik:
                        raise Dur(f"{h}: beklenen çıktı yok: {eksik} — adım koşulmadan kapı açılmaz.")
                    if a.dogrula:
                        a.dogrula(a.arg)
                tamamla(a, durum, [])
            print(f"kapı açıldı: {h}")
            continue
        kimlikler = [k for k, v in manifest_alanlari().items() if v[0] == "taslak"] if h == "taslak" else [h]
        for kimlik in kimlikler:
            p = ham_dosya(kimlik)
            if not p:
                raise Dur(f"{kimlik}: ham dosya yok, onaylanamaz.")
            kayit = next(k for k in manifest_kayitlari() if k["id"] == kimlik)
            hata = harness.varlik_kontrol(kimlik, kayit.get("spec", ""), p)
            if hata:
                raise Dur(f"{kimlik}: harness'ten geçmiyor, onaylanamaz → {hata}")
            manifest_guncelle(kimlik, durum="onaylı", onay_tarihi=bugun, hash=dosya_hash(p))
            print(f"onaylandı: {kimlik}")


def reddet(kimlik, not_metni):
    if kimlik in {a.ad for a in adimlari_uret(durum_oku())}:
        not_ekle(kimlik, not_metni)
        print(f"sonraki koşuda {kimlik} bu notla yeniden üretilecek.")
        return
    kayit = next((k for k in manifest_kayitlari() if k["id"] == kimlik), None)
    if not kayit:
        raise Dur(f"manifest'te yok: {kimlik}")
    tur = int(kayit.get("revizyon", 0)) + 1
    manifest_guncelle(kimlik, durum="revizyon", revizyon=tur,
                      revizyon_notu=json.dumps(not_metni, ensure_ascii=False))
    print(f"revizyona düştü: {kimlik} (tur {tur})" +
          (f" — {REVIZYON_TAVAN}. tur: sonraki parti bu varlıkta DURacak, spec'e bak" if tur >= REVIZYON_TAVAN else ""))


def agac_ciz():
    durum = durum_oku()
    adimlar = adimlari_uret(durum)
    sirada = next((a.ad for a in adimlar if not a.insan and a.ad not in durum["tamamlanan"]), None)
    engel = {a.ad: a.kontrol() for a in adimlar if a.insan}
    gruplar = []
    for a in adimlar:
        if not gruplar or gruplar[-1][0] != a.grup:
            gruplar.append((a.grup, []))
        gruplar[-1][1].append(a)
    print("\n\033[1mSTÜDYO AĞACI\033[0m   ✔ bitti · ▶ sırada · ■ sende · · bekliyor\n")
    for gi, (grup, ogeler) in enumerate(gruplar):
        son_grup = gi == len(gruplar) - 1
        print(f"{'└─' if son_grup else '├─'} \033[1m{grup}\033[0m")
        bosluk = "   " if son_grup else "│  "
        for oi, a in enumerate(ogeler):
            son = oi == len(ogeler) - 1
            if a.insan:
                isaret, renk = ("■", "\033[31m") if engel[a.ad] else ("✔", "\033[32m")
            elif a.ad in durum["tamamlanan"]:
                isaret, renk = "✔", "\033[32m"
            elif a.ad == sirada:
                isaret, renk = "▶", "\033[1m"
            else:
                isaret, renk = "·", "\033[90m"
            hedef = ", ".join(a.cikti) or ("—" if a.insan else "kod")
            print(f"{bosluk}{'└─' if son else '├─'} {renk}{isaret} {a.ad:<20}\033[0m {hedef:<40} {a.not_}")
            if a.insan and engel[a.ad]:
                print(f"{bosluk}{'   ' if son else '│  '}  \033[31m↳ {engel[a.ad]}\033[0m")
    print()


# ================================================================== test

def test():
    import struct
    global DURUM
    g_durum0, DURUM = DURUM, RUNLOG / ".t-durum.json"
    RUNLOG.mkdir(exist_ok=True)
    assert komut_metni("parti", "07").startswith("GÖREV: Varlık partisi 07")
    assert eslesir("tests/a.gd", YASAK) and eslesir("assets/pipeline/harness.py", YASAK)
    assert not eslesir("game/x.gd", YASAK) and eslesir(".wt/dilim-01/x", ATLA)
    assert eslesir("runlog/faz1a.log", YASAK) and not eslesir("indirilenler/x.png", ATLA)
    assert eslesir("game/.godot/imported/x", "game/.godot/*") and eslesir("game/a/b.png.import", "game/*.import")
    try:
        bag_denetle("x", {}, {"runlog/bag.md": ("link", "/tmp/x")})
        raise AssertionError("bağ kaçtı")
    except Dur:
        pass
    bag_denetle("x", {"eski": ("link", "/a")}, {"eski": ("link", "/a")})
    # kapsam + onay nöbeti
    kapsam_denetle("x", ["01-market.md", "runlog/*"], ["01-market.md", "runlog/a-durus.md"], [])
    kapsam_denetle("hazirla", ["game/assets/*"] + MOTOR, [], ["game/assets/eski.png", "game/a.png.import"])  # temiz üretim silebilir
    try:
        kapsam_denetle("faz1a", ["01-market.md"], [], ["game/assets/eski.png"])
        raise AssertionError("kapsam dışı silme geçti")
    except Dur:
        pass
    for degisen, silinen in ((["02-tech.md"], []), ([], ["a.md"]), (["tests/x.gd"], []), (["06-slices/d.md"], [])):
        try:
            kapsam_denetle("x", ["*"] if degisen and degisen[0].startswith(("tests", "06")) else ["01-market.md"], degisen, silinen)
            raise AssertionError(f"kaçtı: {degisen}{silinen}")
        except Dur:
            pass
    once = {"chr_a": ("spec", "-", "-")}
    onay_nobeti("p", "parti", once, {"chr_a": ("taslak", "-", "-")})
    for sonra in ({"chr_a": ("spec", "-", "-"), "chr_b": ("spec", "-", "-")}, {}):
        try:
            onay_nobeti("p", "parti", once, sonra)
            raise AssertionError(f"satır ekleme/silme kaçtı: {sonra}")
        except Dur:
            pass
    for komut, yeni in (("parti", ("onaylı", "-", "-")), ("faz4b", ("taslak", "-", "-")),
                        ("hazirla", ("spec", "ab", "-")), ("parti", ("taslak", "-", "2026-01-01"))):
        try:
            onay_nobeti("p", komut, once, {"chr_a": yeni})
            raise AssertionError(f"kaçtı: {komut} {yeni}")
        except Dur:
            pass
    # manifest satır düzenleme
    global MANIFEST, SECIM
    RUNLOG.mkdir(exist_ok=True)
    gercek, MANIFEST = MANIFEST, RUNLOG / ".t.yaml"
    MANIFEST.write_text("- id: chr_a\n  tip: sprite  # yorum\n  durum: spec\n  hash: '-'\n", encoding="utf-8")
    manifest_guncelle("chr_a", durum="onaylı", hash="abc", onay_tarihi="2026-09-02")
    m = MANIFEST.read_text(encoding="utf-8")
    assert "# yorum" in m and manifest_alanlari(m)["chr_a"] == ("onaylı", "abc", "2026-09-02")
    MANIFEST.unlink()
    MANIFEST = gercek
    # seçim
    g_secim, SECIM = SECIM, RUNLOG / ".t-secim.yaml"
    sec("kisa_liste", "a, b, c")
    assert k_kisa_liste() is None and "oyun tipi" in k_secilen()
    try:
        sec("secilen", "z")
        raise AssertionError("kısa liste dışı seçim geçti")
    except Dur:
        pass
    sec("secilen", "b")
    assert k_secilen() is None
    SECIM.unlink()
    SECIM = g_secim
    # dilim kapsamı spec'ten
    spec = RUNLOG / ".t-dilim.md"
    spec.write_text("Dokun: game/player.gd, game/scenes/player.tscn, game/assets/x.png, tests/t.gd", encoding="utf-8")
    assert dilim_kapsam(spec) == ["game/player.gd", "game/scenes/player.tscn", "tests/t.gd"], dilim_kapsam(spec)
    spec.unlink()
    # charter ayrıştırma
    bilgi_p = RUNLOG / ".t-charter.md"
    bilgi_p.write_text("# Bütçe tavanı\n2000$\n# Kapsam tavanı\n# Varlık bütçesi: 150\n# Kırmızı çizgiler\n"
                       "- multiplayer yok\n- GPL bağımlılık yok\n# Başarı tanımı\n# Kapasite\nhaftada 4 saat\n"
                       "yayın tarihi: 2027-03-01\npaket bütçesi: 200 MB\ndoku belleği: 64 MB\n"
                       "Diller: tr, en, de\n", encoding="utf-8")
    global KOK
    g_kok, KOK = KOK, RUNLOG
    shutil.copy(bilgi_p, RUNLOG / "00-charter.md")
    b = charter_bilgi()
    assert b["eksik"] == [] and b["varlik"] == 150 and b["kirmizi"] == ["multiplayer yok", "GPL bağımlılık yok"]
    assert b["saat_hafta"] == 4 and b["paket_mb"] == 200 and b["doku_mb"] == 64 and str(b["yayin"]) == "2027-03-01"
    assert b["diller"] == ["tr", "en", "de"], b["diller"]           # B9: diller charter'dan
    assert charter_diller() == ["tr", "en", "de"]
    (RUNLOG / "00-charter.md").unlink(), bilgi_p.unlink()
    KOK = g_kok
    assert adet_topla({"kategoriler": [{"ad": "chr", "adet": 12}, {"ad": "ui", "adet": 8}]}) == 20
    ornek_tech = ("## 2A\n### Bağımlılık Adayları (MIT)\n| GdUnit4 | MIT |\n### Salt Referans\n| Tin | GPL-3.0 |\n"
                  "## 2B\n48000 Hz 32x32\n")
    k = re.search(r"^(#+)[^\n]*bağımlılık[^\n]*\n(.*?)(?=^\1 |^#{1,2} |\Z)", ornek_tech, re.M | re.S | re.I)
    assert k and "GPL" not in k.group(2) and "GdUnit4" in k.group(2)
    k2 = re.search(r"^(#+)[^\n]*bağımlılık[^\n]*\n(.*?)(?=^\1 |^#{1,2} |\Z)", ornek_tech.replace("| GdUnit4 | MIT |", "| X | LGPL |"), re.M | re.S | re.I)
    assert re.search(r"\b[al]?gpl\b", k2.group(2), re.I)
    assert duz("Sıra Tabanlı Zindan") == "sira tabanli zindan" and duz("Kart Dövüşü") in duz("### D. Kart Dövüşü (İkincil)")
    iyi = {"adim": "x", "yazilan": ["a.md"], "kanit": [{"komut": "ls", "cikis_kodu": 0}],
           "iddialar": [{"iddia": "3 oyun", "kaynak": "https://x"}], "durus": None}
    sema_dogrula(iyi, RAPOR_SEMA, "r")
    for kotu in ({**iyi, "iddialar": [{"iddia": "3", "kaynak": "bence"}]}, {**iyi, "fazla": 1},
                 {**iyi, "durus": {"neden": "x"}}, {**iyi, "kanit": [{"komut": "ls", "cikis_kodu": "0"}]}):
        try:
            sema_dogrula(kotu, RAPOR_SEMA, "r")
            raise AssertionError(f"şemadan kaçtı: {kotu}")
        except Dur:
            pass
    a = Adim("x", "g", "faz2", kanit_min=2, iddia_zorunlu=True)
    try:
        rapor_denetle(a, iyi, ["a.md"])
        raise AssertionError("kanıt eksikken geçti")
    except Dur:
        pass
    try:
        rapor_denetle(Adim("x", "g", "faz1a"), iyi, ["a.md", "b.md"])
        raise AssertionError("bildirilen≠ölçülen geçti")
    except Dur:
        pass
    assert rapor_denetle(Adim("x", "g", "faz1a"), iyi, ["a.md", "runlog/x.log", "game/.godot/imported/x.ctex", "game/a.png.import"])
    assert rapor_denetle(Adim("x", "g", "faz1a"), iyi, ["a.md"], onceki={"eski.tscn"})  # önceki denemenin dosyası raporsuz
    assert rapor_denetle(Adim("x", "g", "faz1a"), {**iyi, "yazilan": ["a.md", "eski.tscn"]}, ["a.md"], onceki={"eski.tscn"})
    # kanıt tekrar koşulur
    yalan = {**iyi, "kanit": [{"komut": "false", "cikis_kodu": 0}, {"komut": "true", "cikis_kodu": 0}]}
    try:
        rapor_denetle(Adim("x", "g", "faz2", kanit_min=1), yalan, ["a.md"])
        raise AssertionError("sahte kanıt geçti")
    except Dur as e:
        assert "kanıt tutmuyor" in str(e)
    dogru = {**iyi, "kanit": [{"komut": "true", "cikis_kodu": 0}, {"komut": "false", "cikis_kodu": 1},
                              {"komut": "bash tests/yok.sh", "cikis_kodu": 127}]}
    rapor_denetle(Adim("x", "g", "faz2", kanit_min=1), dogru, ["a.md"])
    (RUNLOG / ".t-yan-etki").unlink(missing_ok=True)
    try:
        korumali_kos("x", ["01-market.md"], lambda: (RUNLOG / ".t-yan-etki").write_text("z"))
        raise AssertionError("yan etki kaçtı")
    except Dur:
        pass
    (RUNLOG / ".t-yan-etki").unlink(missing_ok=True)
    assert korumali_kos("x", ["runlog/*"], lambda: 7) == 7
    assert komut_kos(["bash", "-c", "echo merhaba; exit 3"])[0] == 3 and "merhaba" in komut_kos(["echo", "merhaba"])[1]
    assert komut_kos(["sleep", "5"], sure=1)[0] == "zaman aşımı"
    yuk_bekle("x", tavan=10 ** 6)
    try:
        yuk_bekle("x", tavan=0.0, bekle=0)
        raise AssertionError("yük nöbeti geçti")
    except Dur as e:
        assert "makine yüklü" in str(e)
    for kotu in ("true; touch /tmp/x", "ls | wc", "echo $(id)", "bash -c id", "curl http://x", "python3 /tmp/x.py", "bash"):
        try:
            kanit_kos(Adim("x", "g", "faz2"), [{"komut": kotu, "cikis_kodu": 0}], KOK)
            raise AssertionError(f"tehlikeli kanıt koştu: {kotu}")
        except Dur:
            pass
    # yetki dosyası nöbeti
    global YETKI_YOLLARI
    g_yetki, YETKI_YOLLARI = YETKI_YOLLARI, [RUNLOG / ".t-yetki.md"]
    YETKI_YOLLARI[0].write_text("a", encoding="utf-8")
    once = yetki_goruntusu()
    yetki_denetle("x", once)
    YETKI_YOLLARI[0].write_text("zehir", encoding="utf-8")
    try:
        yetki_denetle("x", once)
        raise AssertionError("yetki değişikliği kaçtı")
    except Dur:
        pass
    YETKI_YOLLARI[0].unlink()
    YETKI_YOLLARI = g_yetki
    assert "Bash(git:*)" in YASAK_ARACLAR and "Edit(~/.claude/**)" in YASAK_ARACLAR
    sema_dogrula([{"id": "chr_a", "tip": "s", "spec": "48x48", "kaynak": "cc0", "lisans": "-", "oncelik": 1,
                   "durum": "spec", "revizyon": 0, "hash": "-", "onay_tarihi": "-"}], MANIFEST_SEMA, "m")
    try:
        sema_dogrula({"menu.basla": {"tr": "Başla"}}, strings_sema(), "s")
        raise AssertionError("en eksikken geçti")
    except Dur:
        pass
    sema_dogrula({"menu.basla": {"tr": "Başla", "en": "Start"}}, strings_sema(), "s")
    sema_dogrula({"menu.basla": {"tr": "Başla", "en": "Start", "de": "Los"}}, strings_sema(["tr", "en", "de"]), "s")
    try:  # charter 3 dil diyorsa 2 dillik tablo geçmez
        sema_dogrula({"menu.basla": {"tr": "Başla", "en": "Start"}}, strings_sema(["tr", "en", "de"]), "s")
        raise AssertionError("eksik dil geçti")
    except Dur:
        pass
    # B2 — tests/ denetimi
    assert iddia_sayisi('ok(a == 1, "x")\nok(b, "y")\n# ok(c, "yorumdaki sayılmaz")') == 2
    assert iddia_sayisi("okuma(x)\nbook(y)") == 0  # ok ile başlayan başka ad sayılmaz
    g_td, cagri = test_denetimi, []
    globals()["test_denetimi"] = lambda ad, yollar, kok, taban: cagri.append((ad, tuple(yollar)))
    kapsam_denetle("dilim-07", ["game/x.gd"], ["game/x.gd", "tests/dilim_07_test.gd"], [])
    assert cagri == [("dilim-07", ("tests/dilim_07_test.gd",))], cagri
    try:  # dilim dışı adımda tests/ hâlâ kapsam dışı
        kapsam_denetle("faz3c", ["03-strings.yaml"], ["tests/dilim_07_test.gd"], [])
        raise AssertionError("dilim dışı tests/ yazımı kaçtı")
    except Dur:
        pass
    try:  # tests/ silme her koşulda ret
        kapsam_denetle("dilim-07", ["game/x.gd"], [], ["tests/dilim_07_test.gd"])
        raise AssertionError("test silme kaçtı")
    except Dur:
        pass
    globals()["test_denetimi"] = g_td
    adlar = [x.ad for x in adimlari_uret({"tamamlanan": []})]
    not_ekle("ornek-3a", "daha kısa"); not_ekle("ornek-3a", "daha sert ton")
    assert "1. daha kısa" in notlar_ek("ornek-3a") and "2. daha sert ton" in notlar_ek("ornek-3a")
    for beklenen in ("charter", "faz1a", "kisa-liste", "faz1b", "secilen", "faz2", "ornek-3a", "faz3a", "ornek-3c", "faz3c", "faz4a",
                     "faz4b", "varlik-onay", "hazirla", "dilim-spec", "yayin", "steam"):
        assert beklenen in adlar, (beklenen, adlar)
    # AI motor seçimi (claude | cursor)
    assert ai_adi() in ("claude", "cursor")
    ornek = {"adim": "faz1a", "yazilan": ["01-market.md"], "kanit": [], "iddialar": [], "durus": None}
    assert json_nesne_cikar("ön\n```json\n" + __import__("json").dumps(ornek) + "\n```\nson", RAPOR_SEMA, "t")["adim"] == "faz1a"
    zarf = stream_json_zarf('{"type":"x"}\n{"type":"result","subtype":"success","is_error":false,"result":"{}"}\n')
    assert zarf and zarf["type"] == "result"
    global STUDIO_AI
    _ai0 = STUDIO_AI
    STUDIO_AI = "cursor"
    try:
        cmd, _, motor = ajan_komut("p", KOK, RAPOR_SEMA, salt_okunur=False)
        assert motor == "cursor" and "--force" in cmd and "--trust" in cmd and "--workspace" in cmd
        cmd2, _, _ = ajan_komut("p", KOK, RAPOR_SEMA, salt_okunur=True)
        assert "--mode" in cmd2 and "ask" in cmd2 and "--force" not in cmd2
    finally:
        STUDIO_AI = _ai0
    # öz-yargı / soru sınıflandırma
    assert soru_sinifi("test kırmızı, offset 16px kaydır", "layout") == YAZILIM
    assert soru_sinifi("hangi konsepti seçelim?", "kısa liste") == INSAN_OYUN_TIPI
    assert soru_sinifi("bu sprite güzel mi?", "kontakt palet") == INSAN_ASSET
    a_yaz = Adim("faz2", "t", "faz2")
    assert a_yaz.kapi_turu() == YAZILIM
    a_as = Adim("parti-01", "t", "parti")
    assert a_as.kapi_turu() == INSAN_ASSET
    a_ot = Adim("kisa-liste", "t", kontrol=lambda: None, insan_tur=INSAN_OYUN_TIPI)
    assert a_ot.kapi_turu() == INSAN_OYUN_TIPI
    y = yargi_deterministik(a_yaz, ["02-tech.md"], [], 1)
    assert y["karar"] == "onay" and y["skor"] >= 7
    y2 = yargi_deterministik(a_yaz, ["02-tech.md"], ["uyarı x"], 2)
    assert y2["karar"] == "revizyon" and y2["revizyon_notu"]
    sema_dogrula(y, YARGI_SEMA, "yargi")
    # yazılım Sor → not, kullanıcıya değil
    try:
        raise Sor("x DURDU", neden="test fail", soru="ok() sayısını artırayım mı?")
    except Sor as e:
        assert sor_yonet(a_yaz, e) is False
    assert any("yazılım duruşu" in n for n in durum_oku().get("notlar", {}).get("faz2", []))
    DURUM.unlink(missing_ok=True)
    DURUM = g_durum0
    print("tamam")


if __name__ == "__main__":
    try:
        argv = ARGV
        if "--test" in argv:
            test()
        elif "--agac" in argv or "--durum" in argv:
            agac_ciz()
        elif "--onayla" in argv:
            onayla(argv[argv.index("--onayla") + 1:])
        elif "--reddet" in argv:
            i = argv.index("--reddet")
            reddet(argv[i + 1], " ".join(argv[i + 2:]) or "revizyon")
        elif "--sec" in argv:
            i = argv.index("--sec")
            sec(argv[i + 1], " ".join(argv[i + 2:]))
        elif "--dogrula" in argv:  # ajan koşmadan: çıktı + doğrulayıcı + sonrası (hash, idempotens…)
            ad = argv[argv.index("--dogrula") + 1]
            adim = next(a for a in adimlari_uret(durum_oku()) if a.ad == ad)
            for u in dogrula_ve_sonrasi(adim):
                print(f"   uyarı: {u}")
            print(f"{ad}: doğrulamadan geçti → python3 studio.py --onayla {ad}")
        else:
            kos()
    except Dur as e:
        print(f"\n\033[31m■ DUR:\033[0m {e}")
        sys.exit(1)
