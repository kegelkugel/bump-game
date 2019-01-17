#! /usr/bin/env python3
#
# A fun arcade game where you have to hit other players and must avoid
# dangerous walls (and maybe other dangers later, too).
#
# Not fully implemented yet.
#
# started by Markus Reinert on 2019-01-13

import time
from enum import Enum

import numpy as np
import numpy.linalg as LA
import pygame


# RGB colour codes
# (sorry for not being PEP 8 conform here)
WHITE = [255, 255, 255]
GREY  = [128, 128, 128]
BLACK = [  0,  0,    0]
OCEAN = [181, 231, 238]

# Size of the window
SCREEN_W = 1000
SCREEN_H = 600

# Size of the figure within the game.
# The image file of the figure should be a quadratic image with 'PLAYER_SIZE'
# as length and height.  Within the image, the figure should be be a circle
# with diameter 'PLAYER_SIZE'.  The rest of the image should be transparent.
PLAYER_SIZE = 50

# List of available characters.
# Each character is a 2-tuple.
# The first element is the name as displayed.
# The second element is a "template" for the filenames, such that the full
# filenames are "<template>.<size>.png", with size 200 and PLAYER_SIZE.
CHARACTERS = [
    ("Penguin", "images/characters/penguin"),
    ("Wizard Penguin", "images/characters/wizguin"),
    ("Bot", "images/characters/pony"),
]

N_CHARACTERS = len(CHARACTERS)


class Figure:

    normalspeed = 500  # pixel per second
    boostspeed = 1500  # pixel per second
    acceleration = 600.0  # pixel per second^2
    boostduration = 0.2  # second
    dizzyduration = 0.2  # second

    def __init__(self, name, filename_template):
        self.alive = True
        self.name = name
        self.pic = pygame.image.load(
            ".".join((filename_template, str(PLAYER_SIZE), "png"))
        )
        self.pic_death = pygame.image.load("images/other/skull.png")
        self.w, self.h = self.pic.get_size()
        self.pos = None
        self.direction = np.zeros(2)        # direction imposed by user
        self._direction = np.array([0, 1])  # actual direction (normalized)
        self.speed = 0
        # Timer for the last position update
        self.last_update = None
        # Timer for the start of dizziness (e.g. after a crash)
        # When dizzy, direction cannot be changed and booster cannot be
        # activated but one can decrease velocity.
        self.dizzy_start = None

    def set_centre(self, position):
        self.pos = position - np.array([self.w/2, self.h/2])
        self.last_update = time.time()

    def update(self):
        if not self.alive:
            return
        current_time = time.time()
        # Check if still dizzy
        if self.dizzy_start is not None:
            if current_time - self.dizzy_start >= self.dizzyduration:
                self.dizzy_start = None
        # Evaluate the direction set by player
        if np.all(self.direction == 0):
            # Request to halt
            speed_aim = 0
        else:
            # Request to move with normal speed in the given direction
            speed_aim = self.normalspeed
            # Change direction if not dizzy
            if self.dizzy_start is None:
                # TODO: change gradually
                self._direction = self.direction / LA.norm(self.direction)
        # Accelerate or brake as requested
        current_speed_change = self.acceleration * (current_time-self.last_update)
        if self.speed < speed_aim:
            self.speed = min(self.speed + current_speed_change, speed_aim)
        elif self.speed > speed_aim:
            self.speed = max(self.speed - current_speed_change, speed_aim)
        # Move in the current direction with the current velociy
        current_place_change = self.speed * (current_time-self.last_update)
        for dx in range(int(round(current_place_change))):
            # This is not implemented very well, since the position is updated
            # for one player at first and then for the other, it should be more
            # in parallel.
            self.pos += self._direction
            # Check for collisions
            # 'colcont' is a global variable.  This could/should be changed.
            collision = colcont.check_collision(self)
            # Case 1: no collision occured
            if collision == CT.NoCollision:
                continue
            # Case 2: a deadly collision occured
            elif collision == CT.Critical:
                self.alive = False
                # Dead bodies should disappear after some time
                break
            # Case 3: a collision occured, but not critical
            else:
                # Set the figure dizzy
                self.dizzy_start = current_time
                # Reset to the previous position
                self.pos -= self._direction
                # If collided with a wall, adjust the direction according to an
                # ideal reflection on a solid boundary
                if collision == CT.Horizontal:
                    self._direction[1] = -self._direction[1]
                elif collision == CT.Vertical:
                    self._direction[0] = -self._direction[0]
                # If collided with another player, adjust the direction and
                # speed of both figures according to an elastic collision
                elif collision == CT.Player:
                    opponent = colcont.collision_partner
                    # TODO: make realistic collisions
                    # Take into account:
                    # After a zero-friction collision of a moving ball with a
                    # stationary one of equal mass, the angle between the
                    # directions of the two balls is 90 degrees, unless the
                    # collision is head-on. (for further information see, e.g.:
                    # https://en.wikipedia.org/wiki/Collision#Billiards)
                    # Exchange speeds (this is unrealistic)
                    old_speed = self.speed
                    self.speed = opponent.speed
                    opponent.speed = old_speed
                    # Calculate the collision angle
                    coll_angle = np.arctan2(*((self.pos - opponent.pos)[::-1]))
                    self_angle = coll_angle - np.arctan2(*(self._direction[::-1]))
                    c = np.cos(self_angle)
                    s = np.sin(self_angle)
                    turn_matrix = np.array([[c, -s], [s, c]])
                    # this might be unrealistic
                    self._direction = np.dot(turn_matrix, self._direction)
                    # this is unrealistic and no good style, because
                    # '_direction' should be private.
                    opponent._direction = -self._direction
        self.last_update = current_time

    def activate_boost(self):
        # Booster is activated immediately (without accelerating) if not dizzy
        if self.dizzy_start is None:
            self.speed = self.boostspeed

    def get_rect(self):
        """This method is used to check for collisions with the walls"""
        return self.pic.get_rect().move(self.pos)

    def draw(self, window):
        if self.alive:
            window.blit(self.pic, self.pos)
        else:
            # Dead bodies should disappear after some time
            window.blit(self.pic_death, self.pos)


class BT(Enum):
    """Type of border"""
    Bottom = 0
    Top = 1
    Left = 2
    Right = 3


class Border:

    def __init__(self, border_type: BT, size: int):
        self.type_ = border_type
        if border_type == BT.Bottom:
            self.pattern = "-----XXXX----------XXXX-----"
            self.pic_normal = pygame.image.load("images/walls/alga_normal.png")
            self.pic_danger = pygame.image.load("images/walls/alga_danger.png")
            self.x_rep = SCREEN_W / len(self.pattern)
            self.y_rep = 0
            self.x = 0
            self.y = SCREEN_H - self.pic_normal.get_size()[1]
            self.rect = pygame.Rect(self.x, SCREEN_H-size, SCREEN_W, size)
            # The y-coordinate to display the image is different from the
            # bounding box of the wall, because the tips of the algae are
            # not enough to bounce or kill.
        elif border_type == BT.Top:
            self.pattern = "--XX--XX--X--XX--XX--"
            self.pic_normal = pygame.image.load("images/walls/ice_normal.png")
            self.pic_danger = pygame.image.load("images/walls/ice_danger.png")
            self.x_rep = SCREEN_W / len(self.pattern)
            self.y_rep = 0
            self.x = 0
            self.y = 0
            self.rect = pygame.Rect(self.x, self.y, SCREEN_W, size)
        elif border_type == BT.Left:
            self.pattern = "---XX--XX---"
            self.pic_normal = pygame.image.load("images/walls/grid_normal.png")
            self.pic_danger = pygame.image.load("images/walls/grid_danger_left.png")
            self.x_rep = 0
            self.y_rep = SCREEN_H / len(self.pattern)
            self.x = 0
            self.y = 0
            self.rect = pygame.Rect(self.x, self.y, size, SCREEN_H)
        elif border_type == BT.Right:
            self.pattern = "---XX--XX---"
            self.pic_normal = pygame.image.load("images/walls/grid_normal.png")
            self.pic_danger = pygame.image.load("images/walls/grid_danger_right.png")
            self.x_rep = 0
            self.y_rep = SCREEN_H / len(self.pattern)
            self.x = SCREEN_W - size
            self.y = 0
            self.rect = pygame.Rect(self.x, self.y, size, SCREEN_H)

    def check_critical(self, x, y):
        if self.x_rep != 0:
            if self.pattern[int(x/self.x_rep)] == "X":
                return True
        elif self.y_rep != 0:
            if self.pattern[int(y/self.y_rep)] == "X":
                return True
        return False

    def draw(self, window):
        for i in range(len(self.pattern)):
            if self.pattern[i] == "X":
                window.blit(self.pic_danger, (self.x + i*self.x_rep,
                                              self.y + i*self.y_rep))
            else:
                window.blit(self.pic_normal, (self.x + i*self.x_rep,
                                              self.y + i*self.y_rep))


class CT(Enum):
    """Type of collision"""
    NoCollision = 0
    Horizontal = 1
    Vertical = 2
    Player = 3
    Critical = 10


class CollisionControl:

    def __init__(self, players, walls):
        self.players = players
        self.walls = walls
        self.collision_partner = None

    def check_collision(self, player: Figure) -> CT:
        rect = player.get_rect()
        # Check for collision with boundaries
        for wall in self.walls:
            if rect.colliderect(wall.rect):
                if wall.check_critical(rect[0] + rect[2]/2, rect[1] + rect[3]/2):
                    return CT.Critical
                elif wall.type_ == BT.Top or wall.type_ == BT.Bottom:
                    return CT.Horizontal
                elif wall.type_ == BT.Left or wall.type_ == BT.Right:
                    return CT.Vertical
        # Check for collision with other players
        for fig in self.players:
            if fig != player and fig.alive:
                if LA.norm(player.pos - fig.pos) <= PLAYER_SIZE:
                    self.collision_partner = fig
                    return CT.Player
        return CT.NoCollision


class Joystick:
    # This class could directly control a figure

    def __init__(self):
        # Position of the centre and the top right corner of the star
        self.x = self.y = None
        self.x_disp = self.y_disp = None
        # Position of the pointer, relative to the star's centre
        self.x_pointer = self.y_pointer = 0
        # Display information
        self.point = pygame.image.load("images/control/joystick_pos.png")
        self.star = pygame.image.load("images/control/joystick_star.png")
        self.star_w, self.star_h = self.star.get_size()
        self.point_w, self.point_h = self.point.get_size()
        self.r_squared = (self.star_w/2)**2

    def activate(self, position):
        self.x, self.y = position
        self.x_pointer = 0
        self.y_pointer = 0
        self.x_disp = self.x - self.star_w//2
        self.y_disp = self.y - self.star_h//2

    def deactivate(self):
        self.x = self.y = None

    def set_direction(self, position):
        x_mouse, y_mouse = position
        norm_squared = (x_mouse - self.x)**2 + (y_mouse - self.y)**2
        if norm_squared <= self.r_squared:
            self.x_pointer = x_mouse - self.x
            self.y_pointer = y_mouse - self.y
        else:
            # Scale the position vector to stay within the star
            self.x_pointer = (x_mouse - self.x) / np.sqrt(norm_squared/self.r_squared)
            self.y_pointer = (y_mouse - self.y) / np.sqrt(norm_squared/self.r_squared)

    def draw(self, window):
        if self.x is not None:
            window.blit(self.star, (self.x_disp, self.y_disp))
            window.blit(self.point, (self.x + self.x_pointer - self.point_w//2,
                                     self.y + self.y_pointer - self.point_h//2))


class AI:

    def __init__(self, figure: Figure, player_list: list):
        self.figure = figure
        self.others = player_list
        self.victim = player_list[0]

    def update(self):
        # TODO: use booster
        if not self.victim.alive:
            for player in self.others:
                if player.alive:
                    self.victim = player
                    break
            else:
                self.figure.direction = np.zeros(2)
                return
        self.figure.direction = self.victim.pos - self.figure.pos


class Wave:

    def __init__(self, path, y_offset, speed=0):
        self.pic = pygame.image.load(path)
        self.pic2 = pygame.transform.flip(self.pic, True, False)
        self.x = 0
        self.y = y_offset
        self.speed = speed

    def update(self):
        self.x = (self.x + self.speed) % (2*SCREEN_W)

    def draw(self, window):
        if self.x < SCREEN_W:
            window.blit(self.pic, (self.x, self.y))
        window.blit(self.pic2, (self.x - SCREEN_W, self.y))
        if self.x > SCREEN_W:
            window.blit(self.pic, (self.x - 2*SCREEN_W, self.y))


pygame.init()

# Fonts
ft_title = pygame.font.Font("fonts/Puk-Regular.otf", 60)
ft_info = pygame.font.Font(None, 20)


def display_character(window, name, path_template):
    """Screen to select a character."""
    # Could be improved a lot.
    border_size = 20
    path = ".".join((path_template, "200", "png"))
    pic = pygame.image.load(path)
    pic_w, pic_h = pic.get_size()
    text = ft_title.render(" ".join(("<-", name, "->")), 1, WHITE)
    text_w, text_h = text.get_size()
    pygame.draw.rect(window, GREY, (SCREEN_W/2 - pic_w/2 - border_size,
                                    SCREEN_H/2 - pic_h/2 - text_h - border_size,
                                    pic_w + border_size*2, pic_h + border_size*2),
                     border_size)
    window.blit(pic, (SCREEN_W/2 - pic_w/2, SCREEN_H/2 - pic_h/2 - text_h))
    window.blit(text, (SCREEN_W/2 - text_w/2, SCREEN_H/2 + pic_h/2 - text_h/2))


def draw_background(window, walls, background_layers):
    window.fill(OCEAN)
    # Draw internal waves
    for layer in background_layers:
        layer.draw(window)
    # Draw boundaries
    for wall in walls:
        wall.draw(window)


window = pygame.display.set_mode([SCREEN_W, SCREEN_H])

# Display the screen to select a character
selected_character = 0

window.fill(OCEAN)
display_character(window, *CHARACTERS[selected_character])
pygame.display.flip()

running = True
while running:
    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            exit()
        if event.type == pygame.KEYDOWN:
            if event.key == pygame.K_ESCAPE:
                exit()
            elif event.key == pygame.K_RIGHT:
                selected_character = (selected_character+1) % N_CHARACTERS
                window.fill(OCEAN)
                display_character(window, *CHARACTERS[selected_character])
                pygame.display.flip()
            elif event.key == pygame.K_LEFT:
                selected_character = (selected_character-1) % N_CHARACTERS
                window.fill(OCEAN)
                display_character(window, *CHARACTERS[selected_character])
                pygame.display.flip()
            elif event.key == pygame.K_SPACE or event.key == pygame.K_RETURN:
                running = False

# Create the selected character to be controled by the user
player1 = Figure(*CHARACTERS[selected_character])
player1.set_centre(np.array([100, 100]))
joystick = Joystick()

# Create a bot character
player2 = Figure(*CHARACTERS[-1])
player2.set_centre(np.array([SCREEN_W-100, SCREEN_H-100]))
bot = AI(player2, [player1])

# Create the boundaries
wall_width = 50
walls = []
walls.append(Border(BT.Left, wall_width))
walls.append(Border(BT.Right, wall_width))
walls.append(Border(BT.Bottom, wall_width))
walls.append(Border(BT.Top, wall_width))

# Set up the collision control
colcont = CollisionControl([player1, player2], walls)

# Create the background
background_layers = [
    Wave("images/background/ocean_layer1.png", 210, 0.35),
    Wave("images/background/ocean_layer2.png", 325, 0.65),
    Wave("images/background/ocean_layer3.png", 415, 0.95),
    Wave("images/background/ocean_layer4.png", 480, 1.25),
]

# For user control (can be integrated into the joystick)
press_pos = None
pressed = 0
# To measure the framerate:
frame = 0
frame_time = time.time()
fps = 0
fps_text = ft_info.render("FPS: {}".format(fps), 1, BLACK)
# Start main game loop
while True:
    # Compute framerate
    # TODO use the tools described in the Pygame docs:
    # https://www.pygame.org/docs/ref/time.html#pygame.time.Clock
    frame += 1
    if frame == 10:
        frame = 0
        current_time = time.time()
        fps = int(10 // (current_time-frame_time))
        fps_text = ft_info.render("FPS: {}".format(fps), 1, BLACK)
        frame_time = current_time
    # Update routine
    player1.update()
    player2.update()
    for layer in background_layers:
        layer.update()
    draw_background(window, walls, background_layers)
    window.blit(fps_text, (0, 0))
    joystick.draw(window)
    player1.draw(window)
    player2.draw(window)
    pygame.display.flip()
    # Handle events
    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            exit()
        elif event.type == pygame.KEYDOWN:
            if event.key == pygame.K_ESCAPE:
                exit()
            # For debugging only (restart should be implemented with a menu)
            elif event.key == pygame.K_r:
                player1.alive = True
                player1.set_centre(np.array([500.0, 200.0]))
            # For debugging only (well, there could be a keyboard control, but
            # then the buttons have to be kept pressed to move in a direction;
            # furthermore, one needs to be able to move diagonally)
            elif event.key == pygame.K_LEFT:
                player1.direction = np.array([-1, 0])
            elif event.key == pygame.K_RIGHT:
                player1.direction = np.array([+1, 0])
            elif event.key == pygame.K_UP:
                player1.direction = np.array([0, -1])
            elif event.key == pygame.K_DOWN:
                player1.direction = np.array([0, +1])
            elif event.key == pygame.K_SPACE:
                player1.activate_boost()
        # Other possbility to implement mouse control:
        # mouse motion is directly translated to an according motion of the
        # figure and a mouse click activates boost.  This might be better for
        # control with the touchpad of a laptop.
        # The way it is implemented now is intended for touchscreens.
        elif event.type == pygame.MOUSEBUTTONDOWN:
            pressed += 1
            if press_pos is None:
                press_pos = np.array(event.pos)
                joystick.activate(press_pos)
            else:
                player1.direction = np.array(event.pos) - press_pos
                player1.activate_boost()
        elif event.type == pygame.MOUSEBUTTONUP:
            pressed -= 1
            if pressed == 0:
                press_pos = None
                player1.direction = np.zeros(2)
                player1.speeed = 0
                joystick.deactivate()
        elif event.type == pygame.MOUSEMOTION:
            if press_pos is not None:
                player1.direction = np.array(event.pos) - press_pos
                joystick.set_direction(event.pos)
    # Let the AI make its move
    bot.update()

