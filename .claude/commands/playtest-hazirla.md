---
description: Oynanabilir build hazırla + playtest not şablonu — /playtest-hazirla N
argument-hint: "N (playtest numarası)"
---
GÖREV: Kullanıcının oynayacağı build'i hazırla.
OKU: son merge durumu
YAZ: runlog/playtest-$ARGUMENTS-notlar.md (boş şablon; N = $ARGUMENTS)

1 Build komutunu ve çıktı adını `02-tech.md`'deki CLI export satırından al — bu dosyada motor adı ya da
  paket adı yazmaz. Mevcut build güncel ve testler yeşilse YENİDEN ALMA; boyutunu ve tarihini yaz.
  Yeniden alman gerekiyorsa build çıktısını `yazilan` listesine EKLE (aksi halde "bildirilmeyen dosya" ile reddedilir).
  Çıktı repo kökündeki `build/` altına gider (`game/` içine yazma). Komut ve süreyi yaz.
  Bot günlükleri/ekran görüntüleri `runlog/playtest-bot-N/` altına.
2 Duman testi: `bash tools/duman.sh 60 runlog/duman-testi.log` — betik yönlendirmeyi kendi içinde yapar,
  hata yoksa 0 döner ve kanıt olarak kullanılabilir. Kanıt komutlarında boru/yönlendirme/zincir KULLANMA
  (studio aynı komutu tekrar koşar; meta karakterli komut reddedilir). En az iki sıfır çıkışlı kanıt gerekir
  (ör. `bash tools/duman.sh 60 runlog/duman-testi.log` ve `bash tests/run.sh`).
3 Playtest botu varsa çalıştır: her bölüm baştan sona bitirilebiliyor mu.
4 Kullanıcı için not şablonu üret:
   - Bu build'de yeni ne var (son playtest'ten beri merge edilen dilimler)
   - Özellikle bakılması istenen 3 şey
   - Bilinen eksikler
   - Boş bölüm: "his", "denge", "kafa karıştıran yerler"

BİTİR: Build yolunu ve şablonu yaz, dur. Oynamak kullanıcının işi.
