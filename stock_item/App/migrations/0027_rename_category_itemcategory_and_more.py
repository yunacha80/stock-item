# Generated by Django 5.1.2 on 2024-12-10 20:27

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ("App", "0026_rename_itemcategory_category_alter_category_table"),
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
