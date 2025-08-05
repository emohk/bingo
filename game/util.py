import random
import string

from .models import Game


def generate_numbers():
    numbers = random.sample(range(1, 100), 25)
    return numbers


def generate_board(numbers):
    shuffled = numbers[:]
    random.shuffle(shuffled)
    board = [shuffled[i * 5 : (i + 1) * 5] for i in range(5)]
    return board


def generate_unique_game_code(length=6):
    chars = string.ascii_uppercase + string.digits
    while True:
        code = "".join(random.choices(chars, k=length))
        if not Game.objects.filter(game_code=code).exists():
            return code
