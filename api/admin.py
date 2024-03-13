from django.contrib import admin

from api.filters import DropGameIDFilter, DropPlayerFilter, PlayerFilter
from api.models import TezosUser, GameSession, Token, Boss, Drop, Achievement, UserAchievement


class DropAdmin(admin.ModelAdmin):
    list_display = ['game_hash', 'game_player_address', 'boss_killed', 'dropped_token_name', 'transfer_date']
    list_filter = [DropGameIDFilter, DropPlayerFilter, 'boss_killed', 'dropped_token__name']

    @admin.display(ordering="game__creation_time")
    def game_hash(self, obj):
        return obj.game.hash if obj.game is not None else ''

    @admin.display(ordering="game__player__registration_date")
    def game_player_address(self, obj):
        return obj.game.player.address if obj.game is not None else ''

    @admin.display(ordering="dropped_token__token_id")
    def dropped_token_name(self, obj):
        return obj.dropped_token.name if obj.dropped_token else ''


class GameSessionAdmin(admin.ModelAdmin):
    list_display = ['hash', 'player', 'creation_time', 'status']
    list_filter = [PlayerFilter, 'status']


admin.site.register(TezosUser)
admin.site.register(GameSession, GameSessionAdmin)
admin.site.register(Token)
admin.site.register(Boss)
admin.site.register(Drop, DropAdmin)
admin.site.register(Achievement)
admin.site.register(UserAchievement)
