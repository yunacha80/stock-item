# Generated by Django 5.1.2 on 2024-12-10 20:14

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ("App", "0024_rename_itemcategory_category"),
    ]

    operations = [
        migrations.RenameModel(
            old_name="Category",
            new_name="ItemCategory",
        ),
        migrations.AlterModelTable(
            name="itemcategory",
            table="App_category",
        ),
    ]