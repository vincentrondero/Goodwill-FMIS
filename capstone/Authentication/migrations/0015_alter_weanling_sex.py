# Generated by Django 4.2.4 on 2023-10-11 06:35

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('Authentication', '0014_weanling'),
    ]

    operations = [
        migrations.AlterField(
            model_name='weanling',
            name='sex',
            field=models.CharField(choices=[('male', 'Male'), ('female', 'Female')], max_length=10),
        ),
    ]