# tengri-studio

Faz kapılı stüdyo koşucusu. Tek kopya; oyun kökleri `--kok` ile verilir.

**İnsan:** yalnız oyun tipi + asset (+ oynanır demo playtest).  
**Yazılım:** 10 seviyeli öz-yargı; demo’ya (`playtest-1`) kadar otonom.  
**AI:** `claude` (Claude Code CLI) veya `cursor` (Cursor Agent CLI: `agent` / `cursor-agent`).

```bash
# Claude (varsayılan)
python3 studio.py --kok ../wispward

# Cursor CLI
STUDIO_AI=cursor python3 studio.py --kok ../wispward
STUDIO_AI=cursor STUDIO_MODEL=sonnet-4 python3 studio.py --kok ../wispward

python3 studio.py --kok ../wispward --agac
STUDIO_YARGI_MOD=deterministik python3 studio.py --kok ../wispward --test
npm test
```

## AI motoru

| `STUDIO_AI` | Binary | Not |
|---|---|---|
| `claude` | `claude` | `--json-schema` ile rapor zorlanır |
| `cursor` | `agent` veya `cursor-agent` | Şema prompt’a gömülür; JSON yanıttan çıkarılır; `--force --trust` |

`STUDIO_YARGI_MOD=ai` (varsayılan) öz-yargıda aynı motoru kullanır. `deterministik` test içindir.  
`STUDIO_YARGI_MOD=cursor` veya `claude` motoru geçici olarak o yargı için zorlar.

## İnsan kapıları

| Tür | Örnek | Ne yaparsın |
|---|---|---|
| Oyun tipi | charter, `--sec kisa_liste`, `--sec secilen` | Konsept seç |
| Asset | stil, parti kontakt, `--onayla taslak` | Görsel/ses onayla |
| Demo | `playtest-1` | Build’i oyna, not yaz |

## Playtest QA

Build/run sonrası ajan `playtest-qa-checklist.md` ile sonsuz SS döngüsü koşar
(ikon-first, orantı/şişmiş kutu, layout, feedback). Cursor workspace’te
`.cursor/hooks.json` `godot` komutundan sonra bu döngüyü otomatik devam ettirir.

## Yazılım öz-yargı

Her yazılım adımından sonra: `runlog/<adim>-yargi-NN.md` (yapılan / gereken / doğru / yanlış / skor).  
Yazılım soruları kullanıcıya gitmez.
