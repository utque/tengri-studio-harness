# Faz Kapılı Oyun Stüdyosu — Mimari Plan

**Sekiz faz, on bir kapı.** Kod, takvimin ancak dörtte biri. Önce her şey planlanır, sonra tek tek onaylanan her varlık üretilir, sonra hepsi motora hazırlanır, ve ancak ondan sonra ilk satır yazılır.

Hedef platform: **Steam / PC**. Kontrol modeli: **her faz sonunda insan onayı**.

---

## Temel ilke — stüdyo bir ajan ordusu değil, bir dosya zinciri

Kendi kendine komut veren yapıların dağılma sebebi hep aynı: ajanlar birbirine *görev* aktarıyor. Her aktarımda niyet biraz bozuluyor, üçüncü seviyede artık senin sorduğun şey çalışmıyor.

Bu mimaride ajanlar birbirine görev aktarmıyor. Her faz bir dosya okuyor, tek bir dosya yazıyor ve duruyor. Hafıza ajanda değil, diskte. Ajan durumsuz ve değiştirilebilir; dosya kalıcı ve senin onayından geçmiş.

| İlke | Kural |
|---|---|
| **Tek yönlü akış** | Hiçbir ajan bir üst fazın dosyasını değiştiremez. Yalnızca sen, kapıda değiştirirsin. |
| **İki seviye derinlik** | Orkestratör → işçi. İşçi ajan başka ajan doğuramaz. Patlamanın kaynağı üçüncü seviyedir. |
| **Onay bir alan, rica değil** | Onay durumu dosyada yazar, ajan yazamaz, CI onaysız içerikle build almayı reddeder. |

### Disk üzerindeki yapı

```
studio/
├── 00-charter.md            # sen yazıyorsun, hiç değişmiyor
├── 01-market.md             # Faz 1  → Kapı 1A, 1B
├── 02-tech.md               # Faz 2  → Kapı 2
├── 03-gdd.md + gdd/*.yaml   # Faz 3  → Kapı 3A · DONAR
├── 03-levels/               # bölüm layout'ları  → Kapı 3B
├── 03-strings.yaml          # tüm metinler  → Kapı 3C
├── 04-style.md              # stil kılavuzu  → Kapı 4A
├── assets/manifest.yaml     # satır başına: spec, onay durumu, hash
├── assets/raw/              # onaylı ham dosyalar  → Kapı 4D, tek tek
├── assets/pipeline/         # hazırlama scriptleri  → Faz 5
├── game/assets/             # ÜRETİLMİŞ türevler — elle düzenlenmez
├── game/assets/registry.gd  # ÜRETİLMİŞ — kodun tek varlık arayüzü
├── 06-slices/               # dikey dilim spec'leri
├── game/                    # oyun kaynak kodu
├── tests/                   # kod ajanının DOKUNAMADIĞI dizin
└── runlog/                  # her turun kararı, her duruşun sebebi
```

Ajanın bağlamına dokümanın tamamını değil, o an çalıştığı parçanın spec'ini verirsin. Bağlam ne kadar dar olursa sapma o kadar az olur.

---

## Takvim dağılımı

~13 haftalık bir proje için örnek. Bu tablo mimarinin özeti sayılır: kod yazımı toplam takvimin dörtte birinden azdır. Bu bir israf değil, kontrol mekanizmasının ta kendisi — belirsizlik yapım fazına taşındığında ajan onu kendi doldurur, ve sapma tam orada başlar.

| Faz | Süre | Pay | Senin işin |
|---|---|---|---|
| 0 · Charter | 2 gün | 3% | Tamamı sen |
| 1 · Pazar araştırması | 1,5 hafta | 12% | 2 kapı |
| 2 · Teknik keşif | 1 hafta | 8% | 1 kapı |
| 3 · Tasarım | 2,5 hafta | 19% | 3 kapı, yoğun okuma |
| 4 · Varlık üretimi | 3 hafta | 23% | Varlık başına onay |
| 5 · Motora hazırlama | 1 hafta | 8% | 1 rapor kapısı |
| 6 · Yapım | 3,5 hafta | 27% | Playtest kapıları |
| 7 · Yayın | 4 hafta | paralel | Steam işlemleri |

---

## FAZ 0 — Charter

Tek sayfa, senin elinden. Bu dosya olmadan başlama: ajana "iyi bir oyun bul" dersen sonsuz bir arama uzayı vermiş olursun, ve kontrolden çıkma tam burada başlar.

- **Bütçe tavanı** — takvim ve token/dolar sınırı
- **Kapsam tavanı** — "tek kişiyle 14 haftada bitecek" gibi sert bir cümle
- **Varlık bütçesi** — toplam kaç varlık üretilecek. En kritik satır; sebebi Faz 4'te
- **Kırmızı çizgiler** — multiplayer yok, prosedürel 3D yok, GPL bağımlılık yok, lisansı belirsiz varlık yok
- **Başarı tanımı** — "Steam'de yayında + 500 wishlist" mi, "oynanabilir dikey dilim" mi
- **Senin kapasiten** — haftada kaç saat onay ve playtest. Varlık bütçesi bu sayıdan türetilir

---

## FAZ 1 — Pazar araştırması

İki turlu. 1 orkestratör + 8'e kadar paralel araştırmacı, hepsi salt-okunur. Tek turda karar verdirme: geniş tarama ile derin analiz farklı işlerdir.

### 1A · Geniş tarama — 20 parametre

Parametreleri **sen sabitlersin**, ajan sadece doldurur. Şema sabit olmazsa çıktılar karşılaştırılamaz, karşılaştırılamayan tablo da karar verdirmez.

**Pazar**
1. Tür doygunluğu (son 12 ayda çıkan benzer oyun)
2. Rakiplerin medyan inceleme sayısı
3. Hâkim fiyat bandı
4. Hedef kitle büyüklüğü ve erişilebilirliği
5. Wishlist → satış dönüşüm potansiyeli

**Üretim yükü**
6. Görsel varlık sayısı
7. Animasyon yükü
8. Ses ve müzik yükü
9. İçerik süresi (bölüm × üretim süresi)
10. Teknik karmaşıklık (fizik, AI, netcode)

**Otomasyona uygunluk**
11. Deterministik test edilebilirlik
12. Headless çalıştırılabilirlik
13. Prosedürel içerik payı
14. Varlıkların programatik üretilebilirliği
15. Build + test döngü süresi

**Risk**
16. IP / telif riski
17. Bağımlılık lisansları
18. Platform politikası uyumu
19. Lokalizasyon yükü
20. "Eğlence riski" — mekanik kanıtlanmış mı

> 11–15 arası blok çoğu şablonda yoktur ve senin için en belirleyicisidir: **ajan test edemiyorsa yapım döngüsü kapanmaz.** Ritim oyunu ile bulmaca oyunu arasında pazar farkından çok daha büyük bir otomasyon farkı vardır.

> **Kaynak zorunluluğu.** Ajanların ürettiği owner/gelir rakamları tahmindir ve kendinden çok emin görünürler. Her sayı ya bir URL'e bağlanır, ya `[tahmin]` etiketi taşır. Etiketsiz sayı içeren çıktı kapıdan geçmez.

### 1B · Derin analiz — sadece kısa liste için

- **Rakip teardown** — her aday için 5 rakip; oynanış videolarından çekirdek döngü çıkarımı, içerik miktarı, fiyat/süre oranı
- **İnceleme madenciliği** — olumlu ve olumsuz Steam incelemelerinde tekrar eden temalar. Oyuncular *tam olarak neyi* övüyor, neye kızıyor? GDD'nin en değerli girdisi
- **Ölü oyun analizi** — aynı türde başarısız olmuş 3 oyun ve başarısızlık sebebi. Atlarsan aynı hatayı otonom ve hızlı tekrarlarsın
- **Varlık sayımı** — rakiplerin kaç sprite / kaç bölüm / kaç dakika müzikle çıktığı

**Çıktı:** `01-market.md` — skor tablosu, 3 derin analiz, tek bir öneri.

### Kapı 1A — kısa listeyi 3'e indir
- Skor tablosunu okudun; en yüksek skorluyu değil, *bitirebileceğine inandığını* seçtin
- Etiketsiz sayı kalmadı
- Kapsam ve varlık tavanını aşan adaylar elendi

### Kapı 1B — tek konsepti seç
- Çekirdek döngüyü tek cümleyle sen yazabiliyorsun
- Ölü oyun analizindeki hangi başarısızlık sebeplerine bağışık olduğunu biliyorsun
- Kabaca varlık sayısı charter'daki bütçeye sığıyor

**Donan:** `01-market.md` — hiçbir ajan bundan sonra oyun fikrini yeniden tartışamaz.

---

## FAZ 2 — Teknik keşif

### 2A · Referans ve lisans taraması

İki farklı işi karıştırma: **referans** (mekanik nasıl çözülmüş, sadece okunur) ve **bağımlılık** (projeye girecek, lisans kritik).

> **Lisans kapısı.** GPL lisanslı bir kod tabanını Steam'de kapalı kaynak satamazsın. Lisans matrisi çıkart; MIT / Apache-2.0 / BSD / CC0 dışındaki her şey *salt referans* kutusuna gider. Otonom bir sistemin yapabileceği en pahalı hata projenin altına yanlış lisanslı bir temel koymaktır — ve aylar sonra fark edilir.

### 2B · Motor kararı ve kanıt prototipi

| Kriter | Godot 4.x | Unity | Kod tabanlı |
|---|---|---|---|
| Headless test | `--headless` + GUT / GdUnit4 | batchmode + Test Framework | Dilin test aracı |
| Komut satırından export | Evet | Evet, lisansa bağlı | Evet |
| Ajanın okuyabildiği format | `.tscn` / `.gd` — metin | YAML + GUID | Saf kod |
| Steam entegrasyonu | GodotSteam (4.4+) | Steamworks.NET | Elle |
| İçerik araçları | Dahili | Dahili, güçlü | Yok |

Godot lehine güçlü bir önyargıyla gir; ajandan aksini kanıtlamasını iste. Metin tabanlı sahne formatı tek başına belirleyici — ajan `.tscn` dosyasını okuyabiliyor, diff'ini görebiliyor, düzeltebiliyor.

**Kanıt prototipi:** oyun değil. Boş bir proje, tek bir geçen test, komut satırından alınmış bir build. Kanıt `runlog/`'a yazılır.

### 2C · Varlık pipeline spesifikasyonu

Bu alt faz, "kod yazmadan tüm varlıkları çıkar" fikrini kurtaran şeydir. Üretmeden önce *teknik olarak neyin doğru sayıldığını* yazılı hale getir:

- Çözünürlük ve piksel yoğunluğu; sprite hücre boyutu, pivot noktası, kenar boşluğu
- Dosya formatı, renk profili, şeffaflık, palet kısıtı
- Animasyon çerçeve sayısı ve isimlendirme şeması (`oyuncu_kosu_04.png`)
- Ses: örnekleme hızı, bit derinliği, normalizasyon seviyesi, loop noktaları
- Dizin yapısı ve motorun import ayarları

> Bu spec olmadan üretilen 400 varlık, motora girdiğinde 400 kere yeniden kesilir.

### Kapı 2
- Seçilen motorda gerçek bir test headless çalıştı; kanıt `runlog/`'da
- Build süresi ölçüldü. 2 dakikayı geçiyorsa yapım fazı acı verir — şimdi çöz
- Lisans matrisinde kırmızı yok
- Varlık teknik spec'i yazıldı ve tek bir örnek varlıkla doğrulandı

**Donan:** `02-tech.md`

---

## FAZ 3 — Tasarım, üç ayrı kapı

Bu fazın tek amacı: Faz 4, 5 ve 6'nın soracağı her sorunun cevabı burada yazılı olsun. Yazılı değilse ajan boşluğu kendi doldurur — kontrolden çıkmanın ikinci büyük kaynağı budur.

### 3A · Tasarım dokümanı — 10 açı

1. **Çekirdek döngü** — oyuncunun 30 saniyede tekrarladığı şey, tek cümle
2. **İlerleyiş** — ne açılır, hangi sırayla, oyuncu neden devam eder
3. **Bölüm yapısı** — kaç bölüm, kaç dakika, hangi mekanik nerede giriyor
4. **Hikâye ve tema** — ne kadar az o kadar iyi; her satır metin bir üretim maliyeti
5. **Kontrol şeması** — girdi haritası, klavye + gamepad
6. **Ekran listesi ve akış** — her ekran, her buton, hangi ekrandan hangisine
7. **Sanat yönü ve varlık envanteri** — "pixel art" değil; *12 karakter sprite, 4 tileset, 30 ikon*
8. **Ses envanteri** — efekt sayısı, müzik parça sayısı, süreleri
9. **Zorluk ve ekonomi** — sayısal tablolar ve formüller, prozayla değil
10. **Kapsam dışı listesi** — v1'de *olmayacak* her şey. Dokümanın en önemli bölümü

> **Makine okunabilir yap.** Ekran listesi, varlık envanteri, bölüm tablosu ve zorluk eğrisi ayrıca `gdd/*.yaml` olarak yazılsın. Yapım ajanı prozadan değil tablodan çalışır: proza yorum gerektirir, tablo gerektirmez.

### 3B · Bölüm tasarımları — kağıt üstünde

Ajanların en çok uydurduğu şey budur ve çoğu planda hiç yoktur. Her bölüm için ayrı dosya: ızgara layout'u, düşman/eşya yerleşimi, tempo notu, giriş ve çıkış koşulu, tahmini süre. ASCII ızgara ya da JSON — yeter ki tek yorumu olsun.

Bölümler burada bittiğinde Faz 6'daki "bölüm 7'yi yap" görevi yaratıcı bir iş olmaktan çıkıp mekanik bir işe döner.

### 3C · Metin ve lokalizasyon tablosu

Oyundaki *tüm* metinler kodlanmadan önce yazılır: menü etiketleri, buton metinleri, diyalog, eşya açıklamaları, başarım isimleri, hata mesajları. Tek bir `03-strings.yaml`, anahtar + Türkçe + İngilizce.

Metin de bir varlıktır. Önden yaparsan yapım ajanı hiçbir zaman kendi metnini uydurmaz — sadece anahtar referansı yazar.

### Kapı 3A — tasarımı dondur
- 10 açının hepsi dolu; "sonra netleştiririz" yok
- Varlık envanteri sayı içeriyor ve charter bütçesine sığıyor
- Kapsam dışı listesi gerçekten uzun

**Donan:** `03-gdd.md` — sonraki fazlarda bir ajan GDD değişikliği gerektiğini fark ederse **durur ve sana sorar**.

### Kapı 3B — bölümleri tek tek onayla
- Her bölümü ayrı okudun; tempoyu kafanda kurabildin
- Toplam oynanış süresi GDD'deki iddiayla uyuşuyor
- Hiçbir bölüm envanterde olmayan bir varlık istemiyor

### Kapı 3C — metinleri onayla
- Tüm string'ler yazıldı; ton tutarlı
- Her metin bir anahtara bağlı; kodda düz metin kalmayacak

**Donan:** `03-strings.yaml`

---

## FAZ 4 — Varlık üretimi

Kod yazılmadan önce, her varlık tek tek senin onayından geçer. Bu faz mimarinin en pahalı ve en değerli parçası: varlıklar bittiğinde yapım fazı yaratıcı bir iş olmaktan çıkıp montaja dönüşür — ki otonom ajanların gerçekten iyi olduğu tek şey montajdır.

### Neler "varlık" sayılır

| Kategori | İçerik | Tipik adet |
|---|---|---|
| Karakter | Sprite setleri, animasyon çerçeveleri, portreler | 40–120 |
| Çevre | Tileset, arka plan katmanları, prop'lar | 30–80 |
| Efekt | Parçacık dokuları, vuruş/patlama kareleri | 15–40 |
| Arayüz | Buton durumları, çerçeveler, ikon seti, imleç | 40–90 |
| Tipografi | Font seçimi + **ticari kullanım lisansı** | 2–3 |
| Ses | Efektler, ortam sesleri, arayüz sesleri | 30–80 |
| Müzik | Parçalar, loop noktaları, geçişler | 4–10 |
| Metin | Faz 3C'de tamamlandı | — |
| Veri | Bölüm layout'ları, denge tabloları | 20–40 |
| Pazarlama | Steam capsule (5 boyut), ekran görüntüleri, trailer | 12–20 |

### 4A · Stil kılavuzu

400 varlığı tek tek onaylamanın tek sürdürülebilir yolu, stili *önce* onaylamaktır. Ajan 3–5 anahtar görsel üretir: bir karakter, bir çevre parçası, bir arayüz paneli. Burada revizyon sayısı serbest — her tur sonraki 400 varlıktan tasarruf ettirir.

Kilitlenen: palet (hex değerleriyle), çizgi kalınlığı, ışık yönü, siluet kuralları, kontrast seviyesi, gölge stili.

### 4B · Varlık manifestosu

Tek bir `assets/manifest.yaml`. Her varlık bir satır, ve o satır varlığın tüm hayatını yönetir:

```yaml
- id: chr_player_run
  tip: sprite_animasyon
  spec: 48x48, 8 kare, pivot alt-orta, PNG
  kaynak: ai-üretim        # ai-üretim | komisyon | satın-alma | cc0 | kendi
  lisans: —
  bagimli: [04-style.md]
  oncelik: 1
  durum: taslak            # SADECE SEN değiştirebilirsin
  revizyon: 2
  hash: —                  # Faz 5'te doldurulur
  onay_tarihi: —
```

Kapı 4B'de onayladığın şey dosyalar değil, **listenin kendisi**. Varlık sayısını kısacağın son yer burası.

### 4C · Doğrulama harness'i

Az miktarda kod — ama oyun değil. Harness bir varlığı yükleyip manifest'teki spec'e uyup uymadığını kontrol eder: boyut, format, çerçeve sayısı, pivot, palet dışı renk, isimlendirme, ses seviyesi. Faz 5'teki pipeline ile aynı kod tabanını paylaşır.

> **Onayı sürdürülebilir yapan ayrım: tekniği makine onaylar, estetiği sen onaylarsın.** Harness'tan geçmeyen varlık senin gözünün önüne hiç gelmez. Böylece 400 varlıkta senin verdiğin karar "bu güzel mi" sorusundan ibaret kalır.

### 4D · Parti parti üretim ve onay

Öncelik sırasına göre 20'şerlik partiler. Her parti için ajan bir *kontakt sayfası* üretir: tek HTML sayfada 20 varlık, yan yana, stil kılavuzundaki referansla birlikte. Sen her biri için tek tek karar verirsin, kararlar manifest'e yazılır.

```
spec → taslak → revizyon → onaylı (SADECE SEN) → kilitli
```

Revizyon isteğin serbest metin olarak manifest'e düşer ve bir sonraki turun girdisi olur. Aynı varlıkta üçüncü revizyondan sonra ajan durur — belki sorun varlıkta değil, spec'tedir.

### Onay yükünün gerçek maliyeti

| Varlık sayısı | Tek tek, 90 sn | 20'lik kontakt sayfasıyla | Haftaya yayılınca |
|---|---|---|---|
| 150 | 3,7 saat | ~2 saat | Haftada 30 dk |
| 300 | 7,5 saat | ~4 saat | Haftada 1 saat |
| 600 | 15 saat | ~8 saat | Haftada 2 saat |

Varlık sayısı bir tasarım tercihi değil, **senin takvimindeki bir bütçe kalemi**. GDD 600 varlık isterse bu senden 8 saat onay zamanı istiyor demektir — revizyon turlarıyla iki katı.

> **Steam AI beyanı.** Varlıkları AI ile üretiyorsan bu Steam'de beyan edilir. Valve'ın 16 Ocak 2026 güncellemesi ayrımı netleştirdi: **oyunla birlikte gelen ve oyuncunun tükettiği** AI üretimi görsel, ses ve metin beyana tabi — pazarlama materyalleri dahil. Arka planda verimlilik sağlayan geliştirme araçları (kod yazdırma dahil) beyan kapsamında değil. Manifest'teki `kaynak` alanı tam da bunun için var.

### Kapı 4A — stili kilitle
- 3–5 anahtar görseli beğendin; bunlar 400 varlığın referansı olacak
- Palet hex değerleriyle yazıldı, kural olarak ifade edildi
- Bu stilin üretilebilir olduğunu gördün — tek seferlik şans eseri değil

**Donan:** `04-style.md`

### Kapı 4B — varlık listesini kilitle
- Toplam sayı charter'daki varlık bütçesine sığıyor
- Onay yükü tablosundaki saati kabul ediyorsun
- Her satırın teknik spec'i dolu

**Donan:** manifest satır listesi — ajan yeni satır ekleyemez, sadece mevcut satırları doldurur.

### Kapı 4D — varlıkları tek tek onayla (tekrarlayan, parti başına)
- Her varlık için: onayla, revizyon iste, ya da iptal et
- Kararın manifest'e yazılır; `durum` alanına yazma yetkisi yalnızca sende
- Parti bitmeden sonraki parti başlamaz

**Yaptırım:** CI, manifest'te `onaylı` olmayan bir dosyaya referans veren build'i reddeder. Onay bir ricanın değil, bir derleme koşulunun adıdır.

---

## FAZ 5 — Motora hazırlama

Onaylı ham dosyalar → yazılımın tükettiği türevler. **Tamamen otomatik.**

Onayladığın PNG, motorun yediği şey değil. Aradaki dönüşüm — kırpma, pivot, atlas paketleme, çarpışma şekli, ses normalizasyonu, kaynak dosyası üretimi — ayrı bir iştir. Atlanırsa Faz 6'da ajanın önüne yüzlerce küçük el işi olarak çıkar, ve her biri bir sapma fırsatıdır.

Bu, mimarideki tek **tam otonom** fazdır. Sebebi basit: dönüşüm deterministik, çıktı makineyle doğrulanabilir. Onayı zaten Kapı 4D'de verdin.

### İki dizin, tek yön

```
assets/raw/ (onaylı, dokunulmaz) → pipeline scripti → game/assets/ (üretilmiş)
```

`game/assets/` bir build çıktısıdır: silinip sıfırdan yeniden üretilebilmeli, ve **orada hiç kimse elle düzeltme yapmaz** — ne sen, ne ajan. Bir türev yanlışsa script düzeltilir, dosya değil.

### 5A · Dönüşüm tablosu

| Ham girdi | İşlem | Yazılımın kullandığı çıktı |
|---|---|---|
| Sprite kareleri | Şeffaf kenar kırpma, pivot normalizasyonu, 2px extrude, atlas paketleme | Atlas dokusu + kare koordinat tablosu |
| Animasyon dizisi | FPS, loop bayrağı, olay kareleri ("vuruş 3. karede") | Animasyon kaynağı + olay tablosu |
| Tileset görseli | Izgaraya dilimleme, çarpışma şekilleri, autotile bit maskeleri | TileSet kaynağı |
| Arayüz paneli | Nine-slice kenar bölgeleri, buton durum atlası | Tema / StyleBox kaynağı |
| İkon seti | Boyut varyantları, nearest filtre, mipmap kapalı | İkon atlası |
| Ses efekti | Sessizlik kırpma, DC offset temizliği, hedef seviyeye normalizasyon | WAV — anlık yükleme |
| Müzik | LUFS normalizasyonu, örnek hassasiyetinde loop noktaları | OGG + loop metadata |
| Font | Türkçe karakter kümesi (ğ ı ş İ ö ü ç), hinting, boyut varyantları | Font kaynağı |
| Metin tablosu | Anahtar doğrulama, eksik çeviri kontrolü | Çeviri kaynağı + sabitler |
| Steam görselleri | 5 capsule boyutu, sıkıştırma, renk profili | Mağaza yükleme paketi |

Script **idempotent** olmalı: aynı girdiyle iki kez çalıştığında aynı çıktıyı üretmeli.

> **En sık atlanan üç ayar**
> - **Extrude:** atlas'ta komşu sprite'ların kenarından renk sızar; her kareye 1–2 piksel kendi rengini taşırmadan bu bug oyunda titreyen çizgiler olarak görünür ve sebebi geç anlaşılır.
> - **Filtre ve mipmap:** pixel art için nearest filtre, mipmap kapalı. Varsayılanla bırakılırsa sanat bulanık çıkar ve kimse sebebini varlıkta aramaz.
> - **Pivot:** karakterin ayak hizası. Kare kare değişirse yürüyüş titrer. Pivot ham dosyada değil manifest'te tanımlanır ve scriptle uygulanır.

### 5B · Varlık kaydı — kodun tek arayüzü

Bu fazın en değerli çıktısı bir görsel değil, üretilmiş bir kod dosyası:

```gdscript
# ÜRETİLMİŞ DOSYA — elle düzenlemeyin
class_name Assets
const CHR_PLAYER_RUN  := preload("res://assets/chr/player_run.tres")
const UI_BUTTON_THEME := preload("res://assets/ui/button.tres")
const SFX_JUMP        := preload("res://assets/sfx/jump.wav")

# 03-strings.yaml'dan üretilir
class_name Strings
const MENU_BASLA := "menu.basla"
```

Kodun hiçbir yerinde dosya yolu string'i yok. Ajan `Assets.CHR_PLAYER_RUN` yazar. Olmayan bir varlığa referans verirse **derleme hatası** alır — sessizce eksik bir doku değil, anında duran bir build. Faz 6'daki "ajan olmayan varlığı uydurdu" hatası bu tek dosyayla tamamen kapanır.

### 5C · Otomatik doğrulama

- Her türev headless olarak motora yükleniyor mu
- Atlas'ta komşu sprite sızması var mı — piksel testi
- **Çift yönlü tamlık:** her manifest satırının bir çıktısı, her çıktının bir manifest satırı var mı
- **Yetim varlık raporu:** üretildi ama koddan referans verilmiyor — ya kod eksik, ya varlık gereksiz
- Ses seviyeleri hedef aralıkta mı, kırpılma var mı
- Toplam paket boyutu ve doku belleği bütçe içinde mi

### 5D · Hash kilidi

Her ham dosyanın hash'i manifest'e yazılır. Ham dosya sonradan değişirse hash tutmaz: CI durur, varlık `revizyon` durumuna düşer ve yeniden onayına gelir.

Onayladığın bir varlık, arkandan sessizce değiştirilemez. Onay mekanizmasını gerçekten bağlayıcı yapan şey bu satır.

### Kapı 5 — hazırlama raporunu onayla

Burada varlık başına onay yok; o iş Kapı 4D'de bitti.

- Atlas sayfalarına göz attın: sızma yok, hizalama doğru
- Yetim varlık listesi boş, ya da her satırı açıklanabilir
- Paket boyutu ve doku belleği bütçe içinde
- Registry üretildi ve derleniyor
- Pipeline sıfırdan iki kez çalıştırıldı, iki çıktı birebir aynı

**Donan:** `game/assets/` + registry — Faz 6'da kod dosya yoluna değil, yalnızca bu arayüze bakar.

---

## FAZ 6 — Yapım

Tasarım donmuş, metinler yazılmış, varlıklar motora hazır. Bu fazın kolaylaşmasının sebebi kendisi değil, önündeki beş faz. Ajan artık ne sprite tasarlıyor, ne menü metni uyduruyor, ne bölüm layout'u icat ediyor. Yaptığı iş montaj.

GDD'den **15–25 dikey dilim** çıkar: her biri tanımlanabilir, test edilebilir, 1–3 saatlik. Her dilim ayrı branch, ayrı ajan turu, ayrı merge kararı. Paralellik burada 1'dir — tek yazıcı.

### Dilim başına sabit döngü

1. Dilim spec'ini, ilgili GDD tablosunu ve `registry`'deki varlık sabitlerini oku — başka hiçbir şeyi değil
2. Testi önce yaz. Kırmızı olduğunu gör
3. Kodu yaz. Yeni varlık üretme, yeni metin yazma, dosya yolu yazma — sadece `Assets.*` ve `Strings.*` sabitlerini kullan
4. `--headless` test koşusu. Çıkış kodunu oku
5. Kaldıysa düzelt ve 4'e dön

**Yeşil** → diff kapsam kontrolünden ve varlık onay kontrolünden geçer, merge edilir.
**3. denemede hâlâ kırmızı** → döngü durur, `runlog/`'a rapor yazılır, sana sorulur.

### Pazarlıksız beş kural

1. **Kod ajanı `tests/` dizinine yazamaz.** Testi geçirmek yerine testi gevşetme kaçamağı böyle kapanır
2. **Kod ajanı `assets/`, `game/assets/` ve `03-strings.yaml`'a yazamaz.** Eksik varlık fark ederse durur ve sorar
3. **Deneme sınırı 3.** Sayıyı orkestrasyon koduna göm, prompt'a yazma
4. **Kapsam koruması.** Dilim spec'inde adı geçmeyen dosyaya dokunulduysa merge otomatik reddedilir
5. **Her dilim ayrı worktree.** main'e sadece yeşil testle ve tek kapıdan girilir

### Ajan neyi test edebilir, neyi edemez

| Katman | Kim | Ne yakalar |
|---|---|---|
| Birim testi — hasar, envanter, kayıt/yükleme, durum makineleri | Ajan | Mantık hataları |
| Sahne testi — sahne yükleniyor mu, sinyaller bağlı mı | Ajan | Entegrasyon kopmaları |
| Varlık bütünlüğü — registry sabitleri üzerinden | Derleyici | Eksik/onaysız varlık, kod çalışmadan |
| Duman testi — headless N saniye çalıştır, log'da hata ara | Ajan | Çökmeler |
| Playtest botu — scripted input ile bölümü baştan sona oyna | Ajan | Bitirilemeyen bölüm |
| **His, denge, eğlence** | **Sadece sen** | Oyunun aslında iyi olup olmadığı |

Son satır bu mimarinin kabul ettiği sınır. Hiçbir otonom sistem "bu eğlenceli mi" sorusunu cevaplayamaz, ama *eğlenceli olmadığını fark etmeden aylarca kod üretebilir*.

### Kapı 6 — oynanabilir build (tekrarlayan, 5 dilimde bir)
- Build çalışıyor, sen 10 dakika oynadın, notların `runlog/playtest-N.md`'ye yazıldı
- Hızın charter'daki takvime uyuyor mu? Sapıyorsa dilim listesini kısalt, tempoyu artırma
- GDD ya da varlık değişikliği gerekiyorsa *şimdi* yap ve dondurulmuş dosyaları sen güncelle

Bu kapı olmadan sistem körleşir: yeşil testlerle dolu, kimsenin oynamak istemediği bir oyun üretir.

---

## FAZ 7 — Steam yayını

Burada otonom olamazsın — Valve'ın süreci zaten insan kapıları içeriyor, ve bu senin lehine. Takvimini kodun bitişine değil, **mağaza sayfasının hazır olmasına** göre kur.

| Ne zaman | Ne |
|---|---|
| Uygulama açılışı | Steam Direct ücreti: uygulama başına **100 USD**. İade edilmez, 1.000 USD brüt gelirden sonra ödemeye geri yansır |
| T − 6 hafta | Mağaza sayfası kurulumu. Capsule ve ekran görüntüleri Faz 4'te onaylandı, burada yerleştiriliyor. AI beyan formu manifest'ten dolduruluyor |
| T − 5 hafta | Mağaza sayfasını incelemeye gönder. İnceleme **3–5 iş günü**; düzeltme payı için canlıya çıkıştan en az 7 gün önce gönder |
| T − 4 hafta | "Coming soon" sayfası canlı. Yayından önce **en az 2 hafta** görünür kalmak zorunda — wishlist penceresi bu |
| T − 2 hafta | Build'i `steamcmd` / ContentBuilder ile yükle. Build ayrı incelemeden geçiyor |
| T · gün | **"Release App" düğmesine elle basılıyor.** Son kapı da insanda |

---

## Limit tablosu

Prompt'a yazılan sınır bir ricadır; koda gömülen sınır bir kuraldır. Aradaki fark sistemin kontrolden çıkıp çıkmadığıdır.

| Sınır | Değer |
|---|---|
| Ajan derinliği | 2 seviye · işçi ajan doğuramaz |
| Eşzamanlı işçi — Faz 1–2 | ≤ 8 |
| Eşzamanlı işçi — Faz 4 | ≤ 4 (parti içinde) |
| Eşzamanlı işçi — Faz 6 | 1 (tek yazıcı) |
| Varlık partisi boyutu | 20 |
| Varlık başına revizyon | 3, sonra durur |
| Dilim başına düzeltme denemesi | 3 |
| Dilim başına tur | 20 |
| Yazma yetkisi — Faz 1–3 | sadece kendi çıktı dosyası |
| Yazma yetkisi — Faz 4 | `assets/raw/` + manifest'in `durum` dışı alanları |
| Yazma yetkisi — Faz 5 | `assets/pipeline/` + `game/assets/` (üretim) |
| Yazma yetkisi — Faz 6 | sadece dilim spec'indeki kod dosyaları |
| `game/assets/` elle düzenleme | yasak · her koşuda yeniden üretilir |
| `durum` alanına yazma | yalnızca sen |
| Dosya silme | hiçbir ajanda yok |

### Otomatik durma koşulları

- Test 3 kez üst üste kaldı
- Aynı varlık 3 kez revizyon aldı
- Kapsam dışı dosyaya dokunuldu
- Onaysız bir varlığa referans verildi
- Ham dosyanın hash'i manifest'tekiyle tutmuyor
- Yetim varlık ya da eksik türev bulundu
- GDD, string tablosu ya da manifest değişikliği gerekiyor
- Lisansı belirsiz bir bağımlılık ya da varlık eklenmek isteniyor
- Bütçe veya tur limiti aşıldı

Her duruş `runlog/`'a tek sayfalık rapor yazar: ne denendi, ne oldu, senden ne isteniyor. **Duruş bir başarısızlık değil, sistemin doğru çalıştığının kanıtı.**

---

## Nasıl çalıştırırsın

Fazları bir LLM'e sıraya koydurma. Her faz ayrı bir oturum — bir slash komut ya da deterministik bir workflow scripti. Faz N'in girdisi Faz N−1'in dosyasıdır; sen kapıda dosyayı okur, düzeltir, onaylarsın.

```
/faz1a → oku → /faz1b → oku → /faz2 → oku → /faz3a → /faz3b → /faz3c
       → /faz4a → /faz4b → /parti 01 … /parti N
       → /hazirla → /dilim 01 … /dilim N → /yayin
```

> **Kaçınılması gereken tek tuzak.** Kod öncesi varlık üretmenin gerçek riski şu: motora hiç girmemiş varlıklar teknik olarak yanlış çıkabilir ve 400 tanesi birden yeniden kesilir. Üç savunma var ve üçü aynı zincirin halkası: Faz 2C'deki teknik spec, Faz 4C'deki harness, Faz 5'teki pipeline. **Tek bir varlığı bu zincirin ucundan ucuna geçirmeden toplu üretime başlama** — bir sprite üret, onayla, hazırla, motorda çalıştığını gör.

Ve ilk turda tam hattı gerçek bir oyunla koşturma. Çok küçük bir şeyle — 20 varlık, 3 bölüm — hattı baştan sona bir kere çalıştır. Hattaki hatalar orada ucuza çıkar. **Stüdyonun asıl ürünü ilk oyun değil, ikinci oyunu üç kat hızlı çıkaran hattın kendisi.**

---

## Kaynaklar

- [Steam Direct Fee — Steamworks](https://partner.steamgames.com/doc/gettingstarted/appfee)
- [Releasing Your Product — Steamworks](https://partner.steamgames.com/doc/store/releasing)
- [Uploading to Steam — Steamworks](https://partner.steamgames.com/doc/sdk/uploading)
- [Steam AI beyan formu güncellemesi, 16 Ocak 2026 — PC Gamer](https://www.pcgamer.com/software/ai/steam-updates-ai-disclosure-form-to-specify-that-its-focused-on-ai-generated-content-that-is-consumed-by-players-not-efficiency-tools-used-behind-the-scenes/)
- [gdUnit4 — Godot 4 test framework](https://github.com/godot-gdunit-labs/gdUnit4)
- [GUT — Godot Unit Testing](https://godotengine.org/asset-library/asset/1709)
- [Godot testlerini CI'da headless çalıştırma](https://saltares.com/run-automated-tests-for-your-godot-game-on-ci/)
- [GodotSteam — Exporting and Shipping](https://godotsteam.com/tutorials/exporting_shipping/)
