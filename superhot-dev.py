import pygame
from random import choice, randint
import time
import config
import os

all_sprites = pygame.sprite.Group()

SHOOT_LENGTH = 10

pygame.init()
n1 = 15
n2 = 15
cs = 48
size = 130 + n1 * cs, 130 + n2 * cs
screen = pygame.display.set_mode(size)
pygame.display.set_caption('Superhot 2d')


def load_image(name, color_key=None):
    fullname = os.path.join(config.sprite_folder_name, name)
    try:
        image = pygame.image.load(fullname).convert()
    except pygame.error as message:
        print('Cannot load image:', name)
        raise SystemExit(message)

    if color_key is not None:
        if color_key == -1:
            color_key = image.get_at((0, 0))
        image.set_colorkey(color_key)
    else:
        image = image.convert_alpha()
    return image


# стабильные объекты
class CellObject:
    image = load_image(config.field_sprite)

    def __init__(self, angle=0):
        self.angle = angle

    def __str__(self):
        return self.__class__.__name__


class SimpleField(CellObject):
    image = load_image(config.field_sprite)

    def __init__(self, angle=0):
        super().__init__(angle)


# объекты, которые могут быть живы или мертвы
class Creature(CellObject):
    image = load_image(config.field_sprite)

    def __init__(self, angle=0):
        super().__init__(angle)
        self.alive = True


class Enemy(Creature):
    image = load_image(config.enemy_sprite, -1)

    def __init__(self, pos=(0, 0), angle=0, alive=True):
        super().__init__()
        self.triggered = False
        self.angle = angle
        self.x, self.y = pos
        self.Lose = False
        self.alive = alive
        self.triggered_vector = [0, 0]

    def get_pos(self):
        return self.x, self.y

    def __repr__(self):
        return f'Enemy Triggered - {self.triggered},' \
               f' Triggered vector - {self.triggered_vector},' \
               f' angle - {self.angle}, x - {self.x}, y - {self.y}, Lose - {self.Lose}'

class Player(Creature):
    image = load_image(config.player_sprite, -1)

    def __init__(self, pos=(0, 0), angle=0):
        super().__init__(angle)
        self.x, self.y = pos
        self.angle = angle

    def get_pos(self):
        return self.x, self.y

    def set_pos(self, x, y):
        self.x = x
        self.y = y


class Wall(Creature):
    image = load_image(config.wall_sprite)

    def __init__(self):
        super().__init__()


class Boom(Creature):
    image = load_image(config.boom_sprite)

    def __init__(self):
        super().__init__()


# ошибки
class BorderError(Exception):
    pass


class WallStepError(Exception):
    pass


class StandartSprite(pygame.sprite.Sprite):
    def __init__(self, image, pos, angle):
        super().__init__()
        size = image.get_size()
        self.image = image
        if angle != 0:
            self.image = pygame.transform.rotate(self.image, angle)
        self.rect = self.image.get_rect()
        self.rect.x = pos[0]
        self.rect.y = pos[1]


class ShootSprite(CellObject):
    image = load_image(config.lazer_sprite)

    def __init__(self, pos, angle=0, timer=0):
        super().__init__(pos)
        self.timer = timer
        self.angle = angle


class EnemyShootSprite(ShootSprite):
    image = load_image(config.enemy_lazer_sprite)

class Pepl(CellObject):
    image = load_image(config.pepl_sprite)

    def __init__(self, pos, angle=0, timer=10):
        super().__init__(pos)
        self.timer = timer
        self.angle = angle

class EnemyPepl(Pepl):
    image = load_image(config.enemy_pepl_sprite)



class Pepl_Boom(Pepl):
    image = load_image(config.pepl_boom_sprite)


class Board:
    def __init__(self, width, height, cell_size=30,
                 left_shift=10, top_shift=10):
        self.width = width
        self.height = height
        self.enemies = []
        self.cell_size = cell_size
        self.left_shift = left_shift
        self.top_shift = top_shift
        self.sprites = pygame.sprite.Group()
        self.game_run = False

        self.board = [[[] for _ in range(self.width)] for _ in range(self.height)]

    def enemy_move(self, enemy, vector):
        angles = {(0, 1): 180, (0, -1): 0, (1, 0): 270, (-1, 0): 90}
        x_v, y_v = vector
        x, y = enemy.get_pos()
        if not (0 <= x + x_v < self.width and 0 <= y + y_v < self.height):
            return False
        for cell_obj in self.board[y + y_v][x + x_v]:
            if isinstance(cell_obj, Wall) or isinstance(cell_obj, Boom) or isinstance(cell_obj, Enemy):
                return False
        # если все нормально
        if enemy in self.board[y][x]:
            self.board[y][x].remove(enemy)
            self.board[y + y_v][x + x_v].append(enemy)
            enemy.x, enemy.y = x + x_v, y + y_v
            enemy.angle = angles[tuple(vector)]
            return True
        else:
            return False

    def enemy_step(self):  # ходят враги
        destroed = set()
        angles = {(0, 1): 180, (0, -1): 0, (1, 0): 270, (-1, 0): 90}
        for enemy in self.enemies:
            x, y = enemy.get_pos()
            x_dif = self.player_obj.x - enemy.x
            y_dif = self.player_obj.y - enemy.y
            if x_dif == 0 or y_dif == 0:
                enemy.Lose = False
                enemy.triggered = True
                enemy.triggered_vector = [0, 1] if x_dif == 0 and y_dif > 0 else [0, -1] \
                if x_dif == 0 and y_dif < 0 else [1, 0] if y_dif == 0 and x_dif > 0 else [-1, 0]
                enemy.angle = angles[tuple(enemy.triggered_vector)]
            if abs(x_dif) <= 1 and enemy.triggered == False and enemy.Lose == False:
                enemy.triggered_vector = [0, y_dif // abs(y_dif)]
                enemy.triggered = True
                enemy.angle = angles[tuple(enemy.triggered_vector)]
            if abs(y_dif) <= 1 and enemy.triggered == False and enemy.Lose == False:
                enemy.triggered = True
                enemy.triggered_vector = [x_dif // abs(x_dif), 0]
                enemy.angle = angles[tuple(enemy.triggered_vector)]
            if not enemy.Lose and enemy.triggered:  # если он видит игрока и прошлый раз он не промазал
                enemy.triggered = False
                enemy.Lose = True
                x_v, y_v = enemy.triggered_vector
                x, y = enemy.get_pos()
                while True:
                    if not (0 <= x + x_v < self.width and 0 <= y + y_v < self.height):
                        break
                    if self.player_obj.get_pos() == (x + x_v, y + y_v):
                        self.game_run = False
                        self.board[y + y_v][x + x_v].append(EnemyPepl((y + y_v, x + x_v), enemy.angle))
                        break
                    if len(self.board[y + y_v][
                               x + x_v]) != 1:  # в боарде хранятся списки обектов, и если ничего нет, то там
                        for i in self.board[y + y_v][x + x_v]:
                            if isinstance(i, Wall) or isinstance(i, Enemy):
                                destroed.add((y + y_v, x + x_v, i, enemy.angle))
                            elif isinstance(i, Boom):
                                self.explosion(x + x_v, y + y_v)
                        break  # только объект класса SimpleField
                    x += x_v
                    y += y_v
                    self.board[y][x].append(EnemyShootSprite((y, x), enemy.angle, SHOOT_LENGTH))
                continue
            if len(self.board[y + y_dif // abs(y_dif)][x]) > 1 and len(self.board[y][x + x_dif // abs(x_dif)]) > 1:
                # пасть рвет препятствию
                for i in self.board[y + y_dif // abs(y_dif)][x]:
                    if isinstance(i, SimpleField):
                        continue
                    elif isinstance(i, Boom):
                        self.explosion(x, y + y_dif // abs(y_dif))
                        continue
                    elif isinstance(i, Enemy):
                        if i in self.enemies:
                            self.enemies.remove(i)
                    self.board[y + y_dif // abs(y_dif)][x].remove(i)
                self.board[y + y_dif // abs(y_dif)][x].append(EnemyPepl((x, y + y_dif // abs(y_dif)), enemy.angle, 10))
                continue
            if abs(x_dif) > abs(y_dif):
                if self.enemy_move(enemy, [x_dif // abs(x_dif), 0]):
                    continue
            if self.enemy_move(enemy, [0, y_dif // abs(y_dif)]):
                continue
            else:
                self.enemy_move(enemy, [x_dif // abs(x_dif), 0])
            enemy.Lose = False
        for elem in destroed:
            if isinstance(elem[2], Enemy):
                if elem[2] in self.enemies:
                    self.enemies.remove(elem[2])
            if elem[2] in self.board[elem[0]][elem[1]]:
                self.board[elem[0]][elem[1]].remove(elem[2])
                self.board[elem[0]][elem[1]].append(EnemyPepl((elem[0], elem[1]), elem[3]))

    # Функция, отслеживающая время отрисовки лазеров
    def player_shoot(self, vector):
        x_v, y_v = vector
        x, y = self.player_obj.get_pos()
        while True:
            if not (0 <= x + x_v < self.width and 0 <= y + y_v < self.height):
                break
            if len(self.board[y + y_v][x + x_v]) != 1:  # в боарде хранятся списки обектов, и если ничего нет, то там
                for i in self.board[y + y_v][x + x_v]:
                    if isinstance(i, Wall) or isinstance(i, Enemy):
                        self.board[y + y_v][x + x_v].remove(i)
                        if isinstance(i, Enemy):
                            if i in self.enemies:
                                self.enemies.remove(i)
                        self.board[y + y_v][x + x_v].append(
                            Pepl((x + x_v, y + y_v), self.player_obj.angle, 10))
                    elif isinstance(i, Boom):
                        self.explosion(x + x_v, y + y_v)
                break  # только объект класса SimpleField
            x += x_v
            y += y_v
            self.board[y][x].append(ShootSprite((y, x), self.player_obj.angle, SHOOT_LENGTH))

    def shoot_render(self, screen):
        changed = False
        for i in range(self.height):
            for j in range(self.width):
                for creature in self.board[i][j]:
                    if isinstance(creature, (ShootSprite, Pepl, EnemyShootSprite, EnemyPepl)):
                        if creature.timer > 0:
                            creature.timer -= 1
                        else:
                            changed = True
                            self.board[i][j].remove(creature)
        if changed:
            self.render(screen)

    def explosion(self, x, y):
        for i in range(-1, 2):
            for j in range(-1, 2):
                if x + i < 0 or x + i >= len(self.board):
                    continue
                if y + j < 0 or y + j >= len(self.board):
                    continue
                for z in self.board[y + j][x + i]:
                    if isinstance(z, SimpleField):
                        continue
                    elif isinstance(z, Boom):
                        self.board[y + j][x + i].remove(z)
                        self.explosion(x + i, y + j)
                        return
                    elif isinstance(z, Enemy):
                        if z in self.enemies:
                            self.enemies.remove(z)
                    self.board[y + j][x + i].remove(z)
                self.board[y + j][x + i].append(Pepl_Boom((x + i, y + j)))
                if self.player_obj.get_pos() == (x + i, y + j):
                    self.player_obj.alive = False
                    self.game_run = False

    def render(self, screen):
        screen.fill('black')
        self.sprites.empty()
        self.sprites.add(StandartSprite(load_image(config.background_sprite), (0, 0), 0))
        for i in range(self.height):
            for j in range(self.width):
                for creature in self.board[i][j]:
                    self.sprites.add(StandartSprite(creature.image,
                                                    (j * self.cell_size + self.left_shift,
                                                     i * self.cell_size + self.top_shift), creature.angle))
        self.sprites.add(StandartSprite(self.player_obj.image,
                                        (self.player_obj.x * self.cell_size + self.left_shift,
                                         self.player_obj.y * self.cell_size + self.top_shift), self.player_obj.angle))
        self.sprites.update()
        self.sprites.draw(screen)

    def render_full_screen(self, screen, path):
        #screen.fill('black')
        #self.sprites.empty()
        image = pygame.transform.scale(load_image(path), (screen.get_width(), screen.get_height()))
        image.set_alpha(170)
        self.sprites.add(StandartSprite(image, (0, 0), 0))
        self.sprites.draw(screen)

    def get_cell(self, pos):
        x_index = (pos[0] - self.left_shift) // self.cell_size
        y_index = (pos[1] - self.top_shift) // self.cell_size

        if 0 <= x_index < self.width and 0 <= y_index < self.height:
            return x_index, y_index
        return None

    def add_object_to_cell(self, obj, pos=None):
        # метод для генерации поля, проверяет пустая ли клетка позиции
        # есил да, то добавляет объект и возвращает True, иначе - возвращает False
        # если pos не передали генерирует сама
        if pos is None:
            pos = randint(0, self.height - 1), randint(0, self.width - 1)
        if len(self.board[pos[1]][pos[0]]) == 1:
            self.board[pos[1]][pos[0]].append(obj)
            return True
        return False

    def generate_field(self, box_count=10, boom_count=10, enemy_count=2):
        self.board = [[[] for _ in range(self.width)] for _ in range(self.height)]
        for i in range(self.height):
            for j in range(self.width):
                self.board[i][j].append(SimpleField())
        for i in range(box_count):
            result = False
            while not result:
                result = self.add_object_to_cell(Wall())
        for i in range(boom_count):
            result = False
            while not result:
                result = self.add_object_to_cell(Boom())
        for i in range(enemy_count):
            result = False
            while not result:
                x, y = randint(0, self.height - 1), randint(0, self.width - 1)
                new_enemy = Enemy((x, y), choice([0, 90, 180, 270]))
                result = self.add_object_to_cell(new_enemy, pos=(x, y))
            self.enemies.append(new_enemy)

    def start_game(self):
        self.player_obj = Player(pos=(randint(0, len(self.board[0]) - 1), randint(0, len(self.board) - 1)))
        self.game_run = True

    def check_actions(self):
        x, y = self.player_obj.x, self.player_obj.y
        for obj in self.board[y][x]:
            if isinstance(obj, Creature):
                self.player_obj.alive = False
                self.game_run = False

    def check_enemy_lives(self):
        if not len(self.enemies):
            self.game_run = False
        return len(self.enemies)

    def move_player(self, vector):
        x_v, y_v = vector
        x, y = self.player_obj.get_pos()
        if not (0 <= x + x_v < self.width and 0 <= y + y_v < self.height):
            raise BorderError
        for cell_obj in self.board[y + y_v][x + x_v]:
            if isinstance(cell_obj, Wall) or isinstance(cell_obj, Boom) or isinstance(cell_obj, Enemy):
                raise WallStepError
        # если все нормально
        self.player_obj.set_pos(x + x_v, y + y_v)
        return True

    def new_game(self, screen):
        self.enemies = []
        self.generate_field()
        self.start_game()
        self.render(screen)
        self.game_run = True


def main():
    board = Board(n1, n2, cell_size=cs, left_shift=65, top_shift=75)
    board.start_game()
    board.generate_field()
    fps = 30  # количество кадров в секунду
    clock = pygame.time.Clock()
    running = True
    step = False
    game_over = False
    board.render(screen)
    player_vector = [0, -1]
    changed = False
    while running:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
                continue
            if config.debug_mode:
                if event.type == pygame.MOUSEBUTTONDOWN:
                    print(board.board[board.get_cell(event.pos)[1]][board.get_cell(event.pos)[0]])
            if event.type == pygame.KEYDOWN:
                if board.game_run:
                    # блок перемещения игрока
                    try:
                        if event.key == config.move_up:
                            player_vector = [0, -1]
                            board.player_obj.angle = 0
                        elif event.key == config.move_down:
                            player_vector = [0, 1]
                            board.player_obj.angle = 180
                        elif event.key == config.move_left:
                            player_vector = [-1, 0]
                            board.player_obj.angle = 90
                        elif event.key == config.move_right:
                            player_vector = [1, 0]
                            board.player_obj.angle = 270
                        elif event.key == config.move_button:
                            board.move_player(player_vector)
                            step = True
                        elif event.key == config.shot_button:
                            board.player_shoot(player_vector)
                            step = True
                    except BorderError:
                        pass
                    except WallStepError:
                        pass
                changed = True

        # если сделали ход то идут враги
        if step:
            board.enemy_step()
            step = False
        board.check_enemy_lives()
        # если изменилась картинка то рендерим
        if board.game_run:
            board.shoot_render(screen)
        if changed:
            if board.game_run:
                board.render(screen)
                #board.check_actions()
            else:
                if not game_over:
                    board.render(screen)
                    if board.check_enemy_lives():
                        board.render_full_screen(screen, config.game_over_sprite)
                    else:
                        board.render_full_screen(screen, config.game_win_screen)
                    game_over = True
                else:
                    player_vector = [0, -1]
                    board.new_game(screen)
                    game_over = False
            changed = False
            board.check_enemy_lives()
        # уменьшение таймера
        pygame.display.flip()
        clock.tick(fps)

    pygame.quit()


if __name__ == '__main__':
    main()
