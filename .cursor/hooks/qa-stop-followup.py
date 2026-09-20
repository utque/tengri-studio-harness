#!/usr/bin/env python3
"""Ajan durunca QA pending ise checklist follow-up gönder.

Otomatik döngü KAPALI: `.cursor/state/qa-auto.json` → enabled:false
"""
from __future__ import annotations

import json
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
STATE = ROOT / ".cursor" / "state" / "qa-pending.json"
AUTO = ROOT / ".cursor" / "state" / "qa-auto.json"
MAX_LOOPS = 40


def _auto_acik() -> bool:
	if not AUTO.exists():
		return False
	try:
		return bool(json.loads(AUTO.read_text(encoding="utf-8")).get("enabled"))
	except Exception:
		return False


def main() -> None:
	if not _auto_acik():
		# Pending kalıntısını temizle; otomatik follow-up yok.
		if STATE.exists():
			try:
				STATE.unlink()
			except OSError:
				pass
		print("{}")
		return
	try:
		payload = json.load(sys.stdin)
	except Exception:
		print("{}")
		return
	status = str(payload.get("status") or "completed")
	if status != "completed":
		print("{}")
		return
	if not STATE.exists():
		print("{}")
		return
	try:
		st = json.loads(STATE.read_text(encoding="utf-8"))
	except Exception:
		print("{}")
		return
	if st.get("done"):
		try:
			STATE.unlink()
		except OSError:
			pass
		print("{}")
		return
	loops = int(st.get("loops") or 0) + 1
	st["loops"] = loops
	st["last_followup"] = time.time()
	STATE.parent.mkdir(parents=True, exist_ok=True)
	STATE.write_text(json.dumps(st, ensure_ascii=False, indent=2), encoding="utf-8")
	if loops > MAX_LOOPS:
		try:
			STATE.unlink()
		except OSError:
			pass
		print(
			json.dumps(
				{
					"followup_message": (
						"PLAYTEST QA: döngü limiti aşıldı. "
						"Kalan kırmızıları (özellikle K. UI tasarımcı / eksik fal grafikleri) "
						"`runlog/` altına duruş olarak yaz — 'yeterince iyi' diye done yazma."
					)
				},
				ensure_ascii=False,
			)
		)
		return
	print(
		json.dumps(
			{
				"followup_message": (
					"PLAYTEST QA DÖNGÜSÜ (otomatik, tur %d/%d): "
					"Oyun az önce build/run edildi. Erken bitirme. "
					"`playtest-qa-checklist.md` A–K maddelerini screenshot ile tek tek kontrol et. "
					"Her SS'yi Read ile aç — UI tasarımcı bakış açısı: orantı/boyut, hiyerarşi, "
					"stil (04-style), hayalet UI, eksik ikon. "
					"Eksik/çirkin grafik varsa fal ile üret (fal_uret.py / fal_sanat.py --kurulum), "
					"göster, kur, tekrar SS. "
					"'Çalışıyor ama çirkin/placeholder' = kırmızı. "
					"Kırmızıları düzelt → run → SS → tekrar. "
					"A–K + güzellik barı ('ajansa koyarım') yeşil olmadan "
					"`.cursor/state/qa-pending.json` içine done yazma."
				)
				% (loops, MAX_LOOPS)
			},
			ensure_ascii=False,
		)
	)


if __name__ == "__main__":
	main()
