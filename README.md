# tengri-studio

Faz kapılı stüdyo koşucusu. Tek kopya; oyun kökleri `--kok` ile verilir.

**İnsan:** yalnız oyun tipi + asset (+ oynanır demo playtest).  
**Yazılım:** 10 seviyeli öz-yargı iterasyonu; demo’ya (`playtest-1`) kadar otonom.

```bash
python3 studio.py --kok ../wispward
python3 studio.py --kok ../harita-fatihi
python3 studio.py --kok ../wispward --agac
STUDIO_YARGI_MOD=deterministik python3 studio.py --kok ../wispward --test
npm test
```

## İnsan kapıları

| Tür | Örnek | Ne yaparsın |
|---|---|---|
| Oyun tipi | charter, `--sec kisa_liste`, `--sec secilen` | Konsept seç |
| Asset | stil, parti kontakt, `--onayla taslak` | Görsel/ses onayla |
| Demo | `playtest-1` | Build’i oyna, not yaz |

## Yazılım öz-yargı

Her yazılım adımından sonra studio kendini yargılar (`runlog/<adim>-yargi-NN.md`):

- yapılanlar / yapılması gerekenler  
- neden doğru / neden yanlış  
- karar: `onay` | `revizyon` (en fazla `STUDIO_YARGI=10` tur)

Yazılım soruları (test, layout, kod) kullanıcıya gitmez; revizyon notuna düşer.
