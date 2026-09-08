#!/usr/bin/env python3
"""Ajan durunca QA pending ise checklist follow-up gönder."""
from __future__ import annotations

import json
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
STATE = ROOT / ".cursor" / "state" / "qa-pending.json"
MAX_LOOPS = 25


def main() -> None:
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
						"Kalan kırmızıları `runlog/` altına duruş olarak yaz ve dur."
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
					"Oyun az önce build/run edildi. "
					"`playtest-qa-checklist.md` maddelerini screenshot ile tek tek kontrol et "
					"(A metin, B orantı/şişmiş kutu, C layout, D hiyerarşi, E feedback, F oynanış, G test). "
					"Kırmızıları düzelt → oyunu tekrar çalıştır → SS → tekrar kontrol. "
					"Hiç sorun kalmadıysa `.cursor/state/qa-pending.json` dosyasına "
					'`{"done": true}` yazıp bitir. Erken bırakma.'
				)
				% (loops, MAX_LOOPS)
			},
			ensure_ascii=False,
		)
	)


if __name__ == "__main__":
	main()
