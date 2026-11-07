"""Command line, input handling, and the frame loop. Drawing lives in `render.py`."""
import argparse
import os
from uuid import uuid4
from pathlib import Path

os.environ.setdefault('PYGAME_HIDE_SUPPORT_PROMPT', '1')
import pygame
from .board import Game, SIZE, adjacent
from .adventure import AdventureGame, EXPERIMENTS, CAMPAIGN_KITS, chapter_of, experiment_medal
from .medals import MEDAL_RANK
from .resources import load_symbols
from .audio import Audio
from .scores import Scoreboard, score_categories
from .modes import MODES, MODE_ALIASES, DEFAULT_KEY, CAMPAIGN
from .motion import Motion
from .render import (WIDTH, HEIGHT, LEFT, TOP, TILE, BG, PLAYER_BUTTON, HINT_BUTTON,
                     SCORES_BUTTON, RESTART_BUTTON, Canvas, draw)


def parse_args():
    parser = argparse.ArgumentParser(description='Alchemy: a match-four puzzle')
    parser.add_argument('--seed', type=int, help='Reproducible starting board')
    parser.add_argument('--smoke-test', action='store_true', help='Render a frame and exit')
    parser.add_argument('--screenshot', type=Path, help='Save a frame (.png, .jpg, .bmp; defaults to .png)')
    parser.add_argument('--sound-dir', type=Path, help='Directory of optional WAV/OGG effects')
    parser.add_argument('--mute', action='store_true', help='Start with sound muted')
    parser.add_argument('--no-tones', action='store_true',
                        help='Play only sound files; no built-in tones for the rest')
    parser.add_argument('--volume', type=float, default=0.6, help='Effect volume from 0 to 1')
    parser.add_argument('--assets-dir', type=Path, help='Custom symbol PNG directory')
    parser.add_argument('--player', default=None, help='Set and remember your local player name (up to 16 characters)')
    parser.add_argument('--scores-dir', type=Path, help='Override local scoreboard directory')
    parser.add_argument('--mode', choices=sorted(MODES), default=DEFAULT_KEY,
                        type=lambda key: MODE_ALIASES.get(key, key),
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


ARROWS = {pygame.K_LEFT: (-1, 0), pygame.K_RIGHT: (1, 0), pygame.K_UP: (0, -1), pygame.K_DOWN: (0, 1)}
ACTIVATE = (pygame.K_RETURN, pygame.K_KP_ENTER, pygame.K_SPACE)
KEYBOARD_TIP = 'Keyboard: arrows + Enter'


class Session:
    """Everything the window remembers between frames: the game, overlays, and timing.

    `handle()` takes input, `update()` advances reactions, and `render.draw()`
    reads the result. Games are built from this module's `Game` and
    `AdventureGame` names, so tests can substitute recording subclasses.
    """

    def __init__(self, args, scores, audio):
        self.args, self.scores, self.audio = args, scores, audio
        self.mode = MODES[args.mode]
        pygame.display.set_caption(self.mode.caption)
        self.symbols = load_symbols(args.assets_dir, self.mode.names)
        self.player = scores.set_player(args.player) if args.player is not None else scores.player()
        self.editing_name = self.replace_name = False
        self.name_buffer = ''
        self.reduced_motion = scores.reduced_motion()
        self.motion = Motion()
        self.motion_time = 0
        self.previous_time = pygame.time.get_ticks()
        self.clear_started = self.next_resolve = 0
        self.game = None
        self.run_id = ''
        self.category_index = 0
        self.score_saved = self.show_scores = False
        self.results = []
        self.stage_medals = []   # best medal per campaign stage, refreshed with the scores
        self.selected = self.hint = None
        self.confirming = None   # 'restart', 'mode', or 'kit' while asking to abandon a game
        self.cursor = None       # keyboard cell; appears with the first arrow key
        self.running = True
        self.kit_index = self.unlocked_kits() - 1   # the newest open campaign stage
        self.start_new_game(animate=not args.smoke_test)

    @property
    def adventure(self):
        return self.mode.key in EXPERIMENTS or self.campaign

    @property
    def campaign(self):
        return self.mode.key == CAMPAIGN.key

    @property
    def kit(self):
        return CAMPAIGN_KITS[self.kit_index] if self.campaign else None

    def unlocked_kits(self):
        return min(self.scores.campaign_unlocked(), len(CAMPAIGN_KITS))

    def experiment(self):
        return self.kit.experiment if self.campaign else EXPERIMENTS[self.mode.key]

    def tagline(self):
        if not self.campaign:
            return self.mode.tagline
        chapter, first = self.chapter()
        return f'{chapter.name}: stage {self.kit_index - first + 1} of {len(chapter.kits)}'

    def chapter(self):
        """The current stage's chapter and the index of its first stage."""
        return chapter_of(self.kit_index)

    def score_seed(self):
        return self.game.seed if isinstance(self.game, AdventureGame) else self.args.seed

    def score_mode(self):
        return self.game.experiment.key if self.adventure else self.mode.key

    def categories(self):
        label = f'{self.kit.stage}: {self.kit.experiment.title}' if self.campaign else self.mode.label
        return score_categories(self.score_mode(), label, self.mode.rules)

    def reload_scores(self):
        category = self.categories()[self.category_index]
        self.results = self.scores.top(self.score_seed(), mode=category.mode, rules=category.rules)
        self.stage_medals = [self.best_medal(kit) for kit in CAMPAIGN_KITS] if self.campaign else []

    def best_medal(self, kit):
        """The medal of the best saved win of a campaign stage, or None."""
        experiment = kit.experiment
        seed = experiment.seed if self.args.seed is None else self.args.seed
        medals = [experiment_medal(experiment, entry['material_left'], entry['swaps'], entry['stirs'])
                  for entry in self.scores.top(seed, mode=experiment.key, rules=self.mode.rules)]
        return max(filter(None, medals), key=MEDAL_RANK.get, default=None)

    @property
    def stage_won(self):
        """A campaign stage has just been won and its end screen is showing."""
        return self.campaign and self.game_over_visible() and self.game.outcome == 'success'

    @property
    def next_kit(self):
        """The open stage after a just-won one, which Enter begins."""
        following = self.kit_index + 1
        if self.stage_won and following < self.unlocked_kits():
            return CAMPAIGN_KITS[following]
        return None

    @property
    def chapter_complete(self):
        """The last stage of a chapter has just been won."""
        chapter, first = self.chapter()
        return self.stage_won and self.kit_index == first + len(chapter.kits) - 1

    def advance_stage(self):
        self.kit_index += 1
        self.start_new_game()
        self.audio.play('restart')

    def start_new_game(self, animate=True):
        """Begin a fresh experiment in the current mode. Also used by the mode switch."""
        self.game = (AdventureGame(self.args.seed, experiment=self.experiment())
                     if self.adventure else Game(self.args.seed, self.mode))
        if self.campaign:
            self.game.message = f'{self.kit.stage}: {self.kit.lesson}'
        self.game.message = f'{self.game.message}  /  {KEYBOARD_TIP}'  # until the first move replaces it
        self.run_id = str(uuid4())
        self.score_saved = self.show_scores = False
        self.category_index = 0
        self.selected = self.hint = self.confirming = None
        self.swapped = False
        self.next_resolve = self.clear_started = 0
        self.reload_scores()
        self.motion.finish()
        if animate and not self.reduced_motion:
            self.motion.entrance(self.motion_time)

    def restart(self):
        self.audio.play('restart')
        self.start_new_game()

    def switch_mode(self, key):
        self.mode = MODES[key]
        pygame.display.set_caption(self.mode.caption)
        self.symbols = load_symbols(self.args.assets_dir, self.mode.names)
        self.start_new_game()

    def cycle_kit(self):
        """Move to the next open campaign stage (wrapping to the first)."""
        self.kit_index = (self.kit_index + 1) % self.unlocked_kits()
        self.start_new_game()
        self.audio.play('restart')

    def cycle_mode(self):
        keys = list(MODES)
        self.switch_mode(keys[(keys.index(self.mode.key) + 1) % len(keys)])
        self.audio.play('restart')

    def in_progress(self):
        """Whether starting over would throw away a game the player has begun."""
        return self.swapped and not self.game.finished

    def confirm(self, action, confirming, perform):
        """Run `perform` now, or ask first if it would abandon a game in progress.

        The second request for the same action confirms; any other input cancels.
        """
        if confirming == action or not self.in_progress():
            perform()
        else:
            self.confirming = action

    def can_act(self):
        """Whether board and hint input should be accepted right now."""
        return (not self.show_scores and not self.motion.active(self.motion_time)
                and not self.game.pending and not self.game.finished)

    def game_over_visible(self):
        return self.game.finished and not self.game.pending and not self.motion.active(self.motion_time)

    def undo(self):
        """U on a fixed plate: take back the last swap."""
        if not self.game.experiment.layout or self.motion.active(self.motion_time):
            return
        if self.game.undo():
            self.selected = self.hint = None
            self.audio.play('restart')
        elif not self.game.history:
            self.game.message = 'Nothing to undo.'

    def show_hint(self):
        self.hint = self.game.hint()
        self.audio.play('hint')

    def toggle_scores(self):
        self.show_scores = not self.show_scores
        self.reload_scores()

    def open_name_editor(self):
        self.editing_name = True
        self.name_buffer = self.player
        self.replace_name = True
        pygame.key.start_text_input()

    def close_name_editor(self, save):
        if save:
            self.player = self.scores.set_player(self.name_buffer)
        self.editing_name = False
        pygame.key.stop_text_input()

    # ---------- input ----------

    def handle(self, event, window_size):
        if event.type == pygame.QUIT:
            self.running = False
        elif self.editing_name:
            self.handle_name_input(event)
        elif event.type == pygame.KEYDOWN:
            self.handle_key(event)
        elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            self.handle_click(logical_position(event.pos, window_size))

    def handle_name_input(self, event):
        if event.type == pygame.TEXTINPUT:
            incoming = ''.join(c for c in event.text if c.isprintable())
            if incoming:
                self.name_buffer = (('' if self.replace_name else self.name_buffer) + incoming)[:16]
                self.replace_name = False
        elif event.type == pygame.KEYDOWN:
            if event.key == pygame.K_RETURN:
                self.close_name_editor(save=True)
            elif event.key == pygame.K_ESCAPE:
                self.close_name_editor(save=False)
            elif event.key == pygame.K_BACKSPACE:
                self.name_buffer = '' if self.replace_name else self.name_buffer[:-1]
                self.replace_name = False
            elif event.key == pygame.K_a and event.mod & pygame.KMOD_CTRL:
                self.replace_name = True

    def handle_key(self, event):
        confirming, self.confirming = self.confirming, None
        if event.key == pygame.K_ESCAPE:
            if self.show_scores:
                self.show_scores = False
            elif self.selected is not None:
                self.selected = None
            else:
                self.running = False
        elif event.key in ARROWS:
            self.move_cursor(*ARROWS[event.key])
        elif event.key in ACTIVATE and self.next_kit and not self.show_scores:
            self.advance_stage()
        elif event.key in ACTIVATE and self.cursor is not None and self.can_act():
            self.press_cell(self.cursor)
        elif event.key == pygame.K_a:
            self.reduced_motion = not self.reduced_motion
            self.scores.set_reduced_motion(self.reduced_motion)
            self.motion.finish()
        elif event.key == pygame.K_TAB and self.show_scores:
            self.category_index = (self.category_index + 1) % len(self.categories())
            self.reload_scores()
        elif event.key == pygame.K_p:
            self.open_name_editor()
        elif event.key == pygame.K_l:
            self.toggle_scores()
        elif event.key == pygame.K_c:
            self.confirm('mode', confirming, self.cycle_mode)
        elif event.key == pygame.K_e and self.campaign:
            if self.unlocked_kits() > 1:
                self.confirm('kit', confirming, self.cycle_kit)
            else:
                self.game.message = 'Win this stage to unlock the next.'
        elif event.key == pygame.K_m:
            self.audio.toggle()
        elif event.key == pygame.K_r:
            self.confirm('restart', confirming, self.restart)
        elif event.key == pygame.K_u and self.adventure:
            self.undo()
        elif event.key == pygame.K_h and self.can_act():
            self.show_hint()

    def handle_click(self, pos):
        confirming, self.confirming = self.confirming, None
        self.cursor = None
        if PLAYER_BUTTON.collidepoint(pos):
            self.open_name_editor()
        elif SCORES_BUTTON.collidepoint(pos):
            self.toggle_scores()
        elif RESTART_BUTTON.collidepoint(pos):
            self.confirm('restart', confirming, self.restart)
        elif HINT_BUTTON.collidepoint(pos) and self.can_act():
            self.show_hint()
        elif self.next_kit and not self.show_scores and LEFT <= pos[0] < LEFT + SIZE*TILE \
                and TOP <= pos[1] < TOP + SIZE*TILE:
            self.advance_stage()
        elif self.can_act():
            x = int((pos[0] - LEFT) // TILE)
            y = int((pos[1] - TOP) // TILE)
            if 0 <= x < SIZE and 0 <= y < SIZE:
                self.press_cell((x, y))

    def move_cursor(self, dx, dy):
        """Show the keyboard cursor, or step it one cell, stopping at the board's edge."""
        if self.cursor is None:
            self.cursor = self.selected or (SIZE // 2 - 1, SIZE // 2 - 1)
        else:
            x, y = self.cursor
            self.cursor = (min(SIZE - 1, max(0, x + dx)), min(SIZE - 1, max(0, y + dy)))

    def press_cell(self, cell):
        """A click or Enter on a board cell; empty Adventure cells do nothing."""
        x, y = cell
        if self.game.grid[y][x] is not None:
            self.select(cell)

    def select(self, cell):
        """First click picks a symbol; a click on a neighbor tries the swap."""
        self.hint = None
        if self.selected == cell:
            self.selected = None
        elif self.selected is not None and adjacent(self.selected, cell, self.game.mode):
            if self.game.attempt(self.selected, cell):
                self.audio.play('swap')
                self.swapped = True
                self.clear_started = self.motion_time
                self.next_resolve = self.motion_time + 350
            else:
                self.audio.play('invalid')
            self.selected = None
        else:
            self.selected = cell
            self.audio.play('select')

    # ---------- time ----------

    def tick(self, now):
        """Advance the animation clock; it stands still while the name editor is open."""
        if not self.editing_name:
            self.motion_time += now - self.previous_time
        self.previous_time = now

    def update(self):
        """Resolve one pending reaction once its fade has finished."""
        if (self.editing_name or self.motion.active(self.motion_time) or not self.game.pending
                or self.motion_time < self.next_resolve):
            return
        previous_grid = [row[:] for row in self.game.grid]
        events = self.game.resolve()
        cleared = self.game.last_cleared   # new unstable symbols stay put
        if not self.reduced_motion:
            if 'shuffle' in events:
                self.motion.entrance(self.motion_time)
            else:
                self.motion.fall(cleared, self.motion_time, previous_grid)
        for sound_event in events:
            self.audio.play(sound_event)
            if sound_event == 'game_over':
                self.record_score()
        self.clear_started = self.motion_time + (0 if self.reduced_motion else self.motion.duration)
        self.next_resolve = self.clear_started + 350

    def record_score(self):
        """Save a finished run once; Adventure saves only successful experiments."""
        if self.score_saved or (self.adventure and self.game.outcome != 'success'):
            return
        stats = (dict(material_left=self.game.material_left, swaps=self.game.turns, stirs=self.game.stirs)
                 if self.adventure else {})
        self.score_saved = self.scores.record(self.run_id, self.player, self.game.score, self.score_seed(),
                                              mode=self.score_mode(), rules=self.mode.rules, **stats)
        following = self.kit_index + 1
        # Record progress even past the last stage, so stages added later open for finishers.
        if self.campaign and self.scores.unlock_campaign(following + 1) and following < len(CAMPAIGN_KITS):
            self.game.message = f'{CAMPAIGN_KITS[following].stage} unlocked!  Press Enter to begin it.'
        self.reload_scores()


def run(args, scores):
    pygame.init()
    audio = Audio(args.sound_dir, args.volume, args.mute, tones=not args.no_tones)
    window = pygame.display.set_mode((WIDTH, HEIGHT), pygame.RESIZABLE)
    canvas = Canvas()
    clock = pygame.time.Clock()
    session = Session(args, scores, audio)
    while session.running:
        session.tick(pygame.time.get_ticks())
        for event in pygame.event.get():
            session.handle(event, window.get_size())
        session.update()
        draw(canvas, session)
        rect = viewport(window.get_size())
        window.fill(BG)
        window.blit(pygame.transform.smoothscale(canvas.screen, rect.size), rect)
        pygame.display.flip()
        if args.screenshot:
            pygame.image.save(canvas.screen, str(args.screenshot))
            args.screenshot = None
        if args.smoke_test:
            session.running = False
        clock.tick(60)
    pygame.quit()
