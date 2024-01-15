import codecs
import requests
import json
import random

from django.core.exceptions import ObjectDoesNotExist, MultipleObjectsReturned
from django.conf import settings
from django.utils import timezone
from pytezos import pytezos, Key
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from api.models import TezosUser, GameSession, Token, Boss, Drop, get_payload_for_sign
from api.serializers import TezosUserSerializer
from api.tasks import end_game_session


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
        captcha_value = request.data['captcha']
        if not captcha_value:
            return Response({'error': 'Param "captcha" not provided.'}, status=status.HTTP_400_BAD_REQUEST)

        url = 'https://www.google.com/recaptcha/api/siteverify'
        verified_data = {
            'secret': settings.CAPTCHA_SECRET,
            'response': captcha_value
        }
        google_validation_response = requests.post(url, data=verified_data)
        return Response(json.loads(google_validation_response.text), status=status.HTTP_200_OK)


class StartGame(APIView):
    def get(self, request):
        address = request.query_params.get('address')
        if not address:
            return Response({'error': 'Provide "address" parameter with user\'s Tezos address.'},
                            status=status.HTTP_400_BAD_REQUEST)

        try:
            tezos_user = TezosUser.objects.get(address=address)
        except ObjectDoesNotExist as error:
            return Response({'error': f'Tezos user with this address not found: {error}'},
                            status=status.HTTP_400_BAD_REQUEST)
        if not tezos_user.success_sign:
            return Response({'error': f'This user did not yet successfully signed payload.'},
                            status=status.HTTP_400_BAD_REQUEST)

        try:
            game, created = GameSession.objects.get_or_create(player=tezos_user, status=GameSession.CREATED)
        except MultipleObjectsReturned:
            GameSession.objects.filter(player=tezos_user, status=GameSession.CREATED).delete()
            game = GameSession(player=tezos_user, status=GameSession.CREATED)
            game.save()
            created = True

        if created:
            end_game_session.s(game.hash).apply_async(countdown=settings.TERMINATE_GAME_SESSION_SECONDS)
            all_bosses = Boss.objects.all()
            for boss in all_bosses:
                random_number_for_boss = random.random() * 100
                boss_dropped = random_number_for_boss <= boss.drop_chance
                if boss_dropped:
                    all_tokens = Token.objects.all()
                    total_probability = sum(token.drop_chance for token in all_tokens)
                    random_value = random.uniform(0, total_probability)
                    probability_sum = 0
                    chosen_token = None
                    for token in all_tokens:
                        probability_sum += token.drop_chance
                        if random_value <= probability_sum:
                            chosen_token = token
                            break
                    drop = Drop(game=game, boss=boss, dropped_token=chosen_token)
                    drop.save()

        response_data = {
            'game_id': game.hash,
            'game_drop': [{'boss': drop.boss.id, 'token': drop.dropped_token.token_id}
                          for drop in Drop.objects.filter(game=game)],
            'is_new': created
        }
        return Response(response_data, status=status.HTTP_200_OK)


class PauseGame(APIView):
    def get(self, request):
        game_hash = request.query_params.get('game_id')
        if not game_hash:
            return Response({'error': 'Parameter "game_id" not found.'}, status=status.HTTP_400_BAD_REQUEST)
        try:
            game = GameSession.objects.get(hash=game_hash)
        except ObjectDoesNotExist as error:
            return Response({'error': f'Game with this id not found: {error}'}, status=status.HTTP_400_BAD_REQUEST)

        if game.status is not GameSession.CREATED:
            return Response({'error': f'Game status is not active.'}, status=status.HTTP_400_BAD_REQUEST)

        game.status = GameSession.PAUSED
        game.pause_init_time = timezone.now()
        game.save()
        return Response({'response': f'Game {game_hash} paused.'}, status=status.HTTP_200_OK)


class UnpauseGame(APIView):
    def get(self, request):
        game_hash = request.query_params.get('game_id')
        if not game_hash:
            return Response({'error': 'Provide "game_id" parameter.'}, status=status.HTTP_400_BAD_REQUEST)
        try:
            game = GameSession.objects.get(hash=game_hash)
        except ObjectDoesNotExist as error:
            return Response({'error': f'Game with this id not found: {error}'}, status=status.HTTP_400_BAD_REQUEST)

        if game.status is not GameSession.PAUSED:
            return Response({'error': f'Game status is not paused.'}, status=status.HTTP_400_BAD_REQUEST)

        game.status = GameSession.CREATED
        game.seconds_on_pause += (timezone.now() - game.pause_init_time).total_seconds()
        game.save()
        return Response({'response': f'Game {game_hash} unpaused.'}, status=status.HTTP_200_OK)


class EndGame(APIView):
    def get(self, request):
        bosses = request.query_params.getlist['boss_id']
        if 'game_id' not in request.query_params:
            return Response({'error': f'"game_id" param is missing.'}, status=status.HTTP_400_BAD_REQUEST)

        game_hash = request.query_params.get('game_id')
        try:
            game = GameSession.objects.get(hash=game_hash)
        except ObjectDoesNotExist:
            return Response({'error': f'Game with id {game_hash} not found.'})
        if game.status == GameSession.CREATED:
            game.status = GameSession.ENDED
            game.save()
            return Response({'response': f'Game session {game_hash} ended.'}, status=status.HTTP_200_OK)
        else:
            return Response({'response': f'Game session {game_hash} is not active.'},
                            status=status.HTTP_400_BAD_REQUEST)


class TransferDrop(APIView):
    def get(self, request):
        required_params = ['address', 'captcha']

        for param in required_params:
            if param not in request.query_params:
                return Response({'error': f'"{param}" param is missing.'}, status=status.HTTP_400_BAD_REQUEST)

        try:
            tezos_user = TezosUser.objects.get(address=request.query_params.get('captcha'))
        except ObjectDoesNotExist as error:
            return Response({'error': f'Tezos user with this address not found: {error}'},
                            status=status.HTTP_400_BAD_REQUEST)
        if not tezos_user.success_sign:
            return Response({'error': f'This user did not yet successfully signed payload.'},
                            status=status.HTTP_400_BAD_REQUEST)

        captcha_data_for_check = {
            'secret': settings.CAPTCHA_SECRET,
            'response': request.query_params.get('captcha')
        }
        google_validation_response = requests.post(settings.CAPTCHA_VERIFY_URL, data=captcha_data_for_check)
        if not json.loads(google_validation_response.text)['success']:
            return Response({'error': f'Captcha validation error: {google_validation_response.text}'},
                            status=status.HTTP_400_BAD_REQUEST)

        drops = Drop.objects.filter(game__player__address=tezos_user.address, game__status=GameSession.ENDED,
                                    transfer_date=None)
        if len(drops) == 0:
            return Response({'response': {'tokens_transfered': 0}}, status=status.HTTP_200_OK)
        else:
            pt = pytezos.using(key=settings.PRIVATE_KEY, shell=settings.NETWORK).contract(settings.CONTRACT)
            contract = pt.contract(settings.CONTRACT)
            try:
                tx = contract.transfer([
                    {
                        "from_": f'{pt.key.public_key_hash()}',
                        "txs": [{
                            "to_": f'{tezos_user.address}',
                            "token_id": drop.dropped_token.token_id,
                            "amount": 1
                        } for drop in drops]
                    }
                ]).inject()
                drops.update(transfer_date=timezone.now())
                return Response({
                    'response': {
                        'tokens_transfered': len(drops),
                        'transaction_hash': tx['hash']
                    },
                }, status=status.HTTP_200_OK)
            except Exception as error:
                return Response({'error': f'Tezos error: {error}'}, status=status.HTTP_400_BAD_REQUEST)
