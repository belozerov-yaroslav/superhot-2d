import pygame
from random import choice, randint
import time

all_sprites = pygame.sprite.Group()


class CellObject:
    def __init__(self, file_path):
        self.file_path = file_path

    def __str__(self):
        return self.__class__.__name__


class SimpleField(CellObject):
    def __init__(self, file_path):
        super().__init__(file_path)


class Creature(CellObject):
    def __init__(self, file_path):
        super().__init__(file_path)
        self.alive = True


class Player(Creature):
    def __init__(self, file_path, pos=(0, 0)):
        super().__init__(file_path)
        self.x, self.y = pos

    def get_pos(self):
        return self.x, self.y

    def set_pos(self, x, y):
        self.x = x
        self.y = y


class Wall(Creature):
    def __init__(self, file_path):
        super().__init__(file_path)


# errors
class BorderError(Exception):
    pass


class WallStepError(Exception):
    pass


class StandartSprite(pygame.sprite.Sprite):
    def __init__(self, file_path, pos):
        super().__init__()
        size = pygame.image.load(file_path).get_size()
        self.image = pygame.Surface(size)
        self.image.fill('white')
        self.image.set_colorkey('white')
        pygame.draw.rect(self.image, 'black', [pos[0], pos[1], size[0], size[1]])
        self.image = pygame.image.load(file_path).convert_alpha()
        self.rect = self.image.get_rect()
        self.rect.x = pos[0]
        self.rect.y = pos[1]


class Board:
    def __init__(self, width, height, cell_size=30,
                 left_shift=10, top_shift=10):
        self.width = width
        self.height = height
        self.cell_size = cell_size
        self.left_shift = left_shift
        self.top_shift = top_shift
        self.sprites = pygame.sprite.Group()
        self.game_run = False

        self.board = [[[] for _ in range(self.width)] for _ in range(self.height)]

    def set_view(self, cell_size, left_shift, top_shift):
        self.cell_size = cell_size
        self.left_shift = left_shift
        self.top_shift = top_shift

    def render(self, screen):
        screen.fill('black')
        self.sprites.empty()
        for i in range(self.height):
            for j in range(self.width):
                for creature in self.board[i][j]:
                    self.sprites.add(StandartSprite(creature.file_path,
                                                    (j * self.cell_size + self.left_shift,
                                                     i * self.cell_size + self.top_shift)))
        self.sprites.add(StandartSprite(self.player_obj.file_path,
                                        (self.player_obj.x * self.cell_size + self.left_shift,
                                         self.player_obj.y * self.cell_size + self.top_shift)))
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
        # if all is correct
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
    board.render(screen)
    changed = False
    while running:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
                continue
            if event.type == pygame.KEYDOWN:
                if board.game_run:
                    # move block
                    try:
                        if event.key == pygame.K_UP:
                            board.move_player([0, -1])
                            changed = True
                        elif event.key == pygame.K_DOWN:
                            board.move_player([0, 1])
                            changed = True
                        elif event.key == pygame.K_LEFT:
                            board.move_player([-1, 0])
                            changed = True
                        elif event.key == pygame.K_RIGHT:
                            board.move_player([1, 0])
                            changed = True
                    except BorderError:
                        pass
                    except WallStepError:
                        pass
        if changed:
            board.render(screen)
            changed = False
            board.check_actions()
        pygame.display.flip()
        clock.tick(fps)
    pygame.quit()


if __name__ == '__main__':
    main()
