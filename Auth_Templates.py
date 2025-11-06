FORM_SETUP = """<!doctype html><meta charset="utf-8"><title>Vytvořit prvního uživatele</title>
<h2>První nastavení účtu</h2>
<form method="post">
<label>Uživatelské jméno:<br><input name="u" required></label><br><br>
<label>Heslo:<br><input name="p" type="password" required></label><br><br>
<button type="submit">Vytvořit účet</button>
</form>
<p>Po vytvoření budete přesměrováni na přihlášení.</p>"""

FORM_LOGIN = """<!doctype html><meta charset="utf-8"><title>Přihlášení</title>
<h2>Přihlášení</h2>
<form method="post">
<label>Uživatelské jméno:<br><input name="u" required></label><br><br>
<label>Heslo:<br><input name="p" type="password" required></label><br><br>
<button type="submit">Login</button>
</form>
<p>Nemáš účet? <a href="/setup">Vytvoř první účet</a></p>"""

OK_PAGE = """<!doctype html><meta charset="utf-8"><title>OK</title>
<h2>Přihlášení proběhlo úspěšně.</h2>
<p>Okno můžeš zavřít a vrátit se do hry.</p>"""

ERR_PAGE = """<!doctype html><meta charset="utf-8"><title>Chyba</title>
<h2>Neplatné přihlašovací údaje.</h2>
<p><a href="/login">Zkusit znovu</a></p>"""

PROFILE_PAGE = """<!doctype html><meta charset="utf-8"><title>Profil</title>
<h2>Profil hráče</h2>
<p><b>Uživatel:</b> {username}</p>
<p><b>Datum narození:</b> {dob}</p>
<p><b>Highscore:</b> {score}</p>
<form action="/play" method="post">
    <button type="submit">🎮 Chci hrát</button>
</form>
"""