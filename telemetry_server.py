import json
import os
import sys
from datetime import datetime

from flask import Flask, jsonify, request

try:
    import mysql.connector as mysql_connector
except Exception as exc:
    mysql_connector = None
    _mysql_import_error = exc


APP = Flask(__name__)

DB_HOST = os.getenv("TELEMETRY_DB_HOST", "127.0.0.1")
DB_PORT = int(os.getenv("TELEMETRY_DB_PORT", "3306"))
DB_USER = os.getenv("TELEMETRY_DB_USER", "root")
DB_PASS = os.getenv("TELEMETRY_DB_PASS", "")
DB_NAME = os.getenv("TELEMETRY_DB_NAME", "tetris_telemetry")
API_KEY = os.getenv("TELEMETRY_API_KEY", "")
SERVER_HOST = os.getenv("TELEMETRY_SERVER_HOST", "127.0.0.1")
SERVER_PORT = int(os.getenv("TELEMETRY_SERVER_PORT", "8000"))

_MAX_STR = 512
_schema_ready = False
_schema_error = ""


def _truncate(value: str, limit: int = _MAX_STR) -> str:
    if value is None:
        return ""
    if len(value) <= limit:
        return value
    return value[:limit]

def _coerce_int(value):
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def _coerce_float(value):
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _require_mysql() -> None:
    if mysql_connector is None:
        raise RuntimeError(
            "mysql-connector-python is not installed. "
            "Install with: pip install mysql-connector-python"
        ) from _mysql_import_error


def _connect(database: str | None = None):
    _require_mysql()
    return mysql_connector.connect(
        host=DB_HOST,
        port=DB_PORT,
        user=DB_USER,
        password=DB_PASS,
        database=database,
        autocommit=True,
    )

def _has_table(name: str) -> bool:
    try:
        conn = _connect(DB_NAME)
    except Exception:
        return False
    try:
        cur = conn.cursor()
        cur.execute("SHOW TABLES LIKE %s", (name,))
        found = cur.fetchone() is not None
        cur.close()
        return found
    finally:
        conn.close()


def _ensure_schema() -> None:
    _require_mysql()
    conn = _connect(None)
    try:
        cur = conn.cursor()
        cur.execute(
            f"CREATE DATABASE IF NOT EXISTS {DB_NAME} "
            "DEFAULT CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci"
        )
        cur.close()
    finally:
        conn.close()

    conn = _connect(DB_NAME)
    try:
        cur = conn.cursor()
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS telemetry_events (
                id BIGINT AUTO_INCREMENT PRIMARY KEY,
                received_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
                app_name VARCHAR(128) NOT NULL,
                app_version VARCHAR(32) NOT NULL,
                event_ts VARCHAR(32) NOT NULL,
                event_type VARCHAR(128) NOT NULL,
                payload_json TEXT NOT NULL,
                source_ip VARCHAR(45) NULL
            ) ENGINE=InnoDB
            """
        )
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS telemetry_game_sessions (
                id BIGINT AUTO_INCREMENT PRIMARY KEY,
                received_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
                app_name VARCHAR(128) NOT NULL,
                app_version VARCHAR(32) NOT NULL,
                event_ts VARCHAR(32) NOT NULL,
                duration_s DOUBLE NULL,
                score INT NULL,
                level_max INT NULL,
                lines_cleared INT NULL,
                reason_end VARCHAR(64) NULL,
                payload_json TEXT NOT NULL,
                source_ip VARCHAR(45) NULL
            ) ENGINE=InnoDB
            """
        )
        try:
            cur.execute(
                "CREATE INDEX idx_event_type ON telemetry_events (event_type)"
            )
        except Exception:
            pass
        try:
            cur.execute(
                "CREATE INDEX idx_event_ts ON telemetry_events (event_ts)"
            )
        except Exception:
            pass
        try:
            cur.execute(
                "CREATE INDEX idx_session_ts ON telemetry_game_sessions (event_ts)"
            )
        except Exception:
            pass
        cur.close()
    finally:
        conn.close()

def _ensure_schema_once() -> bool:
    global _schema_ready, _schema_error
    if _schema_ready:
        if _has_table("telemetry_game_sessions"):
            return True
        _schema_ready = False
    try:
        _ensure_schema()
    except Exception:
        _schema_error = str(sys.exc_info()[1] or "unknown_error")
        return False
    _schema_ready = True
    return True


def _list_tables():
    conn = _connect(DB_NAME)
    try:
        cur = conn.cursor()
        cur.execute("SHOW TABLES")
        rows = cur.fetchall()
        cur.close()
    finally:
        conn.close()
    return [row[0] for row in rows]


def _get_source_ip() -> str:
    forwarded = request.headers.get("X-Forwarded-For", "")
    if forwarded:
        return forwarded.split(",")[0].strip()
    return request.remote_addr or ""


@APP.get("/health")
def health():
    schema_ok = _ensure_schema_once()
    payload = {"status": "ok", "time": datetime.utcnow().isoformat() + "Z"}
    if request.args.get("debug") == "1":
        payload["schema_ok"] = schema_ok
        if not schema_ok:
            payload["schema_error"] = _schema_error
        if schema_ok:
            payload["db_name"] = DB_NAME
            payload["tables"] = _list_tables()
    return jsonify(payload)


@APP.post("/telemetry")
def telemetry_post():
    if not _ensure_schema_once():
        return jsonify({"error": "db_init_failed"}), 500
    if API_KEY:
        api_key = request.headers.get("X-API-Key", "")
        if api_key != API_KEY:
            return jsonify({"error": "unauthorized"}), 401

    body = request.get_json(silent=True) or {}
    app_name = _truncate(str(body.get("app", "") or ""), 128)
    app_version = _truncate(str(body.get("version", "") or ""), 32)
    events = body.get("events")

    if not app_name or not app_version or not isinstance(events, list):
        return jsonify({"error": "invalid_payload"}), 400

    rows = []
    session_rows = []
    source_ip = _get_source_ip()
    for item in events:
        if not isinstance(item, dict):
            continue
        event_ts = _truncate(str(item.get("ts", "") or ""), 32)
        event_type = _truncate(str(item.get("type", "") or ""), 128)
        payload = item.get("payload", {})
        try:
            payload_json = json.dumps(payload, ensure_ascii=True)
        except (TypeError, ValueError):
            payload_json = json.dumps({"payload": _truncate(str(payload))}, ensure_ascii=True)
        if not event_ts or not event_type:
            continue
        rows.append((app_name, app_version, event_ts, event_type, payload_json, source_ip))
        if event_type == "game_session_end" and isinstance(payload, dict):
            duration_s = _coerce_float(payload.get("duration_s"))
            score = _coerce_int(payload.get("score"))
            level_max = _coerce_int(payload.get("level_max"))
            lines_cleared = _coerce_int(payload.get("lines"))
            reason_end = _truncate(str(payload.get("reason_end", "") or ""), 64)
            session_rows.append(
                (
                    app_name,
                    app_version,
                    event_ts,
                    duration_s,
                    score,
                    level_max,
                    lines_cleared,
                    reason_end,
                    payload_json,
                    source_ip,
                )
            )

    if not rows:
        return jsonify({"error": "no_events"}), 400

    conn = _connect(DB_NAME)
    try:
        cur = conn.cursor()
        cur.executemany(
            """
            INSERT INTO telemetry_events (
                app_name, app_version, event_ts, event_type, payload_json, source_ip
            ) VALUES (%s, %s, %s, %s, %s, %s)
            """,
            rows,
        )
        if session_rows:
            cur.executemany(
                """
                INSERT INTO telemetry_game_sessions (
                    app_name, app_version, event_ts, duration_s, score, level_max,
                    lines_cleared, reason_end, payload_json, source_ip
                ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                """,
                session_rows,
            )
        cur.close()
    finally:
        conn.close()

    return jsonify({"status": "ok", "inserted": len(rows)})


if __name__ == "__main__":
    try:
        _ensure_schema()
    except Exception as exc:
        sys.stderr.write(f"Telemetry DB init failed: {exc}\n")
        sys.exit(1)
    APP.run(host=SERVER_HOST, port=SERVER_PORT, debug=False)
