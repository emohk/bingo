from django.contrib import admin

from .models import Game, Player
from django.utils.html import format_html

# Register your models here.
admin.site.register(Game)


@admin.register(Player)
class PlayerAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "name",
        "game",
        "display_board",
        "turn",
        "is_connected",
        "joined_at",
    )
    readonly_fields = ("display_board", "board")

    def display_board(self, obj):
        if not obj.board:
            return ""
        html = "<table style='border-collapse:collapse;'>"
        for row in obj.board:
            html += "<tr>"
            for cell in row:
                html += f"<td style='border:1px solid #ccc;padding:4px;text-align:center;'>{cell}</td>"
            html += "</tr>"
        html += "</table>"
        return format_html(html)

    display_board.short_description = "Board"
