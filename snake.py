import pygame
import sys
import random
import pickle
from collections import deque

# --- Constants ---
GRID_WIDTH, GRID_HEIGHT = 16, 12
SCALE = 40
TOP_PANEL_HEIGHT = 40
BOTTOM_PANEL_HEIGHT = 40

SCREEN_WIDTH = GRID_WIDTH * SCALE
SCREEN_HEIGHT = GRID_HEIGHT * SCALE + TOP_PANEL_HEIGHT + BOTTOM_PANEL_HEIGHT

# Colors
BACKGROUND_COLOR_1 = (50, 50, 50)
BACKGROUND_COLOR_2 = (70, 70, 70)
PANEL_COLOR = (25, 25, 25)
WHITE = (255, 255, 255)
RED = (255, 0, 0)
SNAKE_HEAD_COLOR = (0, 200, 0)
SNAKE_BODY_COLOR_1 = (0, 200, 0)
SNAKE_BODY_COLOR_2 = (40, 220, 40)
SNAKE_BORDER_COLOR = (0, 80, 0)
INPUT_BOX_COLOR = (200, 200, 200)

# Game States
PLAYING = "playing"
GAME_OVER = "game_over"

class Scoreboard:
    def __init__(self, filename="scoreboard.dat"):
        self.filename = filename
        self.scores = self.load_scores()

    def load_scores(self):
        try:
            with open(self.filename, "rb") as f:
                return pickle.load(f)
        except (FileNotFoundError, EOFError, pickle.PickleError):
            return []

    def save_scores(self):
        with open(self.filename, "wb") as f:
            pickle.dump(self.scores, f)

    def add_score(self, name, score):
        self.scores.append((name, score))
        # Sort high to low, keep top 10
        self.scores = sorted(self.scores, key=lambda x: x[1], reverse=True)[:10]
        self.save_scores()


class Snake:
    def __init__(self):
        pygame.init()
        self.screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT))
        pygame.display.set_caption("Snek")

        # Load assets
        try:
            self.coin_img = pygame.image.load("src/coin.png").convert_alpha()
            self.coin_img = pygame.transform.scale(self.coin_img, (SCALE, SCALE))
        except pygame.error:
            print("Warning: 'src/coin.png' not found. Using a colored square for the coin.")
            self.coin_img = None

        self.font_large = pygame.font.Font(None, 36)
        self.font_small = pygame.font.Font(None, 24)
        self.clock = pygame.time.Clock()

        # Game state
        self.scoreboard = Scoreboard()
        self.reset()
        self.state = PLAYING

        self.input_text = ""
        self.input_active = False
        self.max_name_len = 16
        self.cursor_timer = 0.0
        self.cursor_visible = True
        self.score_saved = False

    def reset(self):
        self.dir = (1, 0)
        self.body = [(0, GRID_HEIGHT // 2)]
        self.input_buffer = deque()
        self.coin_pos = None
        self.coins = 0
        self.speed = 3.0
        self.progress = 0.0
        self.add_coin()
        self.input_text = ""
        self.input_active = False
        self.cursor_timer = 0.0
        self.cursor_visible = True
        self.score_saved = False

    def run(self):
        while True:
            dt = self.clock.tick(60) / 1000.0 # Delta time in seconds
            self.handle_events()
            self.update(dt)
            self.draw()

    def handle_events(self):
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit()
                sys.exit()
            if event.type == pygame.KEYDOWN:
                if self.state == PLAYING:
                    self.handle_playing_keys(event.key)
                elif self.state == GAME_OVER:
                    self.handle_game_over_keys(event)

    def handle_playing_keys(self, key):
        directions = {
            pygame.K_LEFT: (-1, 0), pygame.K_a: (-1, 0),
            pygame.K_RIGHT: (1, 0), pygame.K_d: (1, 0),
            pygame.K_UP: (0, -1),   pygame.K_w: (0, -1),
            pygame.K_DOWN: (0, 1),  pygame.K_s: (0, 1),
        }
        if key in directions:
            self.input_buffer.append(directions[key])
        if key == pygame.K_ESCAPE:
            pygame.quit()
            sys.exit()

    def handle_game_over_keys(self, event):
        if event.key == pygame.K_ESCAPE:
            pygame.quit()
            sys.exit()
        if event.key == pygame.K_SPACE:
            self.reset()
            self.state = PLAYING

        # Handle name input
        if self.input_active:
            if event.key == pygame.K_RETURN and self.input_text and not self.score_saved:
                self.scoreboard.add_score(self.input_text, self.coins)
                self.input_active = False
                self.score_saved = True
            elif event.key == pygame.K_BACKSPACE:
                self.input_text = self.input_text[:-1]
            elif len(self.input_text) < self.max_name_len and event.unicode.isprintable():
                self.input_text += event.unicode

    def update(self, dt):
        if self.state == PLAYING:
            self.progress += self.speed * dt
            if self.progress >= 1.0:
                self.progress -= 1.0
                self.process_input()
                self.move()
        if self.state == GAME_OVER and self.input_active:
            self.cursor_timer += dt
            if self.cursor_timer >= 0.5:
                self.cursor_timer = 0.0
                self.cursor_visible = not self.cursor_visible

    def process_input(self):
        while self.input_buffer:
            next_dir = self.input_buffer.popleft()
            # Stop self-intersection
            if next_dir != (-self.dir[0], -self.dir[1]):
                self.dir = next_dir
                break

    def move(self):
        head_x, head_y = self.body[0]
        dx, dy = self.dir
        new_head = (head_x + dx, head_y + dy)
        nx, ny = new_head

        # Check collisions
        if nx < 0 or nx >= GRID_WIDTH or ny < 0 or ny >= GRID_HEIGHT or new_head in self.body:
            self.state = GAME_OVER
            self.input_active = True
            return

        self.body.insert(0, new_head)

        # Check coin collection
        if new_head == self.coin_pos:
            self.coins += 1
            self.speed += 0.2
            self.add_coin()
        else:
            # Remove additional tail segment
            self.body.pop()

    def add_coin(self):
        # Place coin in a random position not occupied by the snake
        while True:
            pos = (random.randint(0, GRID_WIDTH - 1), random.randint(0, GRID_HEIGHT - 1))
            if pos not in self.body:
                self.coin_pos = pos
                break

    def draw(self):
        self.screen.fill(PANEL_COLOR)
        self.draw_grid()

        if self.state == PLAYING:
            self.draw_game_elements()
        elif self.state == GAME_OVER:
            self.draw_game_over_screen()

        self.draw_panels()
        pygame.display.flip()

    def draw_grid(self):
        # Draw checkerboard background
        for y in range(GRID_HEIGHT):
            for x in range(GRID_WIDTH):
                rect = pygame.Rect(x * SCALE, y * SCALE + TOP_PANEL_HEIGHT, SCALE, SCALE)
                color = BACKGROUND_COLOR_1 if (x + y) % 2 == 0 else BACKGROUND_COLOR_2
                pygame.draw.rect(self.screen, color, rect)

    def draw_game_elements(self):
        # Draw coin
        if self.coin_pos:
            cx, cy = self.coin_pos
            rect = pygame.Rect(cx * SCALE, cy * SCALE + TOP_PANEL_HEIGHT, SCALE, SCALE)
            if self.coin_img:
                self.screen.blit(self.coin_img, rect.topleft)
            else:
                pygame.draw.rect(self.screen, (255, 215, 0), rect, border_radius=10)

        # Draw snake
        for i, segment in enumerate(self.body):
            sx, sy = segment
            rect = pygame.Rect(sx * SCALE, sy * SCALE + TOP_PANEL_HEIGHT, SCALE, SCALE)
            color = SNAKE_BODY_COLOR_1 if i % 2 == 0 else SNAKE_BODY_COLOR_2
            pygame.draw.rect(self.screen, color, rect, border_radius=6)
            pygame.draw.rect(self.screen, SNAKE_BORDER_COLOR, rect, 2, border_radius=6)

        # Draw snake head with eyes
        head_x, head_y = self.body[0]
        head_rect = pygame.Rect(head_x * SCALE, head_y * SCALE + TOP_PANEL_HEIGHT, SCALE, SCALE)
        pygame.draw.rect(self.screen, SNAKE_HEAD_COLOR, head_rect, border_radius=8)

        eye_radius = SCALE // 8
        offset = SCALE // 4
        center_x, center_y = head_rect.center

        eye1_pos = (center_x + self.dir[1] * offset, center_y - self.dir[0] * offset)
        eye2_pos = (center_x - self.dir[1] * offset, center_y + self.dir[0] * offset)

        pygame.draw.circle(self.screen, WHITE, eye1_pos, eye_radius * 1.5)
        pygame.draw.circle(self.screen, WHITE, eye2_pos, eye_radius * 1.5)
        pygame.draw.circle(self.screen, (0, 0, 0), eye1_pos, eye_radius)
        pygame.draw.circle(self.screen, (0, 0, 0), eye2_pos, eye_radius)

    def draw_panels(self):
        # Top panel
        score_text = self.font_small.render(f"Coins: {self.coins}", True, WHITE)
        self.screen.blit(score_text, (10, 10))

        # Bottom panel
        controls_text = self.font_small.render(
            "Use Arrow Keys/WASD to move. Eat coins to grow. Don't hit walls or yourself.",
            True, WHITE
        )
        text_rect = controls_text.get_rect(center=(SCREEN_WIDTH / 2, SCREEN_HEIGHT - BOTTOM_PANEL_HEIGHT / 2))
        self.screen.blit(controls_text, text_rect)

    def draw_game_over_screen(self):
        text1 = self.font_large.render("Game Over", True, RED)
        text2 = self.font_small.render(f"Final Score: {self.coins}", True, WHITE)
        if not self.score_saved:
            text3 = self.font_small.render("Press SPACE to Restart | ENTER to Save", True, WHITE)
        else:
            text3 = self.font_small.render("Score Saved! Press SPACE to Restart", True, WHITE)

        center_y = TOP_PANEL_HEIGHT + (GRID_HEIGHT * SCALE) / 2

        rect1 = text1.get_rect(center=(SCREEN_WIDTH / 2, center_y - 60))
        rect2 = text2.get_rect(center=(SCREEN_WIDTH / 2, center_y - 30))
        rect3 = text3.get_rect(center=(SCREEN_WIDTH / 2, center_y))

        self.screen.blit(text1, rect1)
        self.screen.blit(text2, rect2)
        self.screen.blit(text3, rect3)

        # Input box for name
        if self.input_active:
            box_rect = pygame.Rect(SCREEN_WIDTH / 2 - 100, center_y + 40, 200, 30)
            pygame.draw.rect(self.screen, INPUT_BOX_COLOR, box_rect)
            pygame.draw.rect(self.screen, WHITE, box_rect, 2)

            display_text = self.input_text
            if self.cursor_visible:
                display_text += "_"

            name_surface = self.font_small.render(display_text, True, (0, 0, 0))
            self.screen.blit(name_surface, (box_rect.x + 5, box_rect.y + 5))

        # Draw scoreboard
        y_offset = center_y + 80
        score_title = self.font_small.render("High Scores:", True, WHITE)
        self.screen.blit(score_title, (SCREEN_WIDTH / 2 - 60, y_offset))
        y_offset += 20

        for i, (name, score) in enumerate(self.scoreboard.scores[:5], 1):
            line = self.font_small.render(f"{i}. {name}: {score}", True, WHITE)
            self.screen.blit(line, (SCREEN_WIDTH / 2 - 80, y_offset))
            y_offset += 20


if __name__ == "__main__":
    game = Snake()
    game.run()
