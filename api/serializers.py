from rest_framework import serializers
from api.utils import get_hex_payload
from api.validators import *
from api.models import Achievement, UserAchievement
from rest_framework.exceptions import ValidationError
from pytezos import Key


class GameHashField(serializers.CharField):
    def __init__(self, *args, **kwargs):
        kwargs.setdefault('required', True)
        kwargs.setdefault('max_length', 32)
        kwargs.setdefault('help_text', 'Unique game hash 32 char hex string')
        super().__init__(**kwargs)


class AddressField(serializers.CharField):
    def __init__(self, *args, **kwargs):
        kwargs.setdefault('required', True)
        kwargs.setdefault('max_length', 36)
        kwargs.setdefault('help_text', 'Tezos address public key hash, can start with tz1')
        super().__init__(**kwargs)


class CaptchaField(serializers.CharField):
    def __init__(self, *args, **kwargs):
        kwargs.setdefault('required', True)
        kwargs.setdefault('min_length', 1000)
        kwargs.setdefault('max_length', 2000)
        kwargs.setdefault('help_text', 'Google captcha value')
        super().__init__(**kwargs)


class PublicKeySerializer(serializers.ModelSerializer):
    public_key = serializers.CharField(required=True, validators=[PublicKeyValidator()],
                                       help_text='Tezos address public key, can start with edpk')

    class Meta:
        model = TezosUser
        fields = ('public_key',)


class AddressSerializer(serializers.ModelSerializer):
    address = AddressField(validators=[SignedAddressValidator()])

    class Meta:
        model = TezosUser
        fields = ('address',)


class UserSignatureSerializer(PublicKeySerializer):
    signature = serializers.CharField(required=True, min_length=54, help_text='Signature value, can start with edsig')

    class Meta(PublicKeySerializer.Meta):
        fields = PublicKeySerializer.Meta.fields + ('signature',)

    def validate(self, data):
        public_key = data.get('public_key')
        signature = data.get('signature')
        try:
            user = TezosUser.objects.get(public_key=public_key)
            key = Key.from_encoded_key(user.public_key)
            hex_payload = get_hex_payload(user.payload)
            verified = key.verify(signature, hex_payload)
        except TezosUser.DoesNotExist:
            raise ValidationError('User with this public_key does not exist.')
        except ValueError as error:
            raise ValidationError(error)
        if not verified:
            raise ValidationError("Invalid signature.")
        return data


class CaptchaSerializer(serializers.Serializer):
    captcha = CaptchaField(validators=[CaptchaValidator()])


class GameHashSerializer(serializers.Serializer):
    game_id = GameHashField(validators=[GameHashValidator()])


class ActiveGameSerializer(GameHashSerializer):
    game_id = GameHashField(validators=[GameIsActiveValidator()])


class PausedGameSerializer(GameHashSerializer):
    game_id = GameHashField(validators=[GameIsPausedValidator()])


class PausedOrActiveGameSerializer(GameHashSerializer):
    game_id = GameHashField(validators=[GameIsActiveOrPausedValidator()])


class EndGameSerializer(PausedOrActiveGameSerializer):
    score = serializers.IntegerField(required=True)
    favourite_weapon = serializers.CharField(required=True)
    shots_fired = serializers.IntegerField(required=True)
    mobs_killed = serializers.IntegerField(required=True)


class TransferDropSerializer(serializers.Serializer):
    # captcha = CaptchaField(validators=[CaptchaValidator()])
    captcha = CaptchaField()
    address = AddressField(validators=[SignedAddressValidator()])


class KillBossSerializer(ActiveGameSerializer):
    boss = serializers.IntegerField(required=True, validators=[KillBossValidator()],
                                    help_text='Numeric identifier of a Boss.')


class AchievementSerializer(serializers.ModelSerializer):
    token_id = serializers.IntegerField(source='reward_token.token_id')

    class Meta:
        model = Achievement
        fields = ('name', 'token_id')


class UserAchievementSerializer(serializers.ModelSerializer):
    achievement = AchievementSerializer()

    class Meta:
        model = UserAchievement
        fields = ('achievement', 'percent_progress')
