"""Drawing for one frame. Reads a `Session` (see `app.py`) and never changes it.

Everything a mode draws differently lives in a view (`ClassicView`,
`AdventureView`); `draw()` lays out the shared frame around it.
"""
import io
from importlib.resources import files
import logging
import math

import pygame
from .board import SIZE
from .modes import ADVENTURE_MODES
from .adventure import medal_thresholds
from .medals import efficiency_medal

WIDTH, HEIGHT = 1040, 780
LEFT, TOP, TILE = 48, 154, 70
PANEL, PANEL_WIDTH = 662, 320
SYMBOL = 48
BG = (15, 24, 30)
TEXT = (241, 229, 203)
MUTED = (156, 173, 174)
GOLD = (223, 181, 103)
MEDAL_COLORS = {'Bronze': (205, 154, 111), 'Silver': (195, 209, 220), 'Gold': GOLD}
UNSTABLE = (255, 196, 110)
SURFACE = (35, 49, 55)
RULE = (57, 68, 68)

BOARD = pygame.Rect(LEFT, TOP, SIZE*TILE, SIZE*TILE)
PLAYER_BUTTON = pygame.Rect(662, 28, 320, 34)
HINT_BUTTON = pygame.Rect(662, 590, 142, 46)
SCORES_BUTTON = pygame.Rect(662, 550, 320, 32)
RESTART_BUTTON = pygame.Rect(818, 590, 164, 46)
# Layout size -> (bundled font, pixel size). Small UI text is Source Sans 3;
# headings are Cormorant Garamond. Cormorant's default digits are old-style
# (a 0 reads as an o), so the large numeric sizes use Cormorant Infant, whose
# default digits are lining; its distinct a and g never appear at those sizes.
SANS, SERIF, NUMERALS = 'SourceSans3-Regular.ttf', 'CormorantGaramond-SemiBold.otf', 'CormorantInfant-SemiBold.otf'
FONTS = {14: (SANS, 15), 16: (SANS, 17), 19: (SANS, 21),
         24: (SERIF, 29), 38: (NUMERALS, 46), 48: (NUMERALS, 58)}
CONFIRM_PROMPTS = {'restart': 'Abandon this experiment? Press R or New game again.',
                   'mode': 'Abandon this experiment and switch mode? Press C again.'}


class Canvas:
    """The logical 1040x780 surface plus the fonts drawn onto it."""

    def __init__(self):
        self.screen = pygame.Surface((WIDTH, HEIGHT))
        self.fonts = {size: load_font(name, pixels, size) for size, (name, pixels) in FONTS.items()}

    def text(self, value, pos, size=19, color=TEXT):
        self.screen.blit(self.fonts[size].render(str(value), True, color), pos)

    def fit(self, value, width, size=16):
        """Trim `value` with a trailing ~ until it renders within `width` pixels."""
        while self.fonts[size].size(value)[0] > width:
            value = value[:-2] + '~'
        return value

    def shade(self, rect, color):
        overlay = pygame.Surface(rect.size, pygame.SRCALPHA)
        overlay.fill(color)
        self.screen.blit(overlay, rect)


def load_font(name, pixels, fallback_size):
    """A bundled font, or a system font with a warning if the file is unusable."""
    try:
        data = files('alchemy').joinpath('assets', 'fonts', name).read_bytes()
        return pygame.font.Font(io.BytesIO(data), pixels)
    except (pygame.error, OSError) as error:
        logging.warning('Cannot load bundled font %s; using a system font: %s', name, error)
        return pygame.font.SysFont('dejavusans', fallback_size)


class ClassicView:
    """Classic and Diagonal: a move budget and the practice notes."""

    def counter(self, game):
        note = f'Banked: +{game.banked_value}' if game.banked and game.unused_bonus is None else None
        return f'{game.moves:02d}', 'MOVES LEFT', note

    def panel(self, canvas, session):
        canvas.text('The practice', (662, 305), 24)
        for i, line in enumerate(session.mode.practice):
            canvas.text(line, (PANEL, 350+i*28), 14, MUTED)

    def end_title(self, game):
        return 'Experiment complete'

    def end_status(self, game, status):
        return status

    def end_details(self, canvas, game):
        bonus = game.unused_bonus
        if bonus and bonus['total']:
            parts = [f"{bonus['on_board']} on the board"] if bonus['on_board'] else []
            parts += [f"{bonus['banked']} banked"] if bonus['banked'] else []
            canvas.text(f"Unused unstable symbols: +{bonus['total']}  ({', '.join(parts)})",
                        (122, 452), 16, GOLD)
            canvas.text('L: view scores    R: new experiment', (122, 485), 16)
        else:
            canvas.text('L: view scores    R: new experiment', (122, 465), 16)

    note_color = GOLD   # the unstable-symbol bank is a reward, so it stands out
    score_row_height = 33
    tab_hint = 'Tab: current and legacy scoring'
    record_status = 'New local high score!'
    ranking_note = ''

    def score_columns(self, canvas):
        canvas.text('DATE (UTC)', (440, 252), 14, MUTED)

    def score_detail(self, canvas, entry, y, category=None):
        canvas.text(entry['completed'][:10], (440, y), 14, MUTED)


class AdventureView:
    """Adventure: finite material, a points target, and efficiency stats."""

    def counter(self, game):
        return (str(game.material_left), 'MATERIAL LEFT',
                'Silver {}+ / Gold {}+'.format(*game.experiment.medals))

    def panel(self, canvas, session):
        game = session.game
        canvas.text(game.experiment.title, (662, 305), 24)
        canvas.text(f'Target: {game.experiment.target:,} points', (PANEL, 341), 19, GOLD)
        canvas.text(f'{game.points_remaining:,} points to go', (PANEL, 366), 14, MUTED)
        if sum(game.reserves):
            canvas.text('Replacement reserves', (PANEL, 390), 14, MUTED)
        else:
            canvas.text('Reserves exhausted', (PANEL, 387), 14, GOLD)
            canvas.text('Use the remaining board.' if not game.finished else 'No reserves remain.',
                        (PANEL, 406), 14, MUTED)
        for i, name in enumerate(session.mode.names):
            canvas.text(f'{name.title()}: {game.reserves[i]}',
                        (PANEL + (i % 2)*160, 429+(i//2)*25), 16)
        stir_text = (f'Stirs: {game.stirs}' if game.stirs_remaining is None
                     else f'Stirs left: {game.stirs_remaining}/{game.experiment.stir_limit}')
        canvas.text(f'Used: {game.consumed}   Swaps: {game.turns}   {stir_text}',
                    (PANEL, 478), 14, MUTED)

    def end_title(self, game):
        return 'Experiment stalled' if game.outcome == 'stalled' else 'Experiment complete'

    def end_status(self, game, status):
        return game.failure_summary if game.outcome == 'stalled' else status

    def end_details(self, canvas, game):
        if game.outcome == 'stalled':
            canvas.text(f'{game.points_remaining:,} points short / {game.material_left} material left',
                        (122, 452), 16, GOLD)
        else:
            canvas.text(f'{game.medal} medal / Material left: {game.material_left}',
                        (122, 452), 16, MEDAL_COLORS[game.medal])
        canvas.text(f'Reactants consumed: {game.consumed}', (122, 478), 16)
        canvas.text(f'Successful swaps: {game.turns} / Stirs: {game.stirs}', (122, 504), 16)
        unspent = len(game.unstable)
        if game.outcome == 'success' and unspent:
            canvas.text(f"{unspent} unstable symbol{'s' if unspent != 1 else ''} left unspent "
                        '(counted in material left)', (122, 526), 14, MUTED)
        canvas.text('L: view scores    R: retry experiment', (122, 548), 16)

    note_color = MUTED
    score_row_height = 34
    tab_hint = 'Tab: current and original experiment'
    record_status = 'New local best: most material left!'
    ranking_note = '  /  ranked by material left, then fewest swaps'

    def score_columns(self, canvas):
        canvas.text('MATERIAL LEFT', (440, 252), 14, MUTED)

    def score_detail(self, canvas, entry, y, category=None):
        if entry['material_left'] is None:
            canvas.text('-', (440, y), 16, MUTED)
            canvas.text('Efficiency stats unavailable', (108, y+19), 14, MUTED)
        else:
            thresholds = medal_thresholds(category.mode) if category else medal_thresholds(None)
            medal = efficiency_medal(entry['material_left'], thresholds)
            canvas.text(f"{entry['material_left']} / {medal}", (440, y), 16, MEDAL_COLORS[medal])
            canvas.text(f"Swaps: {entry['swaps']} / Stirs: {entry['stirs']}", (108, y+19), 14, MUTED)


VIEWS = {mode.key: AdventureView() for mode in ADVENTURE_MODES}
DEFAULT_VIEW = ClassicView()


def view_for(mode):
    return VIEWS.get(mode.key, DEFAULT_VIEW)


def draw(canvas, session):
    view = view_for(session.mode)
    draw_header(canvas, session)
    draw_board(canvas, session)
    draw_panel(canvas, session, view)
    if session.game_over_visible():
        draw_end_screen(canvas, session, view)
    if session.show_scores:
        draw_scoreboard(canvas, session, view)
    if session.scores.error and not session.confirming:
        canvas.text('Local scores unavailable; your game can continue.', (48, 735), 16, GOLD)
    if session.editing_name:
        draw_name_dialog(canvas, session)


def draw_header(canvas, session):
    screen = canvas.screen
    screen.fill(BG)
    pygame.draw.circle(screen, (21, 34, 40), (975, 60), 260, 1)
    pygame.draw.circle(screen, (21, 34, 40), (975, 60), 220, 1)
    canvas.text('A L C H E M Y', (48, 28), 38)
    canvas.text('T H E   F O U R F O L D   A R T', (50, 85), 14, GOLD)
    pygame.draw.rect(screen, SURFACE, PLAYER_BUTTON, border_radius=8)
    canvas.text(f'Player: {session.player}  [P]', (670, 35), 14, GOLD)
    canvas.text(session.mode.tagline, (PANEL, 67), 16, MUTED)
    canvas.text(f'Mode: {session.mode.label}  [C]', (PANEL, 92), 14, GOLD)
    pygame.draw.line(screen, RULE, (48, 125), (982, 125))


def draw_board(canvas, session):
    screen, game, motion, now = canvas.screen, session.game, session.motion, session.motion_time
    fading = not session.reduced_motion and not motion.active(now)
    screen.set_clip(BOARD)
    for y, row in enumerate(game.grid):
        for x, value in enumerate(row):
            if value is None:
                rect = pygame.Rect(LEFT+x*TILE+3, TOP+y*TILE+3, TILE-6, TILE-6)
                pygame.draw.rect(screen, SURFACE, rect, 1, border_radius=10)
                continue
            pending = (x, y) in game.pending
            dx, dy = motion.offset(x, y, now)
            rect = pygame.Rect(LEFT+(x+dx)*TILE+3, TOP+(y+dy)*TILE+3, TILE-6, TILE-6)
            pygame.draw.rect(screen, session.mode.colors[value], rect, border_radius=10)
            pygame.draw.rect(screen, (255, 226, 154) if pending else (104, 107, 99), rect, 1, border_radius=10)
            symbol = session.symbols[value]
            if pending and fading:
                symbol = symbol.copy()
                symbol.set_alpha(max(0, int(255 * (1-(now-session.clear_started)/350))))
            screen.blit(symbol, symbol.get_rect(center=rect.center))
            tier = game.unstable.get((x, y))
            if tier:
                draw_unstable(screen, rect, tier, now, session.reduced_motion)
            if session.selected == (x, y) or (session.hint and (x, y) in session.hint):
                pygame.draw.rect(screen, GOLD, rect.inflate(4, 4), 3, border_radius=12)
            if pending:
                canvas.shade(rect, (255, 234, 173, 95))
    if session.cursor is not None:
        x, y = session.cursor
        cell = pygame.Rect(LEFT+x*TILE+3, TOP+y*TILE+3, TILE-6, TILE-6)
        pygame.draw.rect(screen, TEXT, cell.inflate(10, 10), 2, border_radius=14)
    screen.set_clip(None)


def draw_unstable(screen, rect, tier, now, reduced_motion):
    """Mark an unstable symbol: stripes (Line), corner brackets (Square), or a ring (Element)."""
    glow = 1 if reduced_motion else 0.8 + 0.2 * math.sin(now / 160)
    color = tuple(int(c * glow) for c in UNSTABLE)
    if tier == 'line':
        for y in (rect.top + 6, rect.bottom - 7):
            pygame.draw.line(screen, color, (rect.left + 12, y), (rect.right - 13, y), 3)
    elif tier == 'square':
        inner, arm = rect.inflate(-8, -8), 12
        for (cx, cy), (dx, dy) in (((inner.left, inner.top), (1, 1)), ((inner.right - 1, inner.top), (-1, 1)),
                                   ((inner.left, inner.bottom - 1), (1, -1)),
                                   ((inner.right - 1, inner.bottom - 1), (-1, -1))):
            pygame.draw.line(screen, color, (cx, cy), (cx + dx*arm, cy), 3)
            pygame.draw.line(screen, color, (cx, cy), (cx, cy + dy*arm), 3)
    else:
        pygame.draw.circle(screen, color, rect.center, rect.width // 2 - 4, 3)


def draw_panel(canvas, session, view):
    screen, game = canvas.screen, session.game
    canvas.text('YOUR EXPERIMENT', (662, 158), 14, GOLD)
    canvas.text(f'{game.score:,}', (658, 179), 48)
    canvas.text('POINTS', (664, 244), 14, MUTED)
    value, label, note = view.counter(game)
    canvas.text(value, (855, 179), 48)
    canvas.text(label, (847, 244), 14, MUTED)
    if note:
        canvas.text(note, (817, 264), 14, view.note_color)
    pygame.draw.line(screen, RULE, (662, 282), (982, 282))
    view.panel(canvas, session)
    step = PANEL_WIDTH // len(session.symbols)
    for i, symbol in enumerate(session.symbols):
        screen.blit(symbol, (PANEL + i*step + (step-SYMBOL)//2, 496))
    for button, label in ((SCORES_BUTTON, 'Local scores  [L]'), (HINT_BUTTON, 'Hint  [H]'),
                          (RESTART_BUTTON, 'New game  [R]')):
        pygame.draw.rect(screen, SURFACE, button, border_radius=8)
        asking = button is RESTART_BUTTON and session.confirming == 'restart'
        pygame.draw.rect(screen, GOLD if asking else (92, 105, 103), button, 1, border_radius=8)
        rendered = canvas.fonts[16].render(label, True, TEXT)
        screen.blit(rendered, rendered.get_rect(center=button.center))
    if game.last_reaction:
        reaction = game.last_reaction
        canvas.text(f"Reaction +{reaction['total']}  (x{reaction['multiplier']})", (662, 645), 19, GOLD)
        detail = f"Base {reaction['base']} / long lines +{reaction['length']}"
        if reaction.get('unstable'):
            detail += f" / unstable +{reaction['unstable']}"
        canvas.text(detail, (662, 672), 14, MUTED)
        canvas.text(f"L +{reaction['l_shape']} / T +{reaction['t_shape']} / Plus +{reaction['plus']}",
                    (662, 692), 14, GOLD)
    canvas.text(f'Sound: {"off" if session.audio.muted else "on"}  [M]   /   ESC to quit', (662, 739), 14, MUTED)
    canvas.text(f'Motion: {"reduced" if session.reduced_motion else "animated"}  [A]', (662, 716), 14, MUTED)
    if session.confirming:
        canvas.text(CONFIRM_PROMPTS[session.confirming], (48, 735), 16, GOLD)
    elif not session.scores.error:
        canvas.text(canvas.fit(game.message, 560), (48, 735), 16, GOLD)


def draw_end_screen(canvas, session, view):
    game = session.game
    canvas.shade(BOARD, (9, 17, 24, 225))
    canvas.text(view.end_title(game), (110, 320), 24)
    canvas.text(f'{game.score:,} points', (150, 370), 38, GOLD)
    status = 'Score saved locally' if session.score_saved else 'Score could not be saved'
    if session.score_saved and session.results and session.results[0]['id'] == session.run_id:
        status = view.record_status
    canvas.text(view.end_status(game, status), (110, 425), 16, GOLD)
    view.end_details(canvas, game)


def draw_scoreboard(canvas, session, view):
    pygame.draw.rect(canvas.screen, (20, 33, 40), BOARD, border_radius=12)
    category = session.categories()[session.category_index]
    canvas.text('Local high scores' if session.category_index == 0 else 'Historical high scores',
                (80, 175), 24, GOLD)
    canvas.text(category.label, (80, 215), 16, MUTED)
    seed = session.score_seed()
    seed_label = 'Unseeded / 30 moves' if seed is None else f'Seed {seed}'
    canvas.text(canvas.fit(seed_label[:48] + view.ranking_note, 520, 14), (80, 235), 14, MUTED)
    canvas.text('PLAYER', (80, 252), 14, MUTED)
    canvas.text('POINTS', (340, 252), 14, MUTED)
    view.score_columns(canvas)
    for index, entry in enumerate(session.results):
        y = 282 + index * view.score_row_height
        name = canvas.fit(f'{index+1:2}. {entry["player"]}', 240)
        canvas.text(name, (80, y), 16, GOLD if entry['id'] == session.run_id else TEXT)
        canvas.text(f'{entry["score"]:,}', (340, y), 16, GOLD)
        view.score_detail(canvas, entry, y, category)
    if not session.results:
        canvas.text('Complete an experiment to set a score.', (80, 300), 19)
    if len(session.categories()) > 1:
        canvas.text(view.tab_hint, (80, 630), 16, GOLD)
    canvas.text('L or Esc to return to your experiment', (80, 658), 16, MUTED)


def draw_name_dialog(canvas, session):
    screen = canvas.screen
    canvas.shade(screen.get_rect(), (0, 0, 0, 180))
    pygame.draw.rect(screen, (20, 33, 40), (260, 260, 520, 250), border_radius=12)
    canvas.text('Player name', (292, 280), 24, GOLD)
    canvas.text('Up to 16 characters. Saved for next time.', (292, 323), 16, MUTED)
    pygame.draw.rect(screen, (65, 75, 70) if session.replace_name else SURFACE,
                     (292, 355, 456, 45), border_radius=6)
    canvas.text(session.name_buffer + '|', (306, 362), 19)
    canvas.text('Enter: save    Esc: cancel    Ctrl+A: replace', (292, 420), 16)
    canvas.text('Applies to unfinished and future experiments.', (292, 459), 14, MUTED)
