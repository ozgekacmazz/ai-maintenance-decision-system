from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("tahminler", "0007_tahminreddi"),
    ]

    operations = [
        migrations.AddField(
            model_name="bakimkararisnapshot",
            name="genel_oncelik",
            field=models.PositiveSmallIntegerField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name="bakimkararisnapshot",
            name="genel_oncelik_formul_surumu",
            field=models.CharField(blank=True, max_length=100, null=True),
        ),
        migrations.AddField(
            model_name="bakimkararisnapshot",
            name="ham_genel_oncelik",
            field=models.DecimalField(
                blank=True, decimal_places=4, max_digits=6, null=True
            ),
        ),
        migrations.AddField(
            model_name="bakimkararisnapshot",
            name="stok_katsayisi",
            field=models.DecimalField(
                blank=True, decimal_places=2, max_digits=3, null=True
            ),
        ),
        migrations.AddConstraint(
            model_name="bakimkararisnapshot",
            constraint=models.CheckConstraint(
                condition=models.Q(("genel_oncelik__isnull", True))
                | models.Q(("genel_oncelik__gte", 1), ("genel_oncelik__lte", 5)),
                name="karar_genel_oncelik_1_5",
            ),
        ),
        migrations.AddConstraint(
            model_name="bakimkararisnapshot",
            constraint=models.CheckConstraint(
                condition=models.Q(("stok_katsayisi__isnull", True))
                | models.Q(("stok_katsayisi__gte", 1), ("stok_katsayisi__lte", 2)),
                name="karar_stok_katsayisi_1_2",
            ),
        ),
        migrations.AddConstraint(
            model_name="bakimkararisnapshot",
            constraint=models.CheckConstraint(
                condition=models.Q(("ham_genel_oncelik__isnull", True))
                | models.Q(
                    ("ham_genel_oncelik__gte", 0),
                    ("ham_genel_oncelik__lte", 10),
                ),
                name="karar_ham_genel_oncelik_0_10",
            ),
        ),
        migrations.AddConstraint(
            model_name="bakimkararisnapshot",
            constraint=models.CheckConstraint(
                condition=models.Q(
                    ("genel_oncelik__isnull", True),
                    ("genel_oncelik_formul_surumu__isnull", True),
                    ("ham_genel_oncelik__isnull", True),
                    ("stok_katsayisi__isnull", True),
                )
                | models.Q(
                    ("genel_oncelik__isnull", False),
                    ("genel_oncelik_formul_surumu__isnull", False),
                    ("ham_genel_oncelik__isnull", False),
                    ("stok_katsayisi__isnull", False),
                ),
                name="karar_canonical_alanlar_birlikte",
            ),
        ),
        migrations.AddConstraint(
            model_name="bakimkararisnapshot",
            constraint=models.CheckConstraint(
                condition=models.Q(("genel_oncelik_formul_surumu__isnull", True))
                | ~models.Q(("genel_oncelik_formul_surumu", "")),
                name="karar_formul_surumu_bos_degil",
            ),
        ),
    ]
