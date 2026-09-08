#!/usr/bin/env python3
"""Shell godot sonrası ajana checklist hatırlat."""
from __future__ import annotations

import json
import re
import sys

def _godot_kosu(cmd: str) -> bool:
	dis = "".join(cmd.split("'")[i] for i in range(0, len(cmd.split("'")), 2))
	dis = "".join(dis.split('"')[i] for i in range(0, len(dis.split('"')), 2))
	return bool(re.search(r"(?:^|[\s;|&])godot\b", dis, re.I))


def main() -> None:
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
		"PLAYTEST QA: `godot` çalıştı. "
		"`playtest-qa-checklist.md` (veya tengri-studio/playtest-qa-checklist.md) "
		"maddelerini screenshot ile kontrol et — özellikle B. Orantı "
		"(şişmiş panel/düğme). Kırmızı varsa düzelt → tekrar run → SS. "
		"Temiz çıkışta `.cursor/state/qa-pending.json` içine \"done\": true yaz."
	)
	print(json.dumps({"additional_context": msg}, ensure_ascii=False))


if __name__ == "__main__":
	main()
