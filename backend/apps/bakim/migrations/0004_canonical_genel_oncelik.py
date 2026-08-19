from django.db import migrations, models
from django.db.models import Q


class Migration(migrations.Migration):
    dependencies = [
        ("bakim", "0003_bakimisemri_isemriolayi_and_more"),
    ]

    operations = [
        migrations.AddField(
            model_name="bakimisemri",
            name="kaynak_genel_oncelik",
            field=models.PositiveSmallIntegerField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name="bakimisemri",
            name="kaynak_genel_oncelik_formul_surumu",
            field=models.CharField(blank=True, max_length=100, null=True),
        ),
        migrations.AddField(
            model_name="bakimisemri",
            name="etkin_genel_oncelik",
            field=models.PositiveSmallIntegerField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name="isemriolayi",
            name="onceki_genel_oncelik",
            field=models.PositiveSmallIntegerField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name="isemriolayi",
            name="yeni_genel_oncelik",
            field=models.PositiveSmallIntegerField(blank=True, null=True),
        ),
        migrations.AddConstraint(
            model_name="bakimisemri",
            constraint=models.CheckConstraint(
                condition=Q(kaynak_genel_oncelik__isnull=True)
                | Q(kaynak_genel_oncelik__range=(1, 5)),
                name="is_emri_kaynak_genel_1_5",
            ),
        ),
        migrations.AddConstraint(
            model_name="bakimisemri",
            constraint=models.CheckConstraint(
                condition=Q(etkin_genel_oncelik__isnull=True)
                | Q(etkin_genel_oncelik__range=(1, 5)),
                name="is_emri_etkin_genel_1_5",
            ),
        ),
        migrations.AddConstraint(
            model_name="bakimisemri",
            constraint=models.CheckConstraint(
                condition=(
                    Q(kaynak_genel_oncelik__isnull=True)
                    & Q(kaynak_genel_oncelik_formul_surumu__isnull=True)
                    & Q(etkin_genel_oncelik__isnull=True)
                )
                | (
                    Q(kaynak_genel_oncelik__isnull=False)
                    & Q(kaynak_genel_oncelik_formul_surumu__isnull=False)
                    & Q(etkin_genel_oncelik__isnull=False)
                ),
                name="is_emri_genel_oncelik_birlikte",
            ),
        ),
        migrations.AddConstraint(
            model_name="bakimisemri",
            constraint=models.CheckConstraint(
                condition=Q(kaynak_genel_oncelik_formul_surumu__isnull=True)
                | ~Q(kaynak_genel_oncelik_formul_surumu=""),
                name="is_emri_genel_formul_bos_degil",
            ),
        ),
        migrations.AddConstraint(
            model_name="isemriolayi",
            constraint=models.CheckConstraint(
                condition=Q(onceki_genel_oncelik__isnull=True)
                | Q(onceki_genel_oncelik__range=(1, 5)),
                name="is_emri_olay_onceki_genel_1_5",
            ),
        ),
        migrations.AddConstraint(
            model_name="isemriolayi",
            constraint=models.CheckConstraint(
                condition=Q(yeni_genel_oncelik__isnull=True)
                | Q(yeni_genel_oncelik__range=(1, 5)),
                name="is_emri_olay_yeni_genel_1_5",
            ),
        ),
        migrations.AddConstraint(
            model_name="isemriolayi",
            constraint=models.CheckConstraint(
                condition=(
                    Q(onceki_genel_oncelik__isnull=True)
                    & Q(yeni_genel_oncelik__isnull=True)
                )
                | (
                    Q(onceki_genel_oncelik__isnull=False)
                    & Q(yeni_genel_oncelik__isnull=False)
                ),
                name="is_emri_olay_genel_birlikte",
            ),
        ),
    ]
