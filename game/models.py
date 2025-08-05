from django.db import models
from django.contrib.postgres.fields import ArrayField

import uuid


class Game(models.Model):
    game_code = models.CharField(max_length=100)
    created_at = models.DateTimeField(auto_now_add=True)
    is_active = models.BooleanField(default=True)
    is_private = models.BooleanField(default=False)
    numbers = ArrayField(
        models.IntegerField(), default=list
    )  # List of numbers called in the game
    called_numbers = ArrayField(models.IntegerField(), default=list)

    def __str__(self):
        return f"Game {self.game_code} ({'Active' if self.is_active else 'Ended'})"


class Player(models.Model):
    name = models.CharField(max_length=20, default="John")
    game = models.ForeignKey(Game, on_delete=models.CASCADE, related_name="players")
    player_id = models.UUIDField(default=uuid.uuid4, editable=False, unique=True)
    board = ArrayField(
        ArrayField(models.IntegerField(), size=5), size=5
    )  # 5x5 bingo board
    turn = models.BooleanField(default=False)
    joined_at = models.DateTimeField(auto_now_add=True)
    is_connected = models.BooleanField(default=True)

    def completed_lines(self):
        """Returns no. of completed lines and numbers in those lines in the player's board."""
        completed = 0
        numbers = []
        # Check rows
        for row in self.board:
            if all(cell in self.game.called_numbers for cell in row):
                completed += 1
                numbers.extend(row)
        # Check columns
        for col_idx in range(5):
            if all(
                self.board[row_idx][col_idx] in self.game.called_numbers
                for row_idx in range(5)
            ):
                completed += 1
                numbers.extend(self.board[row_idx][col_idx] for row_idx in range(5))
        # Check diagonals
        if all(self.board[i][i] in self.game.called_numbers for i in range(5)):
            completed += 1
            numbers.extend(self.board[i][i] for i in range(5))
        if all(self.board[i][4 - i] in self.game.called_numbers for i in range(5)):
            completed += 1
            numbers.extend(self.board[i][4 - i] for i in range(5))
        return completed, numbers

    def check_winner(self):
        """Check if the player has won."""
        completed = self.completed_lines()[0]
        return completed >= 5

    def __str__(self):
        return f"Player {self.player_id} in Game {self.game.game_code}"
