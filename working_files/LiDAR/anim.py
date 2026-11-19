"""
Maze escape animation (pygame).

- The car starts at a random spot near the middle of the grid.
- The maze is a circle of radius RADIUS around that start, with one
  random exit on its edge (different every run).
- The solver only knows its distance from where it started. It explores
  one path at a time (DFS with backtracking) and stops once it is
  RADIUS cells away from the start.

Controls: SPACE = new maze, UP/DOWN = faster/slower.
"""
import math
import random

import pygame

# ---------------- config ----------------
COLS, ROWS = 30, 20
CELL = 24
MARGIN = 20
RADIUS = 7               # fixed, known exit distance from the start (cells)
START_JITTER = 2         # start lands within +/- this many cells of the middle
STEPS_PER_FRAME = 1
FPS = 30

BG      = (20, 20, 28)
WALL    = (230, 230, 235)
OUTSIDE = (12, 12, 16)
VISITED = (45, 60, 90)
PATH    = (255, 200, 60)
CAR     = (255, 90, 90)
STARTC  = (90, 200, 120)

DIRS = {'N': (0, -1, 'S'), 'S': (0, 1, 'N'), 'E': (1, 0, 'W'), 'W': (-1, 0, 'E')}


# ---------------- maze + state ----------------
class Maze:
    def __init__(self, cols, rows, start):
        self.cols, self.rows = cols, rows
        self.start = start
        self.walls = {(x, y): set('NSEW') for x in range(cols) for y in range(rows)}

    def dist(self, cell):
        """Straight-line distance from the start: all the car can measure."""
        return math.hypot(cell[0] - self.start[0], cell[1] - self.start[1])

    def inside(self, cell):
        return self.dist(cell) < RADIUS

    def neighbors(self, cell):
        """All in-bounds neighbors, regardless of walls."""
        x, y = cell
        for d, (dx, dy, opp) in DIRS.items():
            n = (x + dx, y + dy)
            if n in self.walls:
                yield d, n, opp

    def open_neighbors(self, cell):
        """Neighbors reachable without crossing a wall."""
        for d, n, _ in self.neighbors(cell):
            if d not in self.walls[cell]:
                yield n

    def remove_wall(self, cell, d, n, opp):
        self.walls[cell].discard(d)
        self.walls[n].discard(opp)


class View:
    """What the renderer draws for the current step."""
    def __init__(self):
        self.current = None
        self.visited = set()
        self.path = []


def random_start():
    return (COLS // 2 + random.randint(-START_JITTER, START_JITTER),
            ROWS // 2 + random.randint(-START_JITTER, START_JITTER))


# ---------------- generation ----------------
def gen_backtracker(maze, view):
    """Randomized DFS, carving only inside the circle around the start."""
    start = maze.start
    stack = [start]
    view.visited = {start}
    while stack:
        cell = stack[-1]
        view.current = cell
        options = [(d, n, opp) for d, n, opp in maze.neighbors(cell)
                   if n not in view.visited and maze.inside(n)]
        if not options:
            stack.pop()
        else:
            d, n, opp = random.choice(options)
            maze.remove_wall(cell, d, n, opp)
            view.visited.add(n)
            stack.append(n)
        yield
    open_random_exit(maze)
    view.current = None
    view.visited = set()


def open_random_exit(maze):
    """Open one random wall on the edge of the circle: the only way out."""
    edges = [(c, d, n, opp) for c in maze.walls if maze.inside(c)
             for d, n, opp in maze.neighbors(c) if not maze.inside(n)]
    maze.remove_wall(*random.choice(edges))


# ---------------- solving ----------------
def solve_dfs(maze, view):
    """One path at a time. The stack is the car's current path."""
    start = maze.start
    stack = [start]
    view.visited = {start}
    while stack:
        cell = stack[-1]
        view.current = cell
        view.path = list(stack)
        if maze.dist(cell) >= RADIUS:          # far enough from start: escaped
            break
        unexplored = [n for n in maze.open_neighbors(cell) if n not in view.visited]
        if unexplored:
            n = random.choice(unexplored)      # or a fixed order, e.g. left-first
            view.visited.add(n)
            stack.append(n)
        else:
            stack.pop()                        # dead end: back up
        yield


# ---------------- drawing ----------------
def cell_rect(cell):
    x, y = cell
    return pygame.Rect(MARGIN + x * CELL, MARGIN + y * CELL, CELL, CELL)


def draw(screen, maze, view):
    screen.fill(BG)

    for cell in maze.walls:
        if not maze.inside(cell):
            screen.fill(OUTSIDE, cell_rect(cell))
    for c in view.visited:
        screen.fill(VISITED, cell_rect(c))
    for c in view.path:
        screen.fill(PATH, cell_rect(c).inflate(-CELL // 2, -CELL // 2))
    screen.fill(STARTC, cell_rect(maze.start).inflate(-6, -6))
    if view.current:
        screen.fill(CAR, cell_rect(view.current).inflate(-6, -6))

    # draw walls only around the maze area, so the outside stays clean
    for cell, ws in maze.walls.items():
        if not maze.inside(cell):
            continue
        r = cell_rect(cell)
        if 'N' in ws: pygame.draw.line(screen, WALL, r.topleft, r.topright, 2)
        if 'S' in ws: pygame.draw.line(screen, WALL, r.bottomleft, r.bottomright, 2)
        if 'W' in ws: pygame.draw.line(screen, WALL, r.topleft, r.bottomleft, 2)
        if 'E' in ws: pygame.draw.line(screen, WALL, r.topright, r.bottomright, 2)


# ---------------- main loop ----------------
def phases():
    """Generate the maze, then solve it."""
    maze, view = Maze(COLS, ROWS, random_start()), View()
    yield maze, view, gen_backtracker(maze, view)
    yield maze, view, solve_dfs(maze, view)


def main():
    assert RADIUS + START_JITTER < min(COLS, ROWS) // 2, "circle won't fit in the grid"

    pygame.init()
    screen = pygame.display.set_mode((COLS * CELL + 2 * MARGIN,
                                      ROWS * CELL + 2 * MARGIN))
    pygame.display.set_caption("Maze escape — SPACE: new maze, UP/DOWN: speed")
    clock = pygame.time.Clock()
    speed = STEPS_PER_FRAME

    stages = phases()
    maze, view, algo = next(stages)

    running = True
    while running:
        for e in pygame.event.get():
            if e.type == pygame.QUIT:
                running = False
            elif e.type == pygame.KEYDOWN:
                if e.key == pygame.K_SPACE:
                    stages = phases()
                    maze, view, algo = next(stages)
                elif e.key == pygame.K_UP:
                    speed = min(speed * 2, 256)
                elif e.key == pygame.K_DOWN:
                    speed = max(speed // 2, 1)

        if algo is not None:
            for _ in range(speed):
                try:
                    next(algo)
                except StopIteration:
                    _, _, algo = next(stages, (None, None, None))
                    break

        draw(screen, maze, view)
        pygame.display.flip()
        clock.tick(FPS)

    pygame.quit()


if __name__ == "__main__":
    main()