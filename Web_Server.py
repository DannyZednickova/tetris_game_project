import os, sqlite3, secrets, hashlib, hmac, threading, webbrowser, re
from flask import Flask, request, redirect, make_response
from string import Template
from Web_Templates import STYLE, FORM_LOGIN, FORM_SETUP, OK_PAGE, ERR_PAGE, PROFILE_PAGE, PLAY_PAGE, USER_EXISTS_PAGE
from html import escape

"""
AUTORIZACE UZIVATELE
"""



def render(tpl, **kwargs):
    """Vrati HTML obsah tim, ze nahradi placeholdery v sablone. Parametry: tpl (str) - sablona, kwargs - promenne pro substituci."""
    # doplní $style a další $placeholdery bezpečně (CSS závorky nevadí)
    return Template(tpl).substitute(**kwargs)

DB_PATH = os.path.abspath(os.path.join(os.path.dirname(__file__), "tetris_users"))
AUTH_EVENT = threading.Event()
AUTH_TOKEN = None
CURRENT_USER = None

app = Flask(__name__)
app.secret_key = secrets.token_hex(16)

# --- DATABASE HELPERS ---
def _db():
    """Otevre a inicializuje SQLite databazi (vytvori tabulku users pokud neexistuje). Vraci sqlite3.Connection."""
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


def _ensure_user_columns(conn: sqlite3.Connection) -> None:
    # highscore
    try:
        conn.execute("ALTER TABLE users ADD COLUMN highscore INTEGER DEFAULT 0")
    except sqlite3.OperationalError:
        pass

    # date_of_birth
    try:
        conn.execute("ALTER TABLE users ADD COLUMN date_of_birth TEXT DEFAULT 'neuvedeno'")
    except sqlite3.OperationalError:
        pass

    conn.commit()


def get_current_user():
    return CURRENT_USER


def get_user_highscore(user_id: int) -> int:
    if not user_id:
        return 0
    conn = _db()
    try:
        _ensure_user_columns(conn)
        row = conn.execute(
            "SELECT COALESCE(highscore, 0) FROM users WHERE id=?",
            (user_id,),
        ).fetchone()
        if not row:
            return 0
        return int(row[0] or 0)
    finally:
        conn.close()


def update_user_highscore(user_id: int, score: int) -> None:
    if not user_id:
        return
    conn = _db()
    try:
        _ensure_user_columns(conn)
        row = conn.execute(
            "SELECT COALESCE(highscore, 0) FROM users WHERE id=?",
            (user_id,),
        ).fetchone()
        current = int(row[0] or 0) if row else 0
        if score > current:
            conn.execute(
                "UPDATE users SET highscore=? WHERE id=?",
                (int(score), user_id),
            )
            conn.commit()
    finally:
        conn.close()

# --- PASSWORDS ---
def hash_password(password: str, salt: bytes = None):
    """Vytvori PBKDF2-HMAC-SHA256 hash pro zadane heslo. Pokud neni zadana sůl, vygeneruje novou. Vraci (hash, salt)."""
    if salt is None:
        salt = secrets.token_bytes(16)
    dk = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, 200_000)
    return dk, salt

def verify_password(password: str, salt: bytes, pwd_hash: bytes) -> bool:
    """Ověri zda zadane heslo odpovida ulozenemu hashi. Parametry: password (str), salt (bytes), pwd_hash (bytes). Vraci bool."""
    test, _ = hash_password(password, salt)
    return hmac.compare_digest(test, pwd_hash)


def valid_username(u):
    """Zkontroluje validitu uzivatelskeho jmena. Podminky: delka 4-32, povolene znaky A-Z a cisla a . _ -."""
    return 4 <= len(u) <= 32 and re.match(r'^[A-Za-z0-9](?:[A-Za-z0-9._-]{1,31})$', u)


def valid_password(p):
    """Zkontroluje heslo podle pravidel: delka 8, alespon jedno male, jedno velike pismeno, cislo a specialni znak.
    Parametry: p (str). Vraci bool."""
    if len(p) < 8:
        return False
    if not re.search(r"[a-z]", p):  # alespon jedno male pismeno
        return False
    if not re.search(r"[A-Z]", p):  # alespon jedno velke pismeno
        return False
    if not re.search(r"[0-9]", p):  # alespon jedno cislo
        return False
    if not re.search(r"[^A-Za-z0-9]", p):  # alespon jeden specialni znak
        return False
    return True




def errbox(msg: str) -> str:
    if not msg:
        return ""
    return f'<div class="error">{escape(msg)}</div>'







# --- ROUTES ---

@app.get("/setup")
def setup_get():
    """GET /setup - Zobrazi HTML formular pro registraci uzivatele. Bez parametru, vraci HTML stranku."""
    return render(FORM_SETUP,  style=STYLE, error_html="", u="")

@app.post("/setup")
def setup_post():
    conn = _db()
    u = (request.form.get("u") or "").strip()
    p = request.form.get("p") or ""

    if not u or not p:
        conn.close()
        return render(FORM_SETUP, style=STYLE, error_html=errbox("Vyplň uživatelské jméno i heslo."), u=u)

    if not valid_username(u):
        conn.close()
        return render(FORM_SETUP, style=STYLE, error_html=errbox("Neplatné uživatelské jméno."), u=u)

    if not valid_password(p):
        conn.close()
        return render(
            FORM_SETUP,
            style=STYLE,
            error_html=errbox("Slabé heslo: musí mít alespoň 8 znaků, malé i velké písmeno, číslo a speciální znak."),
            u=u
        )

    pwd_hash, salt = hash_password(p)
    try:
        conn.execute(
            "INSERT INTO users(username, pwd_hash, salt) VALUES(?,?,?)",
            (u, pwd_hash, salt)
        )
        conn.commit()
    except sqlite3.IntegrityError:
        conn.close()
        return render(FORM_SETUP, style=STYLE, error_html=errbox("Uživatel už existuje."), u=u)
    finally:
        conn.close()

    return redirect("/login")
@app.get("/login")
def login_get():
    """GET /login - Zobrazi prihlasovaci formular. Pokud v DB nejsou zadni uzivatele, presmeruje na /setup."""
    conn = _db()
    cnt = conn.execute("SELECT COUNT(*) FROM users").fetchone()[0]
    conn.close()
    if cnt == 0:
        return redirect("/setup")
    return render(FORM_LOGIN, style=STYLE)

@app.post("/login")
def login_post():
    """POST /login - Zpracuje prihlaseni.
    Ocekava form data: 'u' (username), 'p' (password).
    Pokud je prihlaseni uspesne, vygeneruje AUTH_TOKEN, nastavi cookie 'session' a vrati profilni stranku.
    Pokud ne, vrati chybovou stranku."""
    global AUTH_TOKEN, CURRENT_USER
    u = request.form.get("u", "").strip()
    p = request.form.get("p", "")
    conn = _db()

    # Upravime SQL, aby vracelo i highscore a datum narozeni, pokud existuji
    # Pokud tabulka nema tyto sloupce, pridej je ALTEREM nebo nech score/dob = None
    try:
        _ensure_user_columns(conn)
        row = conn.execute("""
            SELECT id, username, pwd_hash, salt,
                   COALESCE(highscore, 0),
                   COALESCE(date_of_birth, 'neuvedeno')
            FROM users
            WHERE username=?
        """, (u,)).fetchone()
    except sqlite3.OperationalError:
        # starsi DB bez techto sloupcu
        row = conn.execute("SELECT id, username, pwd_hash, salt FROM users WHERE username=?", (u,)).fetchone()
        row = (*row, 0, "neuvedeno")

    conn.close()

    if not row:
        return render(ERR_PAGE, style=STYLE)

    user_id, username, pwd_hash, salt, score, dob = row

    if verify_password(p, salt, pwd_hash):
        AUTH_TOKEN = secrets.token_urlsafe(24)
        CURRENT_USER = {"id": user_id, "username": username}
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

    CURRENT_USER = None
    return render(ERR_PAGE, style=STYLE)



"""
TADY BY TAKY MELA BYT LOGIKA, KTERA BUDE SCHOPNA TAHAT DO 
WEBOWEHO ROZHRANI UDAJE O HIGH SCORE... PAROVAT JE S ID UZIVATELE
JE TO SCHVALNE ODDELENE OD PRIHLASOVACI DB... SPOLECNE BUDE JEN ID UZIVATELE, NIC VIC
V TELEMETRII DB CO SE ULOZI JE FUK
"""




# --- NOVA ROUTA, KTERA UZAVRE PROFIL A VRATI SE DO HRY ---
@app.post("/play")
def play_post():
    """POST /play - Vola se kdyz uzivatel klikne 'Chci hrat'.
    Nastavi AUTH_EVENT (signal pro hru) a vrati PLAY_PAGE spolu s cookie session."""
    global AUTH_TOKEN
    AUTH_EVENT.set()

    html = render(PLAY_PAGE, style=STYLE)

    resp = make_response(html)
    resp.set_cookie("session", AUTH_TOKEN, httponly=True, samesite="Lax")
    return resp





# --- CONTROL HELPERS ---

def run_auth_server(port: int):
    """Spusti Flask aplikaci na zadanem portu. Parametr: port (int)."""
    app.run(host="127.0.0.1", port=port, debug=False, use_reloader=False)

def require_login(port: int = 8765):
    """Spusti auth server v daemon vlakne a otevře prohlizec na /login.
    Parametry: port (int) - port na kterem server pobehne. Vraci port."""
    t = threading.Thread(target=run_auth_server, args=(port,), daemon=True)
    t.start()
    webbrowser.open(f"http://127.0.0.1:{port}/login", new=1, autoraise=True)
    return port

def wait_for_login():
    """Blokuje dokud neni AUTH_EVENT nastaven (uzivatel klikl 'Chci hrat').
    Vraci True pokud event nastal."""
    AUTH_EVENT.wait(timeout=None)
    return AUTH_EVENT.is_set()

def is_authenticated():
    """Vraci True pokud AUTH_EVENT byl nastaven, jinak False. (Signalizuje, ze uzivatel chce hrat)."""
    return AUTH_EVENT.is_set()
