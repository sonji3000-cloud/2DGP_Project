"""Pico2d drawing code for the prototype."""

from math import ceil, cos, floor, pi, sin, tan

import pico2d as pico

from world import PLAYER_RADIUS, TARGET_RADIUS, Target, World
from raycast import cast_wall


WIDTH, HEIGHT = 960, 576
BACKGROUND = (23, 25, 26)
FLOOR = (51, 47, 40)
WALL = (117, 109, 97)
PLAYER = (94, 207, 185)
TARGET = (224, 116, 86)
TARGET_HIT = (161, 114, 78)
SHOT = (255, 217, 127)
CEILING = (34, 36, 39)
SIGHT = (232, 225, 209)
PISTOL_FRAME = (39, 42, 46)
PISTOL_SLIDE = (82, 87, 93)
COLUMN_COUNT = 160
FOV = pi / 3
NEAR = 0.01


def fill_rect(x1, y1, x2, y2, color):
    pico.draw_rectangle(x1, y1, x2, y2, *color, filled=True)


def target_color(target: Target) -> tuple[int, int, int]:
    if target.hit_flash > 0:
        return SHOT
    return TARGET_HIT if target.hits else TARGET


class TopDownRenderer:
    def draw(self, world: World) -> None:
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
            fill_rect(x - size, y - size, x + size, y + size, target_color(target))

        for bullet in world.bullets:
            x, y = left + bullet.x * scale, bottom + bullet.y * scale
            fill_rect(x - 2, y - 2, x + 2, y + 2, SHOT)

        player = world.player
        x, y = left + player.x * scale, bottom + player.y * scale
        size = PLAYER_RADIUS * scale
        fill_rect(x - size, y - size, x + size, y + size, PLAYER)
        aim_length = scale * 0.65
        pico.draw_line(x, y, x + cos(player.angle) * aim_length,
                       y + sin(player.angle) * aim_length, *PLAYER)


class FirstPersonRenderer:
    def draw(self, world: World) -> None:
        horizon = HEIGHT // 2
        fill_rect(0, 0, WIDTH - 1, horizon - 1, FLOOR)
        fill_rect(0, horizon, WIDTH - 1, HEIGHT - 1, CEILING)

        player = world.player
        facing_x, facing_y = cos(player.angle), sin(player.angle)
        plane = tan(FOV / 2)
        focal_length = WIDTH / (2 * plane)
        depths = []
        for column in range(COLUMN_COUNT):
            offset = (2 * (column + 0.5) / COLUMN_COUNT - 1) * plane
            ray_x = facing_x + facing_y * offset
            ray_y = facing_y - facing_x * offset
            # The ray is unnormalized, so the hit parameter is forward depth.
            hit = cast_wall(world, player.x, player.y, ray_x, ray_y)
            if hit is None:
                depths.append(float("inf"))
                continue
            depths.append(hit.distance)
            half_height = focal_length / (2 * max(hit.distance, NEAR))
            brightness = max(0.26, 1.0 / (1 + hit.distance * 0.15))
            if not hit.vertical:
                brightness *= 0.76
            color = tuple(int(channel * brightness) for channel in WALL)
            left = column * WIDTH // COLUMN_COUNT
            right = (column + 1) * WIDTH // COLUMN_COUNT - 1
            fill_rect(left, max(0, ceil(horizon - half_height)),
                      right, min(HEIGHT - 1, floor(horizon + half_height)), color)

        self._draw_targets(world, facing_x, facing_y, focal_length, depths)
        self._draw_pistol(player.muzzle_flash > 0)

    def _draw_targets(self, world, facing_x, facing_y, focal_length, depths):
        player = world.player
        projected = []
        for target in world.targets:
            dx, dy = target.x - player.x, target.y - player.y
            depth = dx * facing_x + dy * facing_y
            if depth > NEAR:
                side = dx * facing_y - dy * facing_x
                projected.append((depth, side, target))

        column_width = WIDTH // COLUMN_COUNT
        for depth, side, target in sorted(projected, key=lambda item: item[0], reverse=True):
            center = WIDTH / 2 + focal_length * side / depth
            half_width = focal_length * TARGET_RADIUS / depth
            left = max(0, ceil(center - half_width))
            right = min(WIDTH - 1, floor(center + half_width))
            if left > right:
                continue

            bottom = max(0, ceil(HEIGHT / 2 - 0.5 * focal_length / depth))
            top = min(HEIGHT - 1, floor(HEIGHT / 2 + 0.24 * focal_length / depth))
            color = target_color(target)
            for column in range(left // column_width, right // column_width + 1):
                if depth < depths[column]:
                    strip_left = max(left, column * column_width)
                    strip_right = min(right, (column + 1) * column_width - 1)
                    fill_rect(strip_left, bottom, strip_right, top, color)

    @staticmethod
    def _draw_pistol(firing: bool) -> None:
        center_x, center_y = WIDTH // 2, HEIGHT // 2
        sight_color = SHOT if firing else SIGHT
        pico.draw_line(center_x - 9, center_y, center_x - 3, center_y, *sight_color)
        pico.draw_line(center_x + 3, center_y, center_x + 9, center_y, *sight_color)
        pico.draw_line(center_x, center_y - 9, center_x, center_y - 3, *sight_color)
        pico.draw_line(center_x, center_y + 3, center_x, center_y + 9, *sight_color)

        # A placeholder pistol made from canvas primitives.
        recoil = 8 if firing else 0
        slide_top = 108 + recoil
        fill_rect(center_x - 34, 0, center_x + 34, 74 + recoil, PISTOL_FRAME)
        fill_rect(center_x - 22, 68 + recoil, center_x + 22, slide_top, PISTOL_SLIDE)
        fill_rect(center_x - 4, slide_top, center_x + 4, slide_top + 8, PISTOL_FRAME)
        if firing:
            fill_rect(center_x - 13, slide_top + 12, center_x + 13, slide_top + 25, SHOT)
