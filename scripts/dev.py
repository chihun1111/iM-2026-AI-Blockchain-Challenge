from __future__ import annotations

import argparse
import os
import shutil
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from backend.app.config import load_settings  # noqa: E402
from backend.app.db import Database  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8000)
    parser.add_argument("--seed", action="store_true", help="안전한 demo DB만 seed한 뒤 서버 실행")
    parser.add_argument("--no-web", action="store_true", help="프런트엔드 없이 API만 실행")
    args = parser.parse_args()
    if args.host not in {"127.0.0.1", "localhost"}:
        raise SystemExit("dev.py는 localhost 바인딩만 허용합니다.")
    settings = load_settings(ROOT)
    if args.seed:
        Database(settings).seed_demo()
    web_process = None
    frontend_dir = ROOT / "frontend"
    npm = shutil.which("npm.cmd") or shutil.which("npm")
    if not args.no_web and npm and (frontend_dir / "node_modules").exists():
        web_env = os.environ.copy()
        web_env.setdefault("VITE_API_BASE_URL", f"http://127.0.0.1:{args.port}")
        web_process = subprocess.Popen(
            [npm, "run", "dev", "--", "--host", "127.0.0.1", "--port", "5173"],
            cwd=frontend_dir,
            env=web_env,
        )
        time.sleep(1)
    elif not args.no_web:
        raise SystemExit("프런트엔드 의존성이 없습니다. frontend에서 npm install 후 실행하거나 --no-web을 사용하세요.")
    try:
        import uvicorn
    except ImportError as exc:
        if web_process:
            web_process.terminate()
        raise SystemExit("의존성을 먼저 설치하세요: python -m pip install -r requirements.txt") from exc
    try:
        uvicorn.run("backend.app.api:app", host=args.host, port=args.port, reload=False, log_level="info")
        return 0
    finally:
        if web_process and web_process.poll() is None:
            web_process.terminate()
            try:
                web_process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                web_process.kill()


if __name__ == "__main__":
    raise SystemExit(main())
