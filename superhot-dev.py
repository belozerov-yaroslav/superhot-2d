import pygame
from random import choice, randint
import time
import config

all_sprites = pygame.sprite.Group()

SHOOT_LENGTH = 10


# стабильные объекты
class CellObject:
    def __init__(self, file_path, angle=0):
        self.file_path = file_path
        self.angle = angle

    def __str__(self):
        return self.__class__.__name__


class SimpleField(CellObject):
    def __init__(self, file_path, angle=0):
        super().__init__(file_path, angle)


# объекты, которые могут быть живы или мертвы
class Creature(CellObject):
    def __init__(self, file_path, angle=0):
        super().__init__(file_path, angle)
        self.alive = True


class Enemy(Creature):
    def __init__(self, file_path, pos=(0, 0), angle=0, alive=True):
        super().__init__(file_path)
        self.triggered = False
        self.angle = angle
        self.x, self.y = pos
        self.Lose = False
        self.alive = alive


class Player(Creature):
    def __init__(self, file_path, pos=(0, 0), angle=0):
        super().__init__(file_path)
        self.x, self.y = pos
        self.angle = angle

    def get_pos(self):
        return self.x, self.y

    def set_pos(self, x, y):
        self.x = x
        self.y = y


class Wall(Creature):
    def __init__(self, file_path):
        super().__init__(file_path)


# ошибки
class BorderError(Exception):
    pass


class WallStepError(Exception):
    pass


class StandartSprite(pygame.sprite.Sprite):
    def __init__(self, file_path, pos, angle):
        super().__init__()
        size = pygame.image.load(file_path).get_size()
        self.image = pygame.Surface(size)
        self.image.fill('white')
        self.image.set_colorkey('white')
        pygame.draw.rect(self.image, 'black', [pos[0], pos[1], size[0], size[1]])
        self.image = pygame.image.load(file_path).convert_alpha()
        self.image = pygame.transform.rotate(self.image, angle)
        self.rect = self.image.get_rect()
        self.rect.x = pos[0]
        self.rect.y = pos[1]


class ShootSprite(CellObject):
    def __init__(self, file_path, pos, angle=0, timer=0):
        super().__init__(file_path, pos)
        self.timer = timer
        self.angle = angle


class Board:
    def __init__(self, width, height, cell_size=30,
                 left_shift=10, top_shift=10):
        self.width = width
        self.height = height
        self.enemis = []
        self.cell_size = cell_size
        self.left_shift = left_shift
        self.top_shift = top_shift
        self.sprites = pygame.sprite.Group()
        self.game_run = False

        self.board = [[[] for _ in range(self.width)] for _ in range(self.height)]

    def enemy_step(self):  # ходят враги
        for enemy in self.enemis:
            for i in self.board[enemy[0]][enemy[1]]:
                if isinstance(i, Enemy):
                    x_difference = self.player_obj.y - enemy[0]
                    y_difference = self.player_obj.x - enemy[1]
                    if abs(x_difference) <= 1 or  abs(y_difference) <= 1:
                        i.triggered = True
                    if not i.Lose and i.triggered: # если он видит игрока и прошлый раз он не промазал
                        pass # то стреляет
                        i.triggered = False
                    else:
                        if abs(x_difference) < abs(y_difference):
                            if y_difference < 0:
                                self.board[enemy[0]][enemy[1]].remove(i)
                                i.angle = 90
                                self.board[enemy[0]][enemy[1] - 1].append(i)
                                self.enemis.remove(enemy)
                                self.enemis.append([enemy[0], enemy[1] - 1])
                            else:
                                self.board[enemy[0]][enemy[1]].remove(i)
                                i.angle = 270
                                self.board[enemy[0]][enemy[1] + 1].append(i)
                                self.enemis.remove(enemy)
                                self.enemis.append([enemy[0], enemy[1] + 1])
                        else:
                            if x_difference < 0:
                                self.board[enemy[0]][enemy[1]].remove(i)
                                i.angle = 0
                                self.board[enemy[0] - 1][enemy[1]].append(i)
                                self.enemis.remove(enemy)
                                self.enemis.append([enemy[0] - 1, enemy[1]])
                            else:
                                self.board[enemy[0]][enemy[1]].remove(i)
                                i.angle = 180
                                self.board[enemy[0] + 1][enemy[1]].append(i)
                                self.enemis.remove(enemy)
                                self.enemis.append([enemy[0] + 1, enemy[1]])


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
                        self.board[y + y_v][x + x_v].append(
                            ShootSprite('pic2/pepl.jpg', (x + x_v, y + y_v), self.player_obj.angle, 10))
                break  # только объект класса SimpleField
            x += x_v
            y += y_v
            self.board[y][x].append(ShootSprite('pic2/cell1_tile_with_lazer.jpg',
                                                (y, x), self.player_obj.angle, SHOOT_LENGTH))

    def shoot_render(self, screen):
        changed = False
        for i in range(self.height):
            for j in range(self.width):
                for creature in self.board[i][j]:
                    if isinstance(creature, ShootSprite):
                        if creature.timer > 0:
                            creature.timer -= 1
                        else:
                            changed = True
                            self.board[i][j].remove(creature)
        if changed:
            self.render(screen)

    def render(self, screen):
        screen.fill('black')
        self.sprites.empty()
        for i in range(self.height):
            for j in range(self.width):
                for creature in self.board[i][j]:
                    self.sprites.add(StandartSprite(creature.file_path,
                                                    (j * self.cell_size + self.left_shift,
                                                     i * self.cell_size + self.top_shift), creature.angle))
        self.sprites.add(StandartSprite(self.player_obj.file_path,
                                        (self.player_obj.x * self.cell_size + self.left_shift,
                                         self.player_obj.y * self.cell_size + self.top_shift), self.player_obj.angle))
        self.sprites.update()
        self.sprites.draw(screen)

    def get_cell(self, pos):
        x_index = (pos[0] - self.left_shift) // self.cell_size
        y_index = (pos[1] - self.top_shift) // self.cell_size

        if 0 <= x_index < self.width and 0 <= y_index < self.height:
            return x_index, y_index
        return None

    def generate_field(self):
        self.board = [[[] for _ in range(self.width)] for _ in range(self.height)]
        t1 = time.time()
        for i in range(self.height):
            for j in range(self.width):
                self.board[i][j].append(SimpleField('pic2/cell1_tile.jpg'))
        for i in range(10):
            self.board[randint(0, self.height - 1)][randint(0, self.width - 1)].append(
                Creature('pic2/cell1_tile_with_boom.jpg'))
            self.board[randint(0, self.height - 1)][randint(0, self.width - 1)].append(
                Wall('pic2/cell1_with_box_tile.jpg'))
        for i in range(10):
            x, y = randint(0, self.height - 1), randint(0, self.width - 1)
            if len(self.board[x][y]) != 1:
                del self.board[x][y][1:]
            self.board[x][y].append(
                Enemy('pic2/enemy.png', (x, y), choice([0, 90, 180, 270])))
            self.enemis.append([x, y])

    def start_game(self):
        self.player_obj = Player('pic2/pers2.png', pos=(2, 4))
        self.game_run = True

    def check_actions(self):
        x, y = self.player_obj.x, self.player_obj.y
        for obj in self.board[y][x]:
            if isinstance(obj, Creature):
                self.player_obj.alive = False
                self.game_run = False

    def move_player(self, vector):
        x_v, y_v = vector
        x, y = self.player_obj.get_pos()
        if not (0 <= x + x_v < self.width and 0 <= y + y_v < self.height):
            raise BorderError
        for cell_obj in self.board[y + y_v][x + x_v]:
            if isinstance(cell_obj, Wall):
                raise WallStepError
        # если все нормально
        self.player_obj.set_pos(x + x_v, y + y_v)


def main():
    pygame.init()
    n = 15
    cs = 48
    size = 40 + n * cs, 40 + n * cs
    screen = pygame.display.set_mode(size)
    pygame.display.set_caption('Superhot 2d')
    board = Board(n, n, cell_size=cs, left_shift=20, top_shift=20)
    board.start_game()
    board.generate_field()
    fps = 30  # количество кадров в секунду
    clock = pygame.time.Clock()
    running = True
    step = False
    board.render(screen)
    player_vector = [0, -1]
    changed = False
    while running:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
                continue
            if event.type == pygame.KEYDOWN:
                if board.game_run:
                    # блок перемещения игрока
                    try:
                        if event.key == config.move_up:
                            player_vector = [0, -1]
                            board.player_obj.angle = 0
                            changed = True
                        elif event.key == config.move_down:
                            player_vector = [0, 1]
                            board.player_obj.angle = 180
                            changed = True
                        elif event.key == config.move_left:
                            player_vector = [-1, 0]
                            board.player_obj.angle = 90
                            changed = True
                        elif event.key == config.move_right:
                            player_vector = [1, 0]
                            board.player_obj.angle = 270
                            changed = True
                        elif event.key == config.move_button:
                            board.move_player(player_vector)
                            changed = True
                            step = True
                        elif event.key == config.shot_button:
                            board.player_shoot(player_vector)
                            changed = True
                            step = True
                    except BorderError:
                        pass
                    except WallStepError:
                        pass
        # если сделали ход то идут враги
        if step:
            board.enemy_step()
            step = False
        # если изменилась картинка то рендерим
        if changed:
            board.render(screen)
            changed = False
            board.check_actions()
        # уменьшее таймера
        board.shoot_render(screen)
        pygame.display.flip()
        clock.tick(fps)

    pygame.quit()


if __name__ == '__main__':
    main()
