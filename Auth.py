# auth_server.py
import os, sqlite3, secrets, hashlib, hmac, threading, webbrowser
from flask import Flask, request, redirect, make_response
from Auth_Templates import FORM_LOGIN, FORM_SETUP, OK_PAGE, ERR_PAGE, PROFILE_PAGE


DB_PATH = os.path.abspath(os.path.join(os.path.dirname(__file__), "tetris_users"))
AUTH_EVENT = threading.Event()
AUTH_TOKEN = None

app = Flask(__name__)
app.secret_key = secrets.token_hex(16)

# --- DATABASE HELPERS ---
def _db():
    conn = sqlite3.connect(DB_PATH, detect_types=sqlite3.PARSE_DECLTYPES)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS users(
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            pwd_hash BLOB NOT NULL,
            salt BLOB NOT NULL
        )
    """)
    conn.commit()
    return conn

# --- PASSWORDS ---
def hash_password(password: str, salt: bytes = None):
    if salt is None:
        salt = secrets.token_bytes(16)
    dk = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, 200_000)
    return dk, salt

def verify_password(password: str, salt: bytes, pwd_hash: bytes) -> bool:
    test, _ = hash_password(password, salt)
    return hmac.compare_digest(test, pwd_hash)


# --- ROUTES ---

@app.get("/setup")
def setup_get():
    # Vždy ukaž formulář pro vytvoření nového účtu
    return FORM_SETUP

@app.post("/setup")
def setup_post():
    conn = _db()
    u = request.form.get("u", "").strip()
    p = request.form.get("p", "")
    if not u or not p:
        conn.close()
        return FORM_SETUP

    pwd_hash, salt = hash_password(p)
    try:
        conn.execute(
            "INSERT INTO users(username, pwd_hash, salt) VALUES(?,?,?)",
            (u, pwd_hash, salt)
        )
        conn.commit()
    except sqlite3.IntegrityError:
        conn.close()
        return "<p>Uživatel už existuje. <a href='/login'>Přihlásit</a></p>"

    conn.close()
    return redirect("/login")

@app.get("/login")
def login_get():
    conn = _db()
    cnt = conn.execute("SELECT COUNT(*) FROM users").fetchone()[0]
    conn.close()
    if cnt == 0:
        return redirect("/setup")
    return FORM_LOGIN

@app.post("/login")
def login_post():
    global AUTH_TOKEN
    u = request.form.get("u", "").strip()
    p = request.form.get("p", "")
    conn = _db()
    row = conn.execute("SELECT id, username, pwd_hash, salt, highscore, date_of_birth FROM users WHERE username=?", (u,)).fetchone()
    conn.close()

    if not row:
        return ERR_PAGE

    user_id, username, pwd_hash, salt, score, dob = row

    if verify_password(p, salt, pwd_hash):
        AUTH_TOKEN = secrets.token_urlsafe(24)
        # ⚠️ TADY SE AUTH_EVENT NESPÚŠTÍ! – zatím jen uloží token a zobrazí profil
        resp = make_response(PROFILE_PAGE.format(
            username=username,
            dob=dob or "neuvedeno",
            score=score or 0
        ))
        resp.set_cookie("session", AUTH_TOKEN, httponly=True, samesite="Lax")
        return resp

    return ERR_PAGE

# --- NOVÁ ROUTA, KTERÁ UZAVŘE PROFIL A VRÁTÍ SE DO HRY ---
@app.post("/play")
def play_post():
    """Uživatel klikl na 'Chci hrát' → aktivuje AUTH_EVENT"""
    global AUTH_TOKEN
    AUTH_EVENT.set()  # ✅ přesunuto sem
    resp = make_response("""<!doctype html><meta charset="utf-8">
    <h2>Přihlášení dokončeno ✅</h2>
    <p>Můžeš se vrátit do hry.</p>""")
    resp.set_cookie("session", AUTH_TOKEN, httponly=True, samesite="Lax")
    return resp



@app.get("/shutdown")
def shutdown():
    func = request.environ.get("werkzeug.server.shutdown")
    if func is None:
        return "Nelze vypnout server – neběží pod Werkzeugem."
    func()
    return "Auth server vypnut."








# --- CONTROL HELPERS ---

def run_auth_server(port: int):
    app.run(host="127.0.0.1", port=port, debug=False, use_reloader=False)

def require_login(port: int = 8765):
    """Spustí auth server, otevře prohlížeč a vrátí port."""
    t = threading.Thread(target=run_auth_server, args=(port,), daemon=True)
    t.start()
    webbrowser.open(f"http://127.0.0.1:{port}/login", new=1, autoraise=True)
    return port

def wait_for_login():
    """Blokuje dokud se uživatel nepřihlásí."""
    AUTH_EVENT.wait(timeout=None)
    return AUTH_EVENT.is_set()

def is_authenticated():
    """Vrací True pokud již došlo k přihlášení."""
    return AUTH_EVENT.is_set()



#