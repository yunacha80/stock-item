# Generated by Django 5.1.2 on 2024-11-27 03:15

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("App", "0020_remove_storeitemreference_unit_quantity_and_more"),
    ]

    operations = [
        migrations.AlterField(
            model_name="storeitemreference",
            name="price",
            field=models.IntegerField(blank=True, null=True),
        ),
        migrations.AlterField(
            model_name="storeitemreference",
            name="price_per_unit",
            field=models.FloatField(blank=True, null=True),
        ),
    ]
