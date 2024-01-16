from django.db import models
from api.utils import get_payload_for_sign, get_uuid_hash


class TezosUser(models.Model):
    address = models.CharField(max_length=36, blank=True, null=True)
    public_key = models.CharField(max_length=64, blank=True, null=True)
    payload = models.CharField(max_length=128, default=get_payload_for_sign)
    signature = models.CharField(max_length=128, blank=True, null=True)
    success_sign = models.BooleanField(default=False)
    registration_date = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.address


class Boss(models.Model):
    level = models.PositiveSmallIntegerField()
    drop_chance = models.FloatField()

    def __str__(self):
        return f'{self.level} - {self.drop_chance}%'


class GameSession(models.Model):
    CREATED = 0
    ENDED = 1
    ABANDONED = 2
    PAUSED = 3
    GAME_STATUS = [
        (CREATED, "Created"),
        (ENDED, "Ended"),
        (ABANDONED, "Abandoned"),
        (PAUSED, "Paused"),
    ]

    hash = models.CharField(max_length=32, default=get_uuid_hash, unique=True)
    player = models.ForeignKey(TezosUser, on_delete=models.SET_NULL, blank=True, null=True)
    status = models.PositiveSmallIntegerField(choices=GAME_STATUS, default=CREATED)
    creation_time = models.DateTimeField(auto_now_add=True)
    pause_init_time = models.DateTimeField(blank=True, null=True)
    seconds_on_pause = models.PositiveIntegerField(default=0)

    def __str__(self):
        return f'{self.creation_time} - {self.player}'


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


class Drop(models.Model):
    game = models.ForeignKey(GameSession, on_delete=models.SET_NULL, blank=True, null=True)
    boss = models.ForeignKey(Boss, on_delete=models.SET_NULL, blank=True, null=True)
    boss_killed = models.BooleanField(default=False)
    dropped_token = models.ForeignKey(Token, on_delete=models.SET_NULL, blank=True, null=True)
    transfer_date = models.DateTimeField(blank=True, null=True)

    @property
    def token_transfered(self):
        return self.transfer_date is not None

    def __str__(self):
        return f'{self.game}, {self.dropped_token}'
