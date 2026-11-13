"""Pico2d drawing code for the prototype."""

from math import cos, sin

import pico2d as pico

from world import PLAYER_RADIUS, TARGET_RADIUS, World


WIDTH, HEIGHT = 960, 576
BACKGROUND = (23, 25, 26)
FLOOR = (51, 47, 40)
WALL = (117, 109, 97)
PLAYER = (94, 207, 185)
TARGET = (224, 116, 86)


def fill_rect(x1, y1, x2, y2, color):
    pico.draw_rectangle(x1, y1, x2, y2, *color, filled=True)


def draw_top_down(world: World) -> None:
    fill_rect(0, 0, WIDTH - 1, HEIGHT - 1, BACKGROUND)
    scale = min((WIDTH - 80) // world.width, (HEIGHT - 80) // world.height)
    left = (WIDTH - world.width * scale) // 2
    bottom = (HEIGHT - world.height * scale) // 2

    for y, row in enumerate(world.tiles):
        for x, tile in enumerate(row):
            sx, sy = left + x * scale, bottom + y * scale
            color = WALL if tile == "#" else FLOOR
            fill_rect(sx, sy, sx + scale - 2, sy + scale - 2, color)

    for target in world.targets:
        x, y = left + target.x * scale, bottom + target.y * scale
        size = TARGET_RADIUS * scale
        fill_rect(x - size, y - size, x + size, y + size, TARGET)

    player = world.player
    x, y = left + player.x * scale, bottom + player.y * scale
    size = PLAYER_RADIUS * scale
    fill_rect(x - size, y - size, x + size, y + size, PLAYER)
    aim_length = scale * 0.65
    pico.draw_line(x, y, x + cos(player.angle) * aim_length,
                   y + sin(player.angle) * aim_length, *PLAYER)
