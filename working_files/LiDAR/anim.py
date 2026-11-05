"""
Animated maze generation + solving with pygame.

Pattern: every algorithm is a generator that yields after each step.
The main loop advances the active generator a few steps per frame,
then redraws. Algorithms never import pygame; drawing never knows
which algorithm is running.
"""
import random
from collections import deque

import pygame

# ---------------- config ----------------
COLS, ROWS = 30, 20
CELL = 24
MARGIN = 20
STEPS_PER_FRAME = 3      # raise to speed up, lower to slow down
FPS = 60

BG       = (20, 20, 28)
WALL     = (230, 230, 235)
CURRENT  = (255, 90, 90)
VISITED  = (45, 60, 90)
FRONTIER = (90, 140, 220)
PATH     = (255, 200, 60)

DIRS = {'N': (0, -1, 'S'), 'S': (0, 1, 'N'), 'E': (1, 0, 'W'), 'W': (-1, 0, 'E')}


# ---------------- shared state ----------------
class Maze:
    def __init__(self, cols, rows):
        self.cols, self.rows = cols, rows
        self.walls = {(x, y): set('NSEW') for x in range(cols) for y in range(rows)}

    def neighbors(self, cell):
        """All in-bounds neighbors, regardless of walls."""
        x, y = cell
        for d, (dx, dy, opp) in DIRS.items():
            n = (x + dx, y + dy)
            if n in self.walls:
                yield d, n, opp

    def open_neighbors(self, cell):
        """Neighbors you can actually walk to (no wall between)."""
        for d, n, _ in self.neighbors(cell):
            if d not in self.walls[cell]:
                yield n


class View:
    """Everything the renderer needs to know about the current step."""
    def __init__(self):
        self.current = None
        self.visited = set()
        self.frontier = set()
        self.path = []


# ---------------- algorithms (generators) ----------------
def gen_backtracker(maze, view):
    start = (0, 0)
    stack = [start]
    view.visited = {start}
    while stack:
        cell = stack[-1]
        view.current = cell
        options = [(d, n, opp) for d, n, opp in maze.neighbors(cell)
                   if n not in view.visited]
        if not options:
            stack.pop()
        else:
            d, n, opp = random.choice(options)
            maze.walls[cell].discard(d)
            maze.walls[n].discard(opp)
            view.visited.add(n)
            stack.append(n)
        yield                       # <- one animation step
    view.current = None


def solve_bfs(maze, view, start, goal):
    """Example solver. Replace with yours; the only rules are:
    update `view` as you go and `yield` once per step."""
    view.visited, view.frontier, view.path = set(), {start}, []
    queue = deque([start])
    came_from = {start: None}
    while queue:
        cell = queue.popleft()
        view.current = cell
        view.frontier.discard(cell)
        view.visited.add(cell)
        if cell == goal:
            break
        for n in maze.open_neighbors(cell):
            if n not in came_from:
                came_from[n] = cell
                queue.append(n)
                view.frontier.add(n)
        yield
    # reconstruct path, animating it back from the goal
    cell = goal
    while cell is not None:
        view.path.append(cell)
        cell = came_from.get(cell)
        yield
    view.current = None


# ---------------- drawing ----------------
def cell_rect(cell):
    x, y = cell
    return pygame.Rect(MARGIN + x * CELL, MARGIN + y * CELL, CELL, CELL)


def draw(screen, maze, view):
    screen.fill(BG)

    for c in view.visited:
        screen.fill(VISITED, cell_rect(c))
    for c in view.frontier:
        screen.fill(FRONTIER, cell_rect(c))
    for c in view.path:
        screen.fill(PATH, cell_rect(c).inflate(-CELL // 2, -CELL // 2))
    if view.current:
        screen.fill(CURRENT, cell_rect(view.current).inflate(-4, -4))

    for cell, ws in maze.walls.items():
        r = cell_rect(cell)
        if 'N' in ws: pygame.draw.line(screen, WALL, r.topleft, r.topright, 2)
        if 'S' in ws: pygame.draw.line(screen, WALL, r.bottomleft, r.bottomright, 2)
        if 'W' in ws: pygame.draw.line(screen, WALL, r.topleft, r.bottomleft, 2)
        if 'E' in ws: pygame.draw.line(screen, WALL, r.topright, r.bottomright, 2)


# ---------------- main loop ----------------
def main():
    pygame.init()
    screen = pygame.display.set_mode((COLS * CELL + 2 * MARGIN,
                                      ROWS * CELL + 2 * MARGIN))
    pygame.display.set_caption("Maze — SPACE: restart, UP/DOWN: speed")
    clock = pygame.time.Clock()
    speed = STEPS_PER_FRAME

    def phases():
        """Chain the stages: generate, then solve."""
        maze, view = Maze(COLS, ROWS), View()
        yield maze, view, gen_backtracker(maze, view)
        yield maze, view, solve_bfs(maze, view, (0, 0), (COLS - 1, ROWS - 1))

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
                    speed = min(speed * 2, 1024)
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
