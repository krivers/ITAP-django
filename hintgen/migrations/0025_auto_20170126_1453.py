# -*- coding: utf-8 -*-
# Generated by Django 1.10 on 2017-01-26 19:53
from __future__ import unicode_literals

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('hintgen', '0024_auto_20170126_1442'),
    ]

    operations = [
        migrations.AlterModelOptions(
            name='problem',
            options={'ordering': ['name']},
        ),
    ]
