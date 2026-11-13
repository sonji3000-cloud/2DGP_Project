"""Run the PicoStein prototype with Python and Pico2d."""

from math import cos, hypot, sin, tau
from time import perf_counter

import pico2d as pico

from combat import Pistol
from render import HEIGHT, WIDTH, FirstPersonRenderer, TopDownRenderer
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


class Game:
    def __init__(self) -> None:
        self.world = World()
        self.pistol = Pistol()
        self.held: set[int] = set()
        self.first_person = False
        self.top_down_renderer = TopDownRenderer()

    def update_player(self, dt: float) -> None:
        player = self.world.player
        turn = (pico.SDLK_q in self.held) - (pico.SDLK_e in self.held)
        player.angle = (player.angle + turn * TURN_SPEED * dt) % tau

        sideways = (pico.SDLK_d in self.held) - (pico.SDLK_a in self.held)
        forward = (pico.SDLK_w in self.held) - (pico.SDLK_s in self.held)
        length = hypot(sideways, forward)
        if not length:
            return

        dx, dy = sideways, forward
        if self.first_person:
            facing_x, facing_y = cos(player.angle), sin(player.angle)
            dx = facing_x * forward + facing_y * sideways
            dy = facing_y * forward - facing_x * sideways
        distance = MOVE_SPEED * dt / length
        self.world.move_player(dx * distance, dy * distance)

    def run(self) -> None:
        pico.open_canvas(WIDTH, HEIGHT, sync=True)
        first_person_renderer = None
        try:
            first_person_renderer = FirstPersonRenderer()
            last_time = perf_counter()
            while True:
                running, pressed = read_input(self.held)
                if not running:
                    break
                now = perf_counter()
                dt = min(now - last_time, MAX_FRAME_TIME)
                last_time = now

                if pico.SDLK_TAB in pressed:
                    self.first_person = not self.first_person
                player = self.world.player
                previous_x, previous_y = player.x, player.y
                self.update_player(dt)
                walk_distance = hypot(player.x - previous_x, player.y - previous_y)
                first_person_renderer.update_walk(walk_distance if self.first_person else 0.0, dt)
                self.pistol.update(self.world, pico.SDLK_SPACE in pressed, dt)

                pico.clear_canvas()
                if self.first_person:
                    first_person_renderer.draw(self.world)
                else:
                    self.top_down_renderer.draw(self.world)
                pico.update_canvas()
        finally:
            # Release the sprite texture before Pico2d destroys its renderer.
            first_person_renderer = None
            pico.close_canvas()


if __name__ == "__main__":
    Game().run()
