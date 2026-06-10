from django.db import models
from django.utils import timezone
from django.conf import settings


class Category(models.Model):
    parent = models.ForeignKey('self', related_name='children', on_delete=models.CASCADE, blank=True, null=True)
    name = models.CharField(max_length=200)
    slug = models.SlugField(max_length=200, unique=True)

    class Meta:
        ordering = ['name']
        indexes = [
            models.Index(fields=['name']),
        ]
        verbose_name = 'category'
        verbose_name_plural = 'categories'

    def __str__(self):
        if self.parent:
            return f'{self.parent.name} -> {self.name}'
        return self.name


class Artisan(models.Model):
    name = models.CharField(max_length=150, verbose_name="Name or Brand")
    region = models.CharField(max_length=100, verbose_name="Region", help_text="e.g., Baku, Sheki")
    description = models.TextField(verbose_name="Artisan Description")

    class Meta:
        verbose_name = "Artisan"
        verbose_name_plural = "Artisans"

    def __str__(self):
        return self.name


class Product(models.Model):
    category = models.ForeignKey(Category, on_delete=models.CASCADE, related_name='products', verbose_name="Category")
    artisan = models.ForeignKey(Artisan, on_delete=models.CASCADE, related_name='products', verbose_name="Artisan")
    name = models.CharField(max_length=200, verbose_name="Product Name")
    slug = models.SlugField(max_length=200, unique=True)
    description = models.TextField(blank=True, verbose_name="Description")
    price = models.DecimalField(max_digits=10, decimal_places=2, verbose_name="Price (AZN)")
    image = models.ImageField(upload_to='products/%Y/%m/%d', blank=True, verbose_name="Image")
    is_available = models.BooleanField(default=True, verbose_name="Is Available")
    created = models.DateTimeField(auto_now_add=True, verbose_name="Date Added")
    # Legacy stock field — kept as fallback; manage stock via ProductVariant
    stock = models.PositiveIntegerField(default=1, verbose_name='Stock Quantity')

    class Meta:
        verbose_name = "Product"
        verbose_name_plural = "Products"
        ordering = ('-created',)

    def __str__(self):
        return self.name

    @property
    def available_stock(self):
        """
        Real sellable stock: the sum of variant stocks when variants exist,
        otherwise the legacy per-product stock field.
        """
        variant_total = self.variants.aggregate(total=models.Sum('stock'))['total']
        if variant_total is not None:
            return variant_total
        return self.stock


class ProductVariant(models.Model):
    # Must cover every size the cart form can offer
    # (letter sizes, shoe 39–45, ring 15–22, belt 85–105, hats)
    SIZE_CHOICES = (
        [('Standard', 'Standard')]
        + [(s, s) for s in ('XS', 'S', 'M', 'L', 'XL', 'XXL')]
        + [(str(i), f'Shoe/Ring {i}') for i in range(15, 23)]
        + [(str(i), f'Size {i}') for i in range(39, 46)]
        + [(str(i), f'{i} cm') for i in range(85, 110, 5)]
    )
    product = models.ForeignKey(
        Product,
        on_delete=models.CASCADE,
        related_name='variants',
        verbose_name='Product',
    )
    size = models.CharField(
        max_length=20,
        choices=SIZE_CHOICES,
        default='Standard',
        verbose_name='Size',
    )
    stock = models.PositiveIntegerField(default=0, verbose_name='Stock')

    class Meta:
        unique_together = ('product', 'size')
        verbose_name = 'Product Variant'
        verbose_name_plural = 'Product Variants'

    def __str__(self):
        return f'{self.product.name} - {self.size} (stock: {self.stock})'


class Newsletter(models.Model):
    email = models.EmailField(unique=True)
    subscribed_at = models.DateTimeField(auto_now_add=True)
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ['-subscribed_at']

    def __str__(self):
        return self.email


class Review(models.Model):
    product = models.ForeignKey(Product, related_name='reviews', on_delete=models.CASCADE)
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    content = models.TextField(verbose_name="Review text")
    rating = models.IntegerField(choices=[(i, i) for i in range(1, 6)], default=5)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f'Review by {self.user.username} on {self.product.name}'


class Favorite(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='favorites')
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name='favorited_by')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('user', 'product')
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.user.username} - {self.product.name}"
