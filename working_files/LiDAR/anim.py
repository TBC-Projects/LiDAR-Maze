"""
Maze escape animation (pygame).

- The maze is a rectangle. The car starts at a random spot near its
  center, and the car does not know exactly where that is.
- The car only knows how far it has moved from its start (odometry),
  separately on each axis.
- It stops once it is more than STOP_X cells left/right of its start, or
  STOP_Y cells up/down. Those distances are set just past the farthest a
  maze wall could be, so the only way to reach them is through the exit.
- One random exit on the outer wall (different every run) opens into a
  straight path that leads out past the stopping distance.
- The solver explores one path at a time (DFS with backtracking).

Controls: SPACE = new maze, UP/DOWN = faster/slower.
"""
import random

import pygame

# ---------------- config ----------------
MAZE_COLS, MAZE_ROWS = 24, 14    # size of the rectangular maze
START_JITTER = 2                 # start is within +/- this of the maze center
CELL = 22
MARGIN_PX = 20
STEPS_PER_FRAME = 1
FPS = 30

# Fixed, known stopping distances (cells from the start, per axis).
# The farthest a maze cell can be from any possible start is
# MAZE_COLS // 2 + START_JITTER, so one more than that is always outside.
STOP_X = MAZE_COLS // 2 + START_JITTER + 1
STOP_Y = MAZE_ROWS // 2 + START_JITTER + 1

# Empty space around the maze so the exit path has room to reach STOP_X/Y.
PAD = 2 * START_JITTER + 2
COLS = MAZE_COLS + 2 * PAD
ROWS = MAZE_ROWS + 2 * PAD

BG       = (20, 20, 28)
WALL     = (230, 230, 235)
OUTSIDE  = (12, 12, 16)
VISITED  = (45, 60, 90)
PATH     = (255, 200, 60)
CAR      = (255, 90, 90)
STARTC   = (90, 200, 120)
STOPLINE = (90, 200, 120)

DIRS = {'N': (0, -1, 'S'), 'S': (0, 1, 'N'), 'E': (1, 0, 'W'), 'W': (-1, 0, 'E')}


# ---------------- maze + state ----------------
class Maze:
    def __init__(self, start):
        self.start = start
        self.walls = {(x, y): set('NSEW') for x in range(COLS) for y in range(ROWS)}
        self.corridor = set()   # cells of the exit path outside the maze

    @staticmethod
    def in_maze(cell):
        x, y = cell
        return PAD <= x < PAD + MAZE_COLS and PAD <= y < PAD + MAZE_ROWS

    def reached_stop(self, cell):
        """All the car can measure: how far it is from its start, per axis."""
        dx = abs(cell[0] - self.start[0])
        dy = abs(cell[1] - self.start[1])
        return dx >= STOP_X or dy >= STOP_Y

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
    cx = PAD + MAZE_COLS // 2
    cy = PAD + MAZE_ROWS // 2
    return (cx + random.randint(-START_JITTER, START_JITTER),
            cy + random.randint(-START_JITTER, START_JITTER))


# ---------------- generation ----------------
def gen_backtracker(maze, view):
    """Randomized DFS, carving only inside the rectangle."""
    start = maze.start
    stack = [start]
    view.visited = {start}
    while stack:
        cell = stack[-1]
        view.current = cell
        options = [(d, n, opp) for d, n, opp in maze.neighbors(cell)
                   if n not in view.visited and maze.in_maze(n)]
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
    """Open one random spot on the outer wall, then a straight path outward."""
    edges = [(c, d, n, opp) for c in maze.walls if maze.in_maze(c)
             for d, n, opp in maze.neighbors(c) if not maze.in_maze(n)]
    cell, d, n, opp = random.choice(edges)
    dx, dy, _ = DIRS[d]
    while n in maze.walls:              # carve straight out to the grid edge
        maze.remove_wall(cell, d, n, opp)
        maze.corridor.add(n)
        cell, n = n, (n[0] + dx, n[1] + dy)


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
        if maze.reached_stop(cell):            # far enough from start: escaped
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
    return pygame.Rect(MARGIN_PX + x * CELL, MARGIN_PX + y * CELL, CELL, CELL)


def draw(screen, maze, view):
    screen.fill(BG)

    for cell in maze.walls:
        if not maze.in_maze(cell) and cell not in maze.corridor:
            screen.fill(OUTSIDE, cell_rect(cell))
    for c in view.visited:
        screen.fill(VISITED, cell_rect(c))
    for c in view.path:
        screen.fill(PATH, cell_rect(c).inflate(-CELL // 2, -CELL // 2))
    screen.fill(STARTC, cell_rect(maze.start).inflate(-6, -6))
    if view.current:
        screen.fill(CAR, cell_rect(view.current).inflate(-6, -6))

    for cell, ws in maze.walls.items():
        if not maze.in_maze(cell) and cell not in maze.corridor:
            continue
        r = cell_rect(cell)
        if 'N' in ws: pygame.draw.line(screen, WALL, r.topleft, r.topright, 2)
        if 'S' in ws: pygame.draw.line(screen, WALL, r.bottomleft, r.bottomright, 2)
        if 'W' in ws: pygame.draw.line(screen, WALL, r.topleft, r.bottomleft, 2)
        if 'E' in ws: pygame.draw.line(screen, WALL, r.topright, r.bottomright, 2)

    # the stopping boundary: crossing this outline means the car is done
    sx, sy = maze.start
    stop = pygame.Rect(cell_rect((sx - STOP_X + 1, sy - STOP_Y + 1)).topleft,
                       ((2 * STOP_X - 1) * CELL, (2 * STOP_Y - 1) * CELL))
    pygame.draw.rect(screen, STOPLINE, stop, 1)


# ---------------- main loop ----------------
def phases():
    """Generate the maze, then solve it."""
    maze, view = Maze(random_start()), View()
    yield maze, view, gen_backtracker(maze, view)
    yield maze, view, solve_dfs(maze, view)


def main():
    pygame.init()
    screen = pygame.display.set_mode((COLS * CELL + 2 * MARGIN_PX,
                                      ROWS * CELL + 2 * MARGIN_PX))
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