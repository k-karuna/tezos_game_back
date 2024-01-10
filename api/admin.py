from django.contrib import admin
from api.models import TezosUser, GameSession, Token, Boss, Drop

admin.site.register(TezosUser)
admin.site.register(GameSession)
admin.site.register(Token)
admin.site.register(Boss)
admin.site.register(Drop)
