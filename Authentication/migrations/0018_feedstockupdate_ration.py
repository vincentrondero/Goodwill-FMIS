# Generated by Django 4.2.4 on 2023-10-17 12:22

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('Authentication', '0017_feedstockupdate'),
    ]

    operations = [
        migrations.AddField(
            model_name='feedstockupdate',
            name='ration',
            field=models.CharField(default='Starter', max_length=255),
        ),
    ]