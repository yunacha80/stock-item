# Generated by Django 5.1.2 on 2024-12-06 14:02

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ("App", "0023_remove_category_user_itemcategory_and_more"),
    ]

    operations = [
        migrations.RenameModel(
            old_name="ItemCategory",
            new_name="Category",
        ),
    ]