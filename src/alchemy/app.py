"""Pygame presentation and input."""
import argparse
import os
from pathlib import Path

os.environ.setdefault('PYGAME_HIDE_SUPPORT_PROMPT', '1')
import pygame
from .board import Game, SIZE, KINDS
from .resources import load_symbols, NAMES
from .audio import Audio

WIDTH, HEIGHT = 1040, 780
LEFT, TOP, TILE = 48, 154, 70
BG = (15, 24, 30)
TEXT = (241, 229, 203)
MUTED = (156, 173, 174)
GOLD = (223, 181, 103)
COLORS = [(107, 54, 45), (38, 80, 103), (73, 89, 77), (85, 68, 104), (110, 88, 42)]
assert len(NAMES) == len(COLORS) == KINDS


def parse_args():
    parser = argparse.ArgumentParser(description='Alchemy: a match-four puzzle')
    parser.add_argument('--seed', type=int, help='Reproducible starting board')
    parser.add_argument('--smoke-test', action='store_true', help='Render a frame and exit')
    parser.add_argument('--screenshot', type=Path, help='Save a frame (.png, .jpg, .bmp; defaults to .png)')
    parser.add_argument('--sound-dir', type=Path, help='Directory of optional WAV/OGG effects')
    parser.add_argument('--mute', action='store_true', help='Start with sound muted')
    parser.add_argument('--volume', type=float, default=0.6, help='Effect volume from 0 to 1')
    parser.add_argument('--assets-dir', type=Path, help='Custom symbol PNG directory')
    args = parser.parse_args()
    if not 0 <= args.volume <= 1:
        parser.error('--volume must be between 0 and 1')
    if args.screenshot:
        if not args.screenshot.suffix:
            args.screenshot = args.screenshot.with_suffix('.png')
        if args.screenshot.suffix.lower() not in ('.png', '.jpg', '.bmp'):
            parser.error('--screenshot requires .png, .jpg, or .bmp')
        if not args.screenshot.parent.is_dir() or args.screenshot.is_dir():
            parser.error('--screenshot requires an existing directory and a file path')
    return args


def viewport(size):
    scale = min(size[0] / WIDTH, size[1] / HEIGHT)
    width, height = max(1, round(WIDTH * scale)), max(1, round(HEIGHT * scale))
    return pygame.Rect((size[0]-width)//2, (size[1]-height)//2, width, height)


def logical_position(position, size):
    rect = viewport(size)
    if not rect.collidepoint(position):
        return (-1, -1)
    return ((position[0]-rect.x)*WIDTH/rect.width,
            (position[1]-rect.y)*HEIGHT/rect.height)


def main():
    args = parse_args()
    try:
        run(args)
    except (pygame.error, OSError, RuntimeError) as error:
        raise SystemExit(f'alchemy: {error}') from None
    finally:
        pygame.quit()


def run(args):
    pygame.init()
    audio = Audio(args.sound_dir, args.volume, args.mute)
    window = pygame.display.set_mode((WIDTH, HEIGHT), pygame.RESIZABLE)
    screen = pygame.Surface((WIDTH, HEIGHT))
    pygame.display.set_caption('Alchemy | The Fourfold Art')
    clock = pygame.time.Clock()
    fonts = {size: pygame.font.SysFont('dejavusans', size) for size in (14, 16, 19, 24, 38, 48)}
    symbols = load_symbols(args.assets_dir)
    game = Game(args.seed)
    selected = None
    hint = None
    next_resolve = 0
    running = True
    hint_button = pygame.Rect(662, 590, 142, 46)
    restart_button = pygame.Rect(818, 590, 164, 46)

    def text(value, pos, size=19, color=TEXT):
        screen.blit(fonts[size].render(str(value), True, color), pos)

    while running:
        now = pygame.time.get_ticks()
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
            elif event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    running = False
                elif event.key == pygame.K_m:
                    audio.toggle()
                elif event.key == pygame.K_r:
                    audio.play("restart")
                    game = Game(args.seed)
                    selected = hint = None
                elif event.key == pygame.K_h and not game.pending and game.moves:
                    hint = game.hint()
                    audio.play("hint")
            elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                pos = logical_position(event.pos, window.get_size())
                if restart_button.collidepoint(pos):
                    audio.play("restart")
                    game = Game(args.seed)
                    selected = hint = None
                elif hint_button.collidepoint(pos) and not game.pending and game.moves:
                    hint = game.hint()
                    audio.play("hint")
                elif not game.pending and game.moves:
                    x = int((pos[0] - LEFT) // TILE)
                    y = int((pos[1] - TOP) // TILE)
                    if 0 <= x < SIZE and 0 <= y < SIZE:
                        cell = (x, y)
                        hint = None
                        if selected == cell:
                            selected = None
                        elif selected is not None and abs(selected[0]-x) + abs(selected[1]-y) == 1:
                            if game.attempt(selected, cell):
                                audio.play("swap")
                                next_resolve = now + 350
                            else:
                                audio.play("invalid")
                            selected = None
                        else:
                            selected = cell
                            audio.play("select")
        if game.pending and now >= next_resolve:
            for sound_event in game.resolve():
                audio.play(sound_event)
            next_resolve = now + 350

        screen.fill(BG)
        pygame.draw.circle(screen, (21, 34, 40), (975, 60), 260, 1)
        pygame.draw.circle(screen, (21, 34, 40), (975, 60), 220, 1)
        text('A L C H E M Y', (48, 28), 38)
        text('T H E   F O U R F O L D   A R T', (50, 85), 14, GOLD)
        text('A little patience. A little transformation.', (662, 67), 16, MUTED)
        pygame.draw.line(screen, (57, 68, 68), (48, 125), (982, 125))
        for y, row in enumerate(game.grid):
            for x, value in enumerate(row):
                rect = pygame.Rect(LEFT+x*TILE+3, TOP+y*TILE+3, TILE-6, TILE-6)
                pygame.draw.rect(screen, COLORS[value], rect, border_radius=10)
                pygame.draw.rect(screen, (255, 226, 154) if (x,y) in game.pending else (104, 107, 99), rect, 1, border_radius=10)
                screen.blit(symbols[value], symbols[value].get_rect(center=rect.center))
                if selected == (x, y) or (hint and (x, y) in hint):
                    pygame.draw.rect(screen, GOLD, rect.inflate(4, 4), 3, border_radius=12)
                if (x,y) in game.pending:
                    overlay = pygame.Surface(rect.size, pygame.SRCALPHA)
                    overlay.fill((255, 234, 173, 95))
                    screen.blit(overlay, rect)

        text('YOUR EXPERIMENT', (662, 158), 14, GOLD)
        text(f'{game.score:,}', (658, 183), 48)
        text('POINTS', (664, 244), 14, MUTED)
        text(f'{game.moves:02d}', (855, 183), 48)
        text('MOVES LEFT', (857, 244), 14, MUTED)
        pygame.draw.line(screen, (57, 68, 68), (662, 282), (982, 282))
        text('The practice', (662, 305), 24)
        for i, line in enumerate(('Swap two neighboring symbols.', 'Align 4 or more in a row or column.', 'Cleared symbols make room for new ones.', 'Chain reactions multiply your points.', 'Cross two 4+ lines: +200 per plus.')):
            text(line, (662, 350+i*28), 14, MUTED)
        for i, symbol in enumerate(symbols):
            screen.blit(symbol, (663+i*65, 508))
        for button, label in ((hint_button, 'Hint  [H]'), (restart_button, 'New game  [R]')):
            pygame.draw.rect(screen, (35, 49, 55), button, border_radius=8)
            pygame.draw.rect(screen, (92, 105, 103), button, 1, border_radius=8)
            screen.blit(fonts[16].render(label, True, TEXT), fonts[16].render(label, True, TEXT).get_rect(center=button.center))
        if game.last_reaction:
            reaction = game.last_reaction
            text(f"Reaction +{reaction['total']}  (x{reaction['multiplier']})", (662, 645), 19, GOLD)
            text(f"Base {reaction['base']} + long lines {reaction['length']} + plus {reaction['plus']}", (662, 675), 14, MUTED)
        text(f'Sound: {"off" if audio.muted else "on"}  [M]   /   ESC to quit', (662, 710), 14, MUTED)
        text(game.message, (48, 735), 16, GOLD)

        if game.moves == 0 and not game.pending:
            shade = pygame.Surface((SIZE*TILE, SIZE*TILE), pygame.SRCALPHA)
            shade.fill((9, 17, 24, 225))
            screen.blit(shade, (LEFT, TOP))
            text('Experiment complete', (110, 320), 24)
            text(f'{game.score:,} points', (150, 370), 38, GOLD)
            text('Press R to begin a new experiment.', (122, 439), 16)
        rect = viewport(window.get_size())
        window.fill(BG)
        window.blit(pygame.transform.smoothscale(screen, rect.size), rect)
        pygame.display.flip()
        if args.screenshot:
            pygame.image.save(screen, str(args.screenshot))
            args.screenshot = None
        if args.smoke_test:
            running = False
        clock.tick(60)
    pygame.quit()
