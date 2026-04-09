from django.db import migrations, models


class Migration(migrations.Migration):
    initial = True

    dependencies = []

    operations = [
        migrations.CreateModel(
            name="SensorReading",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("timestamp", models.DateTimeField()),
                ("temperature_c", models.FloatField()),
                ("humidity_pct", models.FloatField()),
                ("pressure_hpa", models.FloatField()),
                ("door_status", models.CharField(max_length=16)),
                ("light_lux", models.FloatField()),
                (
                    "fridge_type",
                    models.CharField(
                        choices=[("fridge", "Fridge"), ("freezer", "Freezer")],
                        max_length=16,
                    ),
                ),
                ("fridge_number", models.PositiveSmallIntegerField(default=1)),
            ],
            options={
                "ordering": ["-timestamp"],
            },
        ),
        migrations.AddIndex(
            model_name="sensorreading",
            index=models.Index(fields=["fridge_type", "fridge_number", "-timestamp"], name="monitor_sen_fridge__068f85_idx"),
        ),
        migrations.AddIndex(
            model_name="sensorreading",
            index=models.Index(fields=["timestamp"], name="monitor_sen_timesta_4e8385_idx"),
        ),
    ]
