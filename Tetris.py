import random
import pygame
import time, os, requests
#import api_client  # náš nový modul pro komunikaci s XAMPP API

pygame.font.init()

# --- Globalní proměnné ---
col, row = 10, 20
s_width, s_height = 800, 750
play_width, play_height = 300, 600
block_size = 30
top_left_x = (s_width - play_width) // 2
top_left_y = s_height - play_height - 50

filepath = os.path.join(os.path.dirname(__file__), './highscore.txt')
fontpath = os.path.join(os.path.dirname(__file__), 'arcade.TTF')
fontpath_mario = os.path.join(os.path.dirname(__file__), './mario.ttf')

# --- Tvarové formáty ---
S = [['.....','.....','..00.','.00..','.....'],
     ['.....','..0..','..00.','...0.','.....']]
Z = [['.....','.....','.00..','..00.','.....'],
     ['.....','..0..','.00..','.0...','.....']]
I = [['.....','..0..','..0..','..0..','..0..'],
     ['.....','0000.','.....','.....','.....']]
O = [['.....','.....','.00..','.00..','.....']]
J = [['.....','.0...','.000.','.....','.....'],
     ['.....','..00.','..0..','..0..','.....'],
     ['.....','.....','.000.','...0.','.....'],
     ['.....','..0..','..0..','.00..','.....']]
L = [['.....','...0.','.000.','.....','.....'],
     ['.....','..0..','..0..','..00.','.....'],
     ['.....','.....','.000.','.0...','.....'],
     ['.....','.00..','..0..','..0..','.....']]
T = [['.....','..0..','.000.','.....','.....'],
     ['.....','..0..','..00.','..0..','.....'],
     ['.....','.....','.000.','..0..','.....'],
     ['.....','..0..','.00..','..0..','.....']]

shapes = [S, Z, I, O, J, L, T]
shape_colors = [(0,255,0),(255,0,0),(0,255,255),(255,255,0),(255,165,0),(0,0,255),(128,0,128)]

class Piece(object):
    def __init__(self, x, y, shape):
        self.x, self.y, self.shape = x, y, shape
        self.color = shape_colors[shapes.index(shape)]
        self.rotation = 0

def create_grid(locked_pos={}):
    grid = [[(0,0,0) for _ in range(col)] for _ in range(row)]
    for y in range(row):
        for x in range(col):
            if (x, y) in locked_pos:
                grid[y][x] = locked_pos[(x,y)]
    return grid

def convert_shape_format(piece):
    positions = []
    shape_format = piece.shape[piece.rotation % len(piece.shape)]
    for i, line in enumerate(shape_format):
        for j, column in enumerate(line):
            if column == '0':
                positions.append((piece.x + j - 2, piece.y + i - 4))
    return positions

def valid_space(piece, grid):
    accepted_pos = [(x, y) for y in range(row) for x in range(col) if grid[y][x] == (0,0,0)]
    for pos in convert_shape_format(piece):
        if pos not in accepted_pos and pos[1] >= 0:
            return False
    return True

def check_lost(positions):
    return any(y < 1 for _, y in positions)

def get_shape():
    return Piece(5, 0, random.choice(shapes))

def draw_text_middle(text, size, color, surface, offset_y=0):
    font = pygame.font.Font(fontpath, size)
    label = font.render(text, True, color)
    surface.blit(label, (top_left_x + play_width/2 - label.get_width()/2,
                         top_left_y + play_height/2 - label.get_height()/2 + offset_y))

def draw_grid(surface):
    for i in range(row):
        pygame.draw.line(surface, (50,50,50), (top_left_x, top_left_y + i*block_size),
                         (top_left_x + play_width, top_left_y + i*block_size))
    for j in range(col):
        pygame.draw.line(surface, (50,50,50), (top_left_x + j*block_size, top_left_y),
                         (top_left_x + j*block_size, top_left_y + play_height))

def clear_rows(grid, locked):
    inc = 0
    for i in range(len(grid)-1, -1, -1):
        if (0,0,0) not in grid[i]:
            inc += 1
            for j in range(col):
                try: del locked[(j,i)]
                except: pass
    if inc > 0:
        for key in sorted(list(locked), key=lambda k: k[1])[::-1]:
            x, y = key
            if y < i:
                locked[(x, y + inc)] = locked.pop(key)
    return inc

def draw_next_shape(piece, surface):
    font = pygame.font.Font(fontpath, 30)
    label = font.render('Next shape', True, (255,255,255))
    sx, sy = top_left_x + play_width + 50, top_left_y + play_height/2 - 100
    shape_format = piece.shape[piece.rotation % len(piece.shape)]
    for i, line in enumerate(shape_format):
        for j, column in enumerate(line):
            if column == '0':
                pygame.draw.rect(surface, piece.color, (sx + j*block_size, sy + i*block_size, block_size, block_size), 0)
    surface.blit(label, (sx, sy - 30))

def draw_window(surface, grid, score=0, last_score=0):
    surface.fill((0,0,0))
    title_font = pygame.font.Font(fontpath_mario, 65)
    label = title_font.render('TETRIS', True, (255,255,255))
    surface.blit(label, ((top_left_x + play_width/2 - label.get_width()/2), 30))
    score_font = pygame.font.Font(fontpath, 30)
    surface.blit(score_font.render(f'SCORE {score}', True, (255,255,255)), (top_left_x + play_width + 50, top_left_y + 300))
    surface.blit(score_font.render(f'HIGHSCORE {last_score}', True, (255,255,255)), (top_left_x - 200, top_left_y + 400))
    for i in range(row):
        for j in range(col):
            pygame.draw.rect(surface, grid[i][j], (top_left_x + j*block_size, top_left_y + i*block_size, block_size, block_size), 0)
    draw_grid(surface)
    pygame.draw.rect(surface, (255,255,255), (top_left_x, top_left_y, play_width, play_height), 4)

def main(window, username, last_score=0):
    locked_positions = {}
    current_piece, next_piece = get_shape(), get_shape()
    clock = pygame.time.Clock()
    fall_time, fall_speed, level_time = 0, 0.35, 0
    score = 0
    run = True

    while run:
        grid = create_grid(locked_positions)
        fall_time += clock.get_rawtime()
        level_time += clock.get_rawtime()
        clock.tick()

        if level_time/1000 > 5:
            level_time = 0
            fall_speed = max(0.15, fall_speed - 0.005)

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
                run = False
                pygame.quit()
                return
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    run = False
                    pygame.quit()
                    return
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
            if y >= 0: grid[y][x] = current_piece.color

        if change_piece:
            for pos in convert_shape_format(current_piece):
                locked_positions[pos] = current_piece.color
            current_piece, next_piece = next_piece, get_shape()
            score += clear_rows(grid, locked_positions) * 10

        draw_window(window, grid, score, last_score)
        draw_next_shape(next_piece, window)
        pygame.display.update()

        if check_lost(locked_positions):
            draw_text_middle('You Lost', 40, (255,255,255), window)
            pygame.display.update()
            time.sleep(2)
            try:
                api_client.update_highscore(username, score)
            except Exception as e:
                print("Chyba při odesílání highscore:", e)
            run = False

    pygame.quit()

def main_menu(window):
    username, password = "", ""
    font_title = pygame.font.Font(fontpath_mario, 48)
    font_label = pygame.font.Font(fontpath, 32)
    font_input = pygame.font.SysFont("DejaVu Sans Mono", 30)   # <-- moderní font pro inputy
    font_msg = pygame.font.Font(fontpath, 26)
    clock = pygame.time.Clock()
    active_field = "username"
    message = ""
    message_color = (255, 100, 100)
    run = True

    while run:
        window.fill((0, 0, 0))

        # --- Titulek ---
        title = font_title.render("LOGIN TO PLAY TETRIS", True, (255, 255, 255))
        window.blit(title, (s_width/2 - title.get_width()/2, 120))

        # --- Inputy ---
        ux, uy = s_width/2 - 200, 250
        py = uy + 80
        label_user = font_label.render("USERNAME", True, (255, 255, 0))
        label_pass = font_label.render("PASSWORD", True, (255, 255, 0))

        # Rámeček pole
        pygame.draw.rect(window, (60, 60, 60), (ux, uy+35, 400, 40), 0, border_radius=6)
        pygame.draw.rect(window, (60, 60, 60), (ux, py+35, 400, 40), 0, border_radius=6)
        border_color_u = (255, 255, 0) if active_field == "username" else (100, 100, 100)
        border_color_p = (255, 255, 0) if active_field == "password" else (100, 100, 100)
        pygame.draw.rect(window, border_color_u, (ux, uy+35, 400, 40), 2, border_radius=6)
        pygame.draw.rect(window, border_color_p, (ux, py+35, 400, 40), 2, border_radius=6)

        # Texty v polích (moderní font)
        u_display = username + ("_" if active_field == "username" and pygame.time.get_ticks() % 1000 < 500 else "")
        # • místo * kvůli pixel fontům
        p_display = "•" * len(password) + ("_" if active_field == "password" and pygame.time.get_ticks() % 1000 < 500 else "")
        text_user = font_input.render(u_display, True, (255, 255, 255))
        text_pass = font_input.render(p_display, True, (255, 255, 255))

        # Render
        window.blit(label_user, (ux, uy))
        window.blit(text_user, (ux + 10, uy + 40))
        window.blit(label_pass, (ux, py))
        window.blit(text_pass, (ux + 10, py + 40))

        # --- Zpráva ---
        msg = font_msg.render(message, True, message_color)
        window.blit(msg, (s_width/2 - msg.get_width()/2, py + 100))

        pygame.display.update()

        # --- Eventy ---
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                run = False
                pygame.quit()
                return
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    run = False
                    pygame.quit()
                    return
                elif event.key == pygame.K_TAB:
                    active_field = "password" if active_field == "username" else "username"
                elif event.key == pygame.K_BACKSPACE:
                    if active_field == "username":
                        username = username[:-1]
                    else:
                        password = password[:-1]
                elif event.key == pygame.K_RETURN:
                    try:
                        res = api_client.login(username, password)
                        if res.get("ok"):
                            message = "LOGIN SUCCESSFUL"
                            message_color = (0, 255, 0)
                            pygame.display.update()
                            time.sleep(0.8)
                            highscore = res.get("highscore", 0)
                            main(window, username, highscore)
                            return
                        else:
                            message = res.get("error", "Login failed.")
                            message_color = (255, 80, 80)
                    except Exception:
                        message = "SERVER UNREACHABLE"
                        message_color = (255, 80, 80)
                else:
                    if active_field == "username":
                        if len(username) < 20 and event.unicode.isprintable():
                            username += event.unicode
                    else:
                        if len(password) < 20 and event.unicode.isprintable():
                            password += event.unicode
        clock.tick(30)
