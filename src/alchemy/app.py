"""Pygame presentation and input."""
import argparse
import os
from uuid import uuid4
from pathlib import Path

os.environ.setdefault('PYGAME_HIDE_SUPPORT_PROMPT', '1')
import pygame
from .board import Game, SIZE, adjacent
from .resources import load_symbols
from .audio import Audio
from .scores import Scoreboard, RULE_HISTORY, RULE_LABELS
from .modes import MODES, DEFAULT_KEY
from .motion import Motion

WIDTH, HEIGHT = 1040, 780
LEFT, TOP, TILE = 48, 154, 70
PANEL, PANEL_WIDTH = 662, 320
SYMBOL = 48
BG = (15, 24, 30)
TEXT = (241, 229, 203)
MUTED = (156, 173, 174)
GOLD = (223, 181, 103)


def parse_args():
    parser = argparse.ArgumentParser(description='Alchemy: a match-four puzzle')
    parser.add_argument('--seed', type=int, help='Reproducible starting board')
    parser.add_argument('--smoke-test', action='store_true', help='Render a frame and exit')
    parser.add_argument('--screenshot', type=Path, help='Save a frame (.png, .jpg, .bmp; defaults to .png)')
    parser.add_argument('--sound-dir', type=Path, help='Directory of optional WAV/OGG effects')
    parser.add_argument('--mute', action='store_true', help='Start with sound muted')
    parser.add_argument('--volume', type=float, default=0.6, help='Effect volume from 0 to 1')
    parser.add_argument('--assets-dir', type=Path, help='Custom symbol PNG directory')
    parser.add_argument('--player', default=None, help='Set and remember your local player name (up to 16 characters)')
    parser.add_argument('--scores-dir', type=Path, help='Override local scoreboard directory')
    parser.add_argument('--mode', choices=sorted(MODES), default=DEFAULT_KEY,
                        help='Rule variant (default: %(default)s)')
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
        scores = Scoreboard(args.scores_dir)
        try:
            run(args, scores)
        finally:
            scores.close()
    except (pygame.error, OSError, RuntimeError) as error:
        raise SystemExit(f'alchemy: {error}') from None
    finally:
        pygame.quit()


def run(args, scores):
    pygame.init()
    audio = Audio(args.sound_dir, args.volume, args.mute)
    window = pygame.display.set_mode((WIDTH, HEIGHT), pygame.RESIZABLE)
    screen = pygame.Surface((WIDTH, HEIGHT))
    mode = MODES[args.mode]
    pygame.display.set_caption(mode.caption)
    clock = pygame.time.Clock()
    fonts = {size: pygame.font.SysFont('dejavusans', size) for size in (14, 16, 19, 24, 38, 48)}
    symbols = load_symbols(args.assets_dir, mode.names)
    args.player = scores.set_player(args.player) if args.player is not None else scores.player()
    editing_name = False
    name_buffer = ''
    replace_name = False
    reduced_motion = scores.reduced_motion()
    motion = Motion()
    motion_time = 0
    previous_time = pygame.time.get_ticks()
    clear_started = next_resolve = 0
    game = None
    run_id = ''
    rules_index = 0
    score_saved = show_scores = False
    results = []
    selected = hint = None

    def reload_scores():
        nonlocal results
        results = scores.top(args.seed, mode=mode.key, rules=RULE_HISTORY[rules_index])

    def start_new_game(animate=True):
        """Begin a fresh experiment in the current mode. Also used by the mode switch."""
        nonlocal game, run_id, score_saved, show_scores, selected, hint
        nonlocal rules_index, next_resolve, clear_started
        game = Game(args.seed, mode)
        run_id = str(uuid4())
        score_saved = show_scores = False
        rules_index = 0
        selected = hint = None
        next_resolve = clear_started = 0
        reload_scores()
        motion.finish()
        if animate and not reduced_motion:
            motion.entrance(motion_time)

    def switch_mode(key):
        nonlocal mode, symbols
        mode = MODES[key]
        pygame.display.set_caption(mode.caption)
        symbols = load_symbols(args.assets_dir, mode.names)
        start_new_game()

    def can_act():
        """Whether board and hint input should be accepted right now."""
        return (not show_scores and not motion.active(motion_time)
                and not game.pending and game.moves)

    start_new_game(animate=not args.smoke_test)
    running = True
    player_button = pygame.Rect(662, 28, 320, 34)
    hint_button = pygame.Rect(662, 590, 142, 46)
    scores_button = pygame.Rect(662, 550, 320, 32)
    restart_button = pygame.Rect(818, 590, 164, 46)

    def text(value, pos, size=19, color=TEXT):
        screen.blit(fonts[size].render(str(value), True, color), pos)

    while running:
        now = pygame.time.get_ticks()
        if not editing_name:
            motion_time += now - previous_time
        previous_time = now
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
            elif editing_name:
                if event.type == pygame.TEXTINPUT:
                    incoming = ''.join(c for c in event.text if c.isprintable())
                    if incoming:
                        name_buffer = (('' if replace_name else name_buffer) + incoming)[:16]
                        replace_name = False
                elif event.type == pygame.KEYDOWN:
                    if event.key == pygame.K_RETURN:
                        args.player = scores.set_player(name_buffer)
                        editing_name = False
                        pygame.key.stop_text_input()
                    elif event.key == pygame.K_ESCAPE:
                        editing_name = False
                        pygame.key.stop_text_input()
                    elif event.key == pygame.K_BACKSPACE:
                        name_buffer = '' if replace_name else name_buffer[:-1]
                        replace_name = False
                    elif event.key == pygame.K_a and event.mod & pygame.KMOD_CTRL:
                        replace_name = True
            elif event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    if show_scores:
                        show_scores = False
                    else:
                        running = False
                elif event.key == pygame.K_a:
                    reduced_motion = not reduced_motion
                    scores.set_reduced_motion(reduced_motion)
                    motion.finish()
                elif event.key == pygame.K_TAB and show_scores:
                    rules_index = (rules_index + 1) % len(RULE_HISTORY)
                    reload_scores()
                elif event.key == pygame.K_p:
                    editing_name = True
                    name_buffer = args.player
                    replace_name = True
                    pygame.key.start_text_input()
                elif event.key == pygame.K_l:
                    show_scores = not show_scores
                    reload_scores()
                elif event.key == pygame.K_c:
                    keys = list(MODES)
                    switch_mode(keys[(keys.index(mode.key) + 1) % len(keys)])
                    audio.play("restart")
                elif event.key == pygame.K_m:
                    audio.toggle()
                elif event.key == pygame.K_r:
                    audio.play("restart")
                    start_new_game()
                elif event.key == pygame.K_h and can_act():
                    hint = game.hint()
                    audio.play("hint")
            elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                pos = logical_position(event.pos, window.get_size())
                if player_button.collidepoint(pos):
                    editing_name = True
                    name_buffer = args.player
                    replace_name = True
                    pygame.key.start_text_input()
                elif scores_button.collidepoint(pos):
                    show_scores = not show_scores
                    reload_scores()
                elif restart_button.collidepoint(pos):
                    audio.play("restart")
                    start_new_game()
                elif hint_button.collidepoint(pos) and can_act():
                    hint = game.hint()
                    audio.play("hint")
                elif can_act():
                    x = int((pos[0] - LEFT) // TILE)
                    y = int((pos[1] - TOP) // TILE)
                    if 0 <= x < SIZE and 0 <= y < SIZE:
                        cell = (x, y)
                        hint = None
                        if selected == cell:
                            selected = None
                        elif selected is not None and adjacent(selected, cell, mode):
                            if game.attempt(selected, cell):
                                audio.play("swap")
                                clear_started = motion_time
                                next_resolve = motion_time + 350
                            else:
                                audio.play("invalid")
                            selected = None
                        else:
                            selected = cell
                            audio.play("select")
        if not editing_name and not motion.active(motion_time) and game.pending and motion_time >= next_resolve:
            cleared = set(game.pending)
            events = game.resolve()
            if not reduced_motion:
                if 'shuffle' in events:
                    motion.entrance(motion_time)
                else:
                    motion.fall(cleared, motion_time)
            for sound_event in events:
                audio.play(sound_event)
                if sound_event == 'game_over' and not score_saved:
                    score_saved = scores.record(run_id, args.player, game.score, args.seed,
                                                mode=mode.key)
                    reload_scores()
            clear_started = motion_time + (0 if reduced_motion else motion.duration)
            next_resolve = clear_started + 350

        screen.fill(BG)
        pygame.draw.circle(screen, (21, 34, 40), (975, 60), 260, 1)
        pygame.draw.circle(screen, (21, 34, 40), (975, 60), 220, 1)
        text('A L C H E M Y', (48, 28), 38)
        text('T H E   F O U R F O L D   A R T', (50, 85), 14, GOLD)
        pygame.draw.rect(screen, (35, 49, 55), player_button, border_radius=8)
        text(f'Player: {args.player}  [P]', (670, 35), 14, GOLD)
        text(mode.tagline, (PANEL, 67), 16, MUTED)
        text(f'Mode: {mode.label}  [C]', (PANEL, 92), 14, GOLD)
        pygame.draw.line(screen, (57, 68, 68), (48, 125), (982, 125))
        screen.set_clip(pygame.Rect(LEFT, TOP, SIZE*TILE, SIZE*TILE))
        for y, row in enumerate(game.grid):
            for x, value in enumerate(row):
                dx, dy = motion.offset(x, y, motion_time)
                rect = pygame.Rect(LEFT+(x+dx)*TILE+3, TOP+(y+dy)*TILE+3, TILE-6, TILE-6)
                pygame.draw.rect(screen, mode.colors[value], rect, border_radius=10)
                pygame.draw.rect(screen, (255, 226, 154) if (x,y) in game.pending else (104, 107, 99), rect, 1, border_radius=10)
                symbol = symbols[value]
                if (x,y) in game.pending and not reduced_motion and not motion.active(motion_time):
                    symbol = symbol.copy()
                    symbol.set_alpha(max(0, int(255 * (1-(motion_time-clear_started)/350))))
                screen.blit(symbol, symbol.get_rect(center=rect.center))
                if selected == (x, y) or (hint and (x, y) in hint):
                    pygame.draw.rect(screen, GOLD, rect.inflate(4, 4), 3, border_radius=12)
                if (x,y) in game.pending:
                    overlay = pygame.Surface(rect.size, pygame.SRCALPHA)
                    overlay.fill((255, 234, 173, 95))
                    screen.blit(overlay, rect)

        screen.set_clip(None)
        text('YOUR EXPERIMENT', (662, 158), 14, GOLD)
        text(f'{game.score:,}', (658, 183), 48)
        text('POINTS', (664, 244), 14, MUTED)
        text(f'{game.moves:02d}', (855, 183), 48)
        text('MOVES LEFT', (857, 244), 14, MUTED)
        pygame.draw.line(screen, (57, 68, 68), (662, 282), (982, 282))
        text('The practice', (662, 305), 24)
        for i, line in enumerate(mode.practice):
            text(line, (PANEL, 350+i*28), 14, MUTED)
        step = PANEL_WIDTH // len(symbols)
        for i, symbol in enumerate(symbols):
            screen.blit(symbol, (PANEL + i*step + (step-SYMBOL)//2, 496))
        for button, label in ((scores_button, 'Local scores  [L]'), (hint_button, 'Hint  [H]'), (restart_button, 'New game  [R]')):
            pygame.draw.rect(screen, (35, 49, 55), button, border_radius=8)
            pygame.draw.rect(screen, (92, 105, 103), button, 1, border_radius=8)
            screen.blit(fonts[16].render(label, True, TEXT), fonts[16].render(label, True, TEXT).get_rect(center=button.center))
        if game.last_reaction:
            reaction = game.last_reaction
            text(f"Reaction +{reaction['total']}  (x{reaction['multiplier']})", (662, 645), 19, GOLD)
            text(f"Base {reaction['base']} / long lines +{reaction['length']}", (662, 672), 14, MUTED)
            text(f"L +{reaction['l_shape']} / T +{reaction['t_shape']} / Plus +{reaction['plus']}", (662, 692), 14, GOLD)
        text(f'Sound: {"off" if audio.muted else "on"}  [M]   /   ESC to quit', (662, 739), 14, MUTED)
        text(f'Motion: {"reduced" if reduced_motion else "animated"}  [A]', (662, 716), 14, MUTED)
        if not scores.error:
            message = game.message
            while fonts[16].size(message)[0] > 560:
                message = message[:-2] + '~'
            text(message, (48, 735), 16, GOLD)

        if game.moves == 0 and not game.pending and not motion.active(motion_time):
            shade = pygame.Surface((SIZE*TILE, SIZE*TILE), pygame.SRCALPHA)
            shade.fill((9, 17, 24, 225))
            screen.blit(shade, (LEFT, TOP))
            text('Experiment complete', (110, 320), 24)
            text(f'{game.score:,} points', (150, 370), 38, GOLD)
            status = 'Score saved locally' if score_saved else 'Score could not be saved'
            if score_saved and results and results[0]['id'] == run_id:
                status = 'New local high score!'
            text(status, (150, 425), 16, GOLD)
            text('L: view scores    R: new experiment', (122, 465), 16)
        if show_scores:
            panel = pygame.Rect(LEFT, TOP, SIZE*TILE, SIZE*TILE)
            pygame.draw.rect(screen, (20, 33, 40), panel, border_radius=12)
            text(RULE_LABELS[RULE_HISTORY[rules_index]], (80, 175), 24, GOLD)
            category = (f'{mode.label} / {mode.moves} moves' if args.seed is None
                        else f'{mode.label} / seed {args.seed}')
            text(category[:48], (80, 215), 16, MUTED)
            text('PLAYER', (80, 252), 14, MUTED)
            text('POINTS', (340, 252), 14, MUTED)
            text('DATE (UTC)', (440, 252), 14, MUTED)
            for index, entry in enumerate(results):
                y = 282 + index * 33
                name = f'{index+1:2}. {entry["player"]}'
                while fonts[16].size(name)[0] > 240:
                    name = name[:-2] + '~'
                text(name, (80, y), 16, GOLD if entry['id'] == run_id else TEXT)
                text(f'{entry["score"]:,}', (340, y), 16, GOLD)
                text(entry['completed'][:10], (440, y), 14, MUTED)
            if not results:
                text('Complete an experiment to set a score.', (80, 300), 19)
            text('Tab: current and legacy scoring', (80, 630), 16, GOLD)
            text('L or Esc to return to your experiment', (80, 658), 16, MUTED)
        if scores.error:
            text('Local scores unavailable; your game can continue.', (48, 735), 16, GOLD)
        if editing_name:
            shade = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
            shade.fill((0, 0, 0, 180))
            screen.blit(shade, (0, 0))
            pygame.draw.rect(screen, (20, 33, 40), (260, 260, 520, 250), border_radius=12)
            text('Player name', (292, 280), 24, GOLD)
            text('Up to 16 characters. Saved for next time.', (292, 323), 16, MUTED)
            pygame.draw.rect(screen, (65, 75, 70) if replace_name else (35, 49, 55), (292, 355, 456, 45), border_radius=6)
            text(name_buffer + '|', (306, 362), 19)
            text('Enter: save    Esc: cancel    Ctrl+A: replace', (292, 420), 16)
            text('Applies to unfinished and future experiments.', (292, 459), 14, MUTED)
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
