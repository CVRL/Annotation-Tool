# Generated by Django 3.0.7 on 2023-06-15 18:27

from django.db import migrations
from backend.api.manual_migration import import_dataset


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        ('api', '0003_profile'),
    ]

    operations = [

        migrations.RunPython(import_dataset, reverse_code=migrations.RunPython.noop)
        
    ]