---
description: Faz 7 — Steam yayın paketi (mağaza metni, capsule listesi, takvim)
---
GÖREV: Steam mağaza sayfası için yayın paketini hazırla.
OKU: 00-charter.md, 03-gdd.md, 03-strings.yaml, assets/manifest.yaml (mkt_* satırları)
YAZ: 07-yayin.md (sadece bu dosya)

1 MAĞAZA METNİ — iki dilde, ayrı başlıklar altında: "## Türkçe" ve "## English".
  Kısa açıklama (≤300 karakter), uzun açıklama, 5 madde öne çıkan özellik.
  Ton 03-gdd.md'deki tema ile uyuşsun. Oyunda olmayan özellik vaat etme;
  kapsam dışı listesindeki hiçbir şey metinde geçmesin.

2 CAPSULE VE GÖRSEL LİSTESİ — manifest'teki her mkt_* varlığı için bir satır:
  id, Steam'deki adı (Header/Small/Main/Vertical/Library), boyut, durum.
  Onaylı olmayan varsa yaz ve DUR.

3 TAKVİM — charter'daki yayın tarihinden geriye:
  T−6 hafta mağaza sayfası kurulumu, T−5 incelemeye gönderim (3-5 iş günü),
  T−4 "coming soon" canlı (en az 2 hafta görünür), T−2 build yükleme, T gün.
  Her satır için gerçek tarih yaz. Charter'da yayın tarihi yoksa DUR ve sor.

4 AI BEYANI — yazma; runlog/ai-beyani.md'yi studio.py manifest'ten üretir.
  Sadece "AI beyanı: runlog/ai-beyani.md" diye referans ver.

KURAL: Steam ücreti, inceleme süresi gibi her sayıya kaynak URL'i koy.
BİTİR: Dosyayı yaz ve dur. Steam'e tıklamak senin işin değil, kullanıcının.
