import os
import pygame
import thorpy as tp
from book import Book
from library import Library

# --- Configurações ---
MAX_LIBS = 9
MAX_BOOKS = 10
SCREEN_WIDTH, SCREEN_HEIGHT = 1200, 700

def list_input_files(directory="../input"):
    if not os.path.exists(directory):
        return []
    return [f for f in os.listdir(directory) if os.path.isfile(os.path.join(directory, f))]

def read_input_file(filepath):
    data = []
    with open(filepath, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                data.append([int(x) for x in line.split()])
    return data

def parse_input(conteudo):
    num_books, num_libraries, num_days = conteudo[0]
    books = [Book(i, score) for i, score in enumerate(conteudo[1])]
    
    libraries = []
    line_index = 2
    for lib_id in range(num_libraries):
        num_books_in_lib, signup_days, books_per_day = conteudo[line_index]
        lib_books_ids = conteudo[line_index + 1]
        lib_books = [books[i] for i in lib_books_ids]
        libraries.append(Library(lib_id, lib_books, signup_days, books_per_day))
        line_index += 2
    return books, libraries

# --- Inicializar Pygame e Thorpy ---
pygame.init()
screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT))
pygame.display.set_caption("Library Viewer")
tp.init(screen, tp.theme_game2)

# --- Estado global ---
selected_libraries = []

def choose_file(index):
    global selected_libraries
    caminho = os.path.join("../input", files[index])
    conteudo = read_input_file(caminho)
    _, selected_libraries = parse_input(conteudo)

# --- Criar botões ao lado do título ---
files = list_input_files("../input")
if not files:
    files = ["No files found"]

buttons = []
x = 200  # posição inicial dos botões (à direita do título)
y = 20

for i, f in enumerate(files):
    btn = tp.Button(f)
    btn.user_data = i
    btn.set_topleft(x, y)
    x += btn.rect.size[0] + 10  
    buttons.append(btn)

def draw_libraries():
    screen.fill((255, 255, 255))
    # Titulo
    
    font_title = pygame.font.SysFont("Georgia", 28)
    title = font_title.render("Libraries:", True, (0, 0, 0))
    screen.blit(title, (50, 20))

    x_start, y_start = 50, 70
    x, y = x_start, y_start
    col_width = 350
    row_height = 120
    cols = 3

    for idx, lib in enumerate(selected_libraries[:MAX_LIBS]):
        # Card da biblioteca
        pygame.draw.rect(screen, (200, 200, 255), (x, y, col_width - 10, row_height))
        pygame.draw.rect(screen, (0, 0, 0), (x, y, col_width - 10, row_height), 2)

        # Texto da biblioteca
        font = pygame.font.SysFont("Georgia", 20)
        text1 = font.render(f"Lib {lib.id} | signup={lib.signup_days} | rate={lib.books_per_day}", True, (0, 0, 0))
        screen.blit(text1, (x + 5, y + 5))

        # Livros 
        books_to_show = lib.books[:MAX_BOOKS]
        for i, b in enumerate(books_to_show):
            bx = x + 5 + (i % 5) * 65 
            by = y + 35 + (i // 5) * 30
            pygame.draw.rect(screen, (255, 200, 200), (bx, by, 60, 25))
            book_text = font.render(str(b.id), True, (0, 0, 0))
            screen.blit(book_text, (bx + 5, by + 2))

        # Próximo rect
        if (idx + 1) % cols == 0:
            x = x_start
            y += row_height + 10
        else:
            x += col_width

clock = pygame.time.Clock()
running = True

while running:
    clock.tick(60)
    events = pygame.event.get()
    mouse_rel = pygame.mouse.get_rel()

    for event in events:
        if event.type == pygame.QUIT:
            running = False

        if event.type == pygame.MOUSEBUTTONDOWN:
            mouse_pos = event.pos
            for btn in buttons:
                if btn.get_rect().collidepoint(mouse_pos):
                    choose_file(btn.user_data)

    draw_libraries()

    for btn in buttons:
        btn.draw()

    pygame.display.flip()

pygame.quit()