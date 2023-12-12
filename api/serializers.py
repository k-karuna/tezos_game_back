from rest_framework import serializers
from api.models import TezosUser


class TezosUserSerializer(serializers.ModelSerializer):
    class Meta:
        model = TezosUser
        fields = ('payload',)
