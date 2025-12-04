import Tetris
import Web_Server

"""
PODSTATA JE, ZE CELA HRA MUSI MIT ODDELENE DB.... WEBOVY SERVER A SAMOTNOU LOGIKU HRY...
MA? TED AKTUALNE? NEBO POTREBUJE UPRAVY???
"""


if __name__ == '__main__':
    # 1) Spusť lokální login server a otevři browser
    port = Web_Server.require_login()

    # 2) Spusť pygame okno a zobraz login gate
    win = Tetris.pygame.display.set_mode((Tetris.s_width, Tetris.s_height))
    Tetris.pygame.display.set_caption('Tetris (Login Required)')

    # 3) Čekej, dokud se uživatel nepřihlásí (bez toho se hra NESPUSTÍ)
    if Tetris.login_gate_screen(win, port):
        # 4) Po přihlášení teprve dovol do hlavního menu/hry
        Tetris.main_menu(win)

#test test je test. uzivatel...