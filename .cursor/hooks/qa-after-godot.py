#!/usr/bin/env python3
"""godot build/run sonrası QA pending işaretle."""
from __future__ import annotations

import json
import re
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
STATE = ROOT / ".cursor" / "state" / "qa-pending.json"

def _godot_kosu(cmd: str) -> bool:
	# Tırnak içindeki "godot" (echo/JSON) sayılmaz; gerçek çağrı dışarıda olmalı.
	dis = "".join(cmd.split("'")[i] for i in range(0, len(cmd.split("'")), 2))
	dis = "".join(dis.split('"')[i] for i in range(0, len(dis.split('"')), 2))
	return bool(re.search(r"(?:^|[\s;|&])godot\b", dis, re.I))


def main() -> None:
	try:
		payload = json.load(sys.stdin)
	except Exception:
		print("{}")
		return
	cmd = str(payload.get("command") or "")
	if not _godot_kosu(cmd):
		print("{}")
		return
	STATE.parent.mkdir(parents=True, exist_ok=True)
	prev = {}
	if STATE.exists():
		try:
			prev = json.loads(STATE.read_text(encoding="utf-8"))
		except Exception:
			prev = {}
	STATE.write_text(
		json.dumps(
			{
				"done": False,
				"command": cmd[:800],
				"at": time.time(),
				"loops": int(prev.get("loops") or 0),
				"cwd": str(payload.get("cwd") or ""),
			},
			ensure_ascii=False,
			indent=2,
		),
		encoding="utf-8",
	)
	print("{}")


if __name__ == "__main__":
	main()
