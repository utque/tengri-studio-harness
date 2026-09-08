#!/usr/bin/env node
/**
 * Stüdyo öz-yargı duman testleri (JS → python3 subprocess; curl benzeri yerel çağrı).
 */
const { spawnSync } = require("child_process");
const path = require("path");

const ROOT = path.resolve(__dirname, "..");
const STUDIO = path.join(ROOT, "studio.py");
const WISP = path.resolve(ROOT, "../wispward");

let failed = 0;
function ok(name, cond, detail = "") {
  if (cond) console.log(`  OK  ${name}`);
  else {
    failed++;
    console.log(`  FAIL ${name}${detail ? " — " + detail : ""}`);
  }
}

function sh(args, env = {}) {
  return spawnSync("python3", [STUDIO, ...args], {
    cwd: ROOT,
    encoding: "utf8",
    env: { ...process.env, STUDIO_YARGI_MOD: "deterministik", ...env },
    timeout: 180000,
  });
}

console.log("== 1) studio --test ==");
{
  const r = sh(["--kok", WISP, "--test"]);
  ok("çıkış 0", r.status === 0, `status=${r.status}\n${(r.stderr || r.stdout || "").slice(-500)}`);
  ok("tamam", (r.stdout || "").includes("tamam"));
}

console.log("== 2) studio --agac ==");
{
  const r = sh(["--kok", WISP, "--agac"]);
  ok("çıkış 0", r.status === 0, `status=${r.status}`);
  ok("STÜDYO AĞACI", (r.stdout || "").includes("STÜDYO AĞACI"));
}

console.log("== 3) yargı yardımcıları (aynı --kok bootstrap) ==");
{
  const code = `
import importlib.util, sys, os, json
os.environ["STUDIO_YARGI_MOD"] = "deterministik"
sys.argv = ["studio.py", "--kok", ${JSON.stringify(WISP)}, "--test"]
# studio modülünü --kok ayıklanmış halde yükle: çalıştırma, sadece tanımlar
spec = importlib.util.spec_from_loader("studio_under_test", loader=None)
mod = importlib.util.module_from_spec(spec)
src = open(${JSON.stringify(STUDIO)}, encoding="utf-8").read()
# __main__ bloğunu kes
src = src.split("\\nif __name__")[0]
exec(compile(src, "studio.py", "exec"), mod.__dict__)
assert mod.YARGI_SEVIYE == 10
assert mod.DEMO_ADIM == "playtest-1"
assert mod.Adim("faz2","g","faz2").kapi_turu() == mod.YAZILIM
assert mod.Adim("parti-01","g","parti").kapi_turu() == mod.INSAN_ASSET
assert mod.Adim("faz4a","g","faz4a").kapi_turu() == mod.INSAN_ASSET
assert mod.soru_sinifi("test offset px", "fail") == mod.YAZILIM
assert mod.soru_sinifi("hangi konsept?", "kısa liste") == mod.INSAN_OYUN_TIPI
assert mod.soru_sinifi("sprite güzel mi", "palet kontakt") == mod.INSAN_ASSET
a = mod.Adim("faz2","g","faz2")
y = mod.yargi_deterministik(a, ["02-tech.md"], [], 1)
assert y["karar"] == "onay"
y2 = mod.yargi_deterministik(a, ["02-tech.md"], ["uyarı"], 2)
assert y2["karar"] == "revizyon"
mod.sema_dogrula(y, mod.YARGI_SEMA, "y")
print("helpers-ok")
`;
  const r = spawnSync("python3", ["-c", code], {
    encoding: "utf8",
    env: { ...process.env, STUDIO_YARGI_MOD: "deterministik" },
    timeout: 60000,
  });
  ok("helpers", r.status === 0 && (r.stdout || "").includes("helpers-ok"), (r.stderr || r.stdout || "").slice(-800));
}

console.log("== 4) README / CLI bayrakları ==");
{
  const r = sh(["--kok", WISP, "--agac"]);
  ok("süreç ayakta", r.status === 0);
  const helpish = sh(["--kok", WISP, "--dogrula", "charter"]);
  // charter insan adımı; dogrula ajan adımı ister — beklenen DUR veya geçiş
  ok("cli yanıt verdi", helpish.status === 0 || helpish.status === 1, `status=${helpish.status}`);
}

if (failed) {
  console.log(`\n${failed} test başarısız`);
  process.exit(1);
}
console.log("\ntüm testler geçti");
