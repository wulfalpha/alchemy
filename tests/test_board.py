import unittest
from random import Random
from alchemy.board import Game, SIZE, legal_moves, matches, new_grid, refill, plus_centers


class BoardTests(unittest.TestCase):
    def baseline(self):
        return [[(x+y) % 5 for x in range(SIZE)] for y in range(SIZE)]

    def test_three_does_not_match(self):
        grid = self.baseline()
        grid[0][:3] = [4]*3
        self.assertFalse(matches(grid))

    def test_cross_counts_each_cell_once(self):
        grid = self.baseline()
        for x in range(5):
            grid[2][x] = 0
        for y in range(5):
            grid[y][2] = 0
        self.assertEqual(matches(grid), {(x,2) for x in range(5)} | {(2,y) for y in range(5)})

    def test_plus_bonus_and_cascade_multiplier(self):
        for chain in (0, 1):
            game = Game(1)
            game.grid = self.baseline()
            for x in range(4):
                game.grid[1][x] = 0
            for y in range(4):
                game.grid[y][1] = 0
            game.grid[1][4] = 2
            game.grid[4][1] = 2
            self.assertEqual(plus_centers(game.grid), {(1, 1)})
            game.pending = matches(game.grid)
            self.assertEqual(len(game.pending), 7)
            game.chain = chain
            events = game.resolve()
            self.assertEqual(game.score, (175 + 75 + 200) * (chain + 1))
            self.assertIn('plus', events)

    def test_short_arm_and_t_shape_do_not_earn_bonus(self):
        grid = self.baseline()
        for x in range(4):
            grid[0][x] = 0
        for y in range(4):
            grid[y][1] = 0
        self.assertFalse(plus_centers(grid))
        grid = self.baseline()
        for x in range(5):
            grid[2][x] = 0
        for y in range(1, 4):
            grid[y][2] = 0
        self.assertFalse(plus_centers(grid))

    def test_invalid_swap_preserves_board_and_moves(self):
        game = Game(1)
        game.grid = self.baseline()
        before = [r[:] for r in game.grid]
        self.assertFalse(game.attempt((0,0), (1,0)))
        self.assertEqual(game.grid, before)
        self.assertEqual(game.moves, 30)
        self.assertFalse(game.attempt((0,0), (2,2)))

    def test_gravity_preserves_order(self):
        grid = self.baseline()
        column = [row[0] for row in grid]
        refill(grid, {(0,2), (0,5)}, Random(1))
        self.assertEqual([r[0] for r in grid][2:], [v for y,v in enumerate(column) if y not in (2,5)])

    def test_full_games_are_playable(self):
        for seed in range(8):
            game = Game(seed)
            self.assertFalse(matches(game.grid))
            for move in range(30):
                options = legal_moves(game.grid)
                self.assertTrue(options)
                before = [r[:] for r in game.grid]
                legal_moves(game.grid)
                self.assertEqual(game.grid, before)
                self.assertTrue(game.attempt(*options[0]))
                for _ in range(100):
                    if not game.pending:
                        break
                    game.resolve()
                self.assertFalse(game.pending)
                self.assertFalse(matches(game.grid))
                self.assertEqual(game.moves, 29-move)
            self.assertGreater(game.score, 0)
            self.assertFalse(game.attempt((0,0), (1,0)))

    def test_cascade_multiplier(self):
        game = Game(1)
        game.grid = self.baseline()
        game.pending = {(x,0) for x in range(4)}
        game.resolve()
        self.assertEqual(game.score, 100)
        game.pending = {(x,0) for x in range(4)}
        game.resolve()
        self.assertEqual(game.score, 300)

    def test_dead_board_is_replaced(self):
        from unittest.mock import patch
        game = Game(1)
        game.pending = {(x,0) for x in range(4)}
        replacement = new_grid(Random(2))
        with patch('alchemy.board.matches', return_value=set()), patch('alchemy.board.legal_moves', return_value=[]), patch('alchemy.board.new_grid', return_value=replacement):
            game.resolve()
        self.assertEqual(game.grid, replacement)
        self.assertIn('fresh board', game.message)


if __name__ == '__main__':
    unittest.main()
