---
description: Varlık partisi üretimi — /parti NN
argument-hint: "NN (parti numarası)"
---
GÖREV: Varlık partisi $ARGUMENTS'in üretimi. (Bu dosyada geçen NN = $ARGUMENTS)
OKU: assets/manifest.yaml, 04-style.md, 02-tech.md
YAZ: assets/raw/ altına dosyalar, ve runlog/parti-NN.html (kontakt sayfası)

1 Manifest'ten durumu "spec" ya da "revizyon" olan, öncelik sırasına göre ilk
  20 varlığı al. Daha fazlasını alma.

2 Her varlığı 04-style.md'deki kurallara ve manifest'teki spec'e uyarak üret.

3 Her varlığı doğrulama harness'inden geçir:
    python3 assets/pipeline/harness.py <id>
  GEÇMEYENİ TESLİM ETME - düzelt ve tekrar dene. Harness'tan geçmeyen bir varlık kullanıcının önüne gitmez.

4 runlog/parti-NN.html üret: tek sayfada 20 varlık, her birinin yanında
  id'si, spec'i, ve 04-style.md'deki ilgili referans görseli. Her varlığın
  ham dosyasını göreli yolla GÖM. studio.py `src=` VE `href=` özniteliklerini
  tarar; her varlığın ham dosyası ikisinden birinde geçmek ZORUNDA:
    görsel → <img src="../assets/raw/<id>.png">
    ses    → <audio src="../assets/raw/<id>.wav" controls>
    font   → <a href="../assets/raw/<id>.ttf">indir</a> ve ayrıca
             @font-face ile yükleyip beş dilden örnek metin göster
             (ör. "Başla · Zurück · Conquête · Niño · Start")
  Kopya üretme, id'yi metin olarak yazmak yetmez. Şeffaf varlıkların altına
  dama tahtası zemin koy. Animasyonları kare kare göster.

  ÖNEMLİ: Sayfada ADI GEÇEN her varlığı GÖM — bu turda üretmediklerini de.
  Referans olarak "env_su ile aynı palet" gibi bir cümle yazdıysan env_su'nun
  dosyasını da `<img src="../assets/raw/env_su.png">` ile koy. studio.py sayfada
  geçen onaylı varlıkları da gömülü listesinde arar; anıp göstermemek turu
  reddettirir. Anmak istemiyorsan id'sini hiç yazma.

5 Manifest'te bu varlıkların durumunu "taslak" yap. BAŞKA HİÇBİR ALANA
  DOKUNMA - durum alanını "onaylı" yapamazsın.

REVİZYON: Manifest'te revizyon notu olan varlıklar için notu oku ve ona göre
üret. Bir varlık 3. revizyona geldiyse DUR ve sor - sorun varlıkta değil
spec'te olabilir.

RAPORLAMA — turların yarısı burada yanıyor. Bitirmeden önce `yazilan` listesini
şu dört maddeye karşı TEK TEK say:
  [ ] ürettiğin her ham dosya (assets/raw/<id>.png|wav|ogg|ttf) — hepsi, istisnasız
  [ ] üreteç betiği: assets/raw/_partiNN_uret.py
  [ ] assets/manifest.yaml (durum alanlarını yazdın, dokundun demektir)
  [ ] runlog/parti-NN.html
studio.py dosya sistemi anlık görüntüsünü raporunla karşılaştırır; bir dosya bile
eksikse tur reddedilir. "Ürettim ama bildirmedim" en sık ret sebebi — studio anlık görüntü farkıyla ölçer, eksik bildirim ret.
`kanit` komutları tek komut ve meta karaktersiz olacak (`python3 assets/pipeline/harness.py <id>`);
boru/`;`/`&&`/`>` ve `python3 -c "..."` yasak. Çıkış kodunu gerçekten oku — studio
aynı komutu tekrar koşup karşılaştırır.

BİTİR: Kontakt sayfasını üret ve dur. Kullanıcı onaylayana kadar sonraki
partiye geçme.
