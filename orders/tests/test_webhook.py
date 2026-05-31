"""
Тесты для orders/webhooks.py

Stripe API полностью мокируется через unittest.mock —
реальных HTTP-запросов не происходит.

Покрывает:
  - Невалидный payload → 400
  - Неверная подпись → 400
  - checkout.session.completed → paid=True, variant.stock уменьшается
  - variant.stock не уходит ниже 0
  - is_available НЕ меняется при нулевом stock (Sold Out остаётся в каталоге)
  - order_id не найден → 404
  - Другие типы событий → 200, данные не меняются
  - Fallback на product.stock, если вариант не существует
"""
import json
from decimal import Decimal
from unittest.mock import patch, MagicMock

from django.test import TestCase, Client
from django.urls import reverse
from django.contrib.auth import get_user_model

from store.models import Category, Artisan, Product, ProductVariant
from orders.models import Order, OrderItem

User = get_user_model()


# ─────────────────────────── helpers ───────────────────────────

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


def make_order_with_item(product, quantity=1, size="Standard"):
    user = User.objects.create_user(username="wh_user", password="pass")
    order = Order.objects.create(
        user=user, first_name="T", last_name="U",
        email="t@example.com", city="Baku", address="123",
    )
    OrderItem.objects.create(
        order=order, product=product,
        price=product.price, quantity=quantity, size=size,
    )
    return order


def make_stripe_event(event_type, order_id):
    """Строит минимальный объект события Stripe в виде MagicMock."""
    event = MagicMock()
    event.type = event_type
    event.data.object.client_reference_id = str(order_id)
    return event


# ─────────────────────────── ошибки верификации ───────────────────────────

class WebhookVerificationTests(TestCase):
    def setUp(self):
        self.url = reverse('orders:stripe_webhook')

    @patch('orders.webhooks.stripe.Webhook.construct_event',
           side_effect=ValueError("bad payload"))
    def test_invalid_payload_returns_400(self, _mock):
        response = self.client.post(self.url, data=b'bad', content_type='application/json')
        self.assertEqual(response.status_code, 400)

    @patch('orders.webhooks.stripe.Webhook.construct_event')
    def test_invalid_signature_returns_400(self, mock_construct):
        import stripe
        mock_construct.side_effect = stripe.error.SignatureVerificationError(
            "sig error", "sig_header"
        )
        response = self.client.post(self.url, data=b'{}', content_type='application/json')
        self.assertEqual(response.status_code, 400)


# ─────────────────────────── checkout.session.completed ───────────────────────────

class WebhookCheckoutCompletedTests(TestCase):
    def setUp(self):
        self.url = reverse('orders:stripe_webhook')
        self.product = make_product()
        self.variant = make_variant(self.product, size="Standard", stock=5)
        self.order = make_order_with_item(self.product, quantity=2, size="Standard")

    def _post_event(self, event_type, order_id):
        event = make_stripe_event(event_type, order_id)
        with patch('orders.webhooks.stripe.Webhook.construct_event', return_value=event):
            with patch('orders.webhooks.send_premium_invoice'):
                return self.client.post(
                    self.url, data=b'{}', content_type='application/json'
                )

    def test_returns_200_on_success(self):
        response = self._post_event('checkout.session.completed', self.order.id)
        self.assertEqual(response.status_code, 200)

    def test_marks_order_as_paid(self):
        self._post_event('checkout.session.completed', self.order.id)
        self.order.refresh_from_db()
        self.assertTrue(self.order.paid)

    def test_decrements_variant_stock(self):
        self._post_event('checkout.session.completed', self.order.id)
        self.variant.refresh_from_db()
        # stock был 5, купили 2 → должно быть 3
        self.assertEqual(self.variant.stock, 3)

    def test_variant_stock_does_not_go_below_zero(self):
        """Если quantity > stock, stock должен остановиться на 0, не в минусе."""
        self.variant.stock = 1
        self.variant.save()
        # Купили 2, а на складе 1 → stock = max(0, 1-2) = 0
        self._post_event('checkout.session.completed', self.order.id)
        self.variant.refresh_from_db()
        self.assertEqual(self.variant.stock, 0)

    def test_is_available_stays_true_when_variant_stock_reaches_zero(self):
        """
        Товар с нулевым stock варианта остаётся is_available=True.
        Он виден в каталоге как 'Sold Out' — намеренное поведение.
        """
        self.variant.stock = 2
        self.variant.save()
        self._post_event('checkout.session.completed', self.order.id)
        self.variant.refresh_from_db()
        self.assertEqual(self.variant.stock, 0)
        self.product.refresh_from_db()
        self.assertTrue(self.product.is_available)

    def test_sends_invoice_email(self):
        event = make_stripe_event('checkout.session.completed', self.order.id)
        with patch('orders.webhooks.stripe.Webhook.construct_event', return_value=event):
            with patch('orders.webhooks.send_premium_invoice') as mock_email:
                self.client.post(self.url, data=b'{}', content_type='application/json')
                mock_email.assert_called_once_with(self.order)

    def test_nonexistent_order_returns_404(self):
        response = self._post_event('checkout.session.completed', order_id=99999)
        self.assertEqual(response.status_code, 404)

    def test_missing_order_id_returns_200_without_crash(self):
        """Если client_reference_id=None — webhook игнорирует событие."""
        event = make_stripe_event('checkout.session.completed', None)
        event.data.object.client_reference_id = None
        with patch('orders.webhooks.stripe.Webhook.construct_event', return_value=event):
            with patch('orders.webhooks.send_premium_invoice'):
                response = self.client.post(
                    self.url, data=b'{}', content_type='application/json'
                )
        self.assertEqual(response.status_code, 200)
        # Заказ не должен быть помечен оплаченным
        self.order.refresh_from_db()
        self.assertFalse(self.order.paid)

    def test_idempotent_already_paid_order(self):
        """Повторная отправка события не дублирует списание stock."""
        self.order.paid = True
        self.order.save()
        self._post_event('checkout.session.completed', self.order.id)
        self.variant.refresh_from_db()
        # stock не должен измениться — заказ уже оплачен
        self.assertEqual(self.variant.stock, 5)


class WebhookFallbackStockTests(TestCase):
    """
    Если ProductVariant для данного (product, size) не существует,
    webhook должен уменьшить product.stock (legacy-fallback).
    """
    def setUp(self):
        self.url = reverse('orders:stripe_webhook')
        artisan = Artisan.objects.create(name="A", region="Baku", description="x")
        category = Category.objects.create(name="C", slug="c-fallback")
        self.product = Product.objects.create(
            category=category, artisan=artisan,
            name="No Variant Belt", slug="no-variant-belt",
            price=Decimal("50.00"), stock=10,
        )
        user = User.objects.create_user(username="fb_user", password="pass")
        self.order = Order.objects.create(
            user=user, first_name="T", last_name="U",
            email="t@example.com", city="Baku", address="123",
        )
        OrderItem.objects.create(
            order=self.order, product=self.product,
            price=self.product.price, quantity=3, size="Standard",
        )
        # Намеренно НЕ создаём ProductVariant

    def test_fallback_decrements_product_stock(self):
        event = make_stripe_event('checkout.session.completed', self.order.id)
        with patch('orders.webhooks.stripe.Webhook.construct_event', return_value=event):
            with patch('orders.webhooks.send_premium_invoice'):
                response = self.client.post(
                    self.url, data=b'{}', content_type='application/json'
                )
        self.assertEqual(response.status_code, 200)
        self.product.refresh_from_db()
        # 10 - 3 = 7
        self.assertEqual(self.product.stock, 7)


# ─────────────────────────── другие типы событий ───────────────────────────

class WebhookOtherEventTests(TestCase):
    def setUp(self):
        self.url = reverse('orders:stripe_webhook')
        self.product = make_product(slug="other-evt-belt")
        self.variant = make_variant(self.product, stock=5)
        self.order = make_order_with_item(self.product)

    def test_other_event_returns_200(self):
        event = make_stripe_event('payment_intent.created', self.order.id)
        with patch('orders.webhooks.stripe.Webhook.construct_event', return_value=event):
            response = self.client.post(
                self.url, data=b'{}', content_type='application/json'
            )
        self.assertEqual(response.status_code, 200)

    def test_other_event_does_not_modify_order(self):
        event = make_stripe_event('payment_intent.created', self.order.id)
        with patch('orders.webhooks.stripe.Webhook.construct_event', return_value=event):
            self.client.post(self.url, data=b'{}', content_type='application/json')
        self.order.refresh_from_db()
        self.assertFalse(self.order.paid)

    def test_other_event_does_not_modify_variant_stock(self):
        stock_before = self.variant.stock
        event = make_stripe_event('payment_intent.created', self.order.id)
        with patch('orders.webhooks.stripe.Webhook.construct_event', return_value=event):
            self.client.post(self.url, data=b'{}', content_type='application/json')
        self.variant.refresh_from_db()
        self.assertEqual(self.variant.stock, stock_before)
