import json
import os
import subprocess
import sys
import time
from urllib.parse import urlparse
from urllib.request import urlopen

import Tetris
import Web_Server
import telemetry

"""
PODSTATA JE, ZE CELA HRA MUSI MIT ODDELENE DB.... WEBOVY SERVER A SAMOTNOU LOGIKU HRY...
MA? TED AKTUALNE? NEBO POTREBUJE UPRAVY???
"""


MANIFEST_PATH = os.path.join(os.path.dirname(__file__), "manifest.json")
PLAYER_PATH = os.path.join(os.path.dirname(__file__), "player.json")


def _load_json(path: str) -> dict:
    try:
        with open(path, "r", encoding="utf-8") as handle:
            data = json.load(handle)
    except (FileNotFoundError, json.JSONDecodeError):
        return {}
    if isinstance(data, dict):
        return data
    return {}


def _build_telemetry_cfg(player_data: dict, manifest: dict) -> dict:
    return {
        "enabled": bool(player_data.get("telemetry_consent", False)),
        "endpoint_url": str(manifest.get("telemetry_endpoint", "") or ""),
        "api_key": str(manifest.get("telemetry_api_key", "") or ""),
        "app_name": "Tetris",
        "app_version": str(manifest.get("version", "0.0.0") or "0.0.0"),
        "db_path": "telemetry.db",
    }


def _is_local_endpoint(endpoint_url: str) -> bool:
    if not endpoint_url:
        return False
    parsed = urlparse(endpoint_url)
    host = (parsed.hostname or "").lower()
    return host in {"127.0.0.1", "localhost"}


def _health_url(endpoint_url: str) -> str:
    parsed = urlparse(endpoint_url)
    if not parsed.scheme or not parsed.netloc:
        return ""
    return f"{parsed.scheme}://{parsed.netloc}/health"


def _check_health(endpoint_url: str, timeout_s: float = 0.4) -> bool:
    health = _health_url(endpoint_url)
    if not health:
        return False
    try:
        with urlopen(health, timeout=timeout_s) as resp:
            return 200 <= resp.status < 300
    except Exception:
        return False


def _start_local_telemetry_server(endpoint_url: str):
    if not _is_local_endpoint(endpoint_url):
        return None
    parsed = urlparse(endpoint_url)
    port = parsed.port
    if port is None:
        return None
    if _check_health(endpoint_url):
        return None
    server_path = os.path.join(os.path.dirname(__file__), "telemetry_server.py")
    if not os.path.isfile(server_path):
        return None
    env = os.environ.copy()
    env["TELEMETRY_SERVER_HOST"] = parsed.hostname or "127.0.0.1"
    env["TELEMETRY_SERVER_PORT"] = str(port)
    creationflags = 0
    if os.name == "nt":
        creationflags = subprocess.CREATE_NO_WINDOW
    try:
        proc = subprocess.Popen(
            [sys.executable, server_path],
            cwd=os.path.dirname(__file__),
            env=env,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            creationflags=creationflags,
        )
    except Exception:
        return None
    for _ in range(10):
        if _check_health(endpoint_url, timeout_s=0.6):
            break
        time.sleep(0.3)
    return proc


def _stop_local_telemetry_server(proc) -> None:
    if not proc:
        return
    try:
        if proc.poll() is None:
            proc.terminate()
            proc.wait(timeout=2)
    except Exception:
        try:
            proc.kill()
        except Exception:
            pass


if __name__ == '__main__':
    server_proc = None
    try:
        player_data = _load_json(PLAYER_PATH)
        manifest = _load_json(MANIFEST_PATH)
        telemetry_cfg = _build_telemetry_cfg(player_data, manifest)
        server_proc = _start_local_telemetry_server(telemetry_cfg.get("endpoint_url", ""))
        telemetry.init(telemetry_cfg)
        telemetry.send_async({"type": "app_start", "payload": {}})

        # 1) Spus login server a otevri browser
        port = Web_Server.require_login()

        # 2) Spus pygame okno a zobraz login gate
        win = Tetris.pygame.display.set_mode((Tetris.s_width, Tetris.s_height))
        Tetris.pygame.display.set_caption('Tetris (Login Required)')

        # 3) Cekej, dokud se uzivatel neprihlasi (bez toho se hra NESPUSTI)
        if Tetris.login_gate_screen(win, port, telemetry_cfg):
            # 4) Po prihlaseni teprve dovol do hlavniho menu/hry
            Tetris.main_menu(win, telemetry_cfg)

        telemetry.send_async({"type": "app_exit", "payload": {}})
        telemetry.flush()
    except Exception as e:
        telemetry.capture_exception("main", e)
        telemetry.flush()
        raise
    finally:
        _stop_local_telemetry_server(server_proc)

#test test je test. uzivatel...
