# program.py
# Plants vs. Zombies – Pygame Demo (Windows 7, 60 FPS)
# Full PVZ1‑style main menu with Adventure, Mini‑games, Almanac
# Fixed zombie bite detection & lawnmower double‑trigger
# 100% original graphics – no copyrighted assets.

import pygame
import sys
import random
from dataclasses import dataclass

# ------------------------------------------------------------------
# CONSTANTS & GLOBAL SETTINGS
# ------------------------------------------------------------------
SCREEN_WIDTH = 1000
SCREEN_HEIGHT = 700
FPS = 60

# Lawn grid
ROWS = 5
COLS = 9
LAWN_LEFT = 200
LAWN_TOP = 170
TILE_W = 80
TILE_H = 90
LAWN_W = COLS * TILE_W  # 720
LAWN_H = ROWS * TILE_H  # 450

# Cards
CARD_BAR_TOP = 30
CARD_BAR_LEFT = LAWN_LEFT
CARD_W = 120
CARD_H = 60
CARD_GAP = 12

# Gameplay tuning
START_SUN = 50
SUN_VALUE = 25
SKY_SUN_INTERVAL = 9.0

ZOMBIE_BASE_INTERVAL = 4.0
ZOMBIE_MIN_INTERVAL = 1.2
ZOMBIE_INTERVAL_DECAY = 0.005
LEVEL_DURATION = 120.0            # survive 2 minutes to win

# Colors (original)
C_BG = (24, 32, 24)
C_PANEL = (40, 55, 40)
C_LAWN = (55, 90, 55)
C_TILE_A = (65, 110, 65)
C_TILE_B = (58, 100, 58)
C_GRID_LINE = (30, 60, 30)
C_TEXT = (240, 240, 240)
C_ACCENT = (255, 230, 120)
C_WARN = (255, 80, 80)
C_CARD = (90, 70, 40)
C_CARD_BORDER = (220, 200, 140)
C_CARD_DISABLED = (70, 70, 70)
C_CARD_SELECTED = (255, 255, 200)
C_SUN = (255, 220, 60)
C_PEA = (80, 220, 90)
C_ZOMBIE = (130, 160, 160)
C_ZOMBIE_DARK = (80, 110, 110)
C_P_SHOOTER = (70, 200, 80)
C_P_SUNFLOWER = (240, 200, 40)
C_P_WALLNUT = (170, 120, 60)

# ------------------------------------------------------------------
# HELPER FUNCTIONS
# ------------------------------------------------------------------
def clamp(v, lo, hi):
    return max(lo, min(hi, v))

def draw_text(surface, text, font, color, x, y, center=True):
    text_surf = font.render(text, True, color)
    rect = text_surf.get_rect(center=(x, y)) if center else text_surf.get_rect(topleft=(x, y))
    surface.blit(text_surf, rect)

def grid_to_world(row, col):
    x = LAWN_LEFT + col * TILE_W + TILE_W // 2
    y = LAWN_TOP + row * TILE_H + TILE_H // 2
    return x, y

def world_to_grid(mx, my):
    if mx < LAWN_LEFT or mx >= LAWN_LEFT + COLS * TILE_W:
        return None
    if my < LAWN_TOP or my >= LAWN_TOP + ROWS * TILE_H:
        return None
    col = (mx - LAWN_LEFT) // TILE_W
    row = (my - LAWN_TOP) // TILE_H
    return int(row), int(col)

# ------------------------------------------------------------------
# GAME ENTITIES
# ------------------------------------------------------------------
@dataclass
class Sun:
    x: float
    y: float
    value: int = SUN_VALUE
    vy: float = 0.0
    target_y: float = 0.0
    life: float = 10.0
    floating: bool = False

    def rect(self):
        return pygame.Rect(int(self.x - 18), int(self.y - 18), 36, 36)

    def update(self, dt):
        self.life -= dt
        if not self.floating:
            if self.y < self.target_y:
                self.vy = min(self.vy + 900 * dt, 600)
                self.y = min(self.y + self.vy * dt, self.target_y)
            else:
                self.floating = True
                self.vy = -20
        else:
            self.y += self.vy * dt

    def draw(self, surf):
        pygame.draw.circle(surf, C_SUN, (int(self.x), int(self.y)), 18)
        pygame.draw.circle(surf, (255, 245, 160), (int(self.x), int(self.y)), 18, 3)


class Projectile:
    def __init__(self, row, x, y, speed=360, damage=20):
        self.row = row
        self.x = x
        self.y = y
        self.speed = speed
        self.damage = damage
        self.alive = True

    def rect(self):
        return pygame.Rect(int(self.x - 10), int(self.y - 6), 20, 12)

    def update(self, dt, game):
        self.x += self.speed * dt
        if self.x > SCREEN_WIDTH + 30:
            self.alive = False
            return

        for z in game.zombies:
            if z.row != self.row or not z.alive:
                continue
            if self.rect().colliderect(z.rect()):
                z.take_damage(self.damage)
                self.alive = False
                break

    def draw(self, surf):
        pygame.draw.ellipse(surf, C_PEA, self.rect())
        pygame.draw.ellipse(surf, (30, 60, 30), self.rect(), 2)


class Plant:
    name = "Plant"
    cost = 0
    max_hp = 100

    def __init__(self, row, col):
        self.row = row
        self.col = col
        self.x, self.y = grid_to_world(row, col)
        self.hp = self.max_hp
        self.alive = True

    def rect(self):
        return pygame.Rect(int(self.x - 30), int(self.y - 35), 60, 70)

    def update(self, dt, game):
        pass

    def draw_hp_bar(self, surf):
        w = 56
        h = 6
        x = int(self.x - w / 2)
        y = int(self.y + 28)
        pygame.draw.rect(surf, (40, 40, 40), (x, y, w, h))
        fill = int(w * (self.hp / self.max_hp))
        pygame.draw.rect(surf, (80, 220, 80), (x, y, fill, h))

    def take_damage(self, dmg):
        self.hp -= dmg
        if self.hp <= 0:
            self.alive = False


class Peashooter(Plant):
    name = "Peashooter"
    cost = 100
    max_hp = 180

    def __init__(self, row, col):
        super().__init__(row, col)
        self.shoot_cd = 1.4
        self.timer = random.uniform(0.1, 0.8)

    def update(self, dt, game):
        self.timer -= dt
        if self.timer <= 0:
            has_target = any(z.alive and z.row == self.row and z.x > self.x for z in game.zombies)
            if has_target:
                game.projectiles.append(Projectile(self.row, self.x + 25, self.y - 10))
            self.timer = self.shoot_cd

    def draw(self, surf):
        r = self.rect()
        pygame.draw.rect(surf, C_P_SHOOTER, r, border_radius=10)
        pygame.draw.rect(surf, (20, 60, 20), r, 2, border_radius=10)
        pygame.draw.circle(surf, (40, 120, 40), (int(self.x + 22), int(self.y - 10)), 10)
        self.draw_hp_bar(surf)


class SunflowerPlant(Plant):
    name = "Sunflower"
    cost = 50
    max_hp = 160

    def __init__(self, row, col):
        super().__init__(row, col)
        self.sun_cd = 7.5
        self.timer = random.uniform(2.5, 5.0)

    def update(self, dt, game):
        self.timer -= dt
        if self.timer <= 0:
            sx = self.x + random.uniform(-10, 10)
            sy = self.y - 10
            game.suns.append(Sun(sx, sy, value=SUN_VALUE, vy=-80, target_y=sy, life=9.0, floating=True))
            self.timer = self.sun_cd

    def draw(self, surf):
        r = self.rect()
        pygame.draw.rect(surf, C_P_SUNFLOWER, r, border_radius=10)
        pygame.draw.rect(surf, (120, 90, 20), r, 2, border_radius=10)
        pygame.draw.circle(surf, (255, 245, 160), (int(self.x), int(self.y - 10)), 16)
        pygame.draw.circle(surf, (60, 40, 10), (int(self.x - 5), int(self.y - 12)), 3)
        pygame.draw.circle(surf, (60, 40, 10), (int(self.x + 5), int(self.y - 12)), 3)
        self.draw_hp_bar(surf)


class Wallnut(Plant):
    name = "Wall-nut"
    cost = 50
    max_hp = 720

    def draw(self, surf):
        r = self.rect()
        pygame.draw.rect(surf, C_P_WALLNUT, r, border_radius=14)
        pygame.draw.rect(surf, (90, 60, 30), r, 2, border_radius=14)
        hp_ratio = self.hp / self.max_hp
        if hp_ratio < 0.66:
            pygame.draw.line(surf, (80, 50, 25), (r.left + 12, r.top + 14), (r.right - 10, r.bottom - 12), 3)
        if hp_ratio < 0.33:
            pygame.draw.line(surf, (80, 50, 25), (r.left + 14, r.bottom - 16), (r.right - 14, r.top + 16), 3)
        self.draw_hp_bar(surf)


class Zombie:
    def __init__(self, row, x):
        self.row = row
        self.x = x
        self.y = grid_to_world(row, 0)[1]
        self.speed = random.uniform(18, 28)
        self.max_hp = 200
        self.hp = self.max_hp
        self.damage = 40
        self.alive = True
        self.eating = False
        self.target = None

    def rect(self):
        return pygame.Rect(int(self.x - 24), int(self.y - 40), 48, 80)

    def take_damage(self, dmg):
        self.hp -= dmg
        if self.hp <= 0:
            self.alive = False

    def update(self, dt, game):
        if not self.alive:
            return

        if self.eating and self.target is not None and self.target.alive:
            self.target.take_damage(self.damage * dt)
            if not self.target.alive:
                game.remove_plant(self.target.row, self.target.col)
                self.eating = False
                self.target = None
            return

        self.x -= self.speed * dt

        if self.x < LAWN_LEFT - 15:
            if not game.lawnmowers[self.row].used:
                game.trigger_lawnmower(self.row)

        if self.x < 90:
            game.lose_game()

        bite_rect = pygame.Rect(int(self.x - 30), int(self.y - 30), 20, 60)
        plant = game.get_plant_colliding(self.row, bite_rect)
        if plant is not None:
            self.eating = True
            self.target = plant

    def draw(self, surf):
        r = self.rect()
        pygame.draw.rect(surf, C_ZOMBIE, r, border_radius=10)
        pygame.draw.rect(surf, C_ZOMBIE_DARK, r, 2, border_radius=10)
        pygame.draw.circle(surf, (170, 200, 200), (int(self.x), int(self.y - 30)), 16)
        pygame.draw.circle(surf, (30, 40, 40), (int(self.x - 5), int(self.y - 32)), 3)
        pygame.draw.circle(surf, (30, 40, 40), (int(self.x + 5), int(self.y - 32)), 3)
        w = 46
        h = 5
        x = int(self.x - w / 2)
        y = int(self.y - 50)
        pygame.draw.rect(surf, (40, 40, 40), (x, y, w, h))
        fill = int(w * (self.hp / self.max_hp))
        pygame.draw.rect(surf, (255, 80, 80), (x, y, fill, h))


class LawnMower:
    def __init__(self, row):
        self.row = row
        self.x = LAWN_LEFT - 70
        self.y = grid_to_world(row, 0)[1] + 15
        self.speed = 560
        self.active = False
        self.used = False

    def rect(self):
        return pygame.Rect(int(self.x - 28), int(self.y - 18), 56, 36)

    def trigger(self):
        if not self.used:
            self.active = True
            self.used = True

    def update(self, dt, game):
        if not self.active:
            return
        self.x += self.speed * dt
        mr = self.rect()
        for z in game.zombies:
            if z.alive and z.row == self.row and mr.colliderect(z.rect()):
                z.alive = False
        if self.x > SCREEN_WIDTH + 80:
            self.active = False

    def draw(self, surf):
        r = self.rect()
        base = (200, 60, 60) if self.used else (220, 80, 80)
        pygame.draw.rect(surf, base, r, border_radius=8)
        pygame.draw.rect(surf, (60, 20, 20), r, 2, border_radius=8)
        pygame.draw.circle(surf, (50, 50, 50), (r.left + 10, r.bottom), 8)
        pygame.draw.circle(surf, (50, 50, 50), (r.right - 10, r.bottom), 8)


class SeedCard:
    def __init__(self, plant_cls, index, recharge=5.0):
        self.plant_cls = plant_cls
        self.index = index
        self.recharge = recharge
        self.cooldown = 0.0
        self.rect = pygame.Rect(
            CARD_BAR_LEFT + index * (CARD_W + CARD_GAP),
            CARD_BAR_TOP,
            CARD_W,
            CARD_H
        )

    @property
    def name(self):
        return self.plant_cls.name

    @property
    def cost(self):
        return self.plant_cls.cost

    def available(self, sun_amount):
        return self.cooldown <= 0 and sun_amount >= self.cost

    def update(self, dt):
        if self.cooldown > 0:
            self.cooldown -= dt

    def start_cooldown(self):
        self.cooldown = self.recharge

    def draw(self, surf, font, selected=False, can_afford=True):
        if self.cooldown > 0:
            bg = C_CARD_DISABLED
        else:
            bg = C_CARD
        pygame.draw.rect(surf, bg, self.rect, border_radius=10)
        border = C_CARD_SELECTED if selected else C_CARD_BORDER
        pygame.draw.rect(surf, border, self.rect, 2, border_radius=10)

        draw_text(surf, self.name, font, C_TEXT, self.rect.centerx, self.rect.y + 18)
        draw_text(surf, str(self.cost), font, C_ACCENT if can_afford else C_WARN, self.rect.centerx, self.rect.y + 42)

        if self.cooldown > 0:
            pct = clamp(self.cooldown / self.recharge, 0, 1)
            h = int(self.rect.height * pct)
            overlay = pygame.Surface((self.rect.width, h), pygame.SRCALPHA)
            overlay.fill((0, 0, 0, 120))
            surf.blit(overlay, (self.rect.x, self.rect.bottom - h))


# ------------------------------------------------------------------
# ALMANAC DATA
# ------------------------------------------------------------------
PLANT_DATA = {
    "Sunflower": {"cost": 50, "hp": 160, "desc": "Produces extra sun."},
    "Peashooter": {"cost": 100, "hp": 180, "desc": "Shoots peas at zombies."},
    "Wall-nut": {"cost": 50, "hp": 720, "desc": "Tough nut to crack."},
}

ZOMBIE_DATA = {
    "Basic Zombie": {"hp": 200, "speed": "slow", "desc": "Just walks and eats."}
}

# ------------------------------------------------------------------
# MAIN GAME CLASS
# ------------------------------------------------------------------
class Game:
    def __init__(self):
        pygame.init()
        pygame.display.set_caption("PVZ-Inspired Pygame Demo")
        self.screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT))
        self.clock = pygame.time.Clock()
        self.running = True

        self.font_large = pygame.font.Font(None, 64)
        self.font_medium = pygame.font.Font(None, 40)
        self.font_small = pygame.font.Font(None, 28)

        self.state = "main_menu"
        self.player_name = "Gardener"
        self.dt = 0.0

        self.menu_selection = 0
        self.almanac_page = 0
        self.almanac_index = 0

        self.reset_gameplay()

    def reset_gameplay(self, mode="adventure"):
        self.sun = START_SUN
        self.suns = []
        self.projectiles = []
        self.zombies = []
        self.plants = {}
        self.selected_card = None

        self.cards = [
            SeedCard(SunflowerPlant, 0, recharge=7.0),
            SeedCard(Peashooter, 1, recharge=5.0),
            SeedCard(Wallnut, 2, recharge=9.0),
        ]

        self.sky_sun_timer = 2.0
        self.zombie_timer = 2.0
        self.zombie_interval = ZOMBIE_BASE_INTERVAL

        self.elapsed = 0.0
        self.win = False
        self.game_over = False
        self.message = ""
        self.message_timer = 0.0

        self.lawnmowers = [LawnMower(r) for r in range(ROWS)]
        self.mode = mode

    def plant_at(self, row, col):
        return self.plants.get((row, col))

    def remove_plant(self, row, col):
        if (row, col) in self.plants:
            del self.plants[(row, col)]

    def get_plant_colliding(self, row, rect):
        for c in range(COLS):
            p = self.plant_at(row, c)
            if p and p.alive and rect.colliderect(p.rect()):
                return p
        return None

    def trigger_lawnmower(self, row):
        self.lawnmowers[row].trigger()

    def lose_game(self):
        if self.state == "playing":
            self.state = "game_over"
            self.game_over = True

    def win_game(self):
        if self.state == "playing":
            self.state = "win"
            self.win = True

    def show_message(self, text, seconds=1.2):
        self.message = text
        self.message_timer = seconds

    def run(self):
        while self.running:
            self.dt = self.clock.tick(FPS) / 1000.0
            self.handle_events()
            self.update()
            self.draw()
        pygame.quit()
        sys.exit()

    def handle_events(self):
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                self.running = False

            if self.state == "main_menu":
                if event.type == pygame.KEYDOWN:
                    if event.key == pygame.K_UP:
                        self.menu_selection = (self.menu_selection - 1) % 4
                    elif event.key == pygame.K_DOWN:
                        self.menu_selection = (self.menu_selection + 1) % 4
                    elif event.key == pygame.K_RETURN:
                        self._activate_menu_option()
                    elif event.key == pygame.K_ESCAPE:
                        self.running = False

                if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                    mx, my = event.pos
                    btn_adv = pygame.Rect(SCREEN_WIDTH//2-150, 250, 300, 60)
                    btn_mini = pygame.Rect(SCREEN_WIDTH//2-150, 330, 300, 60)
                    btn_alm = pygame.Rect(SCREEN_WIDTH//2-150, 410, 300, 60)
                    btn_quit = pygame.Rect(SCREEN_WIDTH//2-150, 490, 300, 60)
                    if btn_adv.collidepoint(mx, my):
                        self.menu_selection = 0
                        self._activate_menu_option()
                    elif btn_mini.collidepoint(mx, my):
                        self.menu_selection = 1
                        self._activate_menu_option()
                    elif btn_alm.collidepoint(mx, my):
                        self.menu_selection = 2
                        self._activate_menu_option()
                    elif btn_quit.collidepoint(mx, my):
                        self.menu_selection = 3
                        self._activate_menu_option()

            elif self.state == "almanac":
                if event.type == pygame.KEYDOWN:
                    if event.key == pygame.K_LEFT:
                        if self.almanac_page == 0:
                            self.almanac_index = (self.almanac_index - 1) % len(PLANT_DATA)
                        else:
                            self.almanac_index = (self.almanac_index - 1) % len(ZOMBIE_DATA)
                    elif event.key == pygame.K_RIGHT:
                        if self.almanac_page == 0:
                            self.almanac_index = (self.almanac_index + 1) % len(PLANT_DATA)
                        else:
                            self.almanac_index = (self.almanac_index + 1) % len(ZOMBIE_DATA)
                    elif event.key == pygame.K_TAB:
                        self.almanac_page = 1 - self.almanac_page
                        self.almanac_index = 0
                    elif event.key == pygame.K_ESCAPE:
                        self.state = "main_menu"
                if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                    mx, my = event.pos
                    if mx < 100 and my < 100:
                        self.state = "main_menu"

            elif self.state == "playing":
                if event.type == pygame.KEYDOWN:
                    if event.key == pygame.K_ESCAPE:
                        self.state = "main_menu"
                        self.selected_card = None

                if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                    mx, my = event.pos

                    for s in list(self.suns):
                        if s.rect().collidepoint((mx, my)):
                            self.sun += s.value
                            self.suns.remove(s)
                            self.show_message(f"+{s.value} sun!", 0.7)
                            return

                    for card in self.cards:
                        if card.rect.collidepoint((mx, my)):
                            if card.cooldown > 0:
                                self.show_message("Recharging...", 0.8)
                                return
                            if self.sun < card.cost:
                                self.show_message("Not enough sun!", 0.9)
                                return
                            if self.selected_card is card:
                                self.selected_card = None
                            else:
                                self.selected_card = card
                            return

                    cell = world_to_grid(mx, my)
                    if cell is not None and self.selected_card is not None:
                        row, col = cell
                        if self.plant_at(row, col) is not None:
                            self.show_message("Tile occupied!", 0.9)
                            return
                        card = self.selected_card
                        if self.sun < card.cost:
                            self.show_message("Not enough sun!", 0.9)
                            return
                        plant = card.plant_cls(row, col)
                        self.plants[(row, col)] = plant
                        self.sun -= card.cost
                        card.start_cooldown()
                        self.selected_card = None
                        return

            elif self.state in ("game_over", "win"):
                if event.type == pygame.KEYDOWN:
                    if event.key == pygame.K_r:
                        self.reset_gameplay(self.mode)
                        self.state = "playing"
                    elif event.key == pygame.K_ESCAPE:
                        self.state = "main_menu"
                if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                    self.state = "main_menu"

    def _activate_menu_option(self):
        if self.menu_selection == 0:
            self.reset_gameplay("adventure")
            self.state = "playing"
        elif self.menu_selection == 1:
            self.reset_gameplay("minigames")
            self.state = "playing"
        elif self.menu_selection == 2:
            self.almanac_page = 0
            self.almanac_index = 0
            self.state = "almanac"
        elif self.menu_selection == 3:
            self.running = False

    def update(self):
        if self.state == "main_menu" or self.state == "almanac":
            return

        if self.state != "playing":
            return

        dt = self.dt
        self.elapsed += dt

        if self.mode == "minigames":
            if self.elapsed >= 60:
                self.win_game()
        else:
            if self.elapsed >= LEVEL_DURATION:
                self.win_game()

        if self.message_timer > 0:
            self.message_timer -= dt
            if self.message_timer <= 0:
                self.message = ""

        for c in self.cards:
            c.update(dt)

        self.sky_sun_timer -= dt
        if self.sky_sun_timer <= 0:
            sx = random.randint(LAWN_LEFT + 30, LAWN_LEFT + LAWN_W - 30)
            ty = random.randint(LAWN_TOP + 30, LAWN_TOP + LAWN_H - 30)
            self.suns.append(Sun(sx, -20, value=SUN_VALUE, vy=0, target_y=ty, life=11.0, floating=False))
            self.sky_sun_timer = SKY_SUN_INTERVAL + random.uniform(-1.5, 1.5)

        if self.mode == "minigames":
            self.zombie_interval = max(ZOMBIE_MIN_INTERVAL/2, self.zombie_interval - ZOMBIE_INTERVAL_DECAY * dt * 2)
        else:
            self.zombie_interval = max(ZOMBIE_MIN_INTERVAL, self.zombie_interval - ZOMBIE_INTERVAL_DECAY * dt)

        self.zombie_timer -= dt
        if self.zombie_timer <= 0:
            row = random.randrange(ROWS)
            zx = LAWN_LEFT + LAWN_W + 60
            self.zombies.append(Zombie(row, zx))
            self.zombie_timer = self.zombie_interval + random.uniform(-0.4, 0.6)

        for s in list(self.suns):
            s.update(dt)
            if s.life <= 0:
                self.suns.remove(s)

        for (row, col), p in list(self.plants.items()):
            if not p.alive:
                self.remove_plant(row, col)
                continue
            p.update(dt, self)

        for pr in list(self.projectiles):
            pr.update(dt, self)
            if not pr.alive:
                self.projectiles.remove(pr)

        for z in list(self.zombies):
            z.update(dt, self)
        self.zombies = [z for z in self.zombies if z.alive]

        for m in self.lawnmowers:
            m.update(dt, self)

    def draw(self):
        self.screen.fill(C_BG)

        if self.state == "main_menu":
            self.draw_main_menu()
        elif self.state == "almanac":
            self.draw_almanac()
        elif self.state == "playing":
            self.draw_playing()
        elif self.state == "game_over":
            self.draw_playing()
            self.draw_overlay("GAME OVER", "Press R to Restart • Click to Menu")
        elif self.state == "win":
            self.draw_playing()
            self.draw_overlay("YOU WIN!", "Press R to Replay • Click to Menu")

        pygame.display.flip()

    def draw_main_menu(self):
        self.screen.fill((30, 60, 30))
        draw_text(self.screen, "Plants vs. Zombies", self.font_large, C_ACCENT, SCREEN_WIDTH//2, 120)
        draw_text(self.screen, "Pygame Demo", self.font_medium, C_TEXT, SCREEN_WIDTH//2, 180)

        items = ["Adventure", "Mini-games", "Almanac", "Quit"]
        y_start = 250
        for i, txt in enumerate(items):
            rect = pygame.Rect(SCREEN_WIDTH//2 - 150, y_start + i*80, 300, 60)
            color = (100, 150, 100) if i == self.menu_selection else (60, 100, 60)
            pygame.draw.rect(self.screen, color, rect, border_radius=12)
            pygame.draw.rect(self.screen, (200, 200, 150), rect, 2, border_radius=12)
            draw_text(self.screen, txt, self.font_medium, C_TEXT, rect.centerx, rect.centery)

        draw_text(self.screen, "Use arrow keys & Enter • Click also works",
                  self.font_small, (200,200,200), SCREEN_WIDTH//2, SCREEN_HEIGHT-50)

    def draw_almanac(self):
        self.screen.fill((30, 40, 30))
        draw_text(self.screen, "ALMANAC", self.font_large, C_ACCENT, SCREEN_WIDTH//2, 60)

        tab_w = 200
        tab_h = 50
        plants_tab = pygame.Rect(SCREEN_WIDTH//2 - tab_w - 10, 120, tab_w, tab_h)
        zombies_tab = pygame.Rect(SCREEN_WIDTH//2 + 10, 120, tab_w, tab_h)

        col_plants = (100, 150, 100) if self.almanac_page == 0 else (60, 80, 60)
        pygame.draw.rect(self.screen, col_plants, plants_tab, border_radius=8)
        draw_text(self.screen, "Plants", self.font_medium, C_TEXT, plants_tab.centerx, plants_tab.centery)

        col_zombies = (100, 150, 100) if self.almanac_page == 1 else (60, 80, 60)
        pygame.draw.rect(self.screen, col_zombies, zombies_tab, border_radius=8)
        draw_text(self.screen, "Zombies", self.font_medium, C_TEXT, zombies_tab.centerx, zombies_tab.centery)

        if self.almanac_page == 0:
            items = list(PLANT_DATA.items())
            if items:
                name, data = items[self.almanac_index % len(items)]
                draw_text(self.screen, name, self.font_medium, C_ACCENT, SCREEN_WIDTH//2, 220)
                draw_text(self.screen, f"Cost: {data['cost']}  HP: {data['hp']}", self.font_small, C_TEXT, SCREEN_WIDTH//2, 280)
                draw_text(self.screen, data['desc'], self.font_small, C_TEXT, SCREEN_WIDTH//2, 340)
        else:
            items = list(ZOMBIE_DATA.items())
            if items:
                name, data = items[self.almanac_index % len(items)]
                draw_text(self.screen, name, self.font_medium, C_ACCENT, SCREEN_WIDTH//2, 220)
                draw_text(self.screen, f"HP: {data['hp']}  Speed: {data['speed']}", self.font_small, C_TEXT, SCREEN_WIDTH//2, 280)
                draw_text(self.screen, data['desc'], self.font_small, C_TEXT, SCREEN_WIDTH//2, 340)

        draw_text(self.screen, "← → arrows to browse   TAB to switch   ESC to return",
                  self.font_small, (200,200,200), SCREEN_WIDTH//2, SCREEN_HEIGHT-60)

    def draw_playing(self):
        pygame.draw.rect(self.screen, C_PANEL, (0, 0, SCREEN_WIDTH, 110))
        pygame.draw.rect(self.screen, (15, 15, 15), (0, 110, SCREEN_WIDTH, SCREEN_HEIGHT - 110))

        for card in self.cards:
            card.draw(
                self.screen,
                self.font_small,
                selected=(self.selected_card is card),
                can_afford=(self.sun >= card.cost),
            )

        sun_box = pygame.Rect(30, 22, 140, 70)
        pygame.draw.rect(self.screen, (60, 60, 30), sun_box, border_radius=12)
        pygame.draw.rect(self.screen, (250, 240, 180), sun_box, 2, border_radius=12)
        pygame.draw.circle(self.screen, C_SUN, (sun_box.x + 32, sun_box.centery), 16)
        draw_text(self.screen, str(self.sun), self.font_medium, C_TEXT, sun_box.x + 92, sun_box.centery)

        mode_text = "Adventure" if self.mode == "adventure" else "Mini-games"
        draw_text(self.screen, mode_text, self.font_small, (220,220,220), SCREEN_WIDTH - 80, 26)
        remaining = max(0, int((LEVEL_DURATION if self.mode=='adventure' else 60) - self.elapsed))
        draw_text(self.screen, f"Time: {remaining}s", self.font_small, (220,220,220), SCREEN_WIDTH - 90, 55)

        lawn_rect = pygame.Rect(LAWN_LEFT, LAWN_TOP, LAWN_W, LAWN_H)
        pygame.draw.rect(self.screen, C_LAWN, lawn_rect, border_radius=12)

        for r in range(ROWS):
            for c in range(COLS):
                x = LAWN_LEFT + c * TILE_W
                y = LAWN_TOP + r * TILE_H
                tile = pygame.Rect(x, y, TILE_W, TILE_H)
                col = C_TILE_A if (r + c) % 2 == 0 else C_TILE_B
                pygame.draw.rect(self.screen, col, tile)
                pygame.draw.rect(self.screen, C_GRID_LINE, tile, 1)

        if self.selected_card is not None:
            mx, my = pygame.mouse.get_pos()
            cell = world_to_grid(mx, my)
            if cell is not None:
                r, c = cell
                x = LAWN_LEFT + c * TILE_W
                y = LAWN_TOP + r * TILE_H
                tile = pygame.Rect(x, y, TILE_W, TILE_H)
                pygame.draw.rect(self.screen, (255, 255, 255), tile, 3)

        for m in self.lawnmowers:
            m.draw(self.screen)

        for p in self.plants.values():
            p.draw(self.screen)

        for pr in self.projectiles:
            pr.draw(self.screen)

        for z in self.zombies:
            z.draw(self.screen)

        for s in self.suns:
            s.draw(self.screen)

        if self.message:
            draw_text(self.screen, self.message, self.font_small, C_ACCENT, SCREEN_WIDTH // 2, 120)

        draw_text(self.screen, "Click suns • Place plants • ESC to menu",
                  self.font_small, (200,200,200), SCREEN_WIDTH // 2, SCREEN_HEIGHT - 20)

    def draw_overlay(self, title, subtitle):
        overlay = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, 140))
        self.screen.blit(overlay, (0, 0))

        box = pygame.Rect(0, 0, 520, 220)
        box.center = (SCREEN_WIDTH // 2, SCREEN_HEIGHT // 2)
        pygame.draw.rect(self.screen, (30, 30, 40), box, border_radius=18)
        pygame.draw.rect(self.screen, (220, 220, 240), box, 2, border_radius=18)

        draw_text(self.screen, title, self.font_large, C_ACCENT, box.centerx, box.y + 70)
        draw_text(self.screen, subtitle, self.font_small, (230, 230, 230), box.centerx, box.y + 140)


if __name__ == "__main__":
    Game().run()
