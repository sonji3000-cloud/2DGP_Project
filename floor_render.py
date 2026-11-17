"""Draw the first-person floor by sampling a repeating texture in world space."""

from array import array
from ctypes import c_ubyte, string_at
from math import floor
from pathlib import Path

import sdl2
from pico2d import pico2d as pico
from sdl2.sdlimage import IMG_Load


FLOOR_SAMPLE_SIZE = 4
FLOOR_SHADE_LEVELS = 16
FLOOR_FOG_DISTANCE = 24.0
FLOOR_FOG_COLOR = (51, 47, 40)


def _read_rgba(path: Path) -> tuple[int, int, bytes]:
    source = IMG_Load(str(path).encode("utf-8"))
    if not source:
        raise OSError(f"Could not load floor texture: {path}")
    try:
        converted = sdl2.SDL_ConvertSurfaceFormat(source, sdl2.SDL_PIXELFORMAT_RGBA32, 0)
    finally:
        sdl2.SDL_FreeSurface(source)
    if not converted:
        raise OSError(f"Could not convert floor texture to RGBA: {path}")
    try:
        surface = converted.contents
        return surface.w, surface.h, b"".join(
            string_at(surface.pixels + row * surface.pitch, surface.w * 4)
            for row in range(surface.h)
        )
    finally:
        sdl2.SDL_FreeSurface(converted)


class FloorRenderer:
    def __init__(self, path: Path, width: int, height: int, camera_plane: float) -> None:
        self._width = width
        self._height = height // 2
        self._sample_width = width // FLOOR_SAMPLE_SIZE
        self._sample_height = self._height // FLOOR_SAMPLE_SIZE
        self._step_u = 2 * camera_plane / self._sample_width
        self._left_u = -camera_plane + self._step_u / 2

        focal_length = width / (2 * camera_plane)
        self._rows = []
        for row in range(self._sample_height):
            below_horizon = (row + 0.5) * self._height / self._sample_height
            # The eye is half a tile above the floor and the horizon is centered.
            depth = 0.5 * focal_length / below_horizon
            visibility = max(0.0, 1 - depth / FLOOR_FOG_DISTANCE)
            shade = round(visibility * (FLOOR_SHADE_LEVELS - 1))
            self._rows.append((depth, shade))

        self._tile_width, self._tile_height, rgba = _read_rgba(path)
        self._tiles = []
        for level in range(FLOOR_SHADE_LEVELS):
            weight = level / (FLOOR_SHADE_LEVELS - 1)
            tile = bytearray(rgba)
            for pixel in range(0, len(tile), 4):
                for channel, fog in enumerate(FLOOR_FOG_COLOR):
                    tile[pixel + channel] = round(fog + weight * (tile[pixel + channel] - fog))
                tile[pixel + 3] = 255
            colors = array("I")
            colors.frombytes(tile)
            self._tiles.append(colors)

        self._pixels = array("I", [self._tiles[0][0]]) * (self._sample_width * self._sample_height)
        self._buffer = (c_ubyte * (len(self._pixels) * 4)).from_buffer(self._pixels)
        texture = sdl2.SDL_CreateTexture(pico.renderer, sdl2.SDL_PIXELFORMAT_RGBA32,
                                        sdl2.SDL_TEXTUREACCESS_STREAMING,
                                        self._sample_width, self._sample_height)
        if not texture:
            raise OSError(sdl2.SDL_GetError().decode("utf-8", errors="replace"))
        self._image = pico.Image(texture)

    def draw(self, x: float, y: float, facing_x: float, facing_y: float) -> None:
        tile_width, tile_height = self._tile_width, self._tile_height
        left_x = facing_x + facing_y * self._left_u
        left_y = facing_y - facing_x * self._left_u

        for row, (depth, shade) in enumerate(self._rows):
            if shade == 0:
                continue  # Distant rows always keep the fog color.
            tile = self._tiles[shade]
            sample_x = (x + left_x * depth) * tile_width
            sample_y = (y + left_y * depth) * tile_height
            step_x = facing_y * self._step_u * depth * tile_width
            step_y = -facing_x * self._step_u * depth * tile_height
            offset = row * self._sample_width
            for column in range(self._sample_width):
                tex_x = floor(sample_x) % tile_width
                tex_y = tile_height - 1 - floor(sample_y) % tile_height
                self._pixels[offset + column] = tile[tex_y * tile_width + tex_x]
                sample_x += step_x
                sample_y += step_y

        if sdl2.SDL_UpdateTexture(self._image.texture, None, self._buffer, self._sample_width * 4) != 0:
            raise OSError(sdl2.SDL_GetError().decode("utf-8", errors="replace"))
        self._image.draw_to_origin(0, 0, self._width, self._height)
