# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('wlcmanager', '0002_add_high_latency'),
    ]

    operations = [
        migrations.AlterField(
            model_name='accesspoint',
            name='radio_1_profile',
            field=models.ForeignKey(related_name='+', on_delete=django.db.models.deletion.PROTECT, to='wlcmanager.RadioProfile'),
        ),
        migrations.AlterField(
            model_name='accesspoint',
            name='radio_2_profile',
            field=models.ForeignKey(related_name='+', on_delete=django.db.models.deletion.PROTECT, blank=True, to='wlcmanager.RadioProfile', null=True),
        ),
    ]
