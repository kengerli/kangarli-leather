from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('store', '0007_product_stock'),
    ]

    operations = [
        migrations.CreateModel(
            name='ProductVariant',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('size', models.CharField(
                    choices=[
                        ('XS', 'XS'), ('S', 'S'), ('M', 'M'),
                        ('L', 'L'), ('XL', 'XL'), ('XXL', 'XXL'),
                        ('Standard', 'Standard'),
                    ],
                    default='Standard',
                    max_length=20,
                    verbose_name='Size',
                )),
                ('stock', models.PositiveIntegerField(default=0, verbose_name='Stock')),
                ('product', models.ForeignKey(
                    on_delete=django.db.models.deletion.CASCADE,
                    related_name='variants',
                    to='store.product',
                    verbose_name='Product',
                )),
            ],
            options={
                'verbose_name': 'Product Variant',
                'verbose_name_plural': 'Product Variants',
                'unique_together': {('product', 'size')},
            },
        ),
    ]
