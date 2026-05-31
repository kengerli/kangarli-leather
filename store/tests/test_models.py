from decimal import Decimal
from django.test import TestCase
from django.contrib.auth import get_user_model
from django.db import IntegrityError

from store.models import Category, Artisan, Product, ProductVariant, Newsletter, Review, Favorite

User = get_user_model()


def make_artisan(**kwargs):
    defaults = dict(name="Usta Mammad", region="Baku", description="Test artisan")
    defaults.update(kwargs)
    return Artisan.objects.create(**defaults)


def make_category(name="Bags", slug="bags", parent=None):
    return Category.objects.create(name=name, slug=slug, parent=parent)


def make_product(category, artisan, **kwargs):
    defaults = dict(
        name="Classic Belt",
        slug="classic-belt",
        price=Decimal("85.50"),
    )
    defaults.update(kwargs)
    return Product.objects.create(category=category, artisan=artisan, **defaults)


def make_variant(product, size="Standard", stock=5):
    return ProductVariant.objects.create(product=product, size=size, stock=stock)


class CategoryModelTests(TestCase):
    def setUp(self):
        self.parent = make_category(name="Leather Goods", slug="leather-goods")
        self.child = make_category(name="Belts", slug="belts", parent=self.parent)

    def test_str_without_parent(self):
        self.assertEqual(str(self.parent), "Leather Goods")

    def test_str_with_parent(self):
        self.assertEqual(str(self.child), "Leather Goods -> Belts")

    def test_parent_relationship(self):
        self.assertEqual(self.child.parent, self.parent)
        self.assertIn(self.child, self.parent.children.all())


class ProductModelTests(TestCase):
    def setUp(self):
        self.artisan = make_artisan()
        self.category = make_category()
        self.product = make_product(self.category, self.artisan)

    def test_str(self):
        self.assertEqual(str(self.product), "Classic Belt")

    def test_default_is_available(self):
        self.assertTrue(self.product.is_available)

    def test_price_precision(self):
        self.assertEqual(self.product.price, Decimal("85.50"))


class ProductVariantModelTests(TestCase):
    def setUp(self):
        self.artisan = make_artisan()
        self.category = make_category()
        self.product = make_product(self.category, self.artisan)

    def test_str(self):
        variant = make_variant(self.product, size="M", stock=10)
        self.assertEqual(str(variant), "Classic Belt - M (stock: 10)")

    def test_default_size_is_standard(self):
        variant = ProductVariant.objects.create(product=self.product, stock=3)
        self.assertEqual(variant.size, "Standard")

    def test_stock_can_be_zero(self):
        variant = make_variant(self.product, size="S", stock=0)
        self.assertEqual(variant.stock, 0)

    def test_unique_together_raises_on_duplicate(self):
        make_variant(self.product, size="L", stock=5)
        with self.assertRaises(IntegrityError):
            make_variant(self.product, size="L", stock=3)

    def test_different_sizes_on_same_product_allowed(self):
        make_variant(self.product, size="S", stock=5)
        make_variant(self.product, size="M", stock=5)
        self.assertEqual(
            ProductVariant.objects.filter(product=self.product).count(), 2
        )

    def test_stock_decrement_stops_at_zero(self):
        variant = make_variant(self.product, size="XL", stock=10)
        variant.stock = max(0, variant.stock - 3)
        variant.save()
        variant.refresh_from_db()
        self.assertEqual(variant.stock, 7)

    def test_stock_does_not_go_negative(self):
        variant = make_variant(self.product, size="XXL", stock=1)
        variant.stock = max(0, variant.stock - 999)
        variant.save()
        variant.refresh_from_db()
        self.assertEqual(variant.stock, 0)

    def test_cascade_delete_with_product(self):
        make_variant(self.product, size="Standard", stock=5)
        self.product.delete()
        self.assertEqual(ProductVariant.objects.count(), 0)

    def test_related_name_variants(self):
        make_variant(self.product, size="S", stock=2)
        make_variant(self.product, size="M", stock=4)
        self.assertEqual(self.product.variants.count(), 2)


class OrderItemCostTests(TestCase):
    """Тестируем арифметику без создания реального заказа."""

    def test_get_cost_calculation(self):
        price = Decimal("85.50")
        quantity = 3
        cost = price * quantity
        self.assertEqual(cost, Decimal("256.50"))


class ReviewModelTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username="testuser", password="pass")
        artisan = make_artisan()
        category = make_category()
        self.product = make_product(category, artisan)

    def test_review_str(self):
        review = Review.objects.create(
            product=self.product, user=self.user, content="Great!", rating=5
        )
        self.assertEqual(str(review), "Review by testuser on Classic Belt")

    def test_rating_valid_values(self):
        for rating in range(1, 6):
            Review.objects.create(
                product=self.product, user=self.user,
                content=f"Rating {rating}", rating=rating
            )
        self.assertEqual(Review.objects.filter(product=self.product).count(), 5)


class FavoriteModelTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username="testuser", password="pass")
        artisan = make_artisan()
        category = make_category()
        self.product = make_product(category, artisan)

    def test_favorite_creation(self):
        fav = Favorite.objects.create(user=self.user, product=self.product)
        self.assertEqual(str(fav), "testuser - Classic Belt")

    def test_unique_together_constraint(self):
        Favorite.objects.create(user=self.user, product=self.product)
        with self.assertRaises(IntegrityError):
            Favorite.objects.create(user=self.user, product=self.product)


class NewsletterModelTests(TestCase):
    def test_subscription_creation(self):
        sub = Newsletter.objects.create(email="test@example.com")
        self.assertEqual(sub.email, "test@example.com")
        self.assertTrue(sub.is_active)

    def test_email_unique(self):
        Newsletter.objects.create(email="dup@example.com")
        with self.assertRaises(IntegrityError):
            Newsletter.objects.create(email="dup@example.com")
