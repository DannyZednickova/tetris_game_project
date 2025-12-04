#  stylované HTML se šablonami pro Webserver....

STYLE = """
<style>
body {
    background-color: #0d1b2a;
    font-family: "Segoe UI", Roboto, sans-serif;
    color: #f8f9fa;
    display: flex;
    flex-direction: column;
    align-items: center;
    justify-content: center;
    height: 100vh;
    margin: 0;
}
h2 { color: #ffffff; text-align: center; font-size: 2em; margin-bottom: 20px; }
form, .card {
    background-color: #1b263b; padding: 30px 40px; border-radius: 15px;
    box-shadow: 0 0 15px rgba(0,0,0,0.4); text-align: center; min-width: 320px;
}
label { font-size: 1em; color: #e0e0e0; }
input {
    background-color: #415a77; border: none; border-radius: 8px; padding: 10px;
    margin-top: 5px; width: 90%; color: white; font-size: 1em;
}
input:focus { outline: none; box-shadow: 0 0 5px #00aaff; }
button {
    background: linear-gradient(90deg, #0077b6, #0096c7); border: none; border-radius: 8px;
    padding: 10px 20px; color: white; font-weight: bold; font-size: 1em; cursor: pointer;
    margin-top: 20px; transition: all 0.2s ease-in-out;
}
button:hover { background: linear-gradient(90deg, #0096c7, #00b4d8); transform: scale(1.05); }
a { color: #90e0ef; text-decoration: none; }
a:hover { text-decoration: underline; }
p { margin-top: 15px; text-align: center; }
</style>
"""

# Používáme $style, $username, ... (Template), a NE .format() / f-strings
FORM_SETUP = """<!doctype html><meta charset="utf-8"><title>Vytvořit prvního uživatele</title>$style
<h2>První nastavení účtu</h2>
<form method="post" class="card">
<label>Uživatelské jméno:<br><input name="u" required></label><br><br>
<label>Heslo:<br><input name="p" type="password" required></label><br><br>
<button type="submit">Vytvořit účet</button>
</form>
<p>Po vytvoření budete přesměrováni na přihlášení.</p>"""

FORM_LOGIN = """<!doctype html><meta charset="utf-8"><title>Přihlášení</title>$style
<h2>Přihlášení</h2>
<form method="post" class="card">
<label>Uživatelské jméno:<br><input name="u" required></label><br><br>
<label>Heslo:<br><input name="p" type="password" required></label><br><br>
<button type="submit">Login</button>
</form>
<p>Nemáš účet? <a href="/setup">Vytvoř první účet</a></p>"""

OK_PAGE = """<!doctype html><meta charset="utf-8"><title>OK</title>$style
<div class="card">
<h2>Přihlášení proběhlo úspěšně 🎮</h2>
<p>Okno můžeš zavřít a vrátit se do hry.</p>
</div>"""

ERR_PAGE = """<!doctype html><meta charset="utf-8"><title>Chyba</title>$style
<div class="card">
<h2>Neplatné přihlašovací údaje ❌</h2>
<p><a href="/login">Zkusit znovu</a></p>
</div>"""

PROFILE_PAGE = """<!doctype html><meta charset="utf-8"><title>Profil hráče</title>$style
<div class="card">
<h2>Profil hráče</h2>
<p><b>Uživatel:</b> $username</p>
<p><b>Datum narození:</b> $dob</p>
<p><b>Highscore:</b> $score</p>
<form action="/play" method="post">
    <button type="submit">🎮 Chci hrát</button>
</form>
</div>"""


PLAY_PAGE = """<!doctype html><meta charset="utf-8"><title>Přihlášení dokončeno</title>$style
<div class="card">
    <h2>✅ Přihlášení dokončeno</h2>
    <p>Můžeš se vrátit do hry.</p>
</div>"""


USER_EXISTS_PAGE = """<!doctype html><meta charset="utf-8"><title>Uživatel už existuje</title>$style
<div class="card">
    <h2>⚠️ Uživatel už existuje</h2>
    <p><a href="/login">Přihlásit</a></p>
</div>"""