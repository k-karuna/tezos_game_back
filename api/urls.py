from django.urls import path
from api.views import *

urlpatterns = [
    path('payload/get/', GetPayload.as_view()),
    path('payload/verify/', VerifyPayload.as_view()),
    path('captcha/verify/', VerifyCaptcha.as_view()),
    path('game/start/', StartGame.as_view()),
    path('game/pause/', PauseGame.as_view()),
    path('game/unpause/', UnpauseGame.as_view()),
    path('game/end/', EndGame.as_view()),
    path('game/boss/kill/', KillBoss.as_view()),
    path('drop/transfer/', TransferDrop.as_view()),
    path('drop/get/', GetDrop.as_view()),
    path('achievements/get/', GetAchievements.as_view()),
    path('player/stats/get/', GetPlayerStats.as_view()),
    path('player/games/has-active/', HasActiveGames.as_view()),
]
