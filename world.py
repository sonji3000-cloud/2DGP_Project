"""The map and gameplay state shared by both views."""

from dataclasses import dataclass, field
from math import ceil, floor


# The map is written from top to bottom. World y increases upwards.
TEST_MAP = tuple(reversed((
    "#############",
    "#...........#",
    "#..#....#...#",
    "#..#....#...#",
    "#...........#",
    "#.....#.....#",
    "#.....#.....#",
    "#...........#",
    "#############",
)))

PLAYER_RADIUS = 0.2
TARGET_RADIUS = 0.25


@dataclass
class Player:
    x: float = 2.5
    y: float = 4.5
    angle: float = 0.0
    muzzle_flash: float = 0.0


@dataclass
class Target:
    x: float
    y: float
    hits: int = 0
    hit_flash: float = 0.0


@dataclass
class Bullet:
    x: float
    y: float
    dx: float
    dy: float
    range_left: float


@dataclass
class World:
    tiles: tuple[str, ...] = TEST_MAP
    player: Player = field(default_factory=Player)
    targets: list[Target] = field(default_factory=lambda: [
        Target(6.5, 4.5),
        Target(8.5, 2.5),
    ])
    bullets: list[Bullet] = field(default_factory=list)

    @property
    def width(self) -> int:
        return len(self.tiles[0])

    @property
    def height(self) -> int:
        return len(self.tiles)

    def blocks_tile(self, x: int, y: int) -> bool:
        if not (0 <= x < self.width and 0 <= y < self.height):
            return True
        return self.tiles[y][x] == "#"

    def _can_stand(self, x: float, y: float) -> bool:
        for tile_y in range(floor(y - PLAYER_RADIUS), floor(y + PLAYER_RADIUS) + 1):
            for tile_x in range(floor(x - PLAYER_RADIUS), floor(x + PLAYER_RADIUS) + 1):
                if not self.blocks_tile(tile_x, tile_y):
                    continue
                nearest_x = max(tile_x, min(x, tile_x + 1))
                nearest_y = max(tile_y, min(y, tile_y + 1))
                if (x - nearest_x) ** 2 + (y - nearest_y) ** 2 < PLAYER_RADIUS ** 2:
                    return False
        return True

    def move_player(self, dx: float, dy: float) -> None:
        """Move in small steps and let an unblocked axis slide along walls."""
        steps = max(1, ceil(max(abs(dx), abs(dy)) / (PLAYER_RADIUS / 2)))
        step_x, step_y = dx / steps, dy / steps
        for _ in range(steps):
            x, y = self.player.x, self.player.y
            if step_x and self._can_stand(x + step_x, y):
                self.player.x += step_x
            if step_y and self._can_stand(self.player.x, y + step_y):
                self.player.y += step_y
