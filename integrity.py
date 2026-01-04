import hashlib
import json
import sys
from pathlib import Path

SECRET_KEY = "MojeTajneHeslo123"
CONFIG_KEYS = {"version", "telemetry_endpoint", "telemetry_api_key"}

RED = "\x1b[31m"
GREEN = "\x1b[32m"
RESET = "\x1b[0m"


def compute_hash(path: Path, secret: bytes) -> str:
    data = path.read_bytes()
    return hashlib.sha256(data + secret).hexdigest()


def fail(message: str) -> None:
    print(f"{RED}{message}{RESET}", file=sys.stderr)
    raise SystemExit(1)


def main() -> int:
    manifest_path = Path("manifest.json")
    if not manifest_path.is_file():
        fail("manifest.json nenalezen.")

    try:
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        fail("manifest.json je neplatny JSON.")

    if not isinstance(manifest, dict):
        fail("manifest.json ma neplatny format.")

    secret_bytes = SECRET_KEY.encode("utf-8")

    for filename, expected_hash in manifest.items():
        if filename in CONFIG_KEYS:
            continue
        path = Path(filename)
        if not path.is_file():
            fail(f"Soubor chybi: {filename}")
        actual_hash = compute_hash(path, secret_bytes)
        if actual_hash != expected_hash:
            fail(f"Nesouhlasi hash souboru: {filename}")

    print(f"{GREEN}Integrity check OK.{RESET}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
