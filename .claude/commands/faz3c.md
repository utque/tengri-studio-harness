---
description: Faz 3C — oyundaki tüm metinlerin tablosu (03-strings.yaml)
---
GÖREV: Oyundaki tüm metinlerin yazılması.
OKU: 03-gdd.md, gdd/ekranlar.yaml, 03-levels/
YAZ: 03-strings.yaml

Oyuncunun görebileceği HER metni topla ve yaz:
menü etiketleri, buton metinleri, ipuçları, diyalog, eşya açıklamaları,
başarım isimleri ve açıklamaları, hata mesajları, yükleme ekranı metinleri,
ayarlar ekranındaki her satır, kredi ekranı.

FORMAT (diller 00-charter.md'nin "Diller:" satırından gelir; hepsi zorunlu):
  menu.basla:
    tr: "Başla"
    en: "Start"

KURALLAR
- Charter'da yazan HER dil her anahtarda olacak. Eksik dil bırakma; şema reddeder.
- Anahtar isimleri nokta ile gruplanır: menu.*, hud.*, item.*, dialog.*, err.*
  Grup adlarını oyuna göre sen seçersin, dayatılan sözlük yok.
- Ton tutarlı olsun; 03-gdd.md'deki tema ile uyuşsun
- Türkçe ve Almanca metinler İngilizce'den ~%20-35 uzun olabilir; dar arayüz
  alanlarına giren metinleri EN UZUN dile göre kısa tut ve bunu not düş.
  Pilotta üç dilim üst üste bu yüzden yandı: metin sığmadı, düzen bozuldu.
- Hiçbir metni koda bırakma; ekranlarda gördüğün her şeyin anahtarı olsun

BİTİR: Dosyayı yaz ve dur.
