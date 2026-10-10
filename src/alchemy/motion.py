"""Visual tile offsets; never consumes the game's random generator."""
from random import SystemRandom
from .board import SIZE


class Motion:
    duration = 320

    def __init__(self):
        self.started = -self.duration
        self.origins = {}

    def active(self, now):
        return now - self.started < self.duration

    def finish(self):
        self.started = -self.duration
        self.origins = {}

    def entrance(self, now, side=None):
        side = side or SystemRandom().choice(('left', 'right', 'top', 'bottom'))
        dx, dy = {'left': (-SIZE, 0), 'right': (SIZE, 0),
                  'top': (0, -SIZE), 'bottom': (0, SIZE)}[side]
        self.started = now
        self.origins = {(x, y): (dx, dy) for y in range(SIZE) for x in range(SIZE)}

    def fall(self, cleared, now):
        self.started = now
        self.origins = {}
        for x in range(SIZE):
            survivors = [y for y in range(SIZE) if (x, y) not in cleared]
            missing = SIZE - len(survivors)
            for y in range(missing):
                self.origins[x, y] = (0, -missing)
            for target, source in enumerate(survivors, start=missing):
                self.origins[x, target] = (0, source-target)

    def offset(self, x, y, now):
        # Small stagger, all cells settled by duration.
        delay = (x+y) * 3
        progress = max(0, min(1, (now-self.started-delay)/(self.duration-42)))
        remaining = (1-progress)**3
        dx, dy = self.origins.get((x,y), (0,0))
        return dx*remaining, dy*remaining
