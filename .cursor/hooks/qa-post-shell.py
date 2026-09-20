#!/usr/bin/env python3
"""Shell godot sonrası ajana checklist hatırlat.

Otomatik döngü KAPALI: `.cursor/state/qa-auto.json` → enabled:false
"""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
AUTO = ROOT / ".cursor" / "state" / "qa-auto.json"


def _auto_acik() -> bool:
	if not AUTO.exists():
		return False
	try:
		return bool(json.loads(AUTO.read_text(encoding="utf-8")).get("enabled"))
	except Exception:
		return False


def _godot_kosu(cmd: str) -> bool:
	dis = "".join(cmd.split("'")[i] for i in range(0, len(cmd.split("'")), 2))
	dis = "".join(dis.split('"')[i] for i in range(0, len(dis.split('"')), 2))
	return bool(re.search(r"(?:^|[\s;|&])godot\b", dis, re.I))


def main() -> None:
	if not _auto_acik():
		print("{}")
		return
	try:
		payload = json.load(sys.stdin)
	except Exception:
		print("{}")
		return
	inp = payload.get("tool_input") or payload.get("input") or {}
	if isinstance(inp, str):
		try:
			inp = json.loads(inp)
		except Exception:
			inp = {"command": inp}
	cmd = str(inp.get("command") or payload.get("command") or "")
	if not _godot_kosu(cmd):
		print("{}")
		return
	msg = (
		"PLAYTEST QA: `godot` çalıştı. Erken bitirme — 'yeterince iyi' yasak. "
		"`playtest-qa-checklist.md` A–K: her SS'yi Read ile UI tasarımcı gözüyle incele "
		"(B orantı/boyut, H kabuk, K güzellik: ajansa koyar mıydım?). "
		"Eksik/çirkin grafik → fal_uret.py / fal_sanat.py --kurulum → tekrar SS. "
		"Placeholder/ColorRect ile yeşil sayma. "
		"A–K + güzellik barı geçmeden `.cursor/state/qa-pending.json` done yazma."
	)
	print(json.dumps({"additional_context": msg}, ensure_ascii=False))


if __name__ == "__main__":
	main()
