# Generated by Django 5.1.2 on 2024-11-13 18:51

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("App", "0009_alter_item_name_alter_store_travel_time_home_min_and_more"),
    ]

    operations = [
        migrations.AlterUniqueTogether(
            name="storetraveltime",
            unique_together=set(),
        ),
        migrations.AddConstraint(
            model_name="storetraveltime",
            constraint=models.UniqueConstraint(
                fields=("store1", "store2"), name="unique_store_travel_time"
            ),
        ),
        migrations.RemoveField(
            model_name="storetraveltime",
            name="store_from",
        ),
        migrations.RemoveField(
            model_name="storetraveltime",
            name="store_to",
        ),
    ]
