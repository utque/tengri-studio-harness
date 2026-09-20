---
description: Faz 4A — görsel stilin kilitlenmesi (04-style.md)
---
GÖREV: Görsel stilin kilitlenmesi.
OKU: 03-gdd.md (7. açı: sanat yönü), 02-tech.md (2C varlık spec'i)
YAZ: 04-style.md ve assets/raw/_style/ altına 3-5 anahtar görsel

ÖNCE ÜRET, SONRA KİLİTLE. Üret: bir karakter (idle pozunda), bir çevre parçası,
bir arayüz paneli. Hepsi 02-tech.md'deki teknik spec'e uygun boyut ve formatta olmalı.
Stili bu üç görseli ÜRETMEDEN tarif etme: pilotta AI modelinin eğitim verisi
perspektifi dayattı (4 tur, 8 görsel, üretilebilir varlık sıfır) ve prompt bunu
yenemedi. 04-style.md yalnızca gerçekten ürettiğin çıktıyı tarif eder; üretemediğin
bir stili kural olarak yazma.

04-style.md şunları KURAL olarak içerir, tarif olarak değil:
- Palet: hex değerleriyle, her rengin nerede kullanıldığı
- Çizgi kalınlığı (piksel), outline kuralı
- Işık yönü ve gölge stili
- Siluet kuralları (karakter ne kadar geniş, okunabilirlik testi)
- Kontrast seviyesi ve arka plan-ön plan ayrımı kuralı
- Uygulanmayacaklar listesi (bu stilde ne YAPILMAZ)
- Palet muafiyeti: hangi varlık sınıfı palet denetiminden muaf (ör. 3B'den render
  alınan efektler). Muafiyet yazılmazsa muafiyet yoktur.

Bu dosya sonraki 400 varlığın referansı olacak. Bir sanatçıya verilse aynı
sonucu üretebileceği netlikte yaz.

BİTİR: Dosyaları yaz ve dur. Kullanıcı beğenmezse revizyon turu açılır -
revizyon sayısı bu adımda sınırsız.
