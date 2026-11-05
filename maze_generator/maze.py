from enum import Enum

class Direction(Enum):
    UP = [-1, 0]
    DOWN = [1, 0]
    LEFT = [0, -1]
    RIGHT = [0, 1]

    def all():
        return [Direction.UP, Direction.DOWN, Direction.LEFT, Direction.UP]

    def opposite(self):
        match self:
            case Direction.UP: return Direction.DOWN
            case Direction.DOWN: return Direction.UP
            case Direction.LEFT: return Direction.RIGHT
            case Direction.RIGHT: return Direction.LEFT

class Cell:
    def __init__(self, row: int, col: int, walls: dict[Direction, bool], is_start: bool, is_end: bool):
        self.row = row
        self.col = col
        self.walls = walls
        self.visited = False
        self.is_start = is_start
        self.is_end = is_end

    def remove_wall(self, dir: Direction):
        self.walls[dir] = False

class SinglePathMaze:
    def __init__(self, width: int, height: int, start_r: int, start_c: int, end_r: int, end_c: int):
        self.width = width
        self.height = height
        self.start_r = start_r
        self.start_c = start_c
        self.end_r = end_r
        self.end_c = end_c
        self.cells = [[Cell(r, c, {Direction.UP: True, Direction.DOWN: True, Direction.LEFT: True, Direction.RIGHT: True}, r == start_r and c == start_c, r == end_r and c == end_c) for r in range(height)] for c in range(width)]

    def remove_wall(self, r: int, c: int, dir: Direction):
        self.cells[r][c].remove_wall(dir)
        try:
            self.cells[r + dir.value[0]][c + dir.value[1]].remove_wall(dir.opposite())
        except IndexError:
            pass

    def get_unvisited_neighbors(self, r: int, c: int):
        neighbors = []
        for dir in Direction.all():
            new_r = r + dir.value[0]
            new_c = c + dir.value[1]
            if new_r > 0 and new_r < self.height - 1 and new_c > 0 and new_c < self.height - 1 and not self.cells[new_r][new_c].visited:
                neighbors.append(self.cells[new_r][new_c])
        return neighbors


    def generate(self):
        stack: list[Cell] = []
        cell = self.cells[self.start_r][self.start_c]
        cell.visited = True
        stack.append(cell)

        while stack:
            current_cell = stack[-1]
            unvisited_neighbors = self.get_unvisited_neighbors(current_cell.row, current_cell.col)
