from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('orders', '0004_alter_orderitem_product'),
    ]

    operations = [
        migrations.AddField(
            model_name='order',
            name='invoice_sent',
            field=models.BooleanField(default=False, verbose_name='Invoice Emailed'),
        ),
    ]
