# Generated by Django 5.1.2 on 2025-03-28 20:38

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ("App", "0038_alter_storeitemreference_unique_together"),
    ]

    operations = [
        migrations.AlterUniqueTogether(
            name="storeitemreference",
            unique_together={("store", "item")},
        ),
    ]
