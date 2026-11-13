"""Trace a ray through the shared tile grid with DDA."""

from dataclasses import dataclass
from math import floor, inf

from world import World


@dataclass(frozen=True)
class WallHit:
    distance: float
    vertical: bool


def cast_wall(world: World, x: float, y: float, dx: float, dy: float,
              max_distance: float = inf) -> WallHit | None:
    """Return the first blocked tile at (x, y) + distance * (dx, dy)."""
    if not (dx or dy):
        raise ValueError("A ray needs a direction")

    tile_x, tile_y = floor(x), floor(y)
    if world.blocks_tile(tile_x, tile_y):
        return WallHit(0.0, True)

    step_x = 1 if dx > 0 else -1
    step_y = 1 if dy > 0 else -1
    delta_x = abs(1 / dx) if dx else inf
    delta_y = abs(1 / dy) if dy else inf
    next_x = (tile_x + (dx > 0) - x) / dx if dx else inf
    next_y = (tile_y + (dy > 0) - y) / dy if dy else inf

    while min(next_x, next_y) <= max_distance:
        if next_x == next_y:
            distance = next_x
            # A ray through a corner also touches the two neighboring tiles.
            if world.blocks_tile(tile_x + step_x, tile_y):
                return WallHit(distance, True)
            if world.blocks_tile(tile_x, tile_y + step_y):
                return WallHit(distance, False)
            tile_x += step_x
            tile_y += step_y
            next_x += delta_x
            next_y += delta_y
            vertical = True
        elif next_x < next_y:
            distance = next_x
            tile_x += step_x
            next_x += delta_x
            vertical = True
        else:
            distance = next_y
            tile_y += step_y
            next_y += delta_y
            vertical = False

        if world.blocks_tile(tile_x, tile_y):
            return WallHit(distance, vertical)
    return None
