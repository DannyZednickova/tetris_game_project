# auth_server.py


import os, sqlite3, secrets, hashlib, hmac, threading, webbrowser, re
from flask import Flask, request, redirect, make_response
from string import Template
from Auth_Templates import STYLE, FORM_LOGIN, FORM_SETUP, OK_PAGE, ERR_PAGE, PROFILE_PAGE, PLAY_PAGE, USER_EXISTS_PAGE

def render(tpl, **kwargs):
    # doplní $style a další $placeholdery bezpečně (CSS závorky nevadí)
    return Template(tpl).substitute(**kwargs)

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


def valid_username(u):
    return 4 <= len(u) <= 32 and re.match(r'^[A-Za-z0-9](?:[A-Za-z0-9._-]{1,31})$', u)


def valid_password(p):
    """Kontroluje, že heslo má délku 4–15 znaků a obsahuje:
    - malé písmeno
    - velké písmeno
    - číslo
    - speciální znak
    """
    if not 4 <= len(p) <= 15:
        return False
    if not re.search(r"[a-z]", p):  # alespoň jedno malé písmeno
        return False
    if not re.search(r"[A-Z]", p):  # alespoň jedno velké písmeno
        return False
    if not re.search(r"[0-9]", p):  # alespoň jedno číslo
        return False
    if not re.search(r"[^A-Za-z0-9]", p):  # alespoň jeden speciální znak
        return False
    return True



# --- ROUTES ---

@app.get("/setup")
def setup_get():
    return render(FORM_SETUP, style=STYLE)

@app.post("/setup")
def setup_post():
    conn = _db()
    u = request.form.get("u", "").strip()
    p = request.form.get("p", "")
    if not u or not p:
        conn.close()
        return render(FORM_SETUP, style=STYLE)

    #validace usernama
    if not valid_username(u):
        conn.close()
        return render(FORM_SETUP, style=STYLE)

    if not valid_password(p):
        conn.close()
        return render(
            FORM_SETUP,
            style=STYLE)

    pwd_hash, salt = hash_password(p)
    try:
        conn.execute(
            "INSERT INTO users(username, pwd_hash, salt) VALUES(?,?,?)",
            (u, pwd_hash, salt)
        )
        conn.commit()
    except sqlite3.IntegrityError:
        conn.close()
        # nový stylizovaný návrat
        return render(USER_EXISTS_PAGE, style=STYLE)

    conn.close()
    return redirect("/login")

@app.get("/login")
def login_get():
    conn = _db()
    cnt = conn.execute("SELECT COUNT(*) FROM users").fetchone()[0]
    conn.close()
    if cnt == 0:
        return redirect("/setup")
    return render(FORM_LOGIN, style=STYLE)

@app.post("/login")
def login_post():
    global AUTH_TOKEN
    u = request.form.get("u", "").strip()
    p = request.form.get("p", "")
    conn = _db()

    # Upravíme SQL, aby vracelo i highscore a datum narození, pokud existují
    # Pokud tabulka nemá tyto sloupce, přidej je ALTEREM nebo nech score/dob = None
    try:
        row = conn.execute("""
            SELECT id, username, pwd_hash, salt,
                   COALESCE(highscore, 0),
                   COALESCE(date_of_birth, 'neuvedeno')
            FROM users
            WHERE username=?
        """, (u,)).fetchone()
    except sqlite3.OperationalError:
        # starší DB bez těchto sloupců
        row = conn.execute("SELECT id, username, pwd_hash, salt FROM users WHERE username=?", (u,)).fetchone()
        row = (*row, 0, "neuvedeno")

    conn.close()

    if not row:
        return render(ERR_PAGE, style=STYLE)

    user_id, username, pwd_hash, salt, score, dob = row

    if verify_password(p, salt, pwd_hash):
        AUTH_TOKEN = secrets.token_urlsafe(24)
        AUTH_EVENT.clear()

        html = render(
            PROFILE_PAGE,
            style=STYLE,
            username=username,
            dob=dob,
            score=score or 0
        )

        resp = make_response(html)
        resp.set_cookie("session", AUTH_TOKEN, httponly=True, samesite="Lax")
        return resp

    return render(ERR_PAGE, style=STYLE)


# --- NOVÁ ROUTA, KTERÁ UZAVŘE PROFIL A VRÁTÍ SE DO HRY ---
@app.post("/play")
def play_post():
    """Uživatel klikl na 'Chci hrát' → aktivuje AUTH_EVENT"""
    global AUTH_TOKEN
    AUTH_EVENT.set()

    html = render(PLAY_PAGE, style=STYLE)

    resp = make_response(html)
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