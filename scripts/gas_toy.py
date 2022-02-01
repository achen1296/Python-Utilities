import math
import random

import pyglet


def random_color():
    return (random.randint(0, 255), random.randint(0, 255), random.randint(0, 255))


def distance(pos1, pos2):
    x1, y1 = pos1
    x2, y2 = pos2
    return magnitude((x1-x2, y1-y2))


def magnitude(vec):
    return math.sqrt(dot(vec, vec))


def dot(v1, v2):
    x1, y1 = v1
    x2, y2 = v2
    return x1*x2 + y1*y2


def project(vec, onto):
    ox, oy = onto
    mag = dot(vec, onto)/dot(onto, onto)
    return (ox*mag, oy*mag)


def collide(c1: pyglet.shapes.Circle, c2: pyglet.shapes.Circle):
    dist = distance(c1.position,
                    c2.position)
    total_rad = c1.radius + c2.radius
    # bounce
    if dist <= total_rad and not c1.last_collided_with == c2 and not c2.last_collided_with == c1:
        c1.last_collided_with = c2
        c2.last_collided_with = c1

        dx = c2.x - c1.x
        dy = c2.y - c1.y

        # no div by 0 for projections
        if dx == 0 and dy == 0:
            dx = 1

        m1 = c1.radius ** 2
        m2 = c2.radius ** 2

        # change axis
        tan1 = project((c1.dx, c1.dy), (dx, dy))
        perp1 = project((c1.dx, c1.dy), (-dy, dx))

        tan2 = project((c2.dx, c2.dy), (dx, dy))
        perp2 = project((c2.dx, c2.dy), (-dy, dx))

        # elastic collision
        mt1 = magnitude(tan1)
        if (tan1[0] > 0) ^ (dx > 0):
            # against vector from c1 to c2
            mt1 *= -1
        mt2 = magnitude(tan2)
        if (tan2[0] > 0) ^ (dx > 0):
            mt2 *= -1
        v1 = ((m1 - m2)*mt1 + 2*m2*mt2)/(m1+m2)
        v2 = (2*m1*mt1 + (m2-m1) * mt2)/(m1+m2)

        # recombine
        tx, ty = tan1
        px, py = perp1
        if mt1 == 0:
            c1.dx = v1 / magnitude((dx, dy)) * dx + px
            c1.dy = v1 / magnitude((dx, dy)) * dy + py
        else:
            c1.dx = v1/mt1 * tx + px
            c1.dy = v1/mt1 * ty + py

        tx, ty = tan2
        px, py = perp2
        if mt2 == 0:
            c2.dx = v2/magnitude((dx, dy)) * dx + px
            c2.dy = v2/magnitude((dx, dy)) * dy + py
        else:
            c2.dx = v2/mt2 * tx + px
            c2.dy = v2/mt2 * ty + py

    elif dist >= total_rad + 10:
        if c1.last_collided_with == c2:
            c1.last_collided_with = None
        if c2.last_collided_with == c1:
            c2.last_collided_with = None


class GameWindow(pyglet.window.Window):
    circles: list[pyglet.shapes.Circle] = []
    batch = pyglet.graphics.Batch()
    ke_label = pyglet.text.Label(x=10, y=10, font_size = 24)

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        pyglet.clock.schedule_interval(self.update, 1/120)
        self.mouse_circle = None

    def update(self, dt):
        if self.mouse_circle is not None:
            self.mouse_circle.radius += 1
        for c in self.circles:
            c.x += c.dx*dt
            c.y += c.dy*dt
            if (c.x <= c.radius and c.dx < 0) or (c.x >= self.width - c.radius and c.dx > 0):
                c.dx *= -1
            if (c.y <= c.radius and c.dy < 0) or (c.y >= self.height - c.radius and c.dy > 0):
                c.dy *= -1
        for i in range(0, len(self.circles)-1):
            for j in range(i+1, len(self.circles)):
                collide(self.circles[i], self.circles[j])
        ke = 0
        for c in self.circles:
            ke += (c.radius ** 2) * (magnitude((c.dx, c.dy))**2)
        self.ke_label.text = f"Kinetic energy: {round(ke)}"

    def on_draw(self):
        self.clear()
        self.batch.draw()
        self.ke_label.draw()

    def on_key_press(self, symbol, modifiers):
        if symbol == pyglet.window.key.SPACE:
            for c in self.circles:
                c.delete()
            self.circles = []

    def on_mouse_press(self, x, y, button, modifiers):
        self.mouse = x, y
        self.mouse_circle = pyglet.shapes.Circle(
            x, y,
            1, batch=self.batch, color=random_color())

    def on_mouse_release(self, x, y, button, modifiers):
        lastx, lasty = self.mouse
        dx = x-lastx
        dy = y-lasty

        c = self.mouse_circle
        self.mouse_circle = None
        c.dx = dx*5
        c.dy = dy*5
        c.last_collided_with = None
        self.circles.append(c)


if __name__ == "__main__":
    window = GameWindow(
        fullscreen=True)
    pyglet.app.run()
