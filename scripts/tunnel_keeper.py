#!/usr/bin/env python
"""Держит публичный HTTPS-туннель к локальному бэкенду для Telegram Mini App и
автоматически обновляет адрес при переподключении.

- запускает `ssh -R 80:127.0.0.1:<port> nokey@localhost.run` и перезапускает его при обрыве;
- вытаскивает адрес https://xxxx.lhr.life из вывода;
- пишет его в .env (WEBAPP_URL=...) и в scripts/dev/webapp_url.txt (бот читает файл при каждом
  построении клавиатуры, перезапуск не нужен);
- выставляет кнопку меню бота (setChatMenuButton) на новый адрес.

  python scripts/tunnel_keeper.py [--port 8000]
"""
from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import sys
import time
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ENV = ROOT / ".env"
URL_FILE = ROOT / "scripts" / "dev" / "webapp_url.txt"
URL_RE = re.compile(r"https://[a-z0-9]+\.lhr\.life")


def read_env(key: str) -> str:
    if not ENV.exists():
        return ""
    for line in ENV.read_text(encoding="utf-8").splitlines():
        if line.startswith(key + "="):
            return line.split("=", 1)[1].strip()
    return os.environ.get(key, "")


def write_env(key: str, value: str) -> None:
    lines = ENV.read_text(encoding="utf-8").splitlines() if ENV.exists() else []
    out, done = [], False
    for line in lines:
        if line.startswith(key + "="):
            out.append(f"{key}={value}")
            done = True
        else:
            out.append(line)
    if not done:
        out.append(f"{key}={value}")
    ENV.write_text("\n".join(out) + "\n", encoding="utf-8")


def set_menu_button(url: str) -> None:
    token = read_env("BOT_TOKEN")
    if not token:
        return
    body = json.dumps({"menu_button": {"type": "web_app", "text": "Приложение", "web_app": {"url": url + "/"}}},
                      ensure_ascii=False).encode("utf-8")
    req = urllib.request.Request(f"https://api.telegram.org/bot{token}/setChatMenuButton", data=body,
                                 headers={"Content-Type": "application/json; charset=utf-8"})
    try:
        urllib.request.urlopen(req, timeout=20).read()
        print(f"[keeper] кнопка меню бота -> {url}", flush=True)
    except Exception as exc:  # noqa: BLE001
        print(f"[keeper] не удалось обновить кнопку меню: {exc}", flush=True)


def publish(url: str) -> None:
    URL_FILE.parent.mkdir(parents=True, exist_ok=True)
    URL_FILE.write_text(url, encoding="utf-8")
    write_env("WEBAPP_URL", url)
    print(f"[keeper] Mini App URL: {url}", flush=True)
    set_menu_button(url)


def run(port: int) -> None:
    cmd = ["ssh", "-o", "StrictHostKeyChecking=no", "-o", "ServerAliveInterval=30", "-o", "ServerAliveCountMax=3",
           "-o", "ExitOnForwardFailure=yes", "-R", f"80:127.0.0.1:{port}", "nokey@localhost.run"]
    current = ""
    while True:
        print("[keeper] запускаю ssh-туннель...", flush=True)
        proc = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, encoding="utf-8",
                                errors="ignore", bufsize=1)
        try:
            for line in proc.stdout:  # type: ignore[union-attr]
                m = URL_RE.search(line)
                if m and m.group(0) != current:
                    current = m.group(0)
                    publish(current)
        except KeyboardInterrupt:
            proc.terminate()
            return
        code = proc.wait()
        print(f"[keeper] туннель завершился (код {code}), перезапуск через 5 с", flush=True)
        time.sleep(5)


if __name__ == "__main__":
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--port", type=int, default=8000)
    a = p.parse_args()
    try:
        run(a.port)
    except KeyboardInterrupt:
        sys.exit(0)
