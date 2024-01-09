from django.urls import path
from api.views import GetPayload, VerifyPayload, VerifyCaptcha

urlpatterns = [
    path('payload/get/', GetPayload.as_view()),
    path('payload/verify/', VerifyPayload.as_view()),
    path('captcha/verify/', VerifyCaptcha.as_view()),
]
