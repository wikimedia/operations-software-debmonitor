# Generated by Django 2.1.15 on 2020-01-14 11:32

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('images', '0001_initial'),
    ]

    operations = [
        migrations.AddIndex(
            model_name='imagepackage',
            index=models.Index(fields=['upgrade_type', 'upgradable_imagepackage'],
                               name='images_imag_upgrade_6e9cd5_idx'),
        ),
    ]