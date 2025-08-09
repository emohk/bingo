from django.test import TestCase, Client
from django.urls import reverse
from ..models import Game, Player

join_url = reverse("join")


class JoinGameTest(TestCase):
    def setUp(self):
        self.client1 = Client()
        self.client2 = Client()

    def test_join_template_rendering(self):
        response = self.client.get(reverse("join"))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "join.html")

    def test_player_creation(self):
        response = self.client.post(
            join_url,
            {"player_name": "TestPlayer"},
        )
        self.assertEqual(response.status_code, 302)
        game = Game.objects.first()
        player = Player.objects.first()
        self.assertIsNotNone(player)
        self.assertEqual(player.game, game)
        self.assertEqual(player.name, "TestPlayer")
        self.assertEqual(str(player.player_id), self.client.session["player_id"])

    def test_join_random_game_and_player_creation(self):
        response = self.client1.post(
            join_url,
            {"player_name": "TestPlayer1"},
        )
        self.assertEqual(response.status_code, 302)

        game = Game.objects.first()
        player1 = game.players.first()
        self.assertIsNotNone(game)
        self.assertTrue(game.is_active)
        self.assertFalse(game.is_private)

        response = self.client2.post(
            join_url,
            {"player_name": "TestPlayer2"},
        )
        self.assertEqual(response.status_code, 302)

        player2 = Player.objects.get(name="TestPlayer2")

        self.assertTrue(player1.turn)
        self.assertFalse(player2.turn)

    def test_custom_game(self):
        response = self.client1.post(
            join_url,
            {
                "player_name": "TestPlayer1",
                "create_new": True,
            },
        )
        self.assertEqual(response.status_code, 302)

        game = Game.objects.first()
        player1 = game.players.first()
        self.assertIsNotNone(game)
        self.assertTrue(game.is_active)
        self.assertTrue(game.is_private)

        response = self.client.post(
            join_url,
            {
                "player_name": "TestPlayer2",
                "game_code": game.game_code,
            },
        )
        self.assertEqual(response.status_code, 302)
        game.refresh_from_db()
        player2 = Player.objects.get(name="TestPlayer2")
        self.assertEqual(player2.game, game)

        self.assertTrue(player1.turn)
        self.assertFalse(player2.turn)
