---
description: Faz 4B — varlık manifestosu (assets/manifest.yaml)
---
GÖREV: Varlık manifestosunun oluşturulması.
OKU: gdd/varliklar.yaml, 03-levels/, 03-strings.yaml, 04-style.md, 02-tech.md
YAZ: assets/manifest.yaml

Her varlık için bir satır. Şablon:

- id: chr_player_run
  tip: sprite_animasyon
  spec: "48x48, 8 kare, pivot merkez, PNG"   # boyut/pivot/extrude 02-tech.md 2C'den
  kaynak: ai-üretim          # ai-üretim | komisyon | satın-alma | cc0 | kendi
  lisans: "-"
  bagimli: [04-style.md]
  kullanan: [bolum-01, bolum-03]
  oncelik: 1                 # 1 = önce üretilecek
  durum: spec                # SEN DEĞİŞTİREMEZSİN
  revizyon: 0
  hash: "-"
  onay_tarihi: "-"

KURALLAR
- id şeması: <kategori>_<özne>_<varyant>. Kategori kısaltmaları:
  chr, env, fx, ui, ico, sfx, mus, fnt, dat, mkt
- spec alanı 02-tech.md'deki teknik spec'ten türer, serbest metin değildir
- Her bölümün ve her ekranın ihtiyaç duyduğu varlık listede olmalı
- Steam pazarlama varlıklarını da ekle (5 capsule boyutu, ekran görüntüleri)
- durum alanına "spec" dışında bir şey yazma

ÇIKTI SONUNDA şu özeti yaz:
- Kategori başına adet
- Toplam adet
- 00-charter.md'deki varlık bütçesiyle karşılaştırma
- Onay yükü tahmini (adet x 90 saniye, ve 20'lik partilerle tahmini süre)

Toplam bütçeyi aşıyorsa DUR ve sor. Kendi kendine kısma.
BİTİR: Dosyayı yaz ve dur.
