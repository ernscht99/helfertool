# Generated by Django 4.2.13 on 2024-06-27 20:35

from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("registration", "0066_rename_unlimted_shift_unlimited"),
    ]

    operations = [
        migrations.AlterField(
            model_name="shift",
            name="unlimited",
            field=models.BooleanField(default=False, verbose_name="This shift has an unlimited number of helpers"),
        ),
    ]