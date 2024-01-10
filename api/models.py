import uuid
from datetime import datetime
from django.db import models


def get_payload_for_sign():
    return f"Tezos Signed Message: {datetime.now().isoformat()} {get_uuid_hash()}"


def get_uuid_hash():
    return uuid.uuid4().hex


class TezosUser(models.Model):
    address = models.CharField(max_length=36, blank=True, null=True)
    public_key = models.CharField(max_length=64, blank=True, null=True)
    payload = models.CharField(max_length=128, default=get_payload_for_sign)
    signature = models.CharField(max_length=128, blank=True, null=True)
    success_sign = models.BooleanField(default=False)
    registration_date = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.address


class GameSession(models.Model):
    CREATED = 0
    ENDED = 1
    ABANDONED = 2
    GAME_STATUS = [
        (CREATED, "Created"),
        (ENDED, "Ended"),
        (ABANDONED, "Abandoned"),
    ]

    hash = models.CharField(max_length=32, default=get_uuid_hash, unique=True)
    player = models.ForeignKey(TezosUser, on_delete=models.SET_NULL, blank=True, null=True)
    status = models.PositiveSmallIntegerField(choices=GAME_STATUS, default=CREATED)


class Token(models.Model):
    name = models.CharField(max_length=256)
    value = models.PositiveSmallIntegerField()
    token_id = models.PositiveIntegerField()

    @property
    def drop_chance(self):
        all_tokens = Token.objects.all()
        total_values = sum(token.value for token in all_tokens)
        result = self.value * 100 / total_values
        return round(result, 2)

    def __str__(self):
        return f'{self.name}, drop chance: {self.drop_chance}%'


class TokenTransfer(models.Model):
    contract = models.CharField(max_length=36)
    token = models.ForeignKey(Token, on_delete=models.SET_NULL, blank=True, null=True)
    amount = models.PositiveSmallIntegerField()
    game = models.ForeignKey(GameSession, on_delete=models.SET_NULL, blank=True, null=True)
    player = models.ForeignKey(TezosUser, on_delete=models.SET_NULL, blank=True, null=True)
    date = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f'{self.token} - {self.date}'


class BossDrop(models.Model):
    level = models.PositiveSmallIntegerField()
    drop_chance = models.FloatField()

    def __str__(self):
        return f'{self.level} - {self.drop_chance}%'
