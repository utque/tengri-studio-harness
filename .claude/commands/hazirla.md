---
description: Faz 5 — onaylı ham varlıkları motora hazırla
---
GÖREV: Onaylı ham varlıkları motorun kullandığı türevlere çevir.
OKU: assets/manifest.yaml, assets/raw/, 02-tech.md, 03-strings.yaml
YAZ: assets/pipeline/ (scriptler), game/assets/ (üretilmiş çıktı)

ÖN KOŞUL: Manifest'te durumu "onaylı" olmayan varlık varsa DUR ve listele.
Sadece onaylı varlıkları işle.

1 PIPELINE SCRIPTLERİ - assets/pipeline/ altına yaz. Giriş noktası
  assets/pipeline/hazirla.sh olacak; hepsini sırayla koşar, argüman almaz.
  İdempotent olmalı:
  game/assets/ silinip script tekrar çalıştığında birebir aynı çıktı üretilmeli.

  Sprite:    şeffaf kenar kırpma, pivot normalizasyonu, 02-tech.md'deki extrude payı,
             atlas paketleme, kare koordinat tablosu. Her atlas PNG'sinin yanına
             aynı adla JSON: {"extrude": 2, "kareler": [{"id","x","y","w","h"}]}
             (studio.py sızma testini bu tablodan yapar)
  Animasyon: FPS, loop bayrağı, olay kareleri, animasyon kaynağı
  Tileset:   ızgaraya dilimleme, çarpışma şekilleri, autotile bit maskeleri
  Arayüz:    nine-slice kenar bölgeleri, buton durum atlası, tema kaynağı
  İkon:      boyut varyantları, nearest filtre, mipmap KAPALI
  SFX:       sessizlik kırpma, DC offset temizliği, hedef seviyeye normalizasyon
  Müzik:     LUFS normalizasyonu, örnek hassasiyetinde loop noktaları
  Font:      Türkçe karakter kümesi (ğ ı ş İ ö ü ç), hinting, boyut varyantları
  Metin:     03-strings.yaml'dan çeviri kaynağı üret
  Pazarlama: 5 capsule boyutu, sıkıştırma, renk profili

2 REGISTRY ÜRET - game/assets/registry.gd
   İşlenmiş her varlık için bir sabit. Dosyanın başına
   "# ÜRETİLMİŞ DOSYA - elle düzenlemeyin" yaz.
   Aynı şekilde 03-strings.yaml'dan Strings sınıfını üret.

3 DOĞRULA - hepsini çalıştır ve raporla:
   - Her türev headless olarak motora yükleniyor mu
   - Atlas'ta komşu sprite sızması var mı (piksel testi)
   - Çift yönlü tamlık: her manifest satırının bir çıktısı, her çıktının bir
     manifest satırı var mı
   - Yetim varlık: üretildi ama koddan referans verilmiyor
   - Ses seviyeleri hedef aralıkta mı, kırpılma var mı
   - Toplam paket boyutu ve doku belleği

4 HASH VE İDEMPOTENS - bunları SEN YAPMA. Hash'leri manifest'e studio.py
   yazar, idempotens testini studio.py koşar. Manifest'in durum/hash/
   onay_tarihi alanlarına dokunursan tur reddedilir.

RAPORLAMA — turların çoğu burada yanıyor, dikkat et:
- `yazilan` listesine pipeline'ın DOKUNDUĞU HER dosya girer: `game/assets/` altındaki
  üretilmiş çıktılar, `game/project.godot`, ve yazdığın pipeline betiklerinin kendisi
  (`hazirla.sh`, `hazirla.py`, `dogrula.py`, `idempotens.py`…). studio.py anlık görüntü
  farkıyla ölçer; eksik bildirim turu reddettirir.
- `kanit` komutları kendi sarmalayıcıların olacak, tek komut, meta karaktersiz:
  `bash assets/pipeline/hazirla.sh`, `python3 assets/pipeline/dogrula.py`.
  `python3 -c "..."`, boru, `;`, `&&`, `>` YASAK — studio komutu aynen tekrar koşar.
- Çıkış kodunu GERÇEKTEN oku ve yaz. studio aynı komutu tekrar koşup karşılaştırır;
  "0" yazıp 1 dönen komut turu reddettirir.
- Motor import'unu unutma: CSV kaydı yetmez, `.translation` dosyaları import ile doğar.
  Import çağrısı `hazirla.sh` içinde olacak ki pipeline tekrar üretilebilir kalsın.

BİTİR: runlog/hazirlama-raporu.md yaz (üretilen adet, yetim listesi, paket
boyutu, doku belleği, idempotens sonucu) ve dur.
