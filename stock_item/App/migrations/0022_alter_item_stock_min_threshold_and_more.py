# Generated by Django 5.1.2 on 2024-11-27 05:33

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("App", "0021_alter_storeitemreference_price_and_more"),
    ]

    operations = [
        migrations.AlterField(
            model_name="item",
            name="stock_min_threshold",
            field=models.IntegerField(default=1),
        ),
        migrations.AlterField(
            model_name="item",
            name="stock_quantity",
            field=models.IntegerField(default=0),
        ),
    ]
