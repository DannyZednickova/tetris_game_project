import Tetris
import Auth_OLD_Flusk

if __name__ == '__main__':
    # 1) Spusť lokální login server a otevři browser
    port = 1234

    # 2) Spusť pygame okno a zobraz login gate
    win = Tetris.pygame.display.set_mode((Tetris.s_width, Tetris.s_height))
    Tetris.pygame.display.set_caption('Tetris (Login Required)')

    Tetris.main_menu(win)

