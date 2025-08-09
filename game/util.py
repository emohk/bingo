import random
import string

from asgiref.sync import async_to_sync

from .models import Game, Player


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


def create_player(game, player_id, player_name, is_first_player=False):
    """Create or update a player in the game."""
    if Player.objects.filter(player_id=player_id).exists():
        player = Player.objects.get(player_id=player_id)
        player.name = player_name
        player.game = game
        player.board = generate_board(numbers=game.numbers)
        player.turn = is_first_player
        player.save()
    else:
        Player.objects.create(
            game=game,
            player_id=player_id,
            board=generate_board(numbers=game.numbers),
            turn=is_first_player,
            name=player_name,
        )


def announce_winner(channel_layer, group_code, player):
    """Announce the winner of the game."""
    player.game.is_active = False
    player.game.save()
    async_to_sync(channel_layer.group_send)(
        group_code,
        {
            "type": "game_result",
            "winner_id": str(player.player_id),
        },
    )
