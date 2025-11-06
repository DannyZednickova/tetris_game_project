Sebastian Reed, Jakub Doležal, Daniela Zedníčková - projekt Tetris - UTB 2025
+------------------------------+
| 1️⃣  Uživatel spustí hru (main.py)     |
+------------------------------+
               |
               v
+------------------------------+
| 2️⃣  Pygame zobrazí LOGIN okno         |
|     (username + password)             |
+------------------------------+
               |
               v
+------------------------------+
| 3️⃣  Hra odešle přihlášení na API     |
|     POST /api/login                   |
|     { username, password }            |
+------------------------------+
               |
               v
+------------------------------+
| 4️⃣  SERVER ověří uživatele           |
|     - kontrola hesla (PBKDF2/bcrypt) |
|     - vygeneruje token               |
|     - vrátí JSON s profilem          |
|     { ok:true, token, profile:{...} }|
+------------------------------+
               |
               v
+------------------------------+
| 5️⃣  Hra přejde na PROFIL hráče        |
|     (zobrazí data přihlášeného hráče) |
|---------------------------------------|
|   Username: AGIH                      |
|   Lastname: Novak                     |
|   Highscore: 4200                     |
|                                       |
|   [ Change Lastname ]                 |
|   [ 🎮  PLAY GAME ]                   |
|---------------------------------------|
|  ✅ Může měnit jen své údaje (jméno)  |
|  ❌ Nemůže měnit skóre                |
+------------------------------+
               |
               |  ← klikne na tlačítko PLAY 🎮
               v
+------------------------------+
| 6️⃣  Hra spustí TETRIS gameplay        |
|     (lokální Pygame engine)           |
|---------------------------------------|
|  - Hráč hraje, skóre se počítá       |
|  - Po konci hry:                     |
|     POST /api/score {token, score}   |
+------------------------------+
               |
               v
+------------------------------+
| 7️⃣  SERVER ověří token a uloží skóre |
|     UPDATE users                     |
|     SET highscore = new_score        |
|     WHERE token = ...                |
|       AND new_score > old_score      |
+------------------------------+
               |
               v
+------------------------------+
| 8️⃣  Hra zobrazí konečné skóre        |
|     + návrat na profil/menu          |
+------------------------------+