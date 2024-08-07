import random
from datetime import timedelta

from pytezos import pytezos

from django.utils import timezone
from django.db.models import Count, F, Max, Sum
from drf_yasg.utils import swagger_auto_schema
from rest_framework import status
from rest_framework.response import Response
from rest_framework.generics import GenericAPIView

from api.models import Token, Drop, get_payload_for_sign, Achievement, UserAchievement
from api.serializers import *

from drf_yasg import openapi


class GetPayload(GenericAPIView):
    serializer_class = PublicKeySerializer

    @swagger_auto_schema(responses={
        "200": openapi.Response(
            description="Sample response for successful getting payload",
            examples={
                "application/json": {
                    "payload": "Tezos Signed Message: 2024-01-15T21:01:00.145435 7f490f63fd5141bc9b27e9546d8d74d9",
                }
            }
        )
    }, query_serializer=serializer_class)
    def get(self, request):
        serializer = self.serializer_class(data=self.request.query_params)
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

    @swagger_auto_schema(responses={
        "200": openapi.Response(
            description="Sample response for successful signature verification",
            examples={
                "application/json": {
                    "response": "Successfully verified.",
                }
            }
        )
    })
    def post(self, request):
        serializer = self.serializer_class(data=self.request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        user = TezosUser.objects.get(public_key=serializer.validated_data['public_key'])
        user.signature = serializer.validated_data['signature']
        user.success_sign = True
        user.save()
        return Response({'response': 'Successfully verified.'}, status=status.HTTP_200_OK)


class VerifyCaptcha(GenericAPIView):
    serializer_class = CaptchaSerializer

    @swagger_auto_schema(responses={
        "200": openapi.Response(
            description="Sample response for successful captcha verification",
            examples={
                "application/json": {
                    "response": "Successfully verified.",
                }
            }
        )
    })
    def post(self, request):
        serializer = self.serializer_class(data=self.request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        return Response({'response': 'Successfully verified.'}, status=status.HTTP_200_OK)


class StartGame(GenericAPIView):
    serializer_class = AddressSerializer

    @swagger_auto_schema(
        operation_description="Starts new game session, return current if provided address already have active session",
        responses={
            "200": openapi.Response(
                description="Sample response for successful started game",
                examples={
                    "application/json": {
                        "response": {
                            "game_id": "2d946685c41548d7a144873ec3fc9301",
                            "game_drop": [{
                                "boss": 1,
                                "token": 5
                            }, {
                                "boss": 15,
                                "token": 10
                            }]
                        },
                    }
                }
            )
        })
    def post(self, request):
        serializer = self.serializer_class(data=self.request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        tezos_user = TezosUser.objects.get(address=serializer.validated_data['address'])

        last_minute = timezone.now() - timedelta(minutes=1)
        last_minute_games_count = GameSession.objects.filter(player=tezos_user, creation_time__gte=last_minute).count()
        drop_is_able = last_minute_games_count <= settings.MAX_GAMES_PER_MINUTE

        GameSession.objects.filter(player=tezos_user, status__in=[GameSession.CREATED, GameSession.PAUSED]).update(
            status=GameSession.ABANDONED)
        game = GameSession(player=tezos_user, status=GameSession.CREATED)
        game.save()

        first_boss = Boss.objects.all().first()
        armor_token = Token.objects.get(token_id=settings.ARMOR_TOKEN_ID)
        previous_armor_drops = Drop.objects.filter(game__player=tezos_user, boss=first_boss, dropped_token=armor_token)
        previous_armor_boss_killed = previous_armor_drops.filter(boss_killed=True).exists()
        if not previous_armor_drops.exists():
            armor_drop = Drop(boss=first_boss, dropped_token=armor_token, game=game)
            armor_drop.save()
        elif not previous_armor_boss_killed:
            previous_armor_drops.update(game=game)

        if drop_is_able:
            all_bosses = Boss.objects.all()
            if not previous_armor_boss_killed:
                all_bosses = all_bosses.exclude(id=first_boss.id)
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
            'game_drop': [{'boss': drop.boss.id, 'token': drop.dropped_token.token_id} for drop in
                          Drop.objects.filter(game=game)]
        }
        return Response({'response': response_data}, status=status.HTTP_200_OK)


class PauseGame(GenericAPIView):
    serializer_class = ActiveGameSerializer

    @swagger_auto_schema(responses={
        "200": openapi.Response(
            description="Sample response for successful game paused",
            examples={
                "application/json": {
                    "response": "Game 7f490f63fd5141bc9b27e9546d8d74d9 paused.",
                }
            }
        )
    })
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

    @swagger_auto_schema(responses={
        "200": openapi.Response(
            description="Sample response for successful game unpaused",
            examples={
                "application/json": {
                    "response": "Game 7f490f63fd5141bc9b27e9546d8d74d9 unpaused.",
                }
            }
        )
    })
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
    serializer_class = EndGameSerializer

    @swagger_auto_schema(
        operation_description="End active game",
        responses={
            "200": openapi.Response(
                description="Sample response for successful game session ended",
                examples={
                    "application/json": {
                        "response": "Game session 7f490f63fd5141bc9b27e9546d8d74d9 ended.",
                    }
                }
            )
        })
    def post(self, request):
        serializer = self.serializer_class(data=self.request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        game = GameSession.objects.get(hash=serializer.validated_data['game_id'])
        game.status = GameSession.ENDED
        game.score = serializer.validated_data['score']
        game.favourite_weapon = serializer.validated_data['favourite_weapon']
        game.shots_fired = serializer.validated_data['shots_fired']
        game.mobs_killed = serializer.validated_data['mobs_killed']
        game.save()
        return Response({'response': f'Game session {game.hash} ended.'}, status=status.HTTP_200_OK)


class TransferDrop(GenericAPIView):
    serializer_class = TransferDropSerializer

    @swagger_auto_schema(
        operation_description="Transfer all drops from ended and abandoned games to provided address.",
        responses={
            "200": openapi.Response(
                description="Sample response of a successful transfer for 2 tokens.",
                examples={
                    "application/json": {
                        "response": {
                            "tokens_transfered": 2,
                            "operation_hash": "ootF1KoYWnJa9ets9BqmUgVomZNzQE2VDntck1jqzZ8nvXnZ9X7"
                        },
                    }
                }
            )
        })
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
            pt = pytezos.using(key=settings.PRIVATE_KEY, shell=f'https://rpc.tzkt.io/{settings.NETWORK}')
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
                ])
                injected_tx = tx.send(min_confirmations=1)

                num_transferred = drops.update(transfer_date=timezone.now())
                return Response({
                    'response': {
                        'tokens_transfered': num_transferred,
                        'operation_hash': injected_tx.hash()
                    },
                }, status=status.HTTP_200_OK)
            except Exception as error:
                return Response({'error': f'Tezos error: {error}'}, status=status.HTTP_400_BAD_REQUEST)


class GetDrop(GenericAPIView):
    serializer_class = AddressSerializer

    @swagger_auto_schema(
        operation_description="Get list of all drops from ended and abandoned games for provided address.",
        responses={
            "200": openapi.Response(
                description="List of tokes that can be minted / transferred.",
                examples={
                    "application/json": {
                        "response": [{"token_id": 1, "amount": 1}]
                    }
                }
            )
        },
        query_serializer=serializer_class)
    def get(self, request):
        serializer = self.serializer_class(data=self.request.query_params)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        tezos_user = TezosUser.objects.get(address=serializer.validated_data['address'])

        drops = (Drop.objects.filter(game__player__address=tezos_user.address,
                                     game__status__in=[GameSession.ENDED, GameSession.ABANDONED],
                                     boss_killed=True,
                                     dropped_token__isnull=False,
                                     transfer_date=None)
                 .values(token_id=F('dropped_token__token_id'))
                 .annotate(amount=Count('token_id')))

        return Response({'response': drops}, status=status.HTTP_200_OK)


class KillBoss(GenericAPIView):
    serializer_class = KillBossSerializer

    @swagger_auto_schema(
        operation_description="Kill boss in provided game session",
        responses={
            "200": openapi.Response(
                description="Sample response of a successful killed boss.",
                examples={
                    "application/json": {
                        "response": "Successfully killed."
                    }
                }
            )
        })
    def post(self, request):
        serializer = self.serializer_class(data=self.request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        game = GameSession.objects.get(hash=serializer.validated_data['game_id'])
        boss = Boss.objects.get(id=serializer.validated_data['boss'])
        drop, created = Drop.objects.get_or_create(game=game, boss=boss)
        drop.boss_killed = True
        drop.save()

        try:
            kill_boss_achievement = Achievement.objects.get(type=Achievement.KILL_BOSS)
            user_achievement, created = UserAchievement.objects.get_or_create(player=game.player,
                                                                              achievement=kill_boss_achievement)

            if user_achievement.current_progress < user_achievement.achievement.target_progress:
                user_achievement.current_progress += 1
                user_achievement.save()
        except ObjectDoesNotExist:
            pass

        return Response({'response': 'Successfully killed.'}, status=status.HTTP_200_OK)


class GetAchievements(GenericAPIView):
    serializer_class = AddressSerializer

    @swagger_auto_schema(
        operation_description="Returns list of player game achievements.",
        responses={
            "200": openapi.Response(
                description="List of player game achievements.",
                examples={
                    "application/json": [
                        {
                            "achievement": {
                                "name": "Kill 10 bosses",
                                "token_id": 27
                            },
                            "percent_progress": 20
                        }
                    ]
                }
            )
        },
        query_serializer=serializer_class)
    def get(self, request):
        serializer = self.serializer_class(data=self.request.query_params)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        user_achievements = UserAchievement.objects.filter(player__address=serializer.validated_data['address'])
        serialized_achievements = UserAchievementSerializer(user_achievements, many=True)
        return Response(serialized_achievements.data)


class GetPlayerStats(GenericAPIView):
    serializer_class = AddressSerializer

    @swagger_auto_schema(
        operation_description="Returns player statistics.",
        responses={
            "200": openapi.Response(
                description="Object with player statistics.",
                examples={
                    "application/json": {
                        "response": {
                            "games_played": 0,
                            "bosses_killed": 0,
                            "best_score": 0,
                            "mobs_killed": 0,
                            "shots_fired": 0,
                            "favourite_weapon": "ZOOOKA"
                        }
                    }
                }
            )
        },
        query_serializer=serializer_class)
    def get(self, request):
        serializer = self.serializer_class(data=self.request.query_params)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        player = TezosUser.objects.get(address=serializer.validated_data['address'])
        player_games = GameSession.objects.filter(player=player, status=GameSession.ENDED)
        key = 'favourite_weapon'
        favourite_weapon = getattr(
            player_games.values(key).annotate(count=Count(key)).order_by('-count').first(), key,
            '')
        response = {
            "games_played": player_games.count(),
            "bosses_killed": Drop.objects.filter(game__player=player, boss_killed=True).count(),
            "best_score": player_games.aggregate(Max("score", default=0))['score__max'],
            "mobs_killed": player_games.aggregate(Sum("mobs_killed", default=0))['mobs_killed__sum'],
            "shots_fired": player_games.aggregate(Sum("shots_fired", default=0))['shots_fired__sum'],
            "favourite_weapon": favourite_weapon if favourite_weapon is not None else ""
        }
        return Response({'response': response}, status=status.HTTP_200_OK)


class HasActiveGames(GenericAPIView):
    serializer_class = AddressSerializer

    @swagger_auto_schema(
        operation_description="Returns info whether player has active game sessions.",
        responses={
            "200": openapi.Response(
                description="Response object with bool info about active game sessions.",
                examples={
                    "application/json": {
                        "response": {
                            "has_games": True
                        }
                    }
                }
            )
        },
        query_serializer=serializer_class)
    def get(self, request):
        serializer = self.serializer_class(data=self.request.query_params)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        player = TezosUser.objects.get(address=serializer.validated_data['address'])
        has_games = GameSession.objects.filter(player=player,
                                               status__in=[GameSession.CREATED, GameSession.PAUSED]).exists()
        return Response({'response': {'has_games': has_games}}, status=status.HTTP_200_OK)
