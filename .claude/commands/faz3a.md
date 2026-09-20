---
description: Faz 3A — tasarım dokümanı, 10 açı + gdd/*.yaml
---
GÖREV: Tasarım dokümanı, 10 açı.
OKU: 00-charter.md, 01-market.md, 02-tech.md
YAZ: 03-gdd.md ve gdd/*.yaml

10 açının HEPSİNİ doldur. "Sonra netleştiririz" yazma - yazacaksan DUR ve sor.

1 Çekirdek döngü - 30 saniyelik döngü, TEK CÜMLE
2 İlerleyiş - ne açılır, hangi sırayla, oyuncu neden devam eder
3 Bölüm yapısı - kaç bölüm, her biri kaç dakika, hangi mekanik nerede giriyor
4 Hikaye ve tema - mümkün olan en az metinle
5 Kontrol şeması - klavye + gamepad girdi haritası
6 Ekran listesi ve akış - her ekran, her buton, geçişler
7 Sanat yönü ve varlık envanteri - SAYIYLA (12 sprite, 4 tileset, 30 ikon)
8 Ses envanteri - efekt sayısı, parça sayısı, süreler
9 Zorluk ve ekonomi - sayısal tablolar ve formüller, proza değil
10 Kapsam dışı listesi - v1'de OLMAYACAK her şey. En az 15 madde yaz.

AYRICA gdd/ altına makine okunabilir olarak yaz. Şemalar SABİT, alan ekleme:

- gdd/ekranlar.yaml — liste:
    - ad: "ana_menu"
      butonlar: ["basla", "ayarlar", "cikis"]
      gecisler: ["oyun", "ayarlar"]
- gdd/varliklar.yaml — tek nesne:
    kategoriler:
      - {ad: chr, adet: 12, aciklama: "oyuncu + 3 düşman sprite seti"}
      - {ad: env, adet: 4}
    (ad yalnızca: chr env fx ui ico sfx mus fnt dat mkt)
- gdd/bolumler.yaml — liste:
    - {sira: 1, ad: "Giriş", sure_dk: 8, mekanik: "zıplama"}   # "no" yazma: YAML onu false okur
- gdd/denge.yaml — serbest nesne, ama proza değil: formüller ve tablolar.

KONTROL: gdd/varliklar.yaml toplamı 00-charter.md'deki varlık bütçesini
aşıyorsa DUR ve sor. Kendi kendine kısma.

BİTİR: Dosyaları yaz ve dur.
