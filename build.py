import hashlib
import json
import sys
from pathlib import Path

FILES = ["Tetris.py", "main.py"]
SECRET_KEY = "MojeTajneHeslo123"
CONFIG_DEFAULTS = {
    "version": "0.0.0",
    "telemetry_endpoint": "http://localhost:8000/telemetry",
    "telemetry_api_key": "",
}


def compute_hash(path: Path, secret: bytes) -> str:
    data = path.read_bytes()
    return hashlib.sha256(data + secret).hexdigest()


def main() -> int:
    secret_bytes = SECRET_KEY.encode("utf-8")
    manifest = {}
    existing = {}
    manifest_path = Path("manifest.json")
    if manifest_path.is_file():
        try:
            existing = json.loads(manifest_path.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            existing = {}

    for filename in FILES:
        path = Path(filename)
        if not path.is_file():
            print(f"Soubor nenalezen: {filename}", file=sys.stderr)
            return 1
        manifest[filename] = compute_hash(path, secret_bytes)

    if isinstance(existing, dict):
        for key, default in CONFIG_DEFAULTS.items():
            manifest[key] = existing.get(key, default)
    else:
        manifest.update(CONFIG_DEFAULTS)

    with Path("manifest.json").open("w", encoding="utf-8") as handle:
        json.dump(manifest, handle, indent=2, sort_keys=True)

    print("manifest.json byl vygenerovan.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
