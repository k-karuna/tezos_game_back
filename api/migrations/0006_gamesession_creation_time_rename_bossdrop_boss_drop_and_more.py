# Generated by Django 5.0 on 2024-01-10 15:49

import django.db.models.deletion
import django.utils.timezone
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('api', '0005_bossdrop_token_tokentransfer_delete_transferedtoken'),
    ]

    operations = [
        migrations.AddField(
            model_name='gamesession',
            name='creation_time',
            field=models.DateTimeField(auto_now_add=True, default=django.utils.timezone.now),
            preserve_default=False,
        ),
        migrations.RenameModel(
            old_name='BossDrop',
            new_name='Boss',
        ),
        migrations.CreateModel(
            name='Drop',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('transfer_date', models.DateTimeField(blank=True, null=True)),
                ('boss', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, to='api.boss')),
                ('dropped_token', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, to='api.token')),
                ('game', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, to='api.gamesession')),
            ],
        ),
        migrations.DeleteModel(
            name='TokenTransfer',
        ),
    ]
