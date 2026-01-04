import json
import os

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


if __name__ == '__main__':
    try:
        player_data = _load_json(PLAYER_PATH)
        manifest = _load_json(MANIFEST_PATH)
        telemetry_cfg = _build_telemetry_cfg(player_data, manifest)
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

#test test je test. uzivatel...
