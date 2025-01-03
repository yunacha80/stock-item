# Generated by Django 5.1.2 on 2024-11-10 13:21

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("App", "0006_purchasehistory"),
    ]

    operations = [
        migrations.AlterField(
            model_name="item",
            name="name",
            field=models.CharField(max_length=100),
        ),
        migrations.AlterField(
            model_name="purchasehistory",
            name="item",
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.CASCADE,
                related_name="purchase_histories",
                to="App.item",
            ),
        ),
    ]
