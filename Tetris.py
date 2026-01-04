import random
import pygame
import Web_Server
import time, json, os, hmac, hashlib, secrets, glob
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


def _get_current_user_id():
    try:
        user = Web_Server.get_current_user()
    except Exception:
        return None
    if isinstance(user, dict):
        return user.get("id")
    if isinstance(user, (list, tuple)) and user:
        return user[0]
    return None

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
    r = g = b = 0
    grid_color = (r, g, b)

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
def draw_next_shape(piece, surface):
    """Vykresli nasledujici tetromino v panelu.
    Parametry:
        piece (Piece) - nasledujici polozka
        surface (pygame.Surface) - cilovy povrch"""
    font = pygame.font.Font(fontpath, 30)
    label = font.render('Next shape', 1, (255, 255, 255))

    start_x = top_left_x + play_width + 50
    start_y = top_left_y + (play_height / 2 - 100)

    shape_format = piece.shape[piece.rotation % len(piece.shape)]

    for i, line in enumerate(shape_format):
        row = list(line)
        for j, column in enumerate(row):
            if column == '0':
                pygame.draw.rect(surface, piece.color, (start_x + j*block_size, start_y + i*block_size, block_size, block_size), 0)

    surface.blit(label, (start_x, start_y - 30))

    # pygame.display.update()


# draws the content of the window
def draw_window(surface, grid, score=0, last_score=0):
    """Vykresli cele herni okno vÄŤetnÄ› score a highscore.
    Parametry:
        surface (pygame.Surface) - cilovy povrch
        grid (list) - aktualni grid
        score (int) - aktualni score
        last_score (int) - highscore"""
    surface.fill((0, 0, 0))  # fill the surface with black

    pygame.font.init()  # initialise font

    # TITULEK
    font = pygame.font.Font(fontpath_mario, 65)
    font.set_bold(True)  # <-- takhle se to dela
    label = font.render('TETRIS', 1, (255, 255, 255))
    surface.blit(label, ((top_left_x + play_width / 2) - (label.get_width() / 2), 30))

    # SCORE
    font = pygame.font.Font(fontpath, 30)
    label = font.render('SCORE   ' + str(score), 1, (255, 255, 255))
    start_x = top_left_x + play_width + 50
    start_y = top_left_y + (play_height / 2 - 100)
    surface.blit(label, (start_x, start_y + 200))

    # HIGHSCORE
    label_hi = font.render('HIGHSCORE   ' + str(last_score), 1, (255, 255, 255))
    start_x_hi = top_left_x - 240
    start_y_hi = top_left_y + 200
    surface.blit(label_hi, (start_x_hi + 20, start_y_hi + 200))

    # GRID
    for i in range(row):
        for j in range(col):
            pygame.draw.rect(surface, grid[i][j],
                             (top_left_x + j * block_size,
                              top_left_y + i * block_size,
                              block_size, block_size), 0)

    draw_grid(surface)

    # BORDER
    border_color = (255, 255, 255)
    pygame.draw.rect(surface, border_color,
                     (top_left_x, top_left_y, play_width, play_height), 4)









#tady to updatuje Score....

# Tady je zatim hloupy ukladac vysokeho skoree do txt - potreba udelat tak, at se uklada aktualni ID
#uzivatele + datum + nejvyssi skore + ja nwm co dalsiho
#po kazde hre se udela zapis do DB??? nebo budem updatovat dle ID a pricitat skore??














def update_score(new_score):
    """Aktualizuje soubor s highscore. Parametry:
    new_score (int) - novy score pro porovnani a zapis."""
    user_id = _get_current_user_id()
    if user_id:
        Web_Server.update_user_highscore(user_id, new_score)
        return

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
    user_id = _get_current_user_id()
    if user_id:
        try:
            return Web_Server.get_user_highscore(user_id)
        except Exception:
            pass
    with open(filepath, 'r') as file:
        lines = file.readlines()        # reads all the lines and puts in a list
        score = int(lines[0].strip())   # remove \n

    return score










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
    run = True
    exit_game = False
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
        duration_s = max(0.0, time.time() - session_start)
        payload = {
            "duration_s": round(duration_s, 2),
            "score": score,
            "level_max": level_max,
            "lines": lines_cleared,
            "reason_end": reason,
        }
        telemetry.send_async({"type": "game_session_end", "payload": payload})

    while run:
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
                exit_game = True
                run = False
                break
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    end_session("quit")
                    exit_game = True
                    run = False
                    break
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

        if not run:
            break

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
            update_score(score)
            last_score = max(last_score, score)

        draw_window(window, grid, score, last_score)
        draw_next_shape(next_piece, window)
        pygame.display.update()

        if check_lost(locked_positions):
            draw_text_middle('You Lost', 40, (255,255,255), window)
            pygame.display.update()
            time.sleep(2)
            end_session("gameover")
            run = False

    if not session_ended:
        end_session("unknown")

    return "quit" if exit_game else "menu"






def main_menu(window):
    """Zobrazi hlavni menu a ceka na stisk klavesy pro start hry.
    Parametry:
        window (pygame.Surface) - cilove okno."""
    run = True
    while run:
        draw_text_middle('Press any key to begin', 50, (255,255,255), window)
        pygame.display.update()
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                shutdown_auth_server()
                run = False
            elif event.type == pygame.KEYDOWN:
                result = main(window)
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

    # Exit button rect
    btn_w, btn_h = 170, 46
    btn_x = top_left_x + play_width/2 - btn_w/2
    btn_y = top_left_y + play_height - 80
    btn_rect = pygame.Rect(btn_x, btn_y, btn_w, btn_h)

    player_data = load_player_data()
    consent = bool(player_data.get("telemetry_consent", False))
    if telemetry_cfg is not None:
        telemetry_cfg["enabled"] = consent
    consent_text = "Chci posilat anonymni technicka data pro zlepseni hry."
    consent_x = top_left_x - 160
    consent_y = top_left_y + play_height - 150
    consent_box = pygame.Rect(consent_x, consent_y, 22, 22)
    consent_label = small.render(consent_text, True, (200, 200, 200))
    consent_label_pos = (consent_x + 34, consent_y - 2)
    consent_label_rect = consent_label.get_rect(topleft=consent_label_pos)
    hit_width = max(consent_label_rect.width + 40, 420)
    consent_hitbox = pygame.Rect(consent_x - 6, consent_y - 6, hit_width + 12, 34)

    line1 = "Please log in via your browser to start the game."
    line2 = f"If no window opened: http://127.0.0.1:{port}/login"

    while True:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                return False
            if event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
                return False
            if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                if btn_rect.collidepoint(event.pos):
                    return False
                if consent_hitbox.collidepoint(event.pos):
                    previous = consent
                    consent = not consent
                    player_data["telemetry_consent"] = consent
                    save_player_data(player_data)
                    if telemetry_cfg is not None:
                        telemetry_cfg["enabled"] = consent
                        telemetry.init(telemetry_cfg)
                        if consent and not previous:
                            telemetry.send_async({"type": "app_start", "payload": {}})

        window.fill((0, 0, 0))

        # texts
        t1 = font.render(line1, True, (255, 255, 255))
        t2 = small.render(line2, True, (200, 200, 200))

        tick += clock.tick(30)
        if tick > 300:
            dots = "." * ((len(dots) % 3) + 1)
            tick = 0
        t3 = font.render("Waiting for login" + dots, True, (255, 255, 0))

        # draw
        window.blit(t1, (top_left_x - 160, top_left_y + 150))
        window.blit(t2, (top_left_x - 210, top_left_y + 200))
        window.blit(t3, (top_left_x - 50, top_left_y + 260))

        pygame.draw.rect(window, (200, 200, 200), consent_box, 2)
        if consent:
            pygame.draw.rect(window, (60, 200, 60), consent_box.inflate(-6, -6))
        window.blit(consent_label, consent_label_pos)

        # Exit button
        pygame.draw.rect(window, (180, 50, 50), btn_rect, border_radius=8)
        bl = font.render("Exit (Esc)", True, (255, 255, 255))
        window.blit(bl, (btn_x + (btn_w - bl.get_width())/2,
                         btn_y + (btn_h - bl.get_height())/2))

        pygame.display.update()

        if Web_Server.is_authenticated():
            return True





