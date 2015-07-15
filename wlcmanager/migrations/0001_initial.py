# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
    ]

    operations = [
        migrations.CreateModel(
            name='AccessPoint',
            fields=[
                ('number', models.IntegerField(serialize=False, primary_key=True)),
                ('fingerprint', models.CharField(max_length=64)),
                ('model', models.CharField(max_length=16, choices=[('WLA321-WW', 'WLA321-WW'), ('WLA322-WW', 'WLA322-WW'), ('MP_432', 'MP-432')])),
                ('name', models.CharField(unique=True, max_length=64)),
                ('serial_number', models.CharField(unique=True, max_length=16)),
                ('description', models.CharField(unique=True, max_length=128)),
                ('location', models.CharField(unique=True, max_length=128)),
                ('radio_1_channel', models.IntegerField(default=0, help_text='0 = auto')),
                ('radio_1_power', models.IntegerField(default=0, help_text='0 = auto')),
                ('radio_1_enable', models.BooleanField(default=True)),
                ('radio_2_channel', models.IntegerField(default=0, null=True, blank=True)),
                ('radio_2_power', models.IntegerField(default=0, null=True, blank=True)),
                ('radio_2_enable', models.BooleanField(default=False)),
            ],
            options={
                'ordering': ['name'],
            },
        ),
        migrations.CreateModel(
            name='AutoAccessPoint',
            fields=[
                ('serial_number', models.CharField(max_length=64, serialize=False, primary_key=True)),
                ('fingerprint', models.CharField(max_length=64)),
                ('number', models.IntegerField(verbose_name='AP number')),
                ('model', models.CharField(max_length=16)),
                ('ip_address', models.GenericIPAddressField(unique=True, verbose_name='IP address')),
            ],
            options={
                'ordering': ['serial_number'],
            },
        ),
        migrations.CreateModel(
            name='RadioProfile',
            fields=[
                ('name', models.CharField(max_length=64, serialize=False, primary_key=True)),
            ],
        ),
        migrations.CreateModel(
            name='WLC',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('name', models.CharField(unique=True, max_length=64)),
                ('ip_address', models.GenericIPAddressField(unique=True, verbose_name='IP address')),
                ('username', models.CharField(max_length=64)),
                ('password', models.CharField(max_length=64)),
                ('enabled', models.BooleanField(default=True)),
                ('master', models.BooleanField(default=False)),
            ],
            options={
                'ordering': ['name'],
                'verbose_name': 'WLC',
            },
        ),
        migrations.AddField(
            model_name='autoaccesspoint',
            name='wlc',
            field=models.ForeignKey(verbose_name='WLC', to='wlcmanager.WLC'),
        ),
        migrations.AddField(
            model_name='accesspoint',
            name='radio_1_profile',
            field=models.ForeignKey(related_name='+', to='wlcmanager.RadioProfile'),
        ),
        migrations.AddField(
            model_name='accesspoint',
            name='radio_2_profile',
            field=models.ForeignKey(related_name='+', blank=True, to='wlcmanager.RadioProfile', null=True),
        ),
    ]
