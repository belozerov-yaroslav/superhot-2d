import pygame
from random import choice, randint
import time
import config
import os

# ▄▀▀ █░█ █▀▄ █▀▀ █▀▀▄     █░░ ▄▀▄ ▀█▀     ▒▄▀▄     █▀▄
# ░▀▄ █░█ █░█ █▀▀ █▐█▀     █▀▄ █░█ ░█░     ░▒▄▀     █░█
# ▀▀░ ░▀░ █▀░ ▀▀▀ ▀░▀▀     ▀░▀ ░▀░ ░▀░     ▒█▄▄     ▀▀░


all_sprites = pygame.sprite.Group()

# время до исчезновения спрайта стрельбы и пепла
SHOOT_LENGTH = 10

pygame.init()
n1 = 15  # клеток по горизонтали
n2 = 15  # клеток по вертикали
cs = 48  # длинна одной стороны клетки
size = 130 + n1 * cs, 130 + n2 * cs  # размеры экрана
screen = pygame.display.set_mode(size)
pygame.display.set_caption('Superhot 2d')


# опорная функция системы спрайтов, загружает изображение
# если передать color_key -1, то удалит цвет вернего левого пикселя
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


# обычное поле
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

    def __init__(self, pos=(0, 0), angle=0, score=0):
        super().__init__(angle)
        self.x, self.y = pos
        self.angle = angle
        self.score = score

    def get_pos(self):
        return self.x, self.y

    def set_pos(self, x, y):
        self.x = x
        self.y = y


class Wall(Creature):
    image = load_image(config.wall_sprite)


class Boom(Creature):
    image = load_image(config.boom_sprite)


# ошибки
# если попытка пойти в край карты
class BorderError(Exception):
    pass


# если наступаем на занятую клетку
class WallStepError(Exception):
    pass


# Спрайт для отрисовки графики, может повернуться на значение angle
class StandartSprite(pygame.sprite.Sprite):
    def __init__(self, image, pos, angle):
        super().__init__()
        self.image = image
        if angle != 0:
            self.image = pygame.transform.rotate(self.image, angle)
        self.rect = self.image.get_rect()
        self.rect.x = pos[0]
        self.rect.y = pos[1]


# используеться для получения списка кадров
class AnimatedSprite(pygame.sprite.Sprite):
    def __init__(self, sheet, columns, rows):
        super().__init__(all_sprites)
        self.frames = []
        self.cut_sheet(sheet, columns, rows)

    def cut_sheet(self, sheet, columns, rows):
        self.rect = pygame.Rect(0, 0, sheet.get_width() // columns,
                                sheet.get_height() // rows)
        for j in range(rows):
            for i in range(columns):
                frame_location = (self.rect.w * i, self.rect.h * j)
                self.frames.append(sheet.subsurface(pygame.Rect(
                    frame_location, self.rect.size)))


class ShootSprite(CellObject):
    frames = AnimatedSprite(load_image(config.lazer_sprite), 5, 2).frames
    image = frames[0]

    def __init__(self, pos, angle=0, timer=0):
        super().__init__(pos)
        self.timer = timer
        self.angle = angle

    def decrease_timer(self):
        self.timer -= 1
        self.image = self.frames[self.timer % len(self.frames)]


class EnemyShootSprite(ShootSprite):
    frames = AnimatedSprite(load_image(config.enemy_lazer_sprite), 5, 2).frames
    image = frames[0]


class Pepl(ShootSprite):
    frames = AnimatedSprite(load_image(config.pepl_sprite), 5, 2).frames
    image = frames[0]


class EnemyPepl(ShootSprite):
    frames = AnimatedSprite(load_image(config.enemy_pepl_sprite), 5, 2).frames
    image = frames[0]


class Pepl_Boom(ShootSprite):
    frames = AnimatedSprite(load_image(config.pepl_boom_sprite), 5, 2).frames
    image = frames[0]


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
        self.heating = 0
        self.enemies_count = 0
        self.past_enemies_count = 0
        self.player_obj = Player()

        self.board = [[[] for _ in range(self.width)] for _ in range(self.height)]

    # двигает врага в направлении вектора
    def enemy_move(self, enemy, vector):
        angles = {(0, 1): 180, (0, -1): 0, (1, 0): 270, (-1, 0): 90}
        # соответсвие направления хода, повороту спрайта врага
        x_v, y_v = vector
        x, y = enemy.get_pos()
        if not (0 <= x + x_v < self.width and 0 <= y + y_v < self.height):
            return False  # выход за игровое поле
        for cell_obj in self.board[y + y_v][x + x_v]:
            if isinstance(cell_obj, Wall) or isinstance(cell_obj, Boom) or isinstance(cell_obj, Enemy):
                return False  # попытка идти в занятую клетку
        # если все нормально
        if enemy in self.board[y][x]:  # попытка перенести объект врага в игровом поле
            self.board[y][x].remove(enemy)
            self.board[y + y_v][x + x_v].append(enemy)
            enemy.x, enemy.y = x + x_v, y + y_v
            enemy.angle = angles[tuple(vector)]
            return True
        else:
            return False

    # ход врагов, обработка передвижения и стрельбы
    def enemy_step(self):
        destroed = set()  # список всех уничтоженных врагами объектов
        # соответсвие направления выстрела, повороту спрайта врага
        angles = {(0, 1): 180, (0, -1): 0, (1, 0): 270, (-1, 0): 90}
        for enemy in self.enemies:
            x, y = enemy.get_pos()
            x_dif = self.player_obj.x - enemy.x
            y_dif = self.player_obj.y - enemy.y
            # если враг на одной линии с игроком, то он безусловно стреляет
            if x_dif == 0 or y_dif == 0:
                enemy.Lose = False
                enemy.triggered = True
                enemy.triggered_vector = [0, 1] if x_dif == 0 and y_dif > 0 else [0, -1] \
                    if x_dif == 0 and y_dif < 0 else [1, 0] if y_dif == 0 and x_dif > 0 else [-1, 0]
                enemy.angle = angles[tuple(enemy.triggered_vector)]
            # если разница с игроком в 1 клетку, враг пытается убить игрока, но только если он так уже не пытался
            if abs(x_dif) <= 1 and enemy.triggered == False and enemy.Lose == False:
                enemy.triggered_vector = [0, y_dif // abs(y_dif)]
                enemy.triggered = True
                enemy.angle = angles[tuple(enemy.triggered_vector)]
            # если разница с игроком в 1 клетку, враг пытается убить игрока, но только если он так уже не пытался
            if abs(y_dif) <= 1 and enemy.triggered == False and enemy.Lose == False:
                enemy.triggered = True
                enemy.triggered_vector = [x_dif // abs(x_dif), 0]
                enemy.angle = angles[tuple(enemy.triggered_vector)]
            # противник стреляет
            if not enemy.Lose and enemy.triggered:  # если он видит игрока и прошлый раз он не промазал
                enemy.triggered = False
                enemy.Lose = True
                x_v, y_v = enemy.triggered_vector  # задается направление стрельбы
                x, y = enemy.get_pos()
                while True:
                    if not (0 <= x + x_v < self.width and 0 <= y + y_v < self.height):
                        break
                    # игрок не хранится в обычной сетке поля, поэтому отдельно проверяем его позицию
                    if self.player_obj.get_pos() == (x + x_v, y + y_v):
                        self.game_run = False
                        self.board[y + y_v][x + x_v].append(EnemyPepl((y + y_v, x + x_v), enemy.angle, 10))
                        break
                    if len(self.board[y + y_v][x + x_v]) != 1:
                        # если в списке объектов клетки только один, то там только обычное поле,
                        # если нет - проверяем столкновение
                        for i in self.board[y + y_v][x + x_v]:
                            if isinstance(i, Wall) or isinstance(i, Enemy):
                                destroed.add((y + y_v, x + x_v, i, enemy.angle))
                            elif isinstance(i, Boom):
                                self.explosion(x + x_v, y + y_v)
                        break  # только объект класса SimpleField
                    x += x_v
                    y += y_v
                    self.board[y][x].append(EnemyShootSprite((y, x), enemy.angle, SHOOT_LENGTH))
                continue  # если враг выстрелил, то он уже не будет ходить
            # проверка, может ли враг сократить дистацию с игроком, если не может, то уничтожает препятствие
            if len([x for x in self.board[y + y_dif // abs(y_dif)][x]
                    if not (isinstance(x, (Pepl, ShootSprite, EnemyPepl, EnemyShootSprite)))]) > 1 \
                    and len([x for x in self.board[y][x + x_dif // abs(x_dif)] if not
            (isinstance(x, (Pepl, ShootSprite, EnemyPepl, EnemyShootSprite)))]) > 1:
                # очистка клетки
                enemy.angle = angles[(0, y_dif // abs(y_dif))]
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
            # сокращает дистанцию
            if randint(0, 1) == 1:
                if self.enemy_move(enemy, [x_dif // abs(x_dif), 0]):
                    continue
            if self.enemy_move(enemy, [0, y_dif // abs(y_dif)]):
                continue
            else:
                self.enemy_move(enemy, [x_dif // abs(x_dif), 0])
            # если враг сходил, то может выстрелить
            enemy.Lose = False
        # идем по списку уничтоженных объектов, вставляем в нужные места след лазера
        for elem in destroed:
            if isinstance(elem[2], Enemy):
                if elem[2] in self.enemies:
                    self.enemies.remove(elem[2])
            if elem[2] in self.board[elem[0]][elem[1]]:
                self.board[elem[0]][elem[1]].remove(elem[2])
                self.board[elem[0]][elem[1]].append(EnemyPepl((elem[0], elem[1]), elem[3], 10))

    # Функция, отслеживающая время отрисовки лазеров
    def player_shoot(self, vector):  # функция стрельбы игрока
        x_v, y_v = vector
        x, y = self.player_obj.get_pos()  # получает информацию о игроке
        while True:  # идет в сторону направления игрока
            if not (0 <= x + x_v < self.width and 0 <= y + y_v < self.height):
                break  # если лазер дошёл до края ничего не уничтожив, функция выключается
            if len(self.board[y + y_v][x + x_v]) != 1:  # если в настоящей клетке больше одного объекта
                for i in self.board[y + y_v][x + x_v]:  # (всегда есть одна обычная клетка)
                    if isinstance(i, Wall) or isinstance(i, Enemy):  # если это стена или враг
                        self.board[y + y_v][x + x_v].remove(i)  # то лазер его уничтожает
                        if isinstance(i, Enemy):  # и также убирает врага из списка их координат
                            if i in self.enemies:
                                self.enemies.remove(i)
                        self.board[y + y_v][x + x_v].append(
                            Pepl((x + x_v, y + y_v), self.player_obj.angle, 10))  # и добавляет эффект взрыва
                    elif isinstance(i, Boom):
                        self.explosion(x + x_v, y + y_v)  # если же это бочка, то взрывает
                break  # и т.к лазер попал, то функция выключается
            x += x_v  # если не попал, то идёт дальше
            y += y_v
            self.board[y][x].append(ShootSprite((y, x), self.player_obj.angle, SHOOT_LENGTH))
            # и добавляет эффект лазера

    def shoot_render(self):  # функция уничтожения лазеров и взрывов, вреям анимации которых кончилось
        for i in range(self.height):
            for j in range(self.width):
                for creature in self.board[i][j]:  # проходит по всему board
                    if isinstance(creature, (ShootSprite, Pepl, EnemyShootSprite, EnemyPepl, Pepl_Boom)):
                        if creature.timer > 0:  # если время еще осталось, то уменьшает его
                            creature.decrease_timer()
                        else:  # иначе, уничтожает объект
                            self.board[i][j].remove(creature)

    def explosion(self, x, y):  # функция взрыва бочки
        for i in range(-1, 2):
            for j in range(-1, 2):  # проходит по области возле бочки
                if x + i < 0 or x + i >= len(self.board):
                    continue  # проверка на край экрана
                if y + j < 0 or y + j >= len(self.board):
                    continue  # проверка на край экрана
                for z in self.board[y + j][x + i]:  # проходит по клетке
                    if isinstance(z, SimpleField):
                        continue  # пропуск клеток поля
                    elif isinstance(z, Boom):  # цепочка взрывов, если задела вторую бочку
                        self.board[y + j][x + i].remove(z)
                        self.explosion(x + i, y + j)
                        return
                    elif isinstance(z, Enemy):  # уничтожение врага
                        if z in self.enemies:
                            self.enemies.remove(z)
                    self.board[y + j][x + i].remove(z)  # уничтожение коробки, если она там есть
                self.board[y + j][x + i].append(Pepl_Boom((x + i, y + j), 0, 10))  # создание эффекта взрыва
                if self.player_obj.get_pos() == (x + i, y + j):  # если бочка взорвала игрока, игра заканчивается
                    self.player_obj.alive = False
                    self.game_run = False

    def render(self, screen):  # функция рендера изображения
        screen.fill('black')  # очистка экрана
        self.sprites.empty()  # очистка списка спрайтов
        self.sprites.add(StandartSprite(load_image(config.background_sprite), (0, 0), 0))  # добавление фона
        for i in range(self.height):
            for j in range(self.width):  # проходит по board
                for creature in self.board[i][j]:  # и добавляет соотвестсвующий спрайт
                    self.sprites.add(StandartSprite(creature.image,
                                                    (j * self.cell_size + self.left_shift,
                                                     i * self.cell_size + self.top_shift), creature.angle))
        self.sprites.add(StandartSprite(self.player_obj.image,  # отдельная обработка игрока, он не хранится в board
                                        (self.player_obj.x * self.cell_size + self.left_shift,
                                         self.player_obj.y * self.cell_size + self.top_shift), self.player_obj.angle))
        self.sprites.update()  # обновление списка спрайтов
        self.sprites.draw(screen)  # отрисовка

    def render_full_screen(self, screen, path, alpha=250):  # функция добавления фона
        image = pygame.transform.scale(load_image(path), (screen.get_width(), screen.get_height()))  # создание
        image.set_alpha(alpha)  # нужного изобрадения фона
        self.sprites.add(StandartSprite(image, (0, 0), 0))
        self.sprites.draw(screen)  # отрисовка

    def render_heating(self, screen):  # функция отрисовки нагрева
        image = load_image('heat' + str(self.heating) + '.png')  # выбор цифры, в зависимости от нагрева
        self.sprites.add(StandartSprite(image, (810, 280), 0))
        self.sprites.draw(screen)  # отрисовка

    def render_player_score(self, screen):  # функция отрисовки счёта игрока
        score = self.player_obj.score  # получение информации о счёте
        if len(str(score)) == 1:  # если счёт один (она узкая)
            font = pygame.font.Font('score_font.ttf', 133)  # то шрифт больше
            text = font.render(str(score), True, (74, 130, 203))
        else:
            font = pygame.font.Font('score_font.ttf', 75)  # иначе размер меньше
            text = font.render(str(score), True, (74, 130, 203))
        screen.blit(text, (10, 310))  # отрисовка

    def get_cell(self, pos):  # функция для получения координаты клетки по координатам нажатия мышки
        x_index = (pos[0] - self.left_shift) // self.cell_size
        y_index = (pos[1] - self.top_shift) // self.cell_size

        if 0 <= x_index < self.width and 0 <= y_index < self.height:  # если нажали на поле
            return x_index, y_index
        return None

    def add_object_to_cell(self, obj, pos=None):
        # метод для генерации поля, проверяет пустая ли клетка позиции
        # если да, то добавляет объект и возвращает True, иначе - возвращает False
        # если pos не передали генерирует сама
        if pos is None:
            pos = randint(0, self.height - 1), randint(0, self.width - 1)
        if pos == self.player_obj.get_pos():
            return False
        if len(self.board[pos[1]][pos[0]]) == 1:
            self.board[pos[1]][pos[0]].append(obj)
            return True
        return False

    def generate_field(self, box_count=30, boom_count=7, enemy_count=7):  # функция генерации поля
        self.board = [[[] for _ in range(self.width)] for _ in range(self.height)]  # создание новго списка board
        for i in range(self.height):
            for j in range(self.width):
                self.board[i][j].append(SimpleField())  # заполнение его стандартными клетками
        for i in range(box_count):
            result = False
            while not result:
                result = self.add_object_to_cell(Wall())  # создание коробок сколько требуется
        for i in range(boom_count):
            result = False
            while not result:
                result = self.add_object_to_cell(Boom())  # создание бочек сколько требуется
        for i in range(enemy_count):  # создание врагов сколько требуется
            result = False
            while not result:
                x, y = randint(0, self.height - 1), randint(0, self.width - 1)
                new_enemy = Enemy((x, y), choice([0, 90, 180, 270]))  # задание угла и координат врагу
                result = self.add_object_to_cell(new_enemy, pos=(x, y))
            self.enemies.append(new_enemy)  # добавление в список врагов

    def check_actions(self):  # функция проверки
        x, y = self.player_obj.x, self.player_obj.y
        for obj in self.board[y][x]:  # не находится ли игрок внутри чегото
            if isinstance(obj, Creature):  # если находитя, то игра заканчивается
                self.player_obj.alive = False
                self.game_run = False

    def check_enemy_lives(self):  # функция для проверки
        if not len(self.enemies):  # остались ли живые враги
            self.game_run = False
        return len(self.enemies)

    def move_player(self, vector):  # функция перемещения игрока
        x_v, y_v = vector
        x, y = self.player_obj.get_pos()
        if not (0 <= x + x_v < self.width and 0 <= y + y_v < self.height):
            raise BorderError  # если он не вышел за границы карты
        for cell_obj in self.board[y + y_v][x + x_v]:  # и не идёт в препятствие
            if isinstance(cell_obj, Wall) or isinstance(cell_obj, Boom) or isinstance(cell_obj, Enemy):
                raise WallStepError
        self.player_obj.set_pos(x + x_v, y + y_v)  # то двигается
        return True

    def new_game(self, screen, restart=True):  # фунуция для создание новго уровня
        self.enemies = []  # обновление списка врагов

        # self.player_obj = Player(pos=(randint(0, len(self.board[0]) - 1), randint(0, len(self.board) - 1)))
        self.player_obj.set_pos(randint(0, len(self.board[0]) - 1), randint(0, len(self.board) - 1))
        self.player_obj.angle = 0  # создание игрока
        if restart:
            self.player_obj.score = 0  # если игрок умер, а не перешёл на следующий уровень
        self.heating = 0
        self.game_run = True  # обновление переменных

        self.enemies_count = 7
        self.past_enemies_count = 7
        self.generate_field(enemy_count=self.enemies_count)  # создание поля
        self.render(screen)
        self.render_heating(screen)  # отрисовка

    def update_player_score(self):  # функция для обновления счёта игрока
        self.player_obj.score += self.past_enemies_count - self.check_enemy_lives()  # прошлый счёт +
        self.past_enemies_count = self.check_enemy_lives()  # количество врагов всего - количество живых врагов


def main():
    running = True
    fps = 30  # количество кадров в секунду
    clock = pygame.time.Clock()
    screen.blit(pygame.transform.scale(load_image(config.start_screen),
                                       (screen.get_width(), screen.get_height())), (0, 0))
    pygame.display.flip()
    start_screen = True
    while start_screen:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit()
                quit()
            if event.type == pygame.KEYDOWN:
                start_screen = False

    filters = pygame.sprite.Group()
    image = pygame.transform.scale(load_image(config.glass), (screen.get_width(), screen.get_height()))
    image.set_alpha(60)
    filters.add(StandartSprite(image, (0, 0), 0))
    image = pygame.transform.scale(load_image(config.pixels), (screen.get_width(), screen.get_height()))
    image.set_alpha(30)
    filters.add(StandartSprite(image, (0, 0), 0))

    board = Board(n1, n2, cell_size=cs, left_shift=65, top_shift=75)
    board.new_game(screen)
    freeze = 0
    game_over_freeze = 5
    step = False
    game_music = pygame.mixer.Sound(config.game_music)
    start_sound = pygame.mixer.Sound(config.start_sound)
    death_sound = pygame.mixer.Sound(config.death_sound)
    win_sound = pygame.mixer.Sound(config.win_sound)
    game_over = False
    board.render(screen)
    board.render_heating(screen)
    player_vector = [0, -1]
    game_music.play(-1)
    death_sound.set_volume(config.game_volume)
    start_sound.set_volume(config.game_volume)
    game_music.set_volume(config.game_volume)
    win_sound.set_volume(config.game_volume)
    while running:
        pressed = False
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
                continue
            if config.debug_mode:
                if event.type == pygame.MOUSEBUTTONDOWN:
                    if not board.get_cell(event.pos) is None:
                        print(board.board[board.get_cell(event.pos)[1]][board.get_cell(event.pos)[0]])
            if event.type == pygame.KEYDOWN:
                if board.game_run:
                    # блок перемещения игрока
                    try:
                        if not freeze:
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
                                board.heating = 0
                                freeze = 20
                            elif event.key == config.shot_button:
                                board.player_shoot(player_vector)
                                step = True
                                board.heating += 1
                                freeze = 20
                                if board.heating == 3:
                                    board.game_run = False
                    except BorderError:
                        pass
                    except WallStepError:
                        pass
                pressed = True
        if board.game_run or game_over_freeze > 0:
            board.shoot_render()
            board.render(screen)
            board.render_heating(screen)
            board.update_player_score()
            board.render_player_score(screen)
            filters.draw(screen)
        else:
            if not game_over:
                game_music.stop()
                board.shoot_render()
                board.render(screen)
                board.render_heating(screen)
                board.update_player_score()
                board.render_player_score(screen)
                if board.check_enemy_lives():
                    board.render_full_screen(screen, config.game_over_sprite, alpha=170)
                    death_sound.play(0, 0)
                else:
                    board.render_full_screen(screen, config.game_win_screen, alpha=170)
                    win_sound.play()
                game_over = True
            else:
                if pressed:
                    game_music.play(-1, 0)
                    start_sound.play(0, 0)
                    player_vector = [0, -1]
                    print(bool(board.check_enemy_lives()))
                    board.new_game(screen, restart=bool(board.check_enemy_lives()))
                    game_over = False
                    game_over_freeze = 5
        if freeze:
            freeze -= 1
        if not board.game_run:
            game_over_freeze -= 1
        if step and freeze == 9:
            board.enemy_step()
            step = False
        board.check_enemy_lives()
        pygame.display.flip()
        clock.tick(fps)

    pygame.quit()


if __name__ == '__main__':
    main()
