---
description: Faz 3B — tek bölümün tasarımı, /faz3b NN
argument-hint: "NN (bölüm numarası)"
---
GÖREV: Bölüm $ARGUMENTS'in kağıt üstünde tasarımı. SADECE bu bölüm.
OKU: 03-gdd.md, gdd/bolumler.yaml (bölüm $ARGUMENTS satırı), varsa önceki bölüm dosyaları (salt okunur)
YAZ: 03-levels/bolum-$ARGUMENTS.md (yalnızca bu dosya; diğer bölümlere dokunma)

Her bölüm dosyası şunları içerir:
- Izgara layout (ASCII ya da JSON - proje boyunca aynı formatı kullan)
- Düşman ve eşya yerleşimi, koordinatla
- Giriş koşulu ve çıkış koşulu
- Tempo notu: ilk 30 saniye ne olur, zorluk nerede yükselir
- Hangi mekanik burada tanıtılıyor ya da tekrar ediliyor
- Tahmini süre (dakika)
- Kullandığı varlıkların id listesi

KURAL: Sadece gdd/varliklar.yaml'da olan varlıkları kullan. Yeni varlığa
ihtiyaç duyarsan DUR ve sor - envantere kendin ekleme.

KONTROL: Tüm bölümlerin toplam süresi 03-gdd.md'deki iddiayla uyuşuyor mu?
Uyuşmuyorsa raporla.

BİTİR: Dosyaları yaz ve dur.
