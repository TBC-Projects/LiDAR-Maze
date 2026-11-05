from enum import Enum
import random

class Direction(Enum):
    UP = (-1, 0)
    DOWN = (1, 0)
    LEFT = (0, -1)
    RIGHT = (0, 1)

    def opposite(self) -> "Direction":
        match self:
            case Direction.UP: return Direction.DOWN
            case Direction.DOWN: return Direction.UP
            case Direction.LEFT: return Direction.RIGHT
            case Direction.RIGHT: return Direction.LEFT

class Cell:
    def __init__(self, row: int, col: int, is_start: bool, is_end: bool):
        self.row = row
        self.col = col
        self.walls = {d: True for d in Direction}
        self.visited = False
        self.is_start = is_start
        self.is_end = is_end

    def remove_wall(self, direction: Direction):
        self.walls[direction] = False

class SingleSolutionMaze:
    def __init__(self, width: int, height: int, start_r: int, start_c: int, end_r: int, end_c: int):
        self.width = width
        self.height = height
        self.start_r = start_r
        self.start_c = start_c
        self.end_r = end_r
        self.end_c = end_c
        self.check_params()
        self.cells = [[Cell(r, c, r == start_r and c == start_c, r == end_r and c == end_c) for c in range(width)] for r in range(height)]
        self.generate()

    def check_params(self):
        if self.width <= 0 or self.height <= 0:
            raise ValueError("maze dimensions must be positive")

        if not self.in_bounds(self.start_r, self.start_c):
            raise ValueError("start is out of bounds")

        if not self.in_bounds(self.end_r, self.end_c):
            raise ValueError("end is out of bounds")

        if (self.start_r, self.start_c) == (self.end_r, self.end_c):
            raise ValueError("start and end cannot be the same cell")

    def in_bounds(self, r: int, c: int) -> bool:
        return 0 <= r < self.height and 0 <= c < self.width

    def get_unvisited_neighbors(self, r: int, c: int) -> list[tuple[Direction, Cell]]:
        neighbors: list[tuple[Direction, Cell]] = []
        for direction in Direction:
            dr, dc = direction.value
            new_r, new_c = r + dr, c + dc
            if self.in_bounds(new_r, new_c) and not self.cells[new_r][new_c].visited:
                neighbors.append((direction, self.cells[new_r][new_c]))
        return neighbors

    def generate(self):
        stack: list[Cell] = []
        cell = self.cells[self.start_r][self.start_c]
        cell.visited = True
        stack.append(cell)

        while stack:
            current_cell = stack[-1]
            unvisited_neighbors = self.get_unvisited_neighbors(current_cell.row, current_cell.col)
            if unvisited_neighbors:
                direction, next_cell = random.choice(unvisited_neighbors)
                current_cell.remove_wall(direction)
                next_cell.remove_wall(direction.opposite())
                next_cell.visited = True
                if not next_cell.is_end:
                    stack.append(next_cell)
            else:
                stack.pop()

    def __str__(self) -> str:
        output = []
        top_line = "+"

        for c in range(self.width):
            top_line += "---+" if self.cells[0][c].walls[Direction.UP] else "   +"
        output.append(top_line)

        for r in range(self.height):
            row_mid = "|" if self.cells[r][0].walls[Direction.LEFT] else " "
            row_bot = "+"

            for c in range(self.width):
                cell = self.cells[r][c]

                if cell.is_start:
                    body = " S "
                elif cell.is_end:
                    body = " E "
                else:
                    body = "   "

                right_wall = "|" if cell.walls[Direction.RIGHT] else " "
                row_mid += body + right_wall

                bottom_wall = "---+" if cell.walls[Direction.DOWN] else "   +"
                row_bot += bottom_wall

            output.append(row_mid)
            output.append(row_bot)

        return "\n".join(output)

if __name__ == "__main__":
    maze = SingleSolutionMaze(15, 15, 0, 0, 14, 14)
    print(maze)
    assert maze.cells[maze.end_r][maze.end_c].visited