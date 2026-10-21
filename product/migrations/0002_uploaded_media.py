from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("product", "0001_initial"),
    ]

    operations = [
        migrations.AddField(
            model_name="category",
            name="image",
            field=models.ImageField(blank=True, upload_to="categories/%Y/%m/", verbose_name="Image"),
        ),
        migrations.AlterField(
            model_name="category",
            name="image_url",
            field=models.URLField(blank=True, help_text="Facultatif si une image est téléversée.", verbose_name="URL externe de l'image"),
        ),
        migrations.AddField(
            model_name="productmedia",
            name="image",
            field=models.ImageField(blank=True, upload_to="products/%Y/%m/", verbose_name="Image téléversée"),
        ),
        migrations.AlterField(
            model_name="productmedia",
            name="source_url",
            field=models.URLField(
                blank=True,
                help_text="Facultatif pour une image téléversée ; utile pour les vidéos ou les médias externes.",
                max_length=1000,
                verbose_name="URL externe du média",
            ),
        ),
        migrations.AddField(
            model_name="productcraftdetail",
            name="image",
            field=models.ImageField(blank=True, upload_to="products/craft/%Y/%m/", verbose_name="Image téléversée"),
        ),
        migrations.AlterField(
            model_name="productcraftdetail",
            name="image_url",
            field=models.URLField(blank=True, max_length=1000, verbose_name="URL externe de l'image"),
        ),
        migrations.AddField(
            model_name="productusage",
            name="image",
            field=models.ImageField(blank=True, upload_to="products/usage/%Y/%m/", verbose_name="Image téléversée"),
        ),
        migrations.AlterField(
            model_name="productusage",
            name="image_url",
            field=models.URLField(blank=True, max_length=1000, verbose_name="URL externe de l'image"),
        ),
    ]
