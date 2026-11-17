"""Pico2d drawing code for the prototype."""

from math import atan2, ceil, cos, exp, floor, hypot, pi, sin, tan, tau
from pathlib import Path

import pico2d as pico

from combat import Pistol
from world import World
from raycast import cast_wall


WIDTH, HEIGHT = 960, 576
BACKGROUND = (23, 25, 26)
FLOOR = (51, 47, 40)
WALL = (117, 109, 97)
SHOT = (255, 217, 127)
CEILING = (34, 36, 39)
SIGHT = (232, 225, 209)
COLUMN_COUNT = 160
FOV = pi / 3
NEAR = 0.01
ASSET_DIR = Path(__file__).resolve().parent / "assets"
TEXTURE_DIR = ASSET_DIR / "textures"
FLOOR_TEXTURE_PATH = TEXTURE_DIR / "floor_stone_flags.png"
TARGET_SPRITE = "enemy_wehrmacht_infantry_pistol"
TARGET_HIT_FRAME = 8
FIRST_PERSON_TARGET_CELL = 96
PISTOL_SHEET_PATH = ASSET_DIR / "luger_p08_first_person.png"
PISTOL_CELL_WIDTH = 160
PISTOL_CELL_HEIGHT = 128
PISTOL_SCALE = 2
# Front and rear sight positions in the idle cell, measured from its top left.
PISTOL_FRONT_SIGHT = (52, 45)
PISTOL_REAR_SIGHT = (68, 64)
PISTOL_BOB_CYCLE_DISTANCE = 2.4  # World units per sway cycle.
PISTOL_BOB_HORIZONTAL = 3  # Pixels.
PISTOL_BOB_VERTICAL = 4  # Pixels.
PISTOL_BOB_RESPONSE = 14.0  # Per second.
TOP_DOWN_CELL_SIZE = 64
TOP_DOWN_WALK_FRAMES = 6
TOP_DOWN_WALK_CYCLE_DISTANCE = 2.1  # World units per walk cycle.


def fill_rect(x1, y1, x2, y2, color):
    pico.draw_rectangle(x1, y1, x2, y2, *color, filled=True)


def sheet_cell(sheet: pico.Image, frame: int, width: int, height: int) -> tuple[int, int]:
    # Sprite sheets start at the top left, while Pico2d clips from the bottom.
    row, column = divmod(frame, sheet.w // width)
    return column * width, sheet.h - (row + 1) * height


class AmmoHud:
    def __init__(self) -> None:
        font_path = Path(pico.__file__).resolve().parent / "data" / "ConsolaMalgun.ttf"
        self._font = pico.load_font(str(font_path), 20)

    def draw(self, pistol: Pistol) -> None:
        fill_rect(12, 12, 324, 46, BACKGROUND)
        label = f"AMMO {pistol.rounds:02d} / {pistol.reserve:02d}"
        color = SIGHT
        if pistol.reloading:
            label += "  RELOADING"
            color = SHOT
        elif pistol.reserve and pistol.rounds < pistol.MAGAZINE_SIZE:
            label += "  [R] RELOAD"
        elif pistol.rounds == 0:
            label += "  NO AMMO"
            color = SHOT
        self._font.draw(24, 29, label, color)


class TopDownRenderer:
    def __init__(self) -> None:
        self._wall_texture = pico.load_image(str(TEXTURE_DIR / "wall_stone_top_down.png"))
        self._floor_texture = pico.load_image(str(FLOOR_TEXTURE_PATH))
        self._player_sheet = pico.load_image(str(ASSET_DIR / "luger_p08_top_down.png"))
        self._upper_sheet = pico.load_image(str(ASSET_DIR / "luger_p08_top_down_upper.png"))
        self._walk_sheet = pico.load_image(str(ASSET_DIR / "luger_p08_top_down_walk.png"))
        self._target_sheet = pico.load_image(str(ASSET_DIR / f"{TARGET_SPRITE}_top_down.png"))
        self._walk_distance = 0.0
        self._walk_angle = 0.0
        self._walking = False

    def update_walk(self, dx: float, dy: float) -> None:
        distance = hypot(dx, dy)
        self._walking = distance > 1e-6
        if self._walking:
            self._walk_distance = (self._walk_distance + distance) % TOP_DOWN_WALK_CYCLE_DISTANCE
            self._walk_angle = atan2(dy, dx)

    def draw(self, world: World, pistol_frame: int) -> None:
        fill_rect(0, 0, WIDTH - 1, HEIGHT - 1, BACKGROUND)
        scale = min((WIDTH - 80) // world.width, (HEIGHT - 80) // world.height)
        left = (WIDTH - world.width * scale) // 2
        bottom = (HEIGHT - world.height * scale) // 2

        for y, row in enumerate(world.tiles):
            for x, tile in enumerate(row):
                sx, sy = left + x * scale, bottom + y * scale
                texture = self._wall_texture if tile == "#" else self._floor_texture
                texture.draw_to_origin(sx, sy, scale, scale)

        for target in world.targets:
            x, y = left + target.x * scale, bottom + target.y * scale
            frame = TARGET_HIT_FRAME if target.hit_flash > 0 else 0
            self._draw_frame(self._target_sheet, frame, x, y, pi, scale)

        for bullet in world.bullets:
            x, y = left + bullet.x * scale, bottom + bullet.y * scale
            fill_rect(x - 2, y - 2, x + 2, y + 2, SHOT)

        player = world.player
        x, y = left + player.x * scale, bottom + player.y * scale
        if self._walking:
            walk_frame = int(TOP_DOWN_WALK_FRAMES * self._walk_distance / TOP_DOWN_WALK_CYCLE_DISTANCE)
            self._draw_frame(self._walk_sheet, walk_frame, x, y, self._walk_angle, scale)
            self._draw_frame(self._upper_sheet, pistol_frame, x, y, player.angle, scale)
        else:
            self._draw_frame(self._player_sheet, pistol_frame, x, y, player.angle, scale)

    @staticmethod
    def _draw_frame(sheet: pico.Image, frame: int, x: float, y: float, angle: float, size: int) -> None:
        cell = TOP_DOWN_CELL_SIZE
        left, bottom = sheet_cell(sheet, frame, cell, cell)
        sheet.clip_composite_draw(left, bottom, cell, cell, angle, '', x, y, size, size)


class FirstPersonRenderer:
    def __init__(self) -> None:
        self.pistol_sheet = pico.load_image(str(PISTOL_SHEET_PATH))
        self._target_sheet = pico.load_image(str(ASSET_DIR / f"{TARGET_SPRITE}_first_person.png"))
        self._walk_phase = 0.0
        self._walk_amount = 0.0

    def update_walk(self, distance: float, dt: float) -> None:
        self._walk_phase = (self._walk_phase + tau * distance / PISTOL_BOB_CYCLE_DISTANCE) % tau
        target = 1.0 if distance > 1e-6 else 0.0
        blend = 1 - exp(-PISTOL_BOB_RESPONSE * dt)
        self._walk_amount += (target - self._walk_amount) * blend

    def draw(self, world: World, pistol_frame: int) -> None:
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
        self._draw_pistol(pistol_frame)

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
        cell = FIRST_PERSON_TARGET_CELL
        for depth, side, target in sorted(projected, key=lambda item: item[0], reverse=True):
            center = WIDTH / 2 + focal_length * side / depth
            size = max(1, round(focal_length / depth))
            sprite_left = round(center - size / 2)
            left = max(0, sprite_left)
            right = min(WIDTH, sprite_left + size)
            if left >= right:
                continue

            frame = TARGET_HIT_FRAME if target.hit_flash > 0 else 0
            cell_left, cell_bottom = sheet_cell(self._target_sheet, frame, cell, cell)
            last_column = (right - 1) // column_width
            span_left = None
            # Draw contiguous visible columns in one clip, leaving wall-covered gaps.
            for column in range(left // column_width, last_column + 2):
                if column <= last_column and depth < depths[column]:
                    if span_left is None:
                        span_left = max(left, column * column_width)
                elif span_left is not None:
                    span_right = min(right, column * column_width)
                    source_left = (span_left - sprite_left) * cell // size
                    source_right = ceil((span_right - sprite_left) * cell / size)
                    self._target_sheet.clip_draw(
                        cell_left + source_left, cell_bottom, source_right - source_left, cell,
                        (span_left + span_right) / 2, HEIGHT // 2, span_right - span_left, size,
                    )
                    span_left = None

    def _draw_pistol(self, frame: int) -> None:
        center_x, center_y = WIDTH // 2, HEIGHT // 2
        left, bottom = sheet_cell(self.pistol_sheet, frame, PISTOL_CELL_WIDTH, PISTOL_CELL_HEIGHT)
        draw_width = PISTOL_CELL_WIDTH * PISTOL_SCALE
        draw_height = PISTOL_CELL_HEIGHT * PISTOL_SCALE
        front_x, front_y = PISTOL_FRONT_SIGHT
        rear_x, rear_y = PISTOL_REAR_SIGHT
        crosshair_row = PISTOL_CELL_HEIGHT - center_y / PISTOL_SCALE
        # Extend the sight line to the crosshair height before placing the sprite.
        sight_x = front_x + (crosshair_row - front_y) * (rear_x - front_x) / (rear_y - front_y)
        swing = sin(self._walk_phase)
        bob_x = PISTOL_BOB_HORIZONTAL * self._walk_amount * swing
        bob_y = -PISTOL_BOB_VERTICAL * self._walk_amount * swing ** 2
        draw_x = round(center_x + draw_width / 2 - sight_x * PISTOL_SCALE + bob_x)
        draw_y = round(draw_height / 2 + bob_y)
        self.pistol_sheet.clip_draw(left, bottom, PISTOL_CELL_WIDTH, PISTOL_CELL_HEIGHT,
                                    draw_x, draw_y, draw_width, draw_height)

        sight_color = SHOT if frame == 1 else SIGHT
        pico.draw_line(center_x - 9, center_y, center_x - 3, center_y, *sight_color)
        pico.draw_line(center_x + 3, center_y, center_x + 9, center_y, *sight_color)
        pico.draw_line(center_x, center_y - 9, center_x, center_y - 3, *sight_color)
        pico.draw_line(center_x, center_y + 3, center_x, center_y + 9, *sight_color)
