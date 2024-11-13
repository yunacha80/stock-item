# Generated by Django 5.1.2 on 2024-11-13 00:31

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("App", "0008_store_travel_time_home_min"),
    ]

    operations = [
        migrations.AlterField(
            model_name="item",
            name="name",
            field=models.CharField(max_length=50),
        ),
        migrations.AlterField(
            model_name="store",
            name="travel_time_home_min",
            field=models.IntegerField(
                default=0, verbose_name="自宅からの移動時間（分）"
            ),
        ),
        migrations.CreateModel(
            name="StoreTravelTime",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                ("travel_time_min", models.IntegerField(verbose_name="移動時間（分）")),
                (
                    "store1",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="store1_travel_times",
                        to="App.store",
                    ),
                ),
                (
                    "store2",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="store2_travel_times",
                        to="App.store",
                    ),
                ),
                (
                    "store_from",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="travel_from",
                        to="App.store",
                        verbose_name="出発店舗",
                    ),
                ),
                (
                    "store_to",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="travel_to",
                        to="App.store",
                        verbose_name="到着店舗",
                    ),
                ),
            ],
            options={
                "unique_together": {("store_from", "store_to")},
            },
        ),
    ]
