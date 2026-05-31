"""
Tests for account/ — registration, dashboard, settings.
"""
from django.test import TestCase, Client
from django.urls import reverse
from django.contrib.auth import get_user_model
from django.contrib.auth import SESSION_KEY

from store.models import Category, Artisan, Product, Favorite
from orders.models import Order

User = get_user_model()


def make_user(username="testuser", password="testpass123", **kwargs):
    return User.objects.create_user(username=username, password=password, **kwargs)


def make_product():
    artisan = Artisan.objects.create(name="A", region="Baku", description="x")
    category = Category.objects.create(name="C", slug="c-test")
    return Product.objects.create(
        category=category, artisan=artisan,
        name="Belt", slug="belt", price="85.00",
    )


# ────────────────────────── Registration ──────────────────────────

class RegisterViewTests(TestCase):
    def setUp(self):
        self.url = reverse("account:register")
        self.valid_data = {
            "username": "newuser",
            "first_name": "New",
            "email": "new@example.com",
            "password": "securepass123",
            "password_repeat": "securepass123",
        }

    def test_get_shows_form(self):
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)
        self.assertIn("user_form", response.context)

    def test_valid_post_creates_user(self):
        self.client.post(self.url, self.valid_data)
        self.assertTrue(User.objects.filter(username="newuser").exists())

    def test_valid_post_logs_user_in(self):
        self.client.post(self.url, self.valid_data)
        self.assertIn(SESSION_KEY, self.client.session)

    def test_valid_post_redirects_to_dashboard(self):
        response = self.client.post(self.url, self.valid_data)
        self.assertRedirects(response, reverse("account:dashboard"),
                             fetch_redirect_response=False)

    def test_next_param_redirect(self):
        url = self.url + "?next=/cart/"
        response = self.client.post(url, self.valid_data)
        self.assertRedirects(response, "/cart/", fetch_redirect_response=False)

    def test_password_mismatch_does_not_create_user(self):
        data = {**self.valid_data, "password_repeat": "wrongpass"}
        self.client.post(self.url, data)
        self.assertFalse(User.objects.filter(username="newuser").exists())

    def test_password_mismatch_shows_form_error(self):
        data = {**self.valid_data, "password_repeat": "wrongpass"}
        response = self.client.post(self.url, data)
        self.assertEqual(response.status_code, 200)
        self.assertFormError(response.context["user_form"],
                             "password_repeat", "Passwords do not match.")

    def test_duplicate_username_rejected(self):
        make_user(username="newuser")
        response = self.client.post(self.url, self.valid_data)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(User.objects.filter(username="newuser").count(), 1)

    def test_empty_post_does_not_create_user(self):
        self.client.post(self.url, {})
        self.assertEqual(User.objects.count(), 0)


# ────────────────────────── Dashboard ──────────────────────────

class DashboardViewTests(TestCase):
    def setUp(self):
        self.user = make_user()
        self.client.login(username="testuser", password="testpass123")
        self.url = reverse("account:dashboard")

    def test_requires_login(self):
        self.client.logout()
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 302)
        self.assertIn("/login", response["Location"])

    def test_returns_200_for_authenticated(self):
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)

    def test_shows_own_orders(self):
        Order.objects.create(
            user=self.user, first_name="T", last_name="U",
            email="t@example.com", city="Baku", address="123",
        )
        response = self.client.get(self.url)
        self.assertEqual(response.context["orders"].count(), 1)

    def test_does_not_show_other_users_orders(self):
        other = make_user(username="other")
        Order.objects.create(
            user=other, first_name="O", last_name="U",
            email="o@example.com", city="Baku", address="456",
        )
        response = self.client.get(self.url)
        self.assertEqual(response.context["orders"].count(), 0)

    def test_shows_own_favorites(self):
        product = make_product()
        Favorite.objects.create(user=self.user, product=product)
        response = self.client.get(self.url)
        self.assertEqual(response.context["favorites"].count(), 1)

    def test_empty_dashboard_has_no_orders_or_favorites(self):
        response = self.client.get(self.url)
        self.assertEqual(response.context["orders"].count(), 0)
        self.assertEqual(response.context["favorites"].count(), 0)


# ────────────────────────── Settings ──────────────────────────

class SettingsViewTests(TestCase):
    def setUp(self):
        self.user = make_user(
            first_name="Old", last_name="Name", email="old@example.com"
        )
        self.client.login(username="testuser", password="testpass123")
        self.url = reverse("account:settings")

    def test_requires_login(self):
        self.client.logout()
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 302)

    def test_get_returns_200(self):
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)
        self.assertIn("form", response.context)

    def test_get_form_prefilled_with_current_data(self):
        response = self.client.get(self.url)
        form = response.context["form"]
        self.assertEqual(form.initial.get("first_name") or form["first_name"].value(),
                         "Old")

    def test_valid_post_updates_profile(self):
        self.client.post(self.url, {
            "first_name": "Updated",
            "last_name": "User",
            "email": "new@example.com",
        })
        self.user.refresh_from_db()
        self.assertEqual(self.user.first_name, "Updated")
        self.assertEqual(self.user.email, "new@example.com")

    def test_valid_post_redirects_back(self):
        response = self.client.post(self.url, {
            "first_name": "X", "last_name": "Y", "email": "x@example.com",
        })
        self.assertRedirects(response, self.url, fetch_redirect_response=False)

    def test_invalid_post_does_not_update(self):
        self.client.post(self.url, {"email": "not-an-email"})
        self.user.refresh_from_db()
        self.assertEqual(self.user.email, "old@example.com")


# ────────────────────────── Logged out page ──────────────────────────

class LoggedOutPageTests(TestCase):
    def test_returns_200(self):
        response = self.client.get(reverse("account:logged_out_page"))
        self.assertEqual(response.status_code, 200)
