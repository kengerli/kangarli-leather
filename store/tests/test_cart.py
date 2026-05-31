from decimal import Decimal
from django.test import TestCase, RequestFactory
from django.contrib.sessions.backends.db import SessionStore
from django.contrib.auth import get_user_model

from store.models import Category, Artisan, Product, ProductVariant
from cart.cart import Cart

User = get_user_model()


def make_request_with_session():
    """Возвращает request-подобный объект с реальной сессией."""
    factory = RequestFactory()
    request = factory.get('/')
    request.session = SessionStore()
    request.session.create()
    return request


def make_product(name="Belt", slug="belt", price="85.50"):
    artisan = Artisan.objects.create(name="Artisan", region="Baku", description="x")
    category = Category.objects.create(name="Cat", slug=f"cat-{slug}")
    return Product.objects.create(
        category=category, artisan=artisan,
        name=name, slug=slug,
        price=Decimal(price),
    )


def make_variant(product, size="Standard", stock=5):
    return ProductVariant.objects.create(product=product, size=size, stock=stock)


class CartAddTests(TestCase):
    def setUp(self):
        self.request = make_request_with_session()
        self.product = make_product()
        self.variant = make_variant(self.product, size="Standard", stock=5)

    def test_add_product_appears_in_cart(self):
        cart = Cart(self.request)
        cart.add(self.product, quantity=1, size="Standard")
        self.assertEqual(len(cart), 1)

    def test_add_respects_stock_limit(self):
        """Нельзя добавить больше, чем есть на складе варианта."""
        cart = Cart(self.request)
        returned_qty = cart.add(self.product, quantity=999, size="Standard")
        self.assertEqual(returned_qty, self.variant.stock)
        self.assertEqual(len(cart), self.variant.stock)

    def test_add_accumulates_quantity(self):
        cart = Cart(self.request)
        cart.add(self.product, quantity=2, size="Standard")
        cart.add(self.product, quantity=2, size="Standard")
        # 2+2=4, stock=5 → должно быть 4
        self.assertEqual(len(cart), 4)

    def test_add_accumulation_capped_by_variant_stock(self):
        cart = Cart(self.request)
        cart.add(self.product, quantity=3, size="Standard")
        cart.add(self.product, quantity=3, size="Standard")
        # 3+3=6, но stock=5 → должно быть 5
        self.assertEqual(len(cart), self.variant.stock)

    def test_add_override_quantity(self):
        cart = Cart(self.request)
        cart.add(self.product, quantity=3, size="Standard")
        cart.add(self.product, quantity=2, size="Standard", override_quantity=True)
        self.assertEqual(len(cart), 2)

    def test_add_override_capped_by_variant_stock(self):
        """override_quantity тоже не может превысить stock варианта."""
        cart = Cart(self.request)
        returned_qty = cart.add(self.product, quantity=999, size="Standard",
                                override_quantity=True)
        self.assertEqual(returned_qty, self.variant.stock)

    def test_different_sizes_are_separate_items(self):
        make_variant(self.product, size="S", stock=10)
        make_variant(self.product, size="M", stock=10)
        cart = Cart(self.request)
        cart.add(self.product, quantity=1, size="S")
        cart.add(self.product, quantity=1, size="M")
        # Два разных ключа, суммарно 2 единицы
        self.assertEqual(len(cart), 2)

    def test_fallback_to_product_stock_when_no_variant(self):
        """Если вариант не существует, cart использует product.stock."""
        product = make_product(name="NoVariant", slug="no-variant", price="50.00")
        product.stock = 3
        product.save()
        # Намеренно не создаём вариант
        cart = Cart(self.request)
        returned_qty = cart.add(product, quantity=999, size="Standard")
        self.assertEqual(returned_qty, product.stock)


class CartRemoveTests(TestCase):
    def setUp(self):
        self.request = make_request_with_session()
        self.product = make_product()
        self.variant = make_variant(self.product, size="Standard", stock=5)

    def test_remove_existing_item(self):
        cart = Cart(self.request)
        cart.add(self.product, quantity=2, size="Standard")
        cart.remove(f"{self.product.id}_Standard")
        self.assertEqual(len(cart), 0)

    def test_remove_nonexistent_key_does_not_crash(self):
        cart = Cart(self.request)
        cart.remove("999_Standard")  # не должно бросать исключение
        self.assertEqual(len(cart), 0)


class CartTotalTests(TestCase):
    def setUp(self):
        self.request = make_request_with_session()

    def test_get_total_price(self):
        p1 = make_product(name="Belt", slug="belt-1", price="100.00")
        p2 = make_product(name="Bag", slug="bag-1", price="200.00")
        make_variant(p1, stock=10)
        make_variant(p2, stock=10)
        cart = Cart(self.request)
        cart.add(p1, quantity=2, size="Standard")
        cart.add(p2, quantity=1, size="Standard")
        # 2×100 + 1×200 = 400
        self.assertEqual(cart.get_total_price(), Decimal("400.00"))

    def test_empty_cart_total(self):
        cart = Cart(self.request)
        self.assertEqual(cart.get_total_price(), Decimal("0.00"))


class CartClearTests(TestCase):
    def setUp(self):
        self.request = make_request_with_session()
        self.product = make_product()
        self.variant = make_variant(self.product, stock=5)

    def test_clear_empties_cart(self):
        cart = Cart(self.request)
        cart.add(self.product, quantity=2, size="Standard")
        cart.clear()
        # После clear() корзины в сессии нет — новый Cart будет пустым
        new_cart = Cart(self.request)
        self.assertEqual(len(new_cart), 0)
