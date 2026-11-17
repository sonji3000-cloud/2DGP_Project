"""Update pistol fire and projectile impacts in world coordinates."""

from math import cos, inf, sin, sqrt

from raycast import cast_wall
from world import TARGET_RADIUS, Bullet, Target, World


class Pistol:
    MAGAZINE_SIZE = 8
    STARTING_RESERVE = 24
    FIRE_INTERVAL = 0.23
    FIRE_FRAME_ENDS = (0.040, 0.090, 0.135, 0.180)
    RELOAD_FRAME_ENDS = (0.090, 0.190, 0.300, 0.440, 0.570, 0.620, 0.670, 0.760, 0.880)
    BULLET_SPEED = 16.0
    BULLET_RANGE = 18.0
    TARGET_FLASH_TIME = 0.22

    def __init__(self) -> None:
        self.rounds = self.MAGAZINE_SIZE
        self.reserve = self.STARTING_RESERVE
        self.cooldown = 0.0
        self._time_since_shot = inf
        self._reload_elapsed: float | None = None

    @property
    def reloading(self) -> bool:
        return self._reload_elapsed is not None

    @property
    def sprite_frame(self) -> int:
        # Both pistol sheets use the same slots: idle 0, fire 1–4, reload 5–13.
        if self._reload_elapsed is not None:
            for frame, end in enumerate(self.RELOAD_FRAME_ENDS, start=5):
                if self._reload_elapsed < end:
                    return frame
        else:
            for frame, end in enumerate(self.FIRE_FRAME_ENDS, start=1):
                if self._time_since_shot < end:
                    return frame
        return 0

    def update(self, world: World, fire_pressed: bool, dt: float, *, reload_pressed: bool = False) -> None:
        self.cooldown = max(0.0, self.cooldown - dt)
        self._time_since_shot += dt
        for target in world.targets:
            target.hit_flash = max(0.0, target.hit_flash - dt)

        world.bullets[:] = [
            bullet for bullet in world.bullets if self._advance(world, bullet, dt)
        ]

        if self._reload_elapsed is not None:
            self._reload_elapsed += dt
            if self._reload_elapsed < self.RELOAD_FRAME_ENDS[-1]:
                return
            transferred = min(self.MAGAZINE_SIZE - self.rounds, self.reserve)
            self.rounds += transferred
            self.reserve -= transferred
            self._reload_elapsed = None

        if reload_pressed and self.rounds < self.MAGAZINE_SIZE and self.reserve > 0:
            self._reload_elapsed = 0.0
            return

        if fire_pressed and self.cooldown == 0.0 and self.rounds > 0:
            player = world.player
            world.bullets.append(Bullet(player.x, player.y, cos(player.angle),
                                        sin(player.angle), self.BULLET_RANGE))
            self.rounds -= 1
            self.cooldown = self.FIRE_INTERVAL
            self._time_since_shot = 0.0

    def _advance(self, world: World, bullet: Bullet, dt: float) -> bool:
        distance = min(self.BULLET_SPEED * dt, bullet.range_left)
        wall = cast_wall(world, bullet.x, bullet.y, bullet.dx, bullet.dy, distance)

        first_target = None
        first_distance = float("inf")
        for target in world.targets:
            impact = self._target_distance(bullet, target)
            if impact is None or impact > distance or impact >= first_distance:
                continue
            if wall is not None and impact >= wall.distance:
                continue
            first_target = target
            first_distance = impact

        if first_target is not None:
            first_target.hits += 1
            first_target.hit_flash = self.TARGET_FLASH_TIME
            return False
        if wall is not None:
            return False

        bullet.x += bullet.dx * distance
        bullet.y += bullet.dy * distance
        bullet.range_left -= distance
        return bullet.range_left > 0.0

    @staticmethod
    def _target_distance(bullet: Bullet, target: Target) -> float | None:
        dx, dy = target.x - bullet.x, target.y - bullet.y
        radius_squared = TARGET_RADIUS ** 2
        if dx * dx + dy * dy <= radius_squared:
            return 0.0

        along = dx * bullet.dx + dy * bullet.dy
        across = dx * bullet.dy - dy * bullet.dx
        if along <= 0 or across * across > radius_squared:
            return None
        return along - sqrt(radius_squared - across * across)
