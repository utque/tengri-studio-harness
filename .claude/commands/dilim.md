---
description: Faz 6 — dikey dilim yapım turu, /dilim NN
argument-hint: "NN (dilim numarası)"
---
GÖREV: Dikey dilim $ARGUMENTS'in yazılması. (Bu dosyada geçen NN = $ARGUMENTS)
OKU: 06-slices/dilim-NN.md, ilgili gdd/*.yaml, game/assets/registry.gd
YAZ: SADECE dilim spec'inde adı geçen kod dosyaları

DÖNGÜ
1 Spec'i oku. Spec'te olmayan hiçbir şeyi yapma.
2 Testi ÖNCE yaz. Çalıştır, kırmızı olduğunu gör, çıktıyı kaydet.
3 Kodu yaz.
4 Testi çalıştır. Kanıt komutunu İCAT ETME: tools/ altındaki hazır sarmalayıcıyı
  çağır (tek komut, boru/;/&&/> yok). Çıkış kodunu oku.
5 Kaldıysa düzelt ve 4'e dön. EN FAZLA 3 DENEME.

TEST YAZARKEN (pilotun en pahalı dersi: 7 duruşun 4'ü buradan çıktı)
- Sabit gömme. Test bir DEĞERİ değil bir İLİŞKİYİ doğrular:
  `yol_px[0] == Vector2(72, 24)` DEĞİL, `yol_px[0] == Harita.hucre_merkezi(0, 0)`.
  `D.MAKS_SEVIYE == 3` DEĞİL, `D.hasar(sv + 1) > D.hasar(sv)`.
  Sayı yazman şartsa kaynağından oku (ProjectSettings, Denge.*), tekrar yazma.
- Test dosyası DAVRANIŞA göre adlanır (`hud_test.gd`, `yol_test.gd`), dilime göre
  değil. Mevcut bir davranışı değiştiriyorsan o davranışın dosyasını güncelle,
  yenisini açma — yoksa süit zamanla kendisiyle çelişir.
- Arayüz testi üçünü birden ölçer: çakışma yok, minimum genişlik, metin sığıyor.

ARAYÜZ YAZARKEN
Container kullan (HBox/VBox/Grid). Sabit piksel offset'i yazma: düğme minimum
boyutu metne göre büyür, offset bunu tutmaz. Pilotta tek bir düğme eklemek üst
şeridi üç dilim üst üste bozdu.

DENGE DEĞİŞTİRİRKEN
Önce simülatör olacak. Sayıyı hisle değil ölçüyle değiştir; değişikliğin çıktısını
CSV olarak runlog'a yaz. Simülatör yoksa DUR ve sor.

YASAKLAR
- tests/ içinde iddia SİLMEK ya da azaltmak - test gevşetmek yasak.
  Yalnız istisna: eski bir testteki sabit yeni spec yüzünden yanlışsa o sabiti
  güncelleyebilirsin. ok() sayısı azalamaz, yeni test dosyası ekleyemezsin,
  test silemezsin. studio.py sayar; düşerse tur reddedilir ve güncelleme
  kapıda kullanıcıya uyarı olarak çıkar.
- assets/, game/assets/, 03-strings.yaml'a yazmak
- Dosya yolu string'i yazmak - Assets.* ve Strings.* sabitlerini kullan
- Oyuncuya görünen metin yazmak - Strings.* kullan
- Yeni bağımlılık eklemek
- Spec'te adı geçmeyen dosyaya dokunmak

EKSİK VARLIK: registry'de ihtiyacın olan sabit yoksa varlık yok demektir.
Kendin üretme, placeholder koyma. DUR ve sor.

3. DENEMEDE HÂLÂ KIRMIZI: runlog/dilim-NN-durus.md yaz ve dur. Raporda testin
tam çıktısı, denediğin 3 yaklaşım ve senin teşhisin olsun.

BİTİR: Testler yeşilse değişen dosyaların listesini ve test çıktısını yaz, dur.
Merge kararını sen vermezsin.
