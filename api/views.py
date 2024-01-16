import random

from django.utils import timezone
from django.core.exceptions import MultipleObjectsReturned
from pytezos import pytezos
from rest_framework import status
from rest_framework.response import Response
from rest_framework.generics import GenericAPIView

from api.models import Token, Drop, get_payload_for_sign
from api.serializers import *
from api.tasks import end_game_session


class GetPayload(GenericAPIView):
    serializer_class = PublicKeySerializer

    def post(self, request):
        serializer = self.serializer_class(data=self.request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        key = Key.from_encoded_key(serializer.validated_data['public_key'])
        tezos_user, created = TezosUser.objects.get_or_create(
            public_key=key.public_key(),
            address=key.public_key_hash()
        )
        if not created:
            tezos_user.payload = get_payload_for_sign()
            tezos_user.save()

        return Response({'payload': tezos_user.payload}, status=status.HTTP_200_OK)


class VerifyPayload(GenericAPIView):
    serializer_class = UserSignatureSerializer

    def post(self, request):
        serializer = self.serializer_class(data=self.request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        user = TezosUser.objects.get(public_key=serializer.validated_data['public_key'])
        user.signature = serializer.validated_data['signature']
        user.success_sign = True
        user.save()
        return Response({'response': f'Successfully verified.'}, status=status.HTTP_200_OK)


class VerifyCaptcha(GenericAPIView):
    serializer_class = CaptchaSerializer

    def post(self, request):
        serializer = self.serializer_class(data=self.request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        return Response({'response': f'Successfully verified.'}, status=status.HTTP_200_OK)


class StartGame(GenericAPIView):
    serializer_class = AddressSerializer

    def post(self, request):
        serializer = self.serializer_class(data=self.request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        tezos_user = TezosUser.objects.get(address=serializer.validated_data['address'])

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
        return Response({'response': response_data}, status=status.HTTP_200_OK)


class PauseGame(GenericAPIView):
    serializer_class = ActiveGameSerializer

    def post(self, request):
        serializer = self.serializer_class(data=self.request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        game = GameSession.objects.get(hash=serializer.validated_data['game_id'])
        game.status = GameSession.PAUSED
        game.pause_init_time = timezone.now()
        game.save()
        return Response({'response': f'Game {game.hash} paused.'}, status=status.HTTP_200_OK)


class UnpauseGame(GenericAPIView):
    serializer_class = PausedGameSerializer

    def post(self, request):
        serializer = self.serializer_class(data=self.request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        game = GameSession.objects.get(hash=serializer.validated_data['game_id'])
        game.status = GameSession.CREATED
        game.seconds_on_pause += (timezone.now() - game.pause_init_time).total_seconds()
        game.save()
        return Response({'response': f'Game {game.hash} unpaused.'}, status=status.HTTP_200_OK)


class EndGame(GenericAPIView):
    serializer_class = ActiveGameSerializer

    def post(self, request):
        serializer = self.serializer_class(data=self.request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        game = GameSession.objects.get(hash=serializer.validated_data['game_id'])
        game.status = GameSession.ENDED
        game.save()
        return Response({'response': f'Game session {game.hash} ended.'}, status=status.HTTP_200_OK)


class TransferDrop(GenericAPIView):
    serializer_class = TransferDropSerializer

    def post(self, request):
        serializer = self.serializer_class(data=self.request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        tezos_user = TezosUser.objects.get(address=serializer.validated_data['address'])

        drops = Drop.objects.filter(game__player__address=tezos_user.address,
                                    game__status__in=[GameSession.ENDED, GameSession.ABANDONED],
                                    boss_killed=True,
                                    dropped_token__isnull=False,
                                    transfer_date=None)
        if len(drops) == 0:
            return Response({'response': {'tokens_transfered': 0}}, status=status.HTTP_200_OK)
        else:
            pt = pytezos.using(key=settings.PRIVATE_KEY, shell=settings.NETWORK)
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
                num_transfered = drops.update(transfer_date=timezone.now())
                return Response({
                    'response': {
                        'tokens_transfered': num_transfered,
                        'transaction_hash': tx['hash']
                    },
                }, status=status.HTTP_200_OK)
            except Exception as error:
                return Response({'error': f'Tezos error: {error}'}, status=status.HTTP_400_BAD_REQUEST)


class KillBoss(GenericAPIView):
    serializer_class = KillBossSerializer

    def post(self, request):
        serializer = self.serializer_class(data=self.request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        game = GameSession.objects.get(hash=serializer.validated_data['game_id'])
        boss = Boss.objects.get(id=serializer.validated_data['boss'])
        drop, created = Drop.objects.get_or_create(game=game, boss=boss)
        drop.boss_killed = True
        drop.save()
        return Response({'response': f'Successfully killed.'}, status=status.HTTP_200_OK)
