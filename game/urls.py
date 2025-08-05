from django.urls import path

from . import views

urlpatterns = [
    path("", views.join_game, name="join"),
    path("game/<str:game_code>/", views.game_room, name="game"),
    path("game/<str:game_code>/make-move/", views.make_move, name="make_move"),
]
