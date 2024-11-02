# Generated by Django 5.1.2 on 2024-11-02 15:56

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("App", "0004_alter_item_price_category"),
    ]

    operations = [
        migrations.AlterField(
            model_name="item",
            name="category",
            field=models.ForeignKey(
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                to="App.category",
            ),
        ),
        migrations.DeleteModel(
            name="ItemCategory",
        ),
    ]