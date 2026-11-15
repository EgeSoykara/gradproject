from django.db import migrations, models


def mark_existing_archive_example(apps, schema_editor):
    apps.get_model('portfolio', 'Portfolio').objects.filter(
        user__username='demo', dataset='live', name='Arşiv veri örneği',
    ).update(archive_prices=True)


class Migration(migrations.Migration):
    dependencies = [('portfolio', '0002_note_fund')]

    operations = [
        migrations.AddField(
            model_name='portfolio', name='archive_prices',
            field=models.BooleanField(default=False),
        ),
        migrations.RunPython(mark_existing_archive_example, migrations.RunPython.noop),
    ]
