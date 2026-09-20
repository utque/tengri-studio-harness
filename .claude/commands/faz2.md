---
description: Faz 2 — teknik keşif, motor kararı, varlık pipeline spec'i
---
GÖREV: Teknik keşif, motor kararı ve varlık pipeline spesifikasyonu.
OKU: 00-charter.md, 01-market.md, 01-secim.yaml (secilen: kullanıcının seçtiği tek konsept)
YAZ: 02-tech.md, ve kanıt için runlog/faz2-kanit.md

2A REFERANS VE LİSANS
- Benzer 5-8 açık kaynak proje bul. Her biri için: ne çözüyor, lisansı ne,
  kod kalitesi, son commit tarihi.
- İKİ AYRI KUTU: "salt referans" (okunur, kod kopyalanmaz) ve "bağımlılık
  adayı" (projeye girebilir).
- Bağımlılık kutusuna SADECE MIT / Apache-2.0 / BSD / CC0 girebilir.
  GPL/AGPL/LGPL gördüğün her şey salt referans kutusuna gider.

2B MOTOR KARARI
Godot 4.x, Unity ve kod tabanlı bir seçeneği şu kriterlerle karşılaştır:
headless test, komut satırından export, dosya formatının metin olup olmadığı,
Steam entegrasyonu, içerik araçları, motor kaynağının okunabilirliği.
Godot lehine bir önyargı ile başla; aksini savunacaksan gerekçesini yaz.

KANIT PROTOTİPİ — oyun yazma. Her şey runlog/faz2-kanit/ altında olur; başka
yere (game/, /tmp, ~) yazma — kapsam denetimi reddeder. game/ Faz 5'te doğar.
- runlog/faz2-kanit/project.godot ile boş proje oluştur
- Tek bir gerçek test yaz ve headless çalıştır; komutu repo kökünden çalışır
  biçimde yaz (örn. `godot --headless --path runlog/faz2-kanit -s res://test.gd`)
  ve çıkış kodunu yaz. studio.py bu komutu AYNEN tekrar koşar; boru/;/&&/> içeren
  komut kabul edilmez, tek komut yaz.
- Komut satırından bir build al (komut ve süre), çıktıyı runlog/faz2-kanit/build/ altına
- Build süresini ölç ve yaz
- 2C'deki tek örnek varlığı runlog/faz2-kanit/ornek.png (ya da .wav) olarak üret

2C VARLIK PIPELINE SPESİFİKASYONU
Şunları sayı ve kural olarak yaz, "uygun olsun" gibi belirsiz ifade kullanma:
- **Taban çözünürlük** (ör. `Taban çözünürlük: 1920×1080`), **karo boyutu**
  (ör. `Karo: 96 px`) ve **ölçek modu** (`Ölçek modu: kesirli`). Bu üçü burada
  kilitlenir; Faz 6'da değiştirilemez. Pilotta bu karar Faz 6'ya bırakıldı ve
  3 dilim + 14 test iddiası kırdı. studio.py bu üç satırı arar, yoksa reddeder.
- Sprite hücre boyutu, pivot konumu, kenar boşluğu, extrude payı
- Dosya formatı, renk profili, şeffaflık, palet kısıtı
- Animasyon çerçeve sayısı aralığı ve isimlendirme şeması (örnek ver)
- Ses: örnekleme hızı, bit derinliği, hedef normalizasyon seviyesi, loop kuralı
- Dizin yapısı ve motorun import ayarları
Sonunda TEK bir örnek varlık üret ve bu spec'e uyduğunu doğrula.

BİTİR: Dosyaları yaz ve dur.
