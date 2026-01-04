import json
import os
import sqlite3
import threading
import time
import traceback
from dataclasses import dataclass

try:
    import requests as _requests
except Exception:
    _requests = None

_DEFAULT_BATCH_SIZE = 25
_DEFAULT_TIMEOUT_S = 5.0
_MAX_STRING_LEN = 500
_MAX_RETRIES = 5
_BANNED_KEYS = {"username", "email", "token", "password"}


@dataclass
class TelemetryConfig:
    enabled: bool = False
    endpoint_url: str = ""
    api_key: str = ""
    app_name: str = ""
    app_version: str = "0.0.0"
    db_path: str = "telemetry.db"
    batch_size: int = _DEFAULT_BATCH_SIZE
    timeout_s: float = _DEFAULT_TIMEOUT_S


_cfg = TelemetryConfig()
_db_path = None
_init_lock = threading.Lock()
_flush_lock = threading.Lock()
_worker_lock = threading.Lock()
_worker_thread = None


def _utc_now() -> str:
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())


def _resolve_db_path(path: str) -> str:
    base_dir = os.path.dirname(__file__)
    if not path:
        path = "telemetry.db"
    if os.path.isabs(path):
        return path
    return os.path.abspath(os.path.join(base_dir, path))


def _connect():
    if not _db_path:
        return None
    return sqlite3.connect(_db_path, timeout=5)


def _ensure_db():
    conn = _connect()
    if conn is None:
        return
    try:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS events(
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                created_at TEXT NOT NULL,
                event_type TEXT NOT NULL,
                payload_json TEXT NOT NULL,
                sent_at TEXT NULL,
                attempts INTEGER NOT NULL DEFAULT 0,
                last_error TEXT NULL
            )
            """
        )
        conn.commit()
    finally:
        conn.close()


def _coerce_config(cfg) -> TelemetryConfig:
    if isinstance(cfg, TelemetryConfig):
        return cfg
    if isinstance(cfg, dict):
        get = cfg.get
    else:
        get = lambda k, d=None: getattr(cfg, k, d)
    return TelemetryConfig(
        enabled=bool(get("enabled", False)),
        endpoint_url=str(get("endpoint_url", "") or ""),
        api_key=str(get("api_key", "") or ""),
        app_name=str(get("app_name", "") or ""),
        app_version=str(get("app_version", "0.0.0") or "0.0.0"),
        db_path=str(get("db_path", "telemetry.db") or "telemetry.db"),
        batch_size=int(get("batch_size", _DEFAULT_BATCH_SIZE) or _DEFAULT_BATCH_SIZE),
        timeout_s=float(get("timeout_s", _DEFAULT_TIMEOUT_S) or _DEFAULT_TIMEOUT_S),
    )


def init(cfg) -> None:
    global _cfg, _db_path
    new_cfg = _coerce_config(cfg)
    with _init_lock:
        _cfg = new_cfg
        _db_path = _resolve_db_path(_cfg.db_path)
        if _cfg.enabled:
            try:
                _ensure_db()
            except Exception:
                pass


def _truncate(value: str, limit: int = _MAX_STRING_LEN) -> str:
    if value is None:
        return ""
    if len(value) <= limit:
        return value
    return value[:limit]


def _sanitize(value, depth: int = 0):
    if depth > 6:
        return "..."
    if isinstance(value, dict):
        cleaned = {}
        for key, val in value.items():
            key_str = str(key)
            if key_str.lower() in _BANNED_KEYS:
                continue
            cleaned[key_str] = _sanitize(val, depth + 1)
        return cleaned
    if isinstance(value, (list, tuple)):
        return [_sanitize(item, depth + 1) for item in value]
    if isinstance(value, str):
        return _truncate(value)
    if isinstance(value, (int, float, bool)) or value is None:
        return value
    return _truncate(str(value))


def _enqueue_event(event_type: str, payload_json: str) -> None:
    if not _cfg.enabled:
        return
    conn = _connect()
    if conn is None:
        return
    try:
        conn.execute(
            "INSERT INTO events(created_at, event_type, payload_json, sent_at, attempts, last_error)"
            " VALUES(?, ?, ?, NULL, 0, NULL)",
            (_utc_now(), _truncate(str(event_type), 128), payload_json),
        )
        conn.commit()
    finally:
        conn.close()


def send_async(event: dict) -> bool:
    if not _cfg.enabled:
        return False
    if not isinstance(event, dict):
        return False
    event_type = event.get("type")
    if not event_type:
        return False
    payload = _sanitize(event.get("payload", {}) or {})
    try:
        payload_json = json.dumps(payload, ensure_ascii=True)
    except (TypeError, ValueError):
        payload_json = json.dumps({"payload": _truncate(str(payload))}, ensure_ascii=True)
    try:
        _enqueue_event(event_type, payload_json)
    except Exception:
        return False
    _start_worker()
    return True


def _fetch_batch(conn, limit: int):
    return conn.execute(
        "SELECT id, created_at, event_type, payload_json FROM events"
        " WHERE sent_at IS NULL ORDER BY id LIMIT ?",
        (limit,),
    ).fetchall()


def _mark_sent(conn, ids):
    if not ids:
        return
    placeholders = ",".join(["?"] * len(ids))
    conn.execute(
        f"UPDATE events SET sent_at=?, last_error=NULL WHERE id IN ({placeholders})",
        (_utc_now(), *ids),
    )


def _mark_failed(conn, ids, error_text: str):
    if not ids:
        return
    placeholders = ",".join(["?"] * len(ids))
    conn.execute(
        f"UPDATE events SET attempts=attempts+1, last_error=? WHERE id IN ({placeholders})",
        (_truncate(error_text), *ids),
    )


def flush() -> int:
    if not _cfg.enabled:
        return 0
    if not _cfg.endpoint_url:
        return 0
    if _requests is None:
        return 0
    with _flush_lock:
        conn = _connect()
        if conn is None:
            return 0
        try:
            rows = _fetch_batch(conn, _cfg.batch_size)
            if not rows:
                return 0
            events = []
            ids = []
            for event_id, created_at, event_type, payload_json in rows:
                ids.append(event_id)
                try:
                    payload = json.loads(payload_json)
                except (TypeError, ValueError):
                    payload = {}
                events.append({"ts": created_at, "type": event_type, "payload": payload})

            body = {
                "app": _cfg.app_name,
                "version": _cfg.app_version,
                "events": events,
            }
            headers = {"Content-Type": "application/json"}
            if _cfg.api_key:
                headers["X-API-Key"] = _cfg.api_key
            try:
                resp = _requests.post(
                    _cfg.endpoint_url,
                    json=body,
                    headers=headers,
                    timeout=_cfg.timeout_s,
                )
            except Exception as exc:
                _mark_failed(conn, ids, f"request_error: {exc}")
                conn.commit()
                return 0
            if 200 <= resp.status_code < 300:
                _mark_sent(conn, ids)
                conn.commit()
                return len(ids)
            _mark_failed(conn, ids, f"http_status: {resp.status_code}")
            conn.commit()
            return 0
        finally:
            conn.close()


def _has_unsent() -> bool:
    conn = _connect()
    if conn is None:
        return False
    try:
        row = conn.execute(
            "SELECT 1 FROM events WHERE sent_at IS NULL LIMIT 1"
        ).fetchone()
        return row is not None
    except Exception:
        return False
    finally:
        conn.close()


def _start_worker() -> None:
    if not _cfg.enabled:
        return
    global _worker_thread
    with _worker_lock:
        if _worker_thread and _worker_thread.is_alive():
            return
        _worker_thread = threading.Thread(
            target=_worker_loop, name="telemetry-flush", daemon=True
        )
        _worker_thread.start()


def _worker_loop() -> None:
    backoff = 1.0
    retries = 0
    while True:
        sent = flush()
        if sent > 0:
            retries = 0
            backoff = 1.0
        if not _has_unsent():
            return
        if not _cfg.endpoint_url or _requests is None:
            return
        retries += 1
        if retries > _MAX_RETRIES:
            return
        time.sleep(backoff)
        backoff = min(backoff * 2, 30.0)


def _trim_home(text: str) -> str:
    home = os.path.expanduser("~")
    if home:
        text = text.replace(home, "~")
    return text


def capture_exception(where: str, exc: Exception) -> None:
    if not _cfg.enabled:
        return
    trace = "".join(traceback.format_exception(type(exc), exc, exc.__traceback__))
    trace = _trim_home(trace)
    payload = {
        "where": _truncate(str(where)),
        "error_type": exc.__class__.__name__,
        "error": _truncate(str(exc)),
        "trace": _truncate(trace, 2000),
    }
    send_async({"type": "exception", "payload": payload})
