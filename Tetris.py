import random
import pygame
import Web_Server
import time, json, os, hmac, hashlib, secrets, glob, webbrowser
import telemetry




# Press âŚR to execute it or replace it with your code.
# Press Double â‡§ to search everywhere for classes, files, tool windows, actions, and settings.


"""
10 x 20 grid
play_height = 2 * play_width

tetriminos:
    0 - S - green
    1 - Z - red
    2 - I - cyan
    3 - O - yellow
    4 - J - blue
    5 - L - orange
    6 - T - purple
"""

pygame.font.init()

# global variables

col = 10  # 10 columns
row = 20  # 20 rows
s_width = 800  # window width
s_height = 750  # window height
play_width = 300  # play window width; 300/10 = 30 width per block
play_height = 600  # play window height; 600/20 = 20 height per block
block_size = 30  # size of block

top_left_x = (s_width - play_width) // 2
top_left_y = s_height - play_height - 50

filepath = os.path.join(os.path.dirname(__file__), './highscore.txt')
fontpath = os.path.join(os.path.dirname(__file__), 'arcade.TTF')
fontpath_mario = os.path.join(os.path.dirname(__file__), './mario.ttf')
PLAYER_PATH = os.path.join(os.path.dirname(__file__), "player.json")

# UI palette
BG_TOP = (12, 16, 28)
BG_BOTTOM = (6, 10, 18)
PANEL_BG = (18, 22, 38)
PANEL_BORDER = (70, 90, 130)
ACCENT = (0, 200, 170)
TEXT_PRIMARY = (245, 245, 250)
TEXT_MUTED = (160, 170, 190)
GRID_BG = (12, 14, 22)
GRID_LINE = (35, 45, 70)

_bg_cache = None
_bg_size = None


def draw_background(surface):
    global _bg_cache, _bg_size
    size = surface.get_size()
    if _bg_cache is None or _bg_size != size:
        _bg_cache = pygame.Surface(size)
        height = max(size[1] - 1, 1)
        for y in range(size[1]):
            ratio = y / height
            r = int(BG_TOP[0] + (BG_BOTTOM[0] - BG_TOP[0]) * ratio)
            g = int(BG_TOP[1] + (BG_BOTTOM[1] - BG_TOP[1]) * ratio)
            b = int(BG_TOP[2] + (BG_BOTTOM[2] - BG_TOP[2]) * ratio)
            pygame.draw.line(_bg_cache, (r, g, b), (0, y), (size[0], y))
        _bg_size = size
    surface.blit(_bg_cache, (0, 0))


def draw_panel(surface, rect):
    pygame.draw.rect(surface, PANEL_BG, rect, border_radius=10)
    pygame.draw.rect(surface, PANEL_BORDER, rect, 2, border_radius=10)


def draw_button(surface, rect, text, font, bg, fg, border=None):
    pygame.draw.rect(surface, bg, rect, border_radius=10)
    if border:
        pygame.draw.rect(surface, border, rect, 2, border_radius=10)
    label = font.render(text, True, fg)
    surface.blit(label, (rect.x + (rect.width - label.get_width())/2,
                         rect.y + (rect.height - label.get_height())/2))

def load_player_data():
    try:
        with open(PLAYER_PATH, "r", encoding="utf-8") as handle:
            data = json.load(handle)
    except (FileNotFoundError, json.JSONDecodeError):
        return {}
    if isinstance(data, dict):
        return data
    return {}


def save_player_data(data: dict) -> None:
    if not isinstance(data, dict):
        return
    try:
        with open(PLAYER_PATH, "w", encoding="utf-8") as handle:
            json.dump(data, handle, ensure_ascii=True, indent=2)
    except Exception:
        pass

# shapes formats

S = [['.....',
      '.....',
      '..00.',
      '.00..',
      '.....'],
     ['.....',
      '..0..',
      '..00.',
      '...0.',
      '.....']]

Z = [['.....',
      '.....',
      '.00..',
      '..00.',
      '.....'],
     ['.....',
      '..0..',
      '.00..',
      '.0...',
      '.....']]

I = [['.....',
      '..0..',
      '..0..',
      '..0..',
      '..0..'],
     ['.....',
      '0000.',
      '.....',
      '.....',
      '.....']]

O = [['.....',
      '.....',
      '.00..',
      '.00..',
      '.....']]

J = [['.....',
      '.0...',
      '.000.',
      '.....',
      '.....'],
     ['.....',
      '..00.',
      '..0..',
      '..0..',
      '.....'],
     ['.....',
      '.....',
      '.000.',
      '...0.',
      '.....'],
     ['.....',
      '..0..',
      '..0..',
      '.00..',
      '.....']]

L = [['.....',
      '...0.',
      '.000.',
      '.....',
      '.....'],
     ['.....',
      '..0..',
      '..0..',
      '..00.',
      '.....'],
     ['.....',
      '.....',
      '.000.',
      '.0...',
      '.....'],
     ['.....',
      '.00..',
      '..0..',
      '..0..',
      '.....']]

T = [['.....',
      '..0..',
      '.000.',
      '.....',
      '.....'],
     ['.....',
      '..0..',
      '..00.',
      '..0..',
      '.....'],
     ['.....',
      '.....',
      '.000.',
      '..0..',
      '.....'],
     ['.....',
      '..0..',
      '.00..',
      '..0..',
      '.....']]

# index represents the shape
shapes = [S, Z, I, O, J, L, T]
shape_colors = [(0, 255, 0), (255, 0, 0), (0, 255, 255), (255, 255, 0), (255, 165, 0), (0, 0, 255), (128, 0, 128)]

# class to represent each of the pieces


class Piece(object):
    def __init__(self, x, y, shape):
        self.x = x
        self.y = y
        self.shape = shape
        self.color = shape_colors[shapes.index(shape)]  # choose color from the shape_color list
        self.rotation = 0  # chooses the rotation according to index


# initialise the grid
def create_grid(locked_pos={}):
    """Vytvori a vrati 2D seznam (grid) se zakladnimi barvami.
    Parametry:
        locked_pos (dict) - mapovani pozic (x,y) na barvu (r,g,b), ktere budou predem zablokovane.
    Navratova hodnota:
        grid (list of lists) - row x col seznam RGB trojic."""
    grid = [[(0, 0, 0) for x in range(col)] for y in range(row)]  # grid represented rgb tuples

    # locked_positions dictionary
    # (x,y):(r,g,b)
    for y in range(row):
        for x in range(col):
            if (x, y) in locked_pos:
                color = locked_pos[
                    (x, y)]  # get the value color (r,g,b) from the locked_positions dictionary using key (x,y)
                grid[y][x] = color  # set grid position to color

    return grid


def convert_shape_format(piece):
    """Prevede polozku Piece na seznam konkretni polohy bloku v sitce.
    Parametry:
        piece (Piece) - instance s x,y,shape a rotation.
    Navrat:
        positions (list of tuples) - seznam (x,y) souradnic bloku podle aktualni rotace."""
    positions = []
    shape_format = piece.shape[piece.rotation % len(piece.shape)]  # get the desired rotated shape from piece

    '''
    e.g.
       ['.....',
        '.....',
        '..00.',
        '.00..',
        '.....']
    '''
    for i, line in enumerate(shape_format):  # i gives index; line gives string
        row = list(line)  # makes a list of char from string
        for j, column in enumerate(row):  # j gives index of char; column gives char
            if column == '0':
                positions.append((piece.x + j, piece.y + i))

    for i, pos in enumerate(positions):
        positions[i] = (pos[0] - 2, pos[1] - 4)  # offset according to the input given with dot and zero

    return positions


# checks if current position of piece in grid is valid
def valid_space(piece, grid):
    """Zkontroluje zda dane pozice pro piece jsou volne v ramci gridu.
    Parametry:
        piece (Piece) - kontrolovana polozka
        grid (list) - aktualni grid
    Navrat:
        bool - True pokud jsou vsechny obsazene polozky ve volnem prostoru, jinak False."""
    # makes a 2D list of all the possible (x,y)
    accepted_pos = [[(x, y) for x in range(col) if grid[y][x] == (0, 0, 0)] for y in range(row)]
    # removes sub lists and puts (x,y) in one list; easier to search
    accepted_pos = [x for item in accepted_pos for x in item]

    formatted_shape = convert_shape_format(piece)

    for pos in formatted_shape:
        if pos not in accepted_pos:
            if pos[1] >= 0:
                return False
    return True


# check if piece is out of board
def check_lost(positions):
    """Zkontroluje zda nejaka pozice ma y < 1, coz znamena prohra.
    Parametry:
        positions (iterable) - seznam pozic (x,y)
    Navrat:
        bool - True pokud dojde k prohre, jinak False."""
    for pos in positions:
        x, y = pos
        if y < 1:
            return True
    return False


# chooses a shape randomly from shapes list
def get_shape():
    """Vytvori novy objekt Piece umisteny na startovni pozici.
    Navrat:
        Piece instance."""
    return Piece(5, 0, random.choice(shapes))


# draws text in the middle - POUZITO PRO PRESS ANY KEY
def draw_text_middle(text, size, color, surface):
    """Vykresli text doprostred herni oblasti.
    Parametry:
        text (str) - retezec k vykresleni
        size (int) - velikost fontu
        color (tuple) - RGB barva
        surface (pygame.Surface) - cilovy povrch"""
    font = pygame.font.Font(fontpath, size)
    font.set_bold(False)
    font.set_italic(True)
    label = font.render(text, 1, color)

    surface.blit(label, (
        top_left_x + play_width/2 - (label.get_width()/2),
        top_left_y + play_height/2 - (label.get_height()/2 -90)
    ))
# draws the lines of the grid for the game



def draw_grid(surface):
    """Vykresli matici ciary gridu.
    Parametry:
        surface (pygame.Surface) - cilovy povrch."""
    grid_color = GRID_LINE

    for i in range(row):
        # draw grey horizontal lines
        pygame.draw.line(surface, grid_color, (top_left_x, top_left_y + i * block_size),
                         (top_left_x + play_width, top_left_y + i * block_size))
        for j in range(col):
            # draw grey vertical lines
            pygame.draw.line(surface, grid_color, (top_left_x + j * block_size, top_left_y),
                             (top_left_x + j * block_size, top_left_y + play_height))


# clear a row when it is filled
def clear_rows(grid, locked):
    """Odebere plne radky z gridu a posune vsechny vysse leziaci bloky dolu.
    Parametry:
        grid (list) - aktualni grid
        locked (dict) - mapovani pozic (x,y) na barvu
    Navrat:
        increment (int) - pocet smazanych radku"""
    # need to check if row is clear then shift every other row above down one
    increment = 0
    for i in range(len(grid) - 1, -1, -1):      # start checking the grid backwards
        grid_row = grid[i]                      # get the last row
        if (0, 0, 0) not in grid_row:           # if there are no empty spaces (i.e. black blocks)
            increment += 1
            # add positions to remove from locked
            index = i                           # row index will be constant
            for j in range(len(grid_row)):
                try:
                    del locked[(j, i)]          # delete every locked element in the bottom row
                except ValueError:
                    continue

    # shift every row one step down
    # delete filled bottom row
    # add another empty row on the top
    # move down one step
    if increment > 0:
        # sort the locked list according to y value in (x,y) and then reverse
        # reversed because otherwise the ones on the top will overwrite the lower ones
        for key in sorted(list(locked), key=lambda a: a[1])[::-1]:
            x, y = key
            if y < index:                       # if the y value is above the removed index
                new_key = (x, y + increment)    # shift position to down
                locked[new_key] = locked.pop(key)

    return increment


# draws the upcoming piece
def draw_next_shape(piece, surface, start_x=None, start_y=None, box_rect=None):
    """Vykresli nasledujici tetromino v panelu.
    Parametry:
        piece (Piece) - nasledujici polozka
        surface (pygame.Surface) - cilovy povrch"""
    font = pygame.font.Font(fontpath, 26)
    label = font.render('NEXT', 1, TEXT_MUTED)

    if box_rect is not None:
        surface.blit(label, (box_rect.x, box_rect.y - 28))
    else:
        if start_x is None:
            start_x = top_left_x + play_width + 60
        if start_y is None:
            start_y = top_left_y + (play_height / 2 - 100)
        surface.blit(label, (start_x, start_y - 32))

    shape_format = piece.shape[piece.rotation % len(piece.shape)]

    positions = []
    for i, line in enumerate(shape_format):
        row = list(line)
        for j, column in enumerate(row):
            if column == '0':
                positions.append((j, i))

    if not positions:
        return

    min_x = min(p[0] for p in positions)
    max_x = max(p[0] for p in positions)
    min_y = min(p[1] for p in positions)
    max_y = max(p[1] for p in positions)
    shape_w = (max_x - min_x + 1) * block_size
    shape_h = (max_y - min_y + 1) * block_size

    if box_rect is not None:
        draw_x = box_rect.x + (box_rect.width - shape_w) // 2 - min_x * block_size
        draw_y = box_rect.y + (box_rect.height - shape_h) // 2 - min_y * block_size
    else:
        draw_x = start_x
        draw_y = start_y

    for x, y in positions:
        pygame.draw.rect(surface, piece.color,
                         (draw_x + x * block_size, draw_y + y * block_size,
                          block_size, block_size), 0)

    # pygame.display.update()


# draws the content of the window
def draw_window(surface, grid, score=0, last_score=0, next_piece=None):
    """Vykresli cele herni okno vcetne score a highscore.
    Parametry:
        surface (pygame.Surface) - cilovy povrch
        grid (list) - aktualni grid
        score (int) - aktualni score
        last_score (int) - highscore
        next_piece (Piece) - nasledujici polozka"""
    draw_background(surface)

    pygame.font.init()

    title_font = pygame.font.Font(fontpath_mario, 64)
    title_font.set_bold(True)
    title = title_font.render('TETRIS', 1, TEXT_PRIMARY)
    surface.blit(title, (s_width/2 - title.get_width()/2, 24))

    play_outer = pygame.Rect(top_left_x - 12, top_left_y - 12, play_width + 24, play_height + 24)
    draw_panel(surface, play_outer)
    pygame.draw.rect(surface, GRID_BG, (top_left_x, top_left_y, play_width, play_height))

    # GRID
    for i in range(row):
        for j in range(col):
            pygame.draw.rect(surface, grid[i][j],
                             (top_left_x + j * block_size,
                              top_left_y + i * block_size,
                              block_size, block_size), 0)
    draw_grid(surface)

    # SCORE PANEL
    panel_w = 200
    right_x = top_left_x + play_width + 20
    score_panel = pygame.Rect(right_x, top_left_y + 20, panel_w, 300)
    draw_panel(surface, score_panel)
    score_font = pygame.font.Font(fontpath, 26)
    label_score = score_font.render('SCORE', 1, TEXT_MUTED)
    value_score = score_font.render(str(score), 1, TEXT_PRIMARY)
    surface.blit(label_score, (score_panel.x + 18, score_panel.y + 18))
    surface.blit(value_score, (score_panel.x + 18, score_panel.y + 52))

    # NEXT
    if next_piece is not None:
        next_box = pygame.Rect(score_panel.x + 14, score_panel.y + 110,
                               score_panel.width - 28, 160)
        draw_panel(surface, next_box)
        draw_next_shape(next_piece, surface, box_rect=next_box)

    # HIGHSCORE PANEL
    left_x = top_left_x - panel_w - 20
    left_panel = pygame.Rect(left_x, top_left_y + 170, panel_w, 180)
    draw_panel(surface, left_panel)
    label_hi = score_font.render('HIGHSCORE', 1, TEXT_MUTED)
    value_hi = score_font.render(str(last_score), 1, TEXT_PRIMARY)
    surface.blit(label_hi, (left_panel.x + 18, left_panel.y + 18))
    surface.blit(value_hi, (left_panel.x + 18, left_panel.y + 52))

    user_text = "User: -"
    try:
        user = Web_Server.get_current_user()
        if isinstance(user, dict) and user.get("username"):
            user_text = f"User: {user['username']}"
    except Exception:
        pass
    user_font = get_ui_font(20)
    user_label = user_font.render(user_text, 1, TEXT_MUTED)
    surface.blit(user_label, (left_panel.x + 18, left_panel.y + 96))

#tady to updatuje Score....

# Tady je zatim hloupy ukladac vysokeho skoree do txt - potreba udelat tak, at se uklada aktualni ID
#uzivatele + datum + nejvyssi skore + ja nwm co dalsiho
#po kazde hre se udela zapis do DB??? nebo budem updatovat dle ID a pricitat skore??














def update_score(new_score):
    """Aktualizuje soubor s highscore. Parametry:
    new_score (int) - novy score pro porovnani a zapis."""
    score = get_max_score()
    with open(filepath, 'w') as file:
        if new_score > score:
            file.write(str(new_score))
        else:
            file.write(str(score))


# V GUI je to videt jako high score....
def get_max_score():
    """Cte highscore ze souboru filepath.
    Navrat:
        int - hodnota highscore. (Predpoklada, ze soubor existuje a ma cislo)."""
    try:
        with open(filepath, 'r') as file:
            lines = file.readlines()        # reads all the lines and puts in a list
            return int(lines[0].strip())    # remove \n
    except Exception:
        return 0










def shutdown_auth_server():
    """Ukonci vsechny podprocesy flask/python a ukonci proces.
    Neni parametrizovana. Vola psutil pokud je dostupny, jinak vynuti exit."""
    try:
        import psutil
        current = psutil.Process(os.getpid())
        for child in current.children(recursive=True):
            if "flask" in child.name().lower() or "python" in child.name().lower():
                child.terminate()
        time.sleep(0.3)
    except Exception:
        pass
    finally:
        os._exit(0)



def main(window):
    """Hlavni herni smycka, spousti hru.
    Parametry:
        window (pygame.Surface) - otevrene okno pro vykreslovani.
    Funkce bezi dokud hrac neukonci hru nebo neprohra."""
    locked_positions = {}
    current_piece, next_piece = get_shape(), get_shape()
    clock = pygame.time.Clock()
    fall_time, fall_speed, level_time = 0, 0.35, 0
    score, last_score = 0, get_max_score()
    lines_cleared = 0
    level = 1
    level_max = 1
    session_start = time.time()
    session_ended = False

    telemetry.send_async({"type": "game_session_start", "payload": {}})

    def end_session(reason: str) -> None:
        nonlocal session_ended
        if session_ended:
            return
        session_ended = True
        update_score(score)
        duration_s = max(0.0, time.time() - session_start)
        payload = {
            "duration_s": round(duration_s, 2),
            "score": score,
            "level_max": level_max,
            "lines": lines_cleared,
            "reason_end": reason,
        }
        telemetry.send_async({"type": "game_session_end", "payload": payload})

    while True:
        grid = create_grid(locked_positions)
        fall_time += clock.get_rawtime()
        level_time += clock.get_rawtime()
        clock.tick()

        if level_time/1000 > 5:
            level_time = 0
            if fall_speed > 0.15:
                fall_speed -= 0.005
                level += 1
                level_max = max(level_max, level)

        if fall_time/1000 > fall_speed:
            fall_time = 0
            current_piece.y += 1
            if not valid_space(current_piece, grid) and current_piece.y > 0:
                current_piece.y -= 1
                change_piece = True
            else:
                change_piece = False
        else:
            change_piece = False

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                end_session("quit")
                return "quit"
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    end_session("quit")
                    return "quit"
                if event.key == pygame.K_LEFT:
                    current_piece.x -= 1
                    if not valid_space(current_piece, grid):
                        current_piece.x += 1
                elif event.key == pygame.K_RIGHT:
                    current_piece.x += 1
                    if not valid_space(current_piece, grid):
                        current_piece.x -= 1
                elif event.key == pygame.K_DOWN:
                    current_piece.y += 1
                    if not valid_space(current_piece, grid):
                        current_piece.y -= 1
                elif event.key == pygame.K_UP:
                    current_piece.rotation = (current_piece.rotation + 1) % len(current_piece.shape)
                    if not valid_space(current_piece, grid):
                        current_piece.rotation = (current_piece.rotation - 1) % len(current_piece.shape)

        for x, y in convert_shape_format(current_piece):
            if y >= 0:
                grid[y][x] = current_piece.color

        if change_piece:
            for pos in convert_shape_format(current_piece):
                locked_positions[pos] = current_piece.color
            current_piece = next_piece
            next_piece = get_shape()
            cleared = clear_rows(grid, locked_positions)
            lines_cleared += cleared
            score += cleared * 10
            if score > last_score:
                last_score = score

        draw_window(window, grid, score, last_score, next_piece)
        pygame.display.update()

        if check_lost(locked_positions):
            end_session("gameover")
            result = game_over_screen(window, score, last_score)
            return result

    if not session_ended:
        end_session("unknown")

    return "menu"


def game_over_screen(window, score, highscore):
    clock = pygame.time.Clock()
    title_font = pygame.font.Font(fontpath_mario, 52)
    body_font = get_ui_font(26)
    small_font = get_ui_font(20)

    panel_w, panel_h = 440, 260
    panel_x = s_width/2 - panel_w/2
    panel_y = s_height/2 - panel_h/2
    panel = pygame.Rect(panel_x, panel_y, panel_w, panel_h)
    retry_rect = pygame.Rect(panel_x + 24, panel_y + 170, 180, 52)
    menu_rect = pygame.Rect(panel_x + 236, panel_y + 170, 180, 52)

    while True:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                return "quit"
            if event.type == pygame.KEYDOWN:
                if event.key in (pygame.K_RETURN, pygame.K_SPACE):
                    return "retry"
                if event.key == pygame.K_ESCAPE:
                    return "menu"
            if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                if retry_rect.collidepoint(event.pos):
                    return "retry"
                if menu_rect.collidepoint(event.pos):
                    return "menu"

        draw_background(window)
        draw_panel(window, panel)

        title = title_font.render("GAME OVER", True, TEXT_PRIMARY)
        window.blit(title, (panel_x + panel_w/2 - title.get_width()/2, panel_y + 24))

        score_label = body_font.render(f"Score: {score}", True, TEXT_MUTED)
        hi_label = body_font.render(f"Highscore: {highscore}", True, TEXT_MUTED)
        window.blit(score_label, (panel_x + 36, panel_y + 90))
        window.blit(hi_label, (panel_x + 36, panel_y + 120))

        draw_button(window, retry_rect, "Play Again", body_font, ACCENT, (5, 12, 18))
        draw_button(window, menu_rect, "Back to Menu", body_font, (80, 90, 120), TEXT_PRIMARY)

        hint = small_font.render("Enter = Play Again, Esc = Menu", True, TEXT_MUTED)
        window.blit(hint, (panel_x + panel_w/2 - hint.get_width()/2, panel_y + panel_h - 32))

        pygame.display.update()
        clock.tick(30)






def main_menu(window, telemetry_cfg=None):
    """Zobrazi hlavni menu a ceka na stisk klavesy pro start hry.
    Parametry:
        window (pygame.Surface) - cilove okno."""
    run = True

    player_data = load_player_data()
    consent = bool(player_data.get("telemetry_consent", False))
    if telemetry_cfg is not None:
        telemetry_cfg["enabled"] = consent

    def run_game_loop():
        result = main(window)
        while result == "retry":
            result = main(window)
        return result

    def set_consent(value: bool):
        nonlocal consent
        previous = consent
        consent = bool(value)
        player_data["telemetry_consent"] = consent
        save_player_data(player_data)
        if telemetry_cfg is not None:
            telemetry_cfg["enabled"] = consent
            telemetry.init(telemetry_cfg)
            if consent and not previous:
                telemetry.send_async({"type": "app_start", "payload": {}})

    while run:
        draw_background(window)

        title_font = pygame.font.Font(fontpath_mario, 70)
        title_font.set_bold(True)
        title = title_font.render("TETRIS", True, TEXT_PRIMARY)
        window.blit(title, (s_width/2 - title.get_width()/2, 120))

        question = get_ui_font(28).render("Start game?", True, TEXT_PRIMARY)
        window.blit(question, (s_width/2 - question.get_width()/2, 230))

        hint = get_ui_font(22).render("Press Enter to play, Esc to exit", True, TEXT_MUTED)
        window.blit(hint, (s_width/2 - hint.get_width()/2, 280))

        consent_text = get_ui_font(22).render("Uchovavat anonymni technicka data?", True, TEXT_PRIMARY)
        window.blit(consent_text, (s_width/2 - consent_text.get_width()/2, 330))
        yes_rect = pygame.Rect(s_width/2 - 130, 370, 100, 38)
        no_rect = pygame.Rect(s_width/2 + 30, 370, 100, 38)
        yes_color = ACCENT if consent else (80, 90, 120)
        no_color = (80, 90, 120) if consent else ACCENT
        draw_button(window, yes_rect, "Ano", get_ui_font(20), yes_color, (5, 12, 18))
        draw_button(window, no_rect, "Ne", get_ui_font(20), no_color, (5, 12, 18))

        pygame.display.update()
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                shutdown_auth_server()
                run = False
            elif event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    shutdown_auth_server()
                    run = False
                elif event.key == pygame.K_y:
                    set_consent(True)
                elif event.key == pygame.K_n:
                    set_consent(False)
                else:
                    result = run_game_loop()
                    if result == "quit":
                        shutdown_auth_server()
                        run = False
            elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                if yes_rect.collidepoint(event.pos):
                    set_consent(True)
                    continue
                if no_rect.collidepoint(event.pos):
                    set_consent(False)
                    continue
                result = run_game_loop()
                if result == "quit":
                    shutdown_auth_server()
                    run = False
    pygame.quit()


def get_ui_font(size):
    """Vrati pygame font pro UI texty.
    Parametry:
        size (int) - pozadovana velikost pismene.
    Navrat:
        pygame.font.Font."""
    import pygame
    try:

        return pygame.font.SysFont("DejaVu Sans", size)
    except:
        return pygame.font.SysFont(None, size)









def login_gate_screen(window, port, telemetry_cfg=None):
    """Zobrazi cekaeci obrazovku pred prihlasenim.
    Parametry:
        window (pygame.Surface) - cilove okno
        port (int) - port, kde bezi auth server, aby uzivatel vedel URL
        telemetry_cfg (dict) - konfigurace telemetrie, pokud je k dispozici
    Navrat:
        bool - True pokud je uzivatel prihlasen (is_authenticated vrati True), False pri Esc nebo Exit."""
    clock = pygame.time.Clock()
    dots, tick = "", 0

    # UI font â€“ NE z arcade.ttf
    font = get_ui_font(30)
    small = get_ui_font(24)

    panel = pygame.Rect(60, 90, s_width - 120, 480)

    # Exit button rect
    btn_w, btn_h = 170, 46
    btn_x = panel.x + panel.width - btn_w - 24
    btn_y = panel.y + panel.height - btn_h - 20
    btn_rect = pygame.Rect(btn_x, btn_y, btn_w, btn_h)

    open_rect = pygame.Rect(panel.x + 30, panel.y + 320, 260, 52)

    player_data = load_player_data()
    consent = bool(player_data.get("telemetry_consent", False))
    if telemetry_cfg is not None:
        telemetry_cfg["enabled"] = consent
    consent_text_1 = "Chcete uchovavat anonymni technicka data"
    consent_text_2 = "pro zlepseni hry?"
    consent_x = panel.x + 30
    consent_y = panel.y + 220
    consent_label_1 = small.render(consent_text_1, True, TEXT_PRIMARY)
    consent_label_2 = small.render(consent_text_2, True, TEXT_PRIMARY)
    consent_label_pos_1 = (consent_x + 34, consent_y)
    consent_label_pos_2 = (consent_x + 34, consent_y + 26)
    consent_hitbox = pygame.Rect(panel.x + 16, consent_y - 6, panel.width - 32, 60)
    yes_rect = pygame.Rect(panel.x + 30, consent_y + 58, 110, 40)
    no_rect = pygame.Rect(panel.x + 150, consent_y + 58, 110, 40)

    line1 = "Please log in via your browser to start the game."
    line2 = f"If no window opened: http://127.0.0.1:{port}/login"

    while True:
        def set_consent(value: bool):
            nonlocal consent
            value = bool(value)
            if consent == value:
                return
            previous = consent
            consent = value
            player_data["telemetry_consent"] = consent
            save_player_data(player_data)
            if telemetry_cfg is not None:
                telemetry_cfg["enabled"] = consent
                telemetry.init(telemetry_cfg)
                if consent and not previous:
                    telemetry.send_async({"type": "app_start", "payload": {}})

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                return False
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    return False
                if event.key == pygame.K_y:
                    set_consent(True)
                if event.key == pygame.K_n:
                    set_consent(False)
            if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                if btn_rect.collidepoint(event.pos):
                    return False
                if open_rect.collidepoint(event.pos):
                    webbrowser.open(f"http://127.0.0.1:{port}/login", new=1, autoraise=True)
                if yes_rect.collidepoint(event.pos):
                    set_consent(True)
                if no_rect.collidepoint(event.pos):
                    set_consent(False)

        draw_background(window)
        draw_panel(window, panel)

        # texts
        t1 = font.render(line1, True, TEXT_PRIMARY)
        t2 = small.render(line2, True, TEXT_MUTED)

        tick += clock.tick(30)
        if tick > 300:
            dots = "." * ((len(dots) % 3) + 1)
            tick = 0
        t3 = font.render("Waiting for login" + dots, True, ACCENT)

        # draw
        window.blit(t1, (panel.x + 30, panel.y + 40))
        window.blit(t2, (panel.x + 30, panel.y + 90))
        window.blit(t3, (panel.x + 30, panel.y + 150))

        pygame.draw.rect(window, PANEL_BG, consent_hitbox, border_radius=8)
        pygame.draw.rect(window, PANEL_BORDER, consent_hitbox, 1, border_radius=8)
        window.blit(consent_label_1, consent_label_pos_1)
        window.blit(consent_label_2, consent_label_pos_2)

        yes_color = ACCENT if consent else (80, 90, 120)
        no_color = (80, 90, 120) if consent else ACCENT
        draw_button(window, yes_rect, "Ano", small, yes_color, (5, 12, 18))
        draw_button(window, no_rect, "Ne", small, no_color, (5, 12, 18))

        draw_button(window, open_rect, "Open Login Page", small, ACCENT, (5, 12, 18))

        # Exit button
        draw_button(window, btn_rect, "Exit (Esc)", font, (180, 50, 50), TEXT_PRIMARY)

        pygame.display.update()

        if Web_Server.is_authenticated():
            return True








