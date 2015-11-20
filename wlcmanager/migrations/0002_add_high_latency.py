# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models

from django.conf import settings
try:
    HIGHLATENCY_DEFAULT = settings.WLCMANAGER_HIGHLATENCY_DEFAULT
except AttributeError:
    HIGHLATENCY_DEFAULT = False

class Migration(migrations.Migration):

    dependencies = [
        ('wlcmanager', '0001_initial'),
    ]

    operations = [
        migrations.AddField(
            model_name='accesspoint',
            name='high_latency',
            field=models.BooleanField(default=HIGHLATENCY_DEFAULT),
        ),
        migrations.AlterField(
            model_name='accesspoint',
            name='model',
            field=models.CharField(max_length=16, choices=[('WLA321-WW', 'WLA321-WW'), ('WLA322-WW', 'WLA322-WW'), ('MP_432', 'MP-432'), ('MP_522', 'MP-522')]),
        ),
    ]
