# Generated by Django 4.2.4 on 2023-09-20 06:14

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('Authentication', '0001_initial'),
    ]

    operations = [
        migrations.CreateModel(
            name='Task',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('task_name', models.CharField(max_length=255)),
                ('due_date', models.DateField()),
                ('due_time', models.TimeField()),
                ('description', models.TextField()),
            ],
        ),
    ]
