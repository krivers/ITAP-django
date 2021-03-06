# -*- coding: utf-8 -*-
# Generated by Django 1.10 on 2017-01-14 23:37
from __future__ import unicode_literals

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('hintgen', '0006_auto_20170114_1328'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='anonstate',
            name='goal_state',
        ),
        migrations.RemoveField(
            model_name='anonstate',
            name='next_state',
        ),
        migrations.RemoveField(
            model_name='canonicalstate',
            name='goal_state',
        ),
        migrations.RemoveField(
            model_name='canonicalstate',
            name='next_state',
        ),
        migrations.RemoveField(
            model_name='cleanedstate',
            name='anon_state',
        ),
        migrations.RemoveField(
            model_name='sourcestate',
            name='cleaned_state',
        ),
        migrations.RemoveField(
            model_name='sourcestate',
            name='student_state',
        ),
        migrations.AddField(
            model_name='anonstate',
            name='goal',
            field=models.ForeignKey(null=True, on_delete=django.db.models.deletion.CASCADE, related_name='anon_feeder', to='hintgen.State'),
        ),
        migrations.AddField(
            model_name='anonstate',
            name='nextstep',
            field=models.ForeignKey(null=True, on_delete=django.db.models.deletion.CASCADE, related_name='anon_prev', to='hintgen.State'),
        ),
        migrations.AddField(
            model_name='canonicalstate',
            name='goal',
            field=models.ForeignKey(null=True, on_delete=django.db.models.deletion.CASCADE, related_name='canonical_feeder', to='hintgen.State'),
        ),
        migrations.AddField(
            model_name='canonicalstate',
            name='nextstep',
            field=models.ForeignKey(null=True, on_delete=django.db.models.deletion.CASCADE, related_name='canonical_prev', to='hintgen.State'),
        ),
        migrations.AddField(
            model_name='cleanedstate',
            name='anon',
            field=models.ForeignKey(null=True, on_delete=django.db.models.deletion.CASCADE, related_name='cleaned_states', to='hintgen.AnonState'),
        ),
        migrations.AddField(
            model_name='sourcestate',
            name='cleaned',
            field=models.ForeignKey(null=True, on_delete=django.db.models.deletion.CASCADE, related_name='source_states', to='hintgen.CleanedState'),
        ),
        migrations.AddField(
            model_name='sourcestate',
            name='student',
            field=models.ForeignKey(null=True, on_delete=django.db.models.deletion.CASCADE, related_name='code_states', to='hintgen.Student'),
        ),
        migrations.AlterField(
            model_name='anonstate',
            name='canonical_state',
            field=models.ForeignKey(null=True, on_delete=django.db.models.deletion.CASCADE, related_name='anon_states', to='hintgen.CanonicalState'),
        ),
    ]
