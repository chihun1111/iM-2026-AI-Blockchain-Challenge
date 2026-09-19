from __future__ import annotations

import argparse
import json
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def run(label: str, args: list[str], cwd: Path = ROOT) -> dict:
    process = subprocess.run(args, cwd=cwd, text=True, encoding="utf-8", errors="replace", capture_output=True)
    return {"label": label, "command": " ".join(args), "returncode": process.returncode, "stdout": (process.stdout or "")[-4000:], "stderr": (process.stderr or "")[-4000:]}


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--all", action="store_true")
    args = parser.parse_args()
    if not args.all:
        parser.error("현재는 --all만 지원합니다.")
    py = sys.executable
    results = [
        run("v32_readiness", [py, "scripts/check_v32_readiness.py"]),
        run("seed_check", [py, "scripts/seed_demo.py", "--check"]),
        run("parser", [py, "scripts/evaluate_parser.py"]),
        run("tests", [py, "-m", "pytest", "-q"]),
        run("openapi", [py, "scripts/export_openapi.py"]),
    ]
    npm = shutil.which("npm.cmd") or shutil.which("npm")
    if npm and (ROOT / "frontend" / "node_modules").exists():
        results.append(run("frontend_build", [npm, "run", "build"], ROOT / "frontend"))
    else:
        results.append({"label": "frontend_build", "command": "npm run build", "returncode": 1, "stdout": "", "stderr": "frontend dependencies are missing"})
    # PowerShell on Windows may expose a legacy code page that cannot print
    # every Unicode character from paths or tool output. Escaped JSON keeps
    # the verification report machine-readable in every console encoding.
    print(json.dumps(results, ensure_ascii=True, indent=2))
    return 0 if all(x["returncode"] == 0 for x in results) else 1


if __name__ == "__main__":
    raise SystemExit(main())
