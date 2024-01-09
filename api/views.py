import codecs
import requests
import json

from django.core.exceptions import ObjectDoesNotExist
from django.conf import settings
from pytezos import Key
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from api.models import TezosUser, get_payload_for_sign
from api.serializers import TezosUserSerializer


class GetPayload(APIView):
    def get(self, request):
        pub_key = request.query_params.get('pub_key')
        if not pub_key:
            return Response({'error': 'Parameter "pub_key" is missing'}, status=status.HTTP_400_BAD_REQUEST)

        try:
            key = Key.from_encoded_key(pub_key)
        except ValueError as error:
            return Response({'error': f'Public key error: {error}'}, status=status.HTTP_400_BAD_REQUEST)

        tezos_user, created = TezosUser.objects.get_or_create(
            public_key=key.public_key(),
            address=key.public_key_hash()
        )
        if not created:
            tezos_user.payload = get_payload_for_sign()
            tezos_user.save()

        serialized = TezosUserSerializer(tezos_user)
        return Response(serialized.data, status=status.HTTP_200_OK)


class VerifyPayload(APIView):
    def get(self, request):
        required_params = ['pub_key', 'signature']

        for param in required_params:
            if param not in request.query_params:
                return Response({'error': f'"{param}" param is missing'}, status=status.HTTP_400_BAD_REQUEST)

        pub_key = request.query_params.get('pub_key')
        signature = request.query_params.get('signature')

        try:
            user = TezosUser.objects.get(public_key=pub_key)
            key = Key.from_encoded_key(pub_key)
            hex_payload = self.get_hex_payload(user.payload)
            verified = key.verify(signature, hex_payload)
            user.signature = signature
            user.success_sign = verified
            user.save()
            return Response({'result': f'Successfully verified.'}, status=status.HTTP_200_OK)
        except ValueError as error:
            return Response({'error': f'Error: {error}'}, status=status.HTTP_400_BAD_REQUEST)
        except ObjectDoesNotExist as error:
            return Response({'error': f'Tezos user with this public key not found: {error}'},
                            status=status.HTTP_400_BAD_REQUEST)

    def get_hex_payload(self, plain_text_payload):
        bytes_hex = codecs.encode(plain_text_payload.encode('utf-8'), 'hex').decode()
        bytes_length = hex(len(bytes_hex) // 2)[2:]
        add_padding = "00000000" + bytes_length
        padded_bytes_length = add_padding[-8:]
        start_prefix = "0501"
        payload_bytes = start_prefix + padded_bytes_length + bytes_hex
        return payload_bytes


class VerifyCaptcha(APIView):
    def post(self, request):
        captcha_value = request.data['g-recaptcha-response']
        if not captcha_value:
            return Response({'error': 'Param "g-recaptcha-response" not provided.'}, status=status.HTTP_400_BAD_REQUEST)

        url = 'https://www.google.com/recaptcha/api/siteverify'
        verified_data = {
            'secret': settings.CAPTCHA_SECRET,
            'response': captcha_value
        }
        google_validation_response = requests.post(url, data=verified_data)
        return Response(json.loads(google_validation_response.text), status=status.HTTP_200_OK)
