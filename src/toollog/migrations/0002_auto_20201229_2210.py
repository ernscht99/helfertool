# Generated by Django 3.1.4 on 2020-12-29 21:10

import django.core.serializers.json
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('toollog', '0001_initial'),
    ]

    operations = [
        migrations.AlterField(
            model_name='logentry',
            name='extras',
            field=models.JSONField(blank=True, encoder=django.core.serializers.json.DjangoJSONEncoder, null=True, verbose_name='Extra data'),
        ),
    ]