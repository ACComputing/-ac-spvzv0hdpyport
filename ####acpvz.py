import pygame
import sys
import random
import math

# Initialize Pygame
pygame.init()

# Constants
SCREEN_WIDTH = 1000
SCREEN_HEIGHT = 600
GRID_ROWS = 5
GRID_COLS = 9
CELL_SIZE = 80
SIDEBAR_WIDTH = 200
GAME_WIDTH = GRID_COLS * CELL_SIZE
GAME_HEIGHT = GRID_ROWS * CELL_SIZE

# Colors
WHITE = (255, 255, 255)
BLACK = (0, 0, 0)
GREEN = (0, 255, 0)
RED = (255, 0, 0)
BROWN = (139, 69, 19)
YELLOW = (255, 255, 0)
BLUE = (0, 0, 255)
GRAY = (200, 200, 200)
LIGHT_GREEN = (144, 238, 144)
DARK_GREEN = (0, 100, 0)

# Game settings
SUN_START = 100
SUN_DROP_RATE = 120  # frames between sun drops
ZOMBIE_SPAWN_RATE = 180  # frames between zombie spawns
PEA_SHOOT_COOLDOWN = 30  # frames between pea shots
SUNFLOWER_GEN_RATE = 120  # frames between sun generation

# Set up display
screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT))
pygame.display.set_caption("Cat's PVZ")
clock = pygame.time.Clock()
font = pygame.font.Font(None, 36)
small_font = pygame.font.Font(None, 24)

# Game classes
class Plant:
    def __init__(self, x, y, plant_type):
        self.x = x
        self.y = y
        self.type = plant_type  # 'peashooter' or 'sunflower'
        self.health = 100
        self.rect = pygame.Rect(x, y, CELL_SIZE-10, CELL_SIZE-10)
        self.last_shot = 0
        self.last_sun_gen = 0

    def update(self, current_time):
        if self.type == 'sunflower':
            if current_time - self.last_sun_gen > SUNFLOWER_GEN_RATE:
                self.last_sun_gen = current_time
                return Sun(self.x + CELL_SIZE//2, self.y, 30)  # generate sun
        return None

    def draw(self, screen):
        if self.type == 'peashooter':
            pygame.draw.rect(screen, GREEN, self.rect)
            text = small_font.render("P", True, BLACK)
            screen.blit(text, (self.x+30, self.y+25))
        elif self.type == 'sunflower':
            pygame.draw.rect(screen, YELLOW, self.rect)
            text = small_font.render("S", True, BLACK)
            screen.blit(text, (self.x+30, self.y+25))

class Zombie:
    def __init__(self, row, col):
        self.row = row
        self.col = col
        self.x = GAME_WIDTH - CELL_SIZE + 10  # rightmost column
        self.y = row * CELL_SIZE + 10
        self.health = 100
        self.speed = 1
        self.rect = pygame.Rect(self.x, self.y, CELL_SIZE-20, CELL_SIZE-20)
        self.target_col = col
        self.eating = False
        self.target_plant = None

    def move(self):
        if not self.eating:
            self.x -= self.speed
            self.col = max(0, int(self.x / CELL_SIZE))
            self.rect.x = self.x

    def draw(self, screen):
        pygame.draw.rect(screen, BROWN, self.rect)
        text = small_font.render("Z", True, BLACK)
        screen.blit(text, (self.x+25, self.y+20))
        # health bar
        bar_width = self.rect.width * (self.health / 100)
        pygame.draw.rect(screen, RED, (self.x, self.y-10, self.rect.width, 5))
        pygame.draw.rect(screen, GREEN, (self.x, self.y-10, bar_width, 5))

class Projectile:
    def __init__(self, x, y, target_row):
        self.x = x
        self.y = y + CELL_SIZE//2 - 5
        self.target_row = target_row
        self.speed = 5
        self.damage = 20
        self.rect = pygame.Rect(self.x, self.y, 10, 5)

    def move(self):
        self.x += self.speed
        self.rect.x = self.x

    def draw(self, screen):
        pygame.draw.rect(screen, BLUE, self.rect)

class Sun:
    def __init__(self, x, y, value):
        self.x = x
        self.y = y
        self.value = value
        self.rect = pygame.Rect(x-15, y-15, 30, 30)
        self.falling = True
        self.speed = 2

    def update(self):
        if self.falling:
            self.y += self.speed
            self.rect.y = self.y
            # stop falling when near ground
            if self.y > GAME_HEIGHT - 50:
                self.falling = False

    def draw(self, screen):
        pygame.draw.circle(screen, YELLOW, (self.x, self.y), 15)
        text = small_font.render(str(self.value), True, BLACK)
        screen.blit(text, (self.x-8, self.y-10))

class Game:
    def __init__(self):
        self.grid = [[None for _ in range(GRID_COLS)] for _ in range(GRID_ROWS)]
        self.zombies = []
        self.projectiles = []
        self.suns = []
        self.sun_points = SUN_START
        self.frame_count = 0
        self.selected_plant = None  # 'peashooter' or 'sunflower'
        self.game_over = False
        self.win = False

    def handle_click(self, pos):
        x, y = pos
        # Check if click on sidebar
        if x > GAME_WIDTH:
            # Plant selection
            if GAME_WIDTH + 20 < x < GAME_WIDTH + 180:
                if 50 < y < 100:
                    self.selected_plant = 'peashooter'
                elif 120 < y < 170:
                    self.selected_plant = 'sunflower'
        elif not self.game_over:
            # Click on grid
            col = x // CELL_SIZE
            row = y // CELL_SIZE
            if 0 <= row < GRID_ROWS and 0 <= col < GRID_COLS:
                if self.grid[row][col] is None and self.selected_plant:
                    cost = 50 if self.selected_plant == 'peashooter' else 25
                    if self.sun_points >= cost:
                        self.sun_points -= cost
                        new_plant = Plant(col*CELL_SIZE+5, row*CELL_SIZE+5, self.selected_plant)
                        self.grid[row][col] = new_plant
                        self.selected_plant = None

    def update(self):
        if self.game_over:
            return

        self.frame_count += 1

        # Sun drop from sky
        if self.frame_count % SUN_DROP_RATE == 0:
            x = random.randint(0, GAME_WIDTH)
            y = 0
            self.suns.append(Sun(x, y, 25))

        # Zombie spawn
        if self.frame_count % ZOMBIE_SPAWN_RATE == 0:
            row = random.randint(0, GRID_ROWS-1)
            self.zombies.append(Zombie(row, GRID_COLS-1))

        # Update suns
        for sun in self.suns[:]:
            sun.update()
            # Collect sun if clicked (handled in events)
            # Remove if off screen
            if sun.y > SCREEN_HEIGHT:
                self.suns.remove(sun)

        # Update plants (sunflower generation)
        new_suns = []
        for row in range(GRID_ROWS):
            for col in range(GRID_COLS):
                plant = self.grid[row][col]
                if plant:
                    sun = plant.update(self.frame_count)
                    if sun:
                        new_suns.append(sun)
        self.suns.extend(new_suns)

        # Update projectiles
        for proj in self.projectiles[:]:
            proj.move()
            if proj.x > GAME_WIDTH:
                self.projectiles.remove(proj)
                continue
            # Check collision with zombies
            hit = False
            for zombie in self.zombies:
                if zombie.row == proj.target_row and zombie.rect.colliderect(proj.rect):
                    zombie.health -= proj.damage
                    self.projectiles.remove(proj)
                    if zombie.health <= 0:
                        self.zombies.remove(zombie)
                    hit = True
                    break
            if hit:
                continue

        # Plant shooting
        for row in range(GRID_ROWS):
            for col in range(GRID_COLS):
                plant = self.grid[row][col]
                if plant and plant.type == 'peashooter':
                    # Check if any zombie in same row to the right
                    for zombie in self.zombies:
                        if zombie.row == row and zombie.col > col:
                            if self.frame_count - plant.last_shot > PEA_SHOOT_COOLDOWN:
                                plant.last_shot = self.frame_count
                                proj = Projectile(plant.x+CELL_SIZE-10, plant.y, row)
                                self.projectiles.append(proj)
                            break

        # Zombie movement and eating
        for zombie in self.zombies[:]:
            # Check for plant in front
            front_col = max(0, int((zombie.x + 10) // CELL_SIZE))
            if front_col < GRID_COLS and zombie.row < GRID_ROWS:
                plant = self.grid[zombie.row][front_col]
                if plant and not zombie.eating:
                    zombie.eating = True
                    zombie.target_plant = plant
                elif not plant:
                    zombie.eating = False
                    zombie.target_plant = None

            if zombie.eating and zombie.target_plant:
                # Damage plant
                zombie.target_plant.health -= 1
                if zombie.target_plant.health <= 0:
                    # Remove plant
                    for r in range(GRID_ROWS):
                        for c in range(GRID_COLS):
                            if self.grid[r][c] == zombie.target_plant:
                                self.grid[r][c] = None
                                break
                    zombie.eating = False
                    zombie.target_plant = None
            else:
                zombie.move()

            # Check if zombie reached house
            if zombie.x < 10:
                self.game_over = True

    def draw(self, screen):
        # Draw grid
        for row in range(GRID_ROWS):
            for col in range(GRID_COLS):
                rect = pygame.Rect(col*CELL_SIZE, row*CELL_SIZE, CELL_SIZE, CELL_SIZE)
                pygame.draw.rect(screen, LIGHT_GREEN if (row+col)%2==0 else DARK_GREEN, rect)
                pygame.draw.rect(screen, BLACK, rect, 1)

        # Draw plants
        for row in range(GRID_ROWS):
            for col in range(GRID_COLS):
                if self.grid[row][col]:
                    self.grid[row][col].draw(screen)

        # Draw zombies
        for zombie in self.zombies:
            zombie.draw(screen)

        # Draw projectiles
        for proj in self.projectiles:
            proj.draw(screen)

        # Draw suns
        for sun in self.suns:
            sun.draw(screen)

        # Draw sidebar
        sidebar_rect = pygame.Rect(GAME_WIDTH, 0, SIDEBAR_WIDTH, SCREEN_HEIGHT)
        pygame.draw.rect(screen, GRAY, sidebar_rect)
        pygame.draw.rect(screen, BLACK, sidebar_rect, 2)

        # Sun display
        sun_text = font.render(f"Sun: {self.sun_points}", True, BLACK)
        screen.blit(sun_text, (GAME_WIDTH+10, 10))

        # Plant buttons
        peashooter_btn = pygame.Rect(GAME_WIDTH+20, 50, 160, 50)
        pygame.draw.rect(screen, GREEN if self.selected_plant=='peashooter' else WHITE, peashooter_btn)
        pygame.draw.rect(screen, BLACK, peashooter_btn, 2)
        peashooter_text = small_font.render("Peashooter (50)", True, BLACK)
        screen.blit(peashooter_text, (GAME_WIDTH+25, 65))

        sunflower_btn = pygame.Rect(GAME_WIDTH+20, 120, 160, 50)
        pygame.draw.rect(screen, YELLOW if self.selected_plant=='sunflower' else WHITE, sunflower_btn)
        pygame.draw.rect(screen, BLACK, sunflower_btn, 2)
        sunflower_text = small_font.render("Sunflower (25)", True, BLACK)
        screen.blit(sunflower_text, (GAME_WIDTH+25, 135))

        # Game over message
        if self.game_over:
            overlay = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.SRCALPHA)
            overlay.fill((0, 0, 0, 128))
            screen.blit(overlay, (0, 0))
            game_over_text = font.render("GAME OVER", True, RED)
            text_rect = game_over_text.get_rect(center=(SCREEN_WIDTH//2, SCREEN_HEIGHT//2))
            screen.blit(game_over_text, text_rect)

def main_menu():
    while True:
        screen.fill(WHITE)
        title = font.render("Cat's PVZ", True, BLACK)
        title_rect = title.get_rect(center=(SCREEN_WIDTH//2, 200))
        screen.blit(title, title_rect)

        start_btn = pygame.Rect(SCREEN_WIDTH//2-100, 300, 200, 50)
        pygame.draw.rect(screen, GREEN, start_btn)
        pygame.draw.rect(screen, BLACK, start_btn, 2)
        start_text = font.render("Start Game", True, BLACK)
        start_text_rect = start_text.get_rect(center=start_btn.center)
        screen.blit(start_text, start_text_rect)

        pygame.display.flip()

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit()
                sys.exit()
            if event.type == pygame.MOUSEBUTTONDOWN:
                if start_btn.collidepoint(event.pos):
                    return  # start game

def main():
    main_menu()
    game = Game()
    running = True
    while running:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
            if event.type == pygame.MOUSEBUTTONDOWN:
                if event.button == 1:  # left click
                    game.handle_click(event.pos)
                    # Also check for sun collection
                    for sun in game.suns[:]:
                        if sun.rect.collidepoint(event.pos):
                            game.sun_points += sun.value
                            game.suns.remove(sun)

        game.update()
        screen.fill(WHITE)
        game.draw(screen)
        pygame.display.flip()
        clock.tick(60)

    pygame.quit()
    sys.exit()

if __name__ == "__main__":
    main()
