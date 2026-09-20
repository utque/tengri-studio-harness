# Playtest QA Checklist (tüm oyunlar)

Her oyun, her ekran, her build/run sonrası. Screenshot olmadan madde geçilmez.
Sonsuz döngü: **çalıştır → SS → Read (tasarımcı gözü) → checklist A–K → düzelt / fal → tekrar**.
**“Çalışıyor” yetmez. Her nokta gerçekten güzel olmadan durma.**

## Döngü protokolü

Her tur **kapsamı önceden yazılır**. Kapsamsız tur, "bakayım nasıl olmuş" turudur;
reddedilen deneme de tam tur harcar.

### Turdan önce

1. `runlog/<tur>/kapsam.md` yaz: **bu turda neyin değişeceği** ve **hangi
   ekranların etkilenmesinin beklendiği** (dosya adlarıyla). Bir cümle yeter.
2. Değişikliği yap. Kapsam dışına çıkacaksan turu bitir, yeni kapsam yaz.

### Makine kontrolleri — gözden ÖNCE

```bash
bash tests/run.sh                 # birim testler (tests/ dizinine YAZILMAZ)
bash tools/qa_kontrol.sh          # ölçülebilir UI kuralları (B/C/D/K)
```

`qa_kontrol` önce **kendi öz-testini** koşar: bozuk denetçi her şeye yeşil der.
Öz-test kırmızıysa diğer sonuçlar geçersizdir. `godot -s` parse hatasında çıkış
**0** döndürdüğü için doğrudan `godot` çağırma — sarmalayıcı bitiş satırını arar.

`tools/qa_kontrol_ortak.gd` tohumlanır (jenerik UI kuralları + öz-test);
`tools/qa_kontrol.gd` her oyunun KENDİ dosyasıdır — ortak kütüphaneyi çağırır ve
oyuna özel değişmezleri ekler (Harita Fatihi: HP rozeti hex içinde, arazi karosu
maske dışı opak piksel. Wispward: düşman yol üstünde, can çubuğu siluetle
orantılı ve onu örtmüyor, kule karo enini aşmıyor, düşman yokken hayalet mermi).

**Kontrast ÇİZİLEN kareden ölçülür.** Sürücü her ekranda
`await RenderingServer.frame_post_draw` sonrası `Ortak.kare_al(self)` ile kareyi
alıp `Ortak.hepsi(kok, vp, kare)` çağırır. Kare geçilmezse kontrol sessizce
yeşil geçmez, `kontrast_olculemedi` der.

> Bildirilen renkten ölçmek İKİ KEZ yanlış sonuç verdi: Wispward'ın sonuç
> panosunda `StyleBoxFlat.bg_color` `#6B5216`, ekrana basılan piksel `#110E13`.
> O hatalı ölçüm var olmayan bir soruna düzeltme yazdırdı (kör puan geri aldı).
> Gözün gördüğü tek şey karedir.

Gözle bakmadan önce makine yeşil olmalı. Göz, ölçülemeyeni arar; ölçülebileni
ölçüm arar.

### Çekim — sabit kare hızı zorunlu

```bash
godot --fixed-fps 60 --path game -s ../tools/loop_shot.gd -- "$PWD/runlog/<tur>"
```

`--fixed-fps` olmadan tween fazları koşudan koşuya kayar; aynı kod iki farklı
kare üretir ve piksel diff her turu "değişmiş" gösterir. Sabit kare hızıyla
ölçüldü: 31 karenin 31'i birebir aynı.
Çıktının son satırı `loop_shot ok <dizin>` değilse çekim tamamlanmamıştır.

### Diff — neyin değiştiğini göz değil ölçüm söyler

```bash
python3 tools/gorsel_diff.py runlog/<önceki> runlog/<tur> --beklenen 05_baslangic.png
```

`--beklenen` kapsamda yazdığın dosyaları alır. Kapsam dışı bir kare değiştiyse
çıkış 1 — bu **sessiz regresyondur**, turun asıl bulgusu odur.
Kutulu görüntü için `--ciz runlog/diff/`.

### Puanlama — kör

```bash
python3 tools/puan_kiyas.py olcut                      # çıpaları oku, sonra puanla
python3 tools/puan_kiyas.py hazirla <eski.png> <yeni.png> --etiket <ad> [--kirp x,y,w,h]
#   -> yalnız _A.png / _B.png / _kor.png'e bak; hangisi yeni saklı
python3 tools/puan_kiyas.py ac --etiket <ad> --a 7,8,8,7,8,8 --b 8,8,8,7,8,8 --not "..."
```

Kural: yeni tasarım **yalnızca toplam puanı yükseldiyse** kabul. Düşerse geri al
ve gerekçeyi **koda yorum olarak** düş (bir daha aynı denemeyi yapma).
`ac` kararı `runlog/loop-puan.md`'ye kendisi yazar.

En güçlü biçim: `hazirla`yı çalıştıran ajan puanlamayı kendi yapmaz; yalnız
_A/_B gören taze bir ajan puanlar. Tek ajan koşusunda bile A/B karışımı
"yeni olan bu" çapasını kırar — ama tek ajan koşuluyorsa bunu kayda yaz.

### SS zorunlu set

Her tur şu durumlar çekilir (sürücü: `tools/loop_shot.gd`):
splash · ana menü · shop (açık) · oyun başlangıç HUD · birim seçimi + menzil ·
inşa/üretim geri bildirimi · zafer · yenilgi · fraksiyon ayrımı aynı karede ·
dar viewport · kamera sınırları.

**Her** zorunlu SS ajan tarafından `Read` ile açılıp UI tasarımcı gözüyle
incelenir (fonksiyonel yeşil ≠ görsel yeşil). Bir maddeyi atlamak = kırmızı.

### Kırmızı varsa

Düzelt; testi gevşetme; try/catch ile gizleme; "placeholder yeter" deme.
Eksik / çirkin / yanlış boyut grafik → **fal ile üret / yeniden üret**
(aşağı K + fal protokolü). Eşiği kırmızıyı yeşile çekmek için değiştirmek
testi gevşetmektir — eşik ancak ölçtüğü şey yanlışsa ve gerekçesi yazılarak
değişir.

## Erken çıkış yasak

- “Çoğu yeşil” / “bilerek bırakıldı” / “yeterince iyi” / “sonra polish” ile `done: true` **yazılmaz**
- Bilinen kırmızı varsa `done` yazma; düzelt veya (yalnızca **teknik** tıkanmada) `runlog/*-durus.md`
- Yalnızca headless test yeşili yetmez — SS + **K. UI tasarımcı** maddeleri ayrı geçmeli
- Aynı **teknik** madde 5 düzeltmede kırmızı kalırsa `runlog/*-durus.md` yaz, dur
- **UI / güzellik / orantı / grafik** maddelerinde 3–5 denemede “dur” yok: fal, boyut, layout
  ile devam et; `done` yazma
- Placeholder, ColorRect, emoji, boş panelli texture, bulanık/yanlış ölçek sprite = **kırmızı**

---

## A. Icon-first / metin

- [ ] HUD, menü, envanter, buton, durum, ödül, uyarı: önce ikon/sembol/renk
- [ ] Görünen cümle / etiket / buton yazısı yok (yasal, ayar, hikâye, **marka/splash başlık** hariç)
- [ ] Kalan metin `03-strings.yaml` / `Strings.*` kaynaklı; kodda uydurma yok
- [ ] Tooltip’e taşınan anlam ekranda tekrar yazılmamış
- [ ] Arka plan / texture içinde **gömülü boş buton kutusu / hayalet UI** yok

## B. Orantı / yoğunluk (sık kaçan)

- [ ] Panel/düğme boyutu **içerik yoğunluğuna** uyuyor (metin→ikon sonrası eski `min_size` şişmiş mi?)
- [ ] Boş alan oranı: kutu içeriğin 2×’inden geniş/yüksek değil
- [ ] Haritayı / oyunu gereksiz örten şişkin panel yok
- [ ] Dokunma alanı yeterli ama abartılı değil (mobil/PC’ye göre makul)
- [ ] Menü ikonu butonun ≥ %40’ını dolduruyor (ufak nokta ikon = kırmızı)
      → gözle değil `tools/qa_kontrol.sh` ölçer (`ikon_doluluk`)
- [ ] Sonuç / shop modal ekranın ortasında; haritanın bir hex’i kadar küçük değil
      → `modal_en` (%35–55) ve `modal_bosluk` (kutu ≤ 2× içerik) ölçer
- [ ] SS’de ölç: ikon/birim/bina ekran yüksekliğine göre cılız veya devasa değil (bar / hex ölçeği)

## C. Layout / çakışma

- [ ] Üst şerit / yan panel / alt banner ekran içinde
- [ ] Kontroller birbirinin üstüne binmiyor
- [ ] Seçim / yükselt / onay kutusu hedefe göre konumlanmış (taşma kırpılmış)
- [ ] Küçük viewport’ta taşma / kesilme yok
- [ ] Harita birimleri / binalar HUD altında **kesilmiyor** (üst hex HP okunur)
- [ ] Aynı hex’te bina + birim: bina ayak/pivot hizalı; “kaymış kale” yok

## D. Okunabilirlik / hiyerarşi

- [ ] Birincil eylem ikincilden görsel olarak ayrılıyor
- [ ] Pasif / yetersiz altın / kilitli durum renk veya modulate ile belli
- [ ] Sayılar okunaklı (punto, kontrast); ikonlar aynı anlamı tutarlı kullanıyor
- [ ] Geçici mesaj kısa; kalıcı HUD’u boğmuyor
- [ ] Oyuncu / düşman fraksiyonu **renk veya sembolle** ayırt ediliyor

## E. Etkileşim / geri bildirim

- [ ] Tıklanan her şey görsel veya sesli tepki veriyor
- [ ] Seçili birim / karo belirgin (halka, çerçeve, renk)
- [ ] Hata (yetersiz kaynak, yasak yer) ikon veya kısa geri bildirimle anlaşılıyor
- [ ] Pause / tur / inşa / üretim kontrolleri keşfedilebilir (ikon + tooltip)
- [ ] Hareket menzili / saldırı hedefi seçimde görünür

## F. Oynanış yüzeyi

- [ ] Yol / hedef / spawn / sahiplik işaretleri görünür
- [ ] Can / kaynak / tur anlık okunuyor
- [ ] Yerleştirme önizlemesi (menzil, yasak) doğru
- [ ] Zafer / yenilgi / sonraki adım icon-first ve tutarlı (karart + panel)
- [ ] İnşa veya üretim SS’de **kanıtlı** (kaynak düştü / yeni birim / yeni bina)

## G. Teknik kanıt

- [ ] İlgili headless testler yeşil (`bash tests/run.sh` çıkış 0)
- [ ] Makine UI kontrolleri yeşil (`bash tools/qa_kontrol.sh` çıkış 0, öz-test dahil)
- [ ] Çekim `--fixed-fps 60` ile alındı ve `loop_shot ok` satırı var
- [ ] `gorsel_diff.py` kapsam dışı kare değişmediğini gösterdi
- [ ] SS dosyaları `runlog/` altında (mutlak yol); ajan **her** zorunlu SS’yi Read ile okudu
- [ ] Bilerek bırakılan istisna varsa `runlog/*-durus.md` + checklist notu; aksi halde yok sayılmaz
- [ ] `playability` / kabuk testleri (varsa) yeşil

## H. Kabuk (splash / menü / shop) — her oyun

- [ ] `main_scene` splash veya ana menü; **doğrudan maç sahnesi değil**
- [ ] Splash SS: marka görünür; hayalet boş menü kutusu yok; **marka hero** (ufak köşe logosu yetmez)
- [ ] Ana menü SS: Oyna + Shop + Çıkış (icon-first) ayırt edilir; kompozisyon tek bütün
- [ ] Shop SS: panel açılır; arka menü butonları üstüne binmez / gizlenir
- [ ] Oyna → oyun sahnesi; dönüş yolu kırık değil (mümkünse)

## I. Oynanabilirlik min bar (ilk senaryo / demo)

- [ ] SS’de en az **1 düşman** birim veya rakip bina
- [ ] SS’de en az **2 oyuncu** birim (veya üretimle ikinci birim kanıtı)
- [ ] Kaynak sayıları **0 değil** (inşa/üretim 1–2 turda mümkün görünür)
- [ ] En az bir eylem butonu (inşa/üret/tur) aktif veya disabled hali anlaşılır
- [ ] Yalnızca “adam yürüyor” senaryosu = **kırmızı** (playability-min-bar)

## J. Denge / fraksiyon ayrımı (playtest)

- [ ] İlk senaryoda başkentler arası mesafe **≥ 5** (1 turda yürüyüp fetih = kırmızı)
- [ ] Tur 1’de (oyuncu henüz tur bitirmeden) zafer **imkânsız** — headless + başlangıç SS
- [ ] Zafer için minimum tur eşiği (demo fetih: **tur ≥ 3**) veya eşdeğer sert mesafe
- [ ] Üretim tur 1’de mümkün: kaynak yeter + spawn boş; yeni birim **kale üstüne yapışık değil** (komşu hex tercih)
- [ ] Üretim SS kanıtı: birim sayısı arttı **ve** yeni birim görünür (bayrak/kale altında kayıp değil)
- [ ] Oyuncu / düşman **birimleri** SS’de renk veya sembolle net ayırt (aynı gri silüet = kırmızı)
- [ ] Oyuncu / düşman **başkent / bayrak** SS’de net ayırt (aynı sarı bayrak + aynı taş = kırmızı)
- [ ] Headless `denge` / playability testleri bu maddeleri ölçer

## Bileşen spec'i (her oyun kendi tablosunu `04-style.md`'ye doldurur)

"Buton biraz küçük" tartışması her turda yeniden başlıyorsa, bileşenin ölçüsü
hiçbir yerde yazılı değil demektir. Her oyun aşağıdaki tabloyu **ölçülmüş
değerlerle** doldurur; sonraki turlar tabloya bakar, göze değil.

| Bileşen | Kutu (px) | İçerik (px) | Doluluk | Punto / renk | Kural |
|---|---|---|---|---|---|
| HUD şeridi | | | ekran yüksekliğinin %? | | ≤ %40 haritayı yutar |
| Birincil eylem butonu | | ikon | ≥ %40 | | icon-first |
| İkincil eylem butonu | | ikon | ≥ %40 | | |
| Kaynak göstergesi | | ikon + sayı | | | kontrast ≥ 3:1 |
| Sonuç modalı | | ikon + başlık + aksiyon | kutu ≤ 2× içerik | | ekranın %35–55'i |
| Harita üstü rozet | | | | | hex sınırı + pay |

Doldurulmuş örnek: `harita-fatihi/04-style.md` § 10.
Tabloyu `tools/qa_kontrol.sh` çıktısındaki ölçümlerle doldur — elle tahmin etme.

---

## K. UI tasarımcı / güzellik barı (zorunlu — erken bitirme engeli)

SS’ye bakarken ajan **ürün tasarımcısı** gibi sorar: “Bu kareyi ajansa / Steam sayfasına koyar mıydım?”
Hayır → kırmızı. Fonksiyonel ama çirkin / eksik / orantısız = **done yok**.

### Bakış açısı (her SS)

- [ ] İlk bakışta odak net (ne yapacağım 1 sn’de anlaşılıyor)
- [ ] Görsel hiyerarşi: birincil eylem en güçlü; ikinciller bastırmıyor
- [ ] Ritim / boşluk tutarlı; rastgele boşluk veya sıkışık yığın yok
- [ ] Renk / stil `04-style.md` + onaylı referanslarla uyumlu (rastgele pastel / AI çamuru yok)
- [ ] Kontrast yeterli; ikonlar zeminde kaybolmuyor
- [ ] Hizalama: aynı satırdaki ikon/buton taban çizgisi ve boyutu eş
- [ ] Kenar boşlukları tutarlı (ekran kenarına yapışık / uçuşan öğe yok)
- [ ] Motionsuz “ölü” menü yok: en az hafif hover/pulse veya giriş hissi (mümkünse)
- [ ] Texture içinde gömülü UI şeridi / hayalet buton / kırpılmamış atlas kenarı yok
- [ ] “Placeholder geçici” görünen hiçbir şey yeşil sayılmaz

### Boyut / ölçek denetimi (SS + kod)

- [ ] İkon `custom_minimum_size` / texture ölçeği içerikle uyumlu (şişmiş kutu veya nokta ikon yok)
- [ ] Birim / bina / UI ikonu birbirine göre tutarlı ölçek (dev kafalı birim + cılız kale = kırmızı)
- [ ] Atlas pivot / offset: bina hex merkezinde; hardcoded kayma yok
- [ ] Modal / panel: ekranın ~%35–55 genişliği bandında (çok küçük damla / tüm ekranı örten şişkin yok)
- [ ] HUD şeridi haritanın ≥ %40’ını yutmuyor

### Eksik / çirkin grafik → fal protokolü

SS veya sahnede eksik, bozuk, yanlış stil, yanlış boyut veya placeholder grafik varsa:

1. İlgili varlık id’sini / dosyayı tespit et (`Assets.*`, manifest, `assets/raw/`)
2. Oyundaki fal aracını çalıştır:
   - Wispward: `python3 tools/fal_uret.py --id …` (gerekirse boyut/stil)
   - Harita Fatihi: `python3 tools/fal_sanat.py --id … --kurulum`
3. Üretilen görseli **Read ile göster**; `04-style.md`’ye uymuyorsa prompt/boyut düzeltip **yeniden üret**
4. Pipeline / kurulum ile `game/assets/` güncelle; sahneyi tekrar run + SS
5. Onay kapısı engelliyorsa `runlog/*-durus.md` ile sor — ama diğer kırmızıları bırakıp `done` yazma
6. Fal’sız “geçici ColorRect / emoji / boş panel” ile maddeyi yeşile çekmek **yasak**

- [ ] Zorunlu set ekranlarında eksik ikon / sprite / panel grafiği yok (fal ile tamamlandı)
- [ ] Yeni üretilen grafik doğru boyutta ve stilde; SS’de kanıtlandı
- [ ] Manifest / registry sabitleri yeni varlığa bakıyor; kırık yol yok

---

## Çıkış koşulu

Üçü birden sağlanmadan `qa-pending.json` içine `{"done": true}` yazılmaz:

1. **Makine kontrolleri tümü yeşil** — `tests/run.sh` çıkış 0 **ve**
   `tools/qa_kontrol.sh` çıkış 0 (öz-test dahil, 0 kırmızı).
2. **Üst üste 2 tur ciddi bulgu yok** — son iki turun hiçbirinde A–K'da kırmızı
   ve hiçbirinde reddedilen/geri alınan tasarım yok. Tek tur sessizlik yetmez:
   bir turluk sessizlik çoğu zaman o turda bakılmamış demektir.
3. **Piksel diff yalnız amaçlanan bölgeleri gösteriyor** —
   `gorsel_diff.py <önceki> <son> --beklenen <kapsamdaki dosyalar>` çıkış 0.
   Kapsam dışı tek kare bile değiştiyse çıkış koşulu sağlanmamıştır.

Ek olarak K güzellik barı ("ajansa / Steam sayfasına koyar mıydım?") geçmeli.
Tek kırmızı veya "biraz çirkin ama idare eder" = döngü devam; `done` yazma.
