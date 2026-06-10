# Extends ProductVariant size choices to cover every size offered by the
# cart form (letter sizes, shoe 39-45, ring 15-22, belt 85-105 cm, hats).

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('store', '0008_productvariant'),
    ]

    operations = [
        migrations.AlterField(
            model_name='productvariant',
            name='size',
            field=models.CharField(choices=[('Standard', 'Standard'), ('XS', 'XS'), ('S', 'S'), ('M', 'M'), ('L', 'L'), ('XL', 'XL'), ('XXL', 'XXL'), ('15', 'Shoe/Ring 15'), ('16', 'Shoe/Ring 16'), ('17', 'Shoe/Ring 17'), ('18', 'Shoe/Ring 18'), ('19', 'Shoe/Ring 19'), ('20', 'Shoe/Ring 20'), ('21', 'Shoe/Ring 21'), ('22', 'Shoe/Ring 22'), ('39', 'Size 39'), ('40', 'Size 40'), ('41', 'Size 41'), ('42', 'Size 42'), ('43', 'Size 43'), ('44', 'Size 44'), ('45', 'Size 45'), ('85', '85 cm'), ('90', '90 cm'), ('95', '95 cm'), ('100', '100 cm'), ('105', '105 cm')], default='Standard', max_length=20, verbose_name='Size'),
        ),
    ]
