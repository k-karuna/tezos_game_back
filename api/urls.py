from django.urls import path
from api.views import GetPayload, VerifyPayload, VerifyCaptcha, StartGame

urlpatterns = [
    path('payload/get/', GetPayload.as_view()),
    path('payload/verify/', VerifyPayload.as_view()),
    path('captcha/verify/', VerifyCaptcha.as_view()),
    path('game/start/', StartGame.as_view()),
]
