"""Run the PicoStein prototype with Python and Pico2d."""

from math import hypot, tau
from time import perf_counter

import pico2d as pico

from render import HEIGHT, WIDTH, draw_top_down
from world import World


MOVE_SPEED = 3.5  # Tiles per second.
TURN_SPEED = 2.8  # Radians per second.
MAX_FRAME_TIME = 0.05


def read_input(held: set[int]) -> tuple[bool, set[int]]:
    pressed = set()
    for event in pico.get_events():
        if event.type == pico.SDL_QUIT:
            return False, pressed
        if event.type == pico.SDL_KEYDOWN:
            if event.key == pico.SDLK_ESCAPE:
                return False, pressed
            if event.key not in held:
                pressed.add(event.key)
            held.add(event.key)
        elif event.type == pico.SDL_KEYUP:
            held.discard(event.key)
    return True, pressed


def update_player(world: World, held: set[int], dt: float) -> None:
    turn = (pico.SDLK_q in held) - (pico.SDLK_e in held)
    world.player.angle = (world.player.angle + turn * TURN_SPEED * dt) % tau

    dx = (pico.SDLK_d in held) - (pico.SDLK_a in held)
    dy = (pico.SDLK_w in held) - (pico.SDLK_s in held)
    length = hypot(dx, dy)
    if length:
        distance = MOVE_SPEED * dt / length
        world.move_player(dx * distance, dy * distance)


def main() -> None:
    world = World()
    held: set[int] = set()
    pico.open_canvas(WIDTH, HEIGHT, sync=True)
    try:
        last_time = perf_counter()
        while True:
            running, _ = read_input(held)
            if not running:
                break
            now = perf_counter()
            dt = min(now - last_time, MAX_FRAME_TIME)
            last_time = now

            update_player(world, held, dt)

            pico.clear_canvas()
            draw_top_down(world)
            pico.update_canvas()
    finally:
        pico.close_canvas()


if __name__ == "__main__":
    main()
