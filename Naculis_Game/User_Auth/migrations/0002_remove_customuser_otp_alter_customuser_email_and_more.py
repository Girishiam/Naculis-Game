# Generated by Django 4.2.14 on 2025-07-11 07:35

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("User_Auth", "0001_initial"),
    ]

    operations = [
        migrations.RemoveField(
            model_name="customuser",
            name="otp",
        ),
        migrations.AlterField(
            model_name="customuser",
            name="email",
            field=models.EmailField(max_length=254, unique=True),
        ),
        migrations.AlterField(
            model_name="customuser",
            name="phone",
            field=models.CharField(max_length=15),
        ),
    ]
