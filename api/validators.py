import requests
import json

from django.core.exceptions import ObjectDoesNotExist
from django.conf import settings
from rest_framework.exceptions import ValidationError
from api.models import TezosUser, GameSession, Boss
from pytezos import Key
from pytezos.crypto.encoding import is_address


class PublicKeyValidator:
    def __call__(self, pk):
        try:
            Key.from_encoded_key(pk)
        except ValueError as error:
            raise ValidationError(error)
        return pk


class SignedAddressValidator:
    def __call__(self, address):
        try:
            validated = is_address(address)
            if not validated:
                raise ValidationError('It is not Tezos-compatible address.')
            tezos_user = TezosUser.objects.get(address=address)
            if not tezos_user.success_sign:
                raise ValidationError('This user did not yet successfully signed payload.')
        except ObjectDoesNotExist:
            raise ValidationError('Tezos user with this address not found.')
        return address


class CaptchaValidator:
    def __call__(self, captcha_value):
        verified_data = {
            'secret': settings.CAPTCHA_SECRET,
            'response': captcha_value
        }
        google_validation_response = requests.post(settings.CAPTCHA_VERIFY_URL, data=verified_data)
        if not json.loads(google_validation_response.text)['success']:
            raise ValidationError(json.loads(google_validation_response.text))

        return captcha_value


class GameHashValidator:
    def __call__(self, hash_value):
        try:
            GameSession.objects.get(hash=hash_value)
        except ObjectDoesNotExist:
            raise ValidationError('Game with this id not found.')
        return hash_value


class GameIsActiveValidator(GameHashValidator):
    def __call__(self, hash_value):
        super().__call__(hash_value)
        game = GameSession.objects.get(hash=hash_value)
        if game.status != GameSession.CREATED:
            raise ValidationError('Game is not active.')


class GameIsPausedValidator(GameHashValidator):
    def __call__(self, hash_value):
        super().__call__(hash_value)
        game = GameSession.objects.get(hash=hash_value)
        if game.status != GameSession.PAUSED:
            raise ValidationError('Game is not paused.')


class KillBossValidator:
    def __call__(self, boss_id):
        try:
            Boss.objects.get(id=boss_id)
        except ObjectDoesNotExist:
            raise ValidationError('Boss with this id not found.')
        return boss_id
