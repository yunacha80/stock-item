# Generated by Django 5.1.2 on 2025-03-02 12:49

import django.utils.timezone
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("App", "0035_remove_storeitemreference_no_price_and_more"),
    ]

    operations = [
        migrations.AddField(
            model_name="storetraveltime",
            name="created_at",
            field=models.DateTimeField(
                auto_now_add=True, default=django.utils.timezone.now
            ),
            preserve_default=False,
        ),
        migrations.AddField(
            model_name="storetraveltime",
            name="updated_at",
            field=models.DateTimeField(auto_now=True),
        ),
    ]
