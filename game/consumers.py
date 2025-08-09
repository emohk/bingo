import json
from channels.generic.websocket import AsyncWebsocketConsumer
from django.urls import reverse
from channels.db import database_sync_to_async
from asgiref.sync import sync_to_async
from django.template.loader import render_to_string
from .models import Player, Game


class GameConsumer(AsyncWebsocketConsumer):
    """
    Handles WebSocket connections for a bingo game room.
    - On connect/disconnect: marks player as connected/disconnected.
    - On refresh_board_and_heading: renders and sends updated board and heading for the current player.
    """

    async def connect(self):
        self.game_code = self.scope["url_route"]["kwargs"]["game_code"]
        self.player_id = self.scope["session"].get("player_id")
        self.group_name = f"game_{self.game_code}"
        await self.channel_layer.group_add(self.group_name, self.channel_name)
        await self.accept()
        # Mark player as connected
        if self.player_id:
            try:
                game = await database_sync_to_async(Game.objects.get)(
                    game_code=self.game_code
                )
                players_qs = await database_sync_to_async(list)(game.players.all())
                player_count = len(players_qs)

                if player_count == 1:
                    waiting_html = render_to_string(
                        "partials/waiting.html",
                        {
                            "game": game,
                            "player_count": player_count,
                            "players": players_qs,
                        },
                    )
                    await self.send(text_data=waiting_html)
                elif player_count == 2:
                    await self.channel_layer.group_send(
                        self.group_name,
                        {
                            "type": "game_update",
                        },
                    )
                else:
                    await self.send(
                        text_data=json.dumps(
                            {
                                "type": "redirect_to_join",
                            }
                        )
                    )
            except Player.DoesNotExist:
                pass

    async def disconnect(self, close_code):
        await self.channel_layer.group_discard(self.group_name, self.channel_name)

        try:
            game = await database_sync_to_async(Game.objects.get)(
                game_code=self.game_code
            )
            is_active = game.is_active
            if is_active:
                # Render game over partial
                game_over_html = await database_sync_to_async(render_to_string)(
                    "partials/game_over.html"
                )

                # Send to all in group
                await self.channel_layer.group_send(
                    self.group_name,
                    {
                        "type": "game_update",
                        "html": game_over_html,
                    },
                )

            await database_sync_to_async(game.delete)()
        except Game.DoesNotExist:
            pass

    async def receive(self, text_data):
        """
        Optionally handle client-initiated messages (e.g., for ws-send moves).
        Currently, all game state changes are handled via HTTP POST and broadcast from the view.
        """
        pass

    async def game_update(self, event):
        if "html" in event:
            await self.send(text_data=event["html"])
            return

        # Use current WebSocket's player_id
        if not self.player_id:
            return

        player = await database_sync_to_async(Player.objects.get)(
            game__game_code=self.game_code, player_id=self.player_id
        )
        game = await database_sync_to_async(Game.objects.get)(game_code=self.game_code)

        completed_lines = await database_sync_to_async(player.completed_lines)()

        players = await database_sync_to_async(list)(game.players.all())
        player_count = len(players)

        context = {
            "board": player.board,
            "game": game,
            "player": player,
            "line_numbers": completed_lines[1],
            "completed_lines": completed_lines[0],
            "player_count": player_count,
            "players": players,
        }

        html = render_to_string("partials/board_oob.html", context)
        await self.send(text_data=html)

    async def game_result(self, event):
        """
        Handle game result updates (e.g., when a player wins).
        """
        winner_id = event.get("winner_id")
        if not winner_id or not self.player_id:
            return

        is_winner = str(self.player_id) == winner_id

        result_html = await database_sync_to_async(render_to_string)(
            "partials/game_result.html",
            {"is_winner": is_winner},
        )

        await self.send(text_data=result_html)
