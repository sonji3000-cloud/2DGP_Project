"""Update pistol fire and projectile impacts in world coordinates."""

from math import cos, sin, sqrt

from raycast import cast_wall
from world import TARGET_RADIUS, Bullet, Target, World


class Pistol:
    FIRE_INTERVAL = 0.23
    BULLET_SPEED = 16.0
    BULLET_RANGE = 18.0
    TARGET_FLASH_TIME = 0.22

    def __init__(self) -> None:
        self.cooldown = 0.0

    def update(self, world: World, fire_pressed: bool, dt: float) -> None:
        player = world.player
        self.cooldown = max(0.0, self.cooldown - dt)
        player.time_since_shot += dt
        for target in world.targets:
            target.hit_flash = max(0.0, target.hit_flash - dt)

        world.bullets[:] = [
            bullet for bullet in world.bullets if self._advance(world, bullet, dt)
        ]

        if fire_pressed and self.cooldown == 0.0:
            world.bullets.append(Bullet(player.x, player.y, cos(player.angle),
                                        sin(player.angle), self.BULLET_RANGE))
            self.cooldown = self.FIRE_INTERVAL
            player.time_since_shot = 0.0

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
