# Generated by Django 3.2.15 on 2022-08-24 07:29

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('users', '0001_initial'),
    ]

    operations = [
        migrations.AlterModelOptions(
            name='follow',
            options={'ordering': ['author'], 'verbose_name': 'Подписчик', 'verbose_name_plural': 'Подписчики'},
        ),
    ]
