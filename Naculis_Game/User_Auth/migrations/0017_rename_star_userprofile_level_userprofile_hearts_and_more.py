# Generated by Django 5.2.4 on 2025-07-17 09:35

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('User_Auth', '0016_customuser_role'),
    ]

    operations = [
        migrations.RenameField(
            model_name='userprofile',
            old_name='star',
            new_name='level',
        ),
        migrations.AddField(
            model_name='userprofile',
            name='hearts',
            field=models.IntegerField(default=5),
        ),
        migrations.AlterField(
            model_name='userprofile',
            name='xp',
            field=models.IntegerField(default=0),
        ),
    ]
