# Playtest QA Checklist (tüm oyunlar)

Her oyun, her ekran, her build/run sonrası. Screenshot olmadan madde geçilmez.
Sonsuz döngü: **çalıştır → SS → checklist → düzelt → tekrar**. Hiç kırmızı kalmayınca çık.

## Döngü protokolü

1. Oyunu / sahneyi **build & run** et (pencereli; SS için headless yetmez).
2. Kritik durumlar için SS al — **zorunlu set**:
   - splash
   - ana menü
   - shop / ek menü (açık)
   - oyun başlangıç HUD
   - birim/seçim + hareket/menzil
   - inşa veya üretim geri bildirimi
   - zafer **ve** yenilgi paneli
   - fraksiyon ayrımı (birim + bayrak/başkent renkleri aynı karede)
3. Aşağıdaki **her bölümün her maddesini** SS üzerinden işaretle. Bir maddeyi atlamak = kırmızı.
4. Kırmızı varsa düzelt; testi gevşetme; try/catch ile gizleme; “placeholder yeter” deme.
5. Temizlenene kadar tekrarla. Temizse `done` yaz ve dur.

## Erken çıkış yasak

- “Çoğu yeşil” / “bilerek bırakıldı” ile `done: true` **yazılmaz**
- Bilinen kırmızı varsa `done` yazma; düzelt veya `runlog/*-durus.md`
- Yalnızca headless test yeşili yetmez — SS maddeleri ayrı geçmeli
- Aynı madde 3 düzeltmede kırmızı kalırsa `runlog/*-durus.md` yaz, dur

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
- [ ] Sonuç / shop modal ekranın ortasında; haritanın bir hex’i kadar küçük değil

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
- [ ] SS dosyaları `runlog/` altında (mutlak yol); ajan **her** zorunlu SS’yi Read ile okudu
- [ ] Bilerek bırakılan istisna varsa `runlog/*-durus.md` + checklist notu; aksi halde yok sayılmaz
- [ ] `playability` / kabuk testleri (varsa) yeşil

## H. Kabuk (splash / menü / shop) — her oyun

- [ ] `main_scene` splash veya ana menü; **doğrudan maç sahnesi değil**
- [ ] Splash SS: marka görünür; hayalet boş menü kutusu yok
- [ ] Ana menü SS: Oyna + Shop + Çıkış (icon-first) ayırt edilir
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

---

## Çıkış koşulu

A–J **tümü** yeşil **ve** son SS turunda yeni sorun yok → `qa-pending.json` içine `{"done": true}`.
Tek kırmızı = döngü devam; `done` yazma.
