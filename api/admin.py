from django.contrib import admin
from api.models import TezosUser, GameSession, TokenTransfer, Token, BossDrop

admin.site.register(TezosUser)
admin.site.register(GameSession)
admin.site.register(TokenTransfer)
admin.site.register(Token)
admin.site.register(BossDrop)
