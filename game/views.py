from django.http import JsonResponse
from django.shortcuts import get_object_or_404, render, redirect
from django.http import HttpResponse
from django.db.models import Count

from django.template.loader import render_to_string
from channels.layers import get_channel_layer
from asgiref.sync import async_to_sync

from .models import Game, Player
from . import util
import uuid


def join_game(request):
    """Join or create a game, handling session and player creation."""

    if not request.session.session_key:
        request.session.create()

    if "player_id" not in request.session:
        request.session["player_id"] = str(uuid.uuid4())
    if "player_name" not in request.session:
        request.session["player_name"] = "John"

    player_id = request.session["player_id"]

    if request.method == "POST":
        create_new = request.POST.get("create_new")
        game_code = request.POST.get("game_code")
        player_name = request.POST.get("player_name", "John")
        request.session["player_name"] = player_name
        # Create Game
        if create_new:
            game = Game.objects.create(
                game_code=util.generate_unique_game_code(),
                numbers=util.generate_numbers(),
                is_private=True,
            )
            util.create_player(game, player_id, player_name, True)
            return redirect("game", game_code=game.game_code)

        # Join Game by code
        if game_code:
            try:
                game = Game.objects.get(
                    game_code=game_code,
                    is_active=True,
                    is_private=True,
                )
                is_first_player = not game.players.exists()
                util.create_player(game, player_id, player_name, is_first_player)
                return redirect("game", game_code=game_code)
            except Game.DoesNotExist:
                return HttpResponse("Invalid game code", status=400)

        # Quick Play (random matchmaking)
        game = (
            Game.objects.annotate(num_players=Count("players"))
            .filter(is_active=True, is_private=False, num_players__lt=2)
            .first()
        )
        is_first_player = False
        if not game:
            game = Game.objects.create(
                game_code=util.generate_unique_game_code(),
                numbers=util.generate_numbers(),
            )
            is_first_player = True
        util.create_player(game, player_id, player_name, is_first_player)
        return redirect("game", game.game_code)
    return render(
        request,
        "join.html",
        {
            "player_name": request.session["player_name"],
        },
    )


def game_room(request, game_code):
    player_id = request.session.get("player_id")
    if not player_id:
        return redirect("join")

    try:
        game = Game.objects.get(
            game_code=game_code,
            is_active=True,
        )
        player = Player.objects.get(
            game=game,
            player_id=player_id,
        )
    except (Game.DoesNotExist, Player.DoesNotExist):
        return redirect("join")

    return render(
        request,
        "game.html",
        {
            "game": game,
            "player": player,
            "completed_lines": player.completed_lines()[0],
            "line_numbers": player.completed_lines()[1],
        },
    )


def make_move(request, game_code):
    """Handle a player's move in the game."""
    player_id = request.session.get("player_id")
    if not player_id:
        return HttpResponse("Player not found", status=400)

    if request.method == "POST":
        try:
            game = get_object_or_404(Game, game_code=game_code, is_active=True)
            player = get_object_or_404(Player, game=game, player_id=player_id)

            if not player.turn:
                return JsonResponse({"error": "Not your turn"}, status=400)

            row = request.POST.get("row")
            col = request.POST.get("col")

            if row is None and col is None:
                called_number = util.get_random_number(game)
            else:
                row, col = int(row), int(col)

                if not (0 <= row < 5 and 0 <= col < 5):
                    return JsonResponse({"error": "Invalid move"}, status=400)

                called_number = player.board[row][col]

            # If already called, reject
            if called_number in game.called_numbers:
                return JsonResponse({"error": "Number already called"}, status=400)

            # Mark the number as called globally
            game.called_numbers.append(called_number)
            game.save()

            channel_layer = get_channel_layer()
            group_code = f"game_{player.game.game_code}"
            async_to_sync(channel_layer.group_send)(
                group_code,
                {"type": "game_update"},
            )

            if player.check_winner():
                util.announce_winner(channel_layer, group_code, player)
                return HttpResponse(status=204)
            opponent = game.players.exclude(player_id=player_id).first()
            if opponent.check_winner():
                util.announce_winner(channel_layer, group_code, opponent)
                return HttpResponse(status=204)

            player.turn = not player.turn
            player.save()
            opponent.turn = not opponent.turn
            opponent.save()

            return HttpResponse(status=204)
        except (Game.DoesNotExist, Player.DoesNotExist):
            return HttpResponse("Invalid game or player", status=400)
