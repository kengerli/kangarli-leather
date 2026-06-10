"""
Tests for orders/views.py
"""
import datetime
from decimal import Decimal

from django.test import TestCase, Client
from django.urls import reverse
from django.contrib.auth import get_user_model
from django.utils import timezone

from store.models import Category, Artisan, Product, ProductVariant
from orders.models import Order, OrderItem

User = get_user_model()
CART_SESSION_KEY = 'cart'


def make_user(username="buyer", password="testpass123"):
    return User.objects.create_user(username=username, password=password)


def make_product(name="Belt", slug="belt", price="85.50"):
    artisan = Artisan.objects.create(name="A", region="Baku", description="x")
    category = Category.objects.create(name="C", slug=f"c-{slug}")
    return Product.objects.create(
        category=category, artisan=artisan,
        name=name, slug=slug,
        price=Decimal(price),
    )


def make_variant(product, size="Standard", stock=5):
    return ProductVariant.objects.create(product=product, size=size, stock=stock)


def make_order(user, paid=False, created_offset_days=0):
    order = Order.objects.create(
        user=user,
        first_name="Test", last_name="User",
        email="test@example.com",
        city="Baku", address="123 Main St",
        paid=paid,
    )
    if created_offset_days:
        Order.objects.filter(pk=order.pk).update(
            created=timezone.now() - datetime.timedelta(days=created_offset_days)
        )
        order.refresh_from_db()
    return order


class OrderCreateAuthTests(TestCase):
    def test_redirects_to_login_if_not_authenticated(self):
        response = self.client.get(reverse("orders:order_create"))
        self.assertEqual(response.status_code, 302)
        self.assertIn("/login", response["Location"])


class OrderCreateTests(TestCase):
    def setUp(self):
        self.client = Client()
        self.user = make_user()
        self.client.login(username="buyer", password="testpass123")
        self.product = make_product()
        self.variant = make_variant(self.product, size="Standard", stock=5)

    def _add_to_cart(self, product, quantity=1, size="Standard"):
        session = self.client.session
        session[CART_SESSION_KEY] = {
            f"{product.id}_{size}": {
                "quantity": quantity,
                "price": str(product.price),
                "size": size,
                "product_id": str(product.id),
            }
        }
        session.save()

    def test_empty_cart_redirects_to_product_list(self):
        response = self.client.get(reverse("orders:order_create"))
        self.assertRedirects(response, reverse("store:product_list"),
                             fetch_redirect_response=False)

    def test_get_shows_form_when_cart_not_empty(self):
        self._add_to_cart(self.product)
        response = self.client.get(reverse("orders:order_create"))
        self.assertEqual(response.status_code, 200)
        self.assertIn("form", response.context)

    def test_post_creates_order_and_items(self):
        self._add_to_cart(self.product, quantity=2)
        data = {
            "first_name": "Fikret", "last_name": "Kangarli",
            "email": "f@example.com", "city": "Baku", "address": "123 Street",
        }
        response = self.client.post(reverse("orders:order_create"), data)
        self.assertRedirects(response, reverse("orders:payment_process"),
                             fetch_redirect_response=False)
        order = Order.objects.get(user=self.user)
        self.assertEqual(order.first_name, "Fikret")
        self.assertEqual(order.items.count(), 1)
        self.assertEqual(order.items.first().quantity, 2)

    def test_post_sets_order_id_in_session(self):
        self._add_to_cart(self.product)
        data = {"first_name": "Fikret", "last_name": "K",
                "email": "f@example.com", "city": "Baku", "address": "123"}
        self.client.post(reverse("orders:order_create"), data)
        order = Order.objects.get(user=self.user)
        self.assertEqual(self.client.session.get("order_id"), order.id)

    def test_invalid_form_does_not_create_order(self):
        self._add_to_cart(self.product)
        response = self.client.post(reverse("orders:order_create"), {})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(Order.objects.count(), 0)


class PaymentDoneTests(TestCase):
    def setUp(self):
        self.client = Client()
        self.user = make_user()
        self.client.login(username="buyer", password="testpass123")
        self.product = make_product()
        self.variant = make_variant(self.product, size="Standard", stock=3)
        self.order = make_order(self.user)
        OrderItem.objects.create(
            order=self.order, product=self.product,
            price=self.product.price, quantity=2, size="Standard",
        )
        session = self.client.session
        session["order_id"] = self.order.id
        session[CART_SESSION_KEY] = {
            f"{self.product.id}_Standard": {
                "quantity": 2, "price": str(self.product.price),
                "size": "Standard", "product_id": str(self.product.id),
            }
        }
        session.save()

    def test_returns_200(self):
        response = self.client.get(reverse("orders:payment_done"))
        self.assertEqual(response.status_code, 200)

    def test_clears_cart_from_session(self):
        self.client.get(reverse("orders:payment_done"))
        self.assertNotIn(CART_SESSION_KEY, self.client.session)

    def test_removes_order_id_from_session(self):
        self.client.get(reverse("orders:payment_done"))
        self.assertNotIn("order_id", self.client.session)

    def test_does_not_modify_variant_stock(self):
        """payment_done не трогает stock — это зона webhook."""
        stock_before = self.variant.stock
        self.client.get(reverse("orders:payment_done"))
        self.variant.refresh_from_db()
        self.assertEqual(self.variant.stock, stock_before)

    def test_does_not_mark_order_paid(self):
        """payment_done не отмечает заказ оплаченным — это зона webhook."""
        self.client.get(reverse("orders:payment_done"))
        self.order.refresh_from_db()
        self.assertFalse(self.order.paid)

    def test_works_without_order_id_in_session(self):
        session = self.client.session
        if "order_id" in session:
            del session["order_id"]
            session.save()
        response = self.client.get(reverse("orders:payment_done"))
        self.assertEqual(response.status_code, 200)


class UserOrdersTests(TestCase):
    def setUp(self):
        self.client = Client()
        self.user = make_user()
        self.client.login(username="buyer", password="testpass123")

    def test_requires_login(self):
        self.client.logout()
        response = self.client.get(reverse("orders:user_orders"))
        self.assertEqual(response.status_code, 302)

    def test_shows_only_own_orders(self):
        other = make_user(username="other", password="pass")
        make_order(self.user)
        make_order(other)
        response = self.client.get(reverse("orders:user_orders"))
        self.assertEqual(len(list(response.context["orders"])), 1)

    # def test_unpaid_order_has_ship_stage_0(self):
    #     make_order(self.user, paid=False)
    #     response = self.client.get(reverse("orders:user_orders"))
    #     self.assertEqual(list(response.context["orders"])[0].ship_stage, 0)

    def test_paid_fresh_order_has_ship_stage_1(self):
        make_order(self.user, paid=True, created_offset_days=0)
        response = self.client.get(reverse("orders:user_orders"))
        self.assertEqual(list(response.context["orders"])[0].ship_stage, 1)

    def test_paid_3day_old_order_has_ship_stage_3(self):
        make_order(self.user, paid=True, created_offset_days=3)
        response = self.client.get(reverse("orders:user_orders"))
        self.assertEqual(list(response.context["orders"])[0].ship_stage, 3)

    def test_paid_old_order_has_ship_stage_4(self):
        make_order(self.user, paid=True, created_offset_days=6)
        response = self.client.get(reverse("orders:user_orders"))
        self.assertEqual(list(response.context["orders"])[0].ship_stage, 4)

    def test_pagination_5_per_page(self):
        for i in range(7):
            make_order(self.user)
        response = self.client.get(reverse("orders:user_orders"))
        self.assertEqual(len(response.context["orders"]), 5)

    def test_second_page(self):
        for i in range(7):
            make_order(self.user)
        response = self.client.get(reverse("orders:user_orders") + "?page=2")
        self.assertEqual(len(response.context["orders"]), 2)
