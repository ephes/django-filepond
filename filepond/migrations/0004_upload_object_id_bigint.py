from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [("filepond", "0003_auto_20181127_0938")]

    operations = [
        migrations.AlterField(
            model_name="upload",
            name="object_id",
            field=models.PositiveBigIntegerField(blank=True, null=True),
        ),
    ]
