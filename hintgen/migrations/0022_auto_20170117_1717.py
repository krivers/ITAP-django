# -*- coding: utf-8 -*-
# Generated by Django 1.10 on 2017-01-17 22:17
from __future__ import unicode_literals

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('hintgen', '0021_auto_20170117_1257'),
    ]

    operations = [
        migrations.RenameField(
            model_name='anonstate',
            old_name='canonical_state',
            new_name='canonical',
        ),
    ]
