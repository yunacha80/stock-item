# Generated by Django 5.1.2 on 2024-11-25 07:40

import django.db.models.deletion
import django.utils.timezone
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("App", "0019_remove_storeprice_item_alter_store_name"),
    ]

    operations = [
        migrations.RemoveField(
            model_name="storeitemreference",
            name="unit_quantity",
        ),
        migrations.AddField(
            model_name="category",
            name="created_at",
            field=models.DateTimeField(
                auto_now_add=True, default=django.utils.timezone.now
            ),
            preserve_default=False,
        ),
        migrations.AddField(
            model_name="category",
            name="updated_at",
            field=models.DateTimeField(auto_now=True),
        ),
        migrations.AddField(
            model_name="storeitemreference",
            name="created_at",
            field=models.DateTimeField(
                auto_now_add=True, default=django.utils.timezone.now
            ),
            preserve_default=False,
        ),
        migrations.AddField(
            model_name="storeitemreference",
            name="price_per_unit",
            field=models.FloatField(default=0),
            preserve_default=False,
        ),
        migrations.AddField(
            model_name="storeitemreference",
            name="updated_at",
            field=models.DateTimeField(auto_now=True),
        ),
        migrations.AlterField(
            model_name="item",
            name="category",
            field=models.ForeignKey(
                default=1,
                on_delete=django.db.models.deletion.CASCADE,
                to="App.category",
            ),
            preserve_default=False,
        ),
        migrations.AlterField(
            model_name="item",
            name="memo",
            field=models.CharField(blank=True, max_length=100, null=True),
        ),
        migrations.AlterField(
            model_name="item",
            name="stock_quantity",
            field=models.IntegerField(),
        ),
        migrations.AlterField(
            model_name="store",
            name="address",
            field=models.CharField(blank=True, max_length=200, null=True),
        ),
        migrations.AlterField(
            model_name="store",
            name="phone_number",
            field=models.CharField(blank=True, max_length=20, null=True),
        ),
        migrations.AlterField(
            model_name="storeitemreference",
            name="item",
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.CASCADE, to="App.item"
            ),
        ),
        migrations.AlterField(
            model_name="storeitemreference",
            name="memo",
            field=models.CharField(blank=True, max_length=100, null=True),
        ),
        migrations.AlterField(
            model_name="storeitemreference",
            name="price",
            field=models.IntegerField(default=1),
            preserve_default=False,
        ),
        migrations.AlterField(
            model_name="storeitemreference",
            name="store",
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.CASCADE, to="App.store"
            ),
        ),
        migrations.DeleteModel(
            name="StorePrice",
        ),
    ]
