from django.db import models
from store.models import Product
from django.contrib.auth.models import User


class Order(models.Model):
    user = models.ForeignKey(User, on_delete=models.SET_NULL, related_name='orders', null=True, blank=True)
    first_name = models.CharField(max_length=50, verbose_name="First Name")
    last_name = models.CharField(max_length=50, verbose_name="Last Name")
    email = models.EmailField(verbose_name="Email")
    city = models.CharField(max_length=100, verbose_name="City (e.g. Baku)")
    address = models.CharField(max_length=250, verbose_name="Full Address")
    created = models.DateTimeField(auto_now_add=True, verbose_name="Created At")
    updated = models.DateTimeField(auto_now=True, verbose_name="Updated At")
    paid = models.BooleanField(default=False, verbose_name="Is Paid")
    invoice_sent = models.BooleanField(default=False, verbose_name="Invoice Emailed")

    class Meta:
        ordering = ('-created',)
        verbose_name = "Order"
        verbose_name_plural = "Orders"

    def __str__(self):
        return f"Order {self.id}"

    # Delivery: 15 AZN for orders under the free-delivery threshold
    FREE_DELIVERY_THRESHOLD = 500
    DELIVERY_FEE = 15

    def get_total_cost(self):
        return sum(item.get_cost() for item in self.items.all())

    def get_delivery_fee(self):
        if self.get_total_cost() >= self.FREE_DELIVERY_THRESHOLD:
            return 0
        return self.DELIVERY_FEE

    def get_total_with_delivery(self):
        return self.get_total_cost() + self.get_delivery_fee()


class OrderItem(models.Model):
    order = models.ForeignKey(Order, related_name='items', on_delete=models.CASCADE)
    product = models.ForeignKey(
        Product,
        related_name='order_items',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
    )
    size = models.CharField(max_length=20, default="Standard", verbose_name="Size")
    price = models.DecimalField(max_digits=10, decimal_places=2, verbose_name="Price at Purchase")
    quantity = models.PositiveIntegerField(default=1, verbose_name="Quantity")

    def __str__(self):
        return str(self.id)

    def get_cost(self):
        return self.price * self.quantity


class SalesStatistic(Order):
    class Meta:
        proxy = True 
        verbose_name = 'Sales Statistic'
        verbose_name_plural = 'Sales Statistics'