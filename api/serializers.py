from rest_framework import serializers
from api.utils import get_hex_payload
from api.validators import *
from rest_framework.exceptions import ValidationError
from pytezos import Key


class PublicKeySerializer(serializers.ModelSerializer):
    public_key = serializers.CharField(required=True, validators=[PublicKeyValidator()])

    class Meta:
        model = TezosUser
        fields = ('public_key',)


class AddressSerializer(serializers.ModelSerializer):
    address = serializers.CharField(max_length=36, required=True, validators=[SignedAddressValidator()])

    class Meta:
        model = TezosUser
        fields = ('address',)


class UserSignatureSerializer(PublicKeySerializer):
    signature = serializers.CharField(required=True)

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
    captcha = serializers.CharField(max_length=2048, required=True, validators=[CaptchaValidator()])


class GameHashSerializer(serializers.Serializer):
    game_id = serializers.CharField(required=True, validators=[GameHashValidator()])


class ActiveGameSerializer(GameHashSerializer):
    game_id = serializers.CharField(required=True, validators=[GameIsActiveValidator()])


class PausedGameSerializer(GameHashSerializer):
    game_id = serializers.CharField(required=True, validators=[GameIsPausedValidator()])


class TransferDropSerializer(serializers.Serializer):
    captcha = serializers.CharField(max_length=2048, required=True, validators=[CaptchaValidator()])
    address = serializers.CharField(max_length=36, required=True, validators=[SignedAddressValidator()])


class KillBossSerializer(ActiveGameSerializer):
    boss = serializers.IntegerField(required=True, validators=[KillBossValidator()])
