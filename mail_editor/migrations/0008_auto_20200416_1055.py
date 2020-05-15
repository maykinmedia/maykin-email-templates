# Generated by Django 2.2.8 on 2020-04-16 08:55

from django.db import migrations



def set_null(apps, schema_editor):
    """
    Set the base_template_path of templates which don't have one to None
    """
    MailTemplate = apps.get_model("mail_editor", "MailTemplate")

    for template in MailTemplate.objects.all():
        if template.base_template_path:
            continue

        template.base_template_path = None
        template.save()


class Migration(migrations.Migration):

    dependencies = [
        ("mail_editor", "0007_auto_20200415_1513"),
    ]

    operations = [
        migrations.RunPython(set_null)
    ]