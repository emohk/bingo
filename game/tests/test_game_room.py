from django.test import TestCase, Client
from django.urls import reverse

import uuid

from ..models import Game, Player
from .. import util


class GameRoomTest(TestCase):
    def setUp(self):
        self.player = Client()
        player_id = str(uuid.uuid4())
        session = self.player.session
        session["player_id"] = player_id
        session.save()
        self.game = Game.objects.create(
            game_code=util.generate_unique_game_code(),
            numbers=util.generate_numbers(),
        )
        util.create_player(self.game, player_id, "TestPlayer", True)

    def test_renders_correct_template(self):
        response = self.player.get(reverse("game", args=[self.game.game_code]))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "game.html")

    def test_redirects_invalid_game_code(self):
        response = self.player.get(reverse("game", args=["RANDOMID"]))
        self.assertEqual(response.status_code, 302)
