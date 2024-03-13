# Generated by Django 5.0 on 2024-03-13 16:59

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('api', '0011_achievement_type'),
    ]

    operations = [
        migrations.AddField(
            model_name='gamesession',
            name='favourite_weapon',
            field=models.CharField(blank=True, max_length=64, null=True),
        ),
        migrations.AddField(
            model_name='gamesession',
            name='mobs_killed',
            field=models.IntegerField(default=0),
        ),
        migrations.AddField(
            model_name='gamesession',
            name='score',
            field=models.IntegerField(default=0),
        ),
        migrations.AddField(
            model_name='gamesession',
            name='shots_fired',
            field=models.IntegerField(default=0),
        ),
    ]