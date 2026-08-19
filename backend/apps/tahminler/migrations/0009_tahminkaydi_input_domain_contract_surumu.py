from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [("tahminler", "0008_bakimkararisnapshot_canonical_genel_oncelik")]
    operations = [
        migrations.AddField(
            model_name="tahminkaydi",
            name="input_domain_contract_surumu",
            field=models.CharField(blank=True, max_length=100, null=True),
        )
    ]
