# Playtest QA Checklist (tüm oyunlar)

Her oyun, her ekran, her build/run sonrası. Screenshot olmadan madde geçilmez.
Sonsuz döngü: **çalıştır → SS → checklist → düzelt → tekrar**. Hiç kırmızı kalmayınca çık.

## Döngü protokolü

1. Oyunu / sahneyi **build & run** et (pencereli; SS için headless yetmez).
2. Kritik durumlar için SS al (menü, oyun HUD, seçim/panel, onay, zafer/yenilgi, ayar).
3. Aşağıdaki her maddeyi SS üzerinden işaretle.
4. Kırmızı varsa düzelt; testi gevşetme; try/catch ile gizleme.
5. Temizlenene kadar tekrarla. Temizse `done` yaz ve dur.

## A. Icon-first / metin

- [ ] HUD, menü, envanter, buton, durum, ödül, uyarı: önce ikon/sembol/renk
- [ ] Görünen cümle / etiket / buton yazısı yok (yasal, ayar, hikâye hariç)
- [ ] Kalan metin `03-strings.yaml` / `Strings.*` kaynaklı; kodda uydurma yok
- [ ] Tooltip’e taşınan anlam ekranda tekrar yazılmamış

## B. Orantı / yoğunluk (sık kaçan)

- [ ] Panel/düğme boyutu **içerik yoğunluğuna** uyuyor (metin→ikon sonrası eski `min_size` şişmiş mi?)
- [ ] Boş alan oranı: kutu içeriğin 2×’inden geniş/yüksek değil
- [ ] Haritayı / oyunu gereksiz örten şişkin panel yok
- [ ] Dokunma alanı yeterli ama abartılı değil (mobil/PC’ye göre makul)

## C. Layout / çakışma

- [ ] Üst şerit / yan panel / alt banner ekran içinde
- [ ] Kontroller birbirinin üstüne binmiyor
- [ ] Seçim / yükselt / onay kutusu hedefe göre konumlanmış (taşma kırpılmış)
- [ ] Küçük viewport’ta taşma / kesilme yok

## D. Okunabilirlik / hiyerarşi

- [ ] Birincil eylem ikincilden görsel olarak ayrılıyor
- [ ] Pasif / yetersiz altın / kilitli durum renk veya modulate ile belli
- [ ] Sayılar okunaklı (punto, kontrast); ikonlar aynı anlamı tutarlı kullanıyor
- [ ] Geçici mesaj kısa; kalıcı HUD’u boğmuyor

## E. Etkileşim / geri bildirim

- [ ] Tıklanan her şey görsel veya sesli tepki veriyor
- [ ] Seçili kart / kule / slot belirgin
- [ ] Hata (yetersiz kaynak, yasak yer) ikon veya kısa geri bildirimle anlaşılıyor
- [ ] Pause / hız / dalga gibi kontroller keşfedilebilir (ikon + tooltip)

## F. Oynanış yüzeyi

- [ ] Yol / hedef / spawn işaretleri görünür
- [ ] Can / kaynak / ilerleme anlık okunuyor
- [ ] Yerleştirme önizlemesi (menzil, yasak) doğru
- [ ] Zafer / yenilgi / sonraki adım ikon-first ve tutarlı

## G. Teknik kanıt

- [ ] İlgili headless testler yeşil
- [ ] SS dosyaları `runlog/` altında (mutlak yol); ajan SS’leri okuyup gösterdi
- [ ] Bilerek bırakılan metin/istisna checklist notunda yazılı

## Çıkış koşulu

Tüm maddeler yeşil **ve** son SS turunda yeni sorun yok → döngüden çık.
Aynı madde 3 düzeltmede kırmızı kalırsa `runlog/*-durus.md` yaz, dur.
