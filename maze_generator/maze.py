from enum import Enum

class Direction(Enum):
    UP = [-1, 0]
    DOWN = [1, 0]
    LEFT = [0, -1]
    RIGHT = [0, 1]

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

class Maze:
    def __init__(self, width: int, height: int, grid: list[list[Cell]], start_cell, end_cell):
        self.width = width
        self.height = height
        