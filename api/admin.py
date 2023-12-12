from django.contrib import admin
from api.models import TezosUser, GameSession, TransferedToken

admin.site.register(TezosUser)
admin.site.register(GameSession)
admin.site.register(TransferedToken)
