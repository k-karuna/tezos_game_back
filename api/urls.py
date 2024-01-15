from django.urls import path
from api.views import GetPayload, VerifyPayload, VerifyCaptcha, StartGame, PauseGame, UnpauseGame, EndGame, TransferDrop

urlpatterns = [
    path('payload/get/', GetPayload.as_view()),
    path('payload/verify/', VerifyPayload.as_view()),
    path('captcha/verify/', VerifyCaptcha.as_view()),
    path('game/start/', StartGame.as_view()),
    path('game/pause/', PauseGame.as_view()),
    path('game/unpause/', UnpauseGame.as_view()),
    path('game/end/', EndGame.as_view()),
    path('drop/transfer/', TransferDrop.as_view()),
]
