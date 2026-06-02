# Kangarli Leather — E-Commerce Marketplace

A full-featured e-commerce platform for handcrafted Azerbaijani leather goods, built with Django.

**Live demo:** https://kangarli-leather.onrender.com

---

## Screenshots

| Product Catalog | AI Stylist — Fiko |
|---|---|
| ![Catalog](docs/screenshots/catalog.png) | ![AI Stylist](docs/screenshots/ai-stylist.png) |

| Product Detail | Order Successful |
|---|---|
| ![Product](docs/screenshots/product-detail.png) | ![Payment](docs/screenshots/payment-success.png) |

---

## Features

- **Product catalog** — categories, artisan profiles, search, filtering, pagination
- **Per-size stock management** — `ProductVariant` model prevents overselling per size
- **Shopping cart** — session-based, stock-capped at add time
- **Stripe Checkout + Webhooks** — stock deduction and order fulfillment happen exclusively in the webhook to prevent double-processing
- **User accounts** — registration, login (with brute-force lockout), order history with delivery stage tracking
- **AI Stylist** — Groq-powered (LLaMA) chat assistant for product recommendations
- **Favorites & Reviews** — verified-purchase-only reviews
- **Newsletter** subscription
- **Admin panel** — Jazzmin theme with inline variant management
- **Rate limiting** — django-axes + django-ratelimit on login and order endpoints
- **Cloudinary** media storage

---

## Tech Stack

| Layer | Technology |
|---|---|
| Backend | Django 6, Python |
| Database | PostgreSQL (production) / SQLite (local) |
| Payments | Stripe Checkout + Webhooks |
| Media | Cloudinary |
| AI | Groq API (LLaMA 3.1) |
| Auth security | django-axes |
| Static files | WhiteNoise |
| Deployment | Render |

---

## Project Structure

```
heritage_project/
├── store/      # Products, categories, artisans, reviews, AI stylist
├── orders/     # Order creation, Stripe payment processing, webhooks
├── cart/       # Session-based shopping cart with variant stock enforcement
├── account/    # Registration, login, dashboard, user settings
└── core/       # Settings, URLs
```

---

## Getting Started

### 1. Clone & set up environment

```bash
git clone https://github.com/kengerli/kangarli-leather.git
cd kangarli-leather/heritage_project
python -m venv venv
venv\Scripts\activate      # Windows
# source venv/bin/activate  # macOS/Linux
pip install -r requirements.txt
```

### 2. Configure environment variables

```bash
cp .env.example .env
```

Edit `.env` with your values:

```env
SECRET_KEY=your-django-secret-key
DEBUG=True

# Leave empty to use SQLite locally
DATABASE_URL=

# Stripe (use test keys for local dev)
STRIPE_PUBLISHABLE_KEY=pk_test_...
STRIPE_SECRET_KEY=sk_test_...
STRIPE_WEBHOOK_SECRET=whsec_...

# Cloudinary
CLOUDINARY_URL=cloudinary://api_key:api_secret@cloud_name

# Groq AI
GROQ_API_KEY=gsk_...

# Gmail SMTP
EMAIL_HOST_USER=your@gmail.com
EMAIL_HOST_PASSWORD=your-app-password
DEFAULT_FROM_EMAIL=Kangarli Leather <your@gmail.com>
CONTACT_EMAIL=your@gmail.com
```

### 3. Run migrations & create admin

```bash
python manage.py migrate
python manage.py createsuperuser
python manage.py runserver
```

### 4. Forward Stripe webhooks locally

```bash
stripe listen --forward-to localhost:8000/orders/webhook/
```

Copy the `whsec_...` key it prints into your `.env` as `STRIPE_WEBHOOK_SECRET`.

### 5. Run tests

```bash
python manage.py test orders.tests.test_webhook orders.tests.test_views store.tests.test_cart store.tests.test_models --settings=core.settings_test -v 2
```

---

## Key Design Decisions

**Webhook-only fulfillment** — `paid=True` and stock deduction happen exclusively in the Stripe webhook, not in the redirect handler. This prevents double-processing when both fire simultaneously.

**Sold Out ≠ Hidden** — products with zero stock stay visible in the catalog with a "Sold Out" badge. Removing them would break SEO and returning-customer links.

**Stock cap at cart level** — `Cart.add()` enforces the variant stock limit on every add, so users can never place an order for more units than exist. The variant is checked first, with a fallback to the legacy `product.stock` field.

**Verified-purchase reviews** — the review form is only shown to users who have a paid `OrderItem` for that product.

---

## Architecture & Data Model

The project follows Django's app-per-domain convention. Each app owns its own models, views, URLs, forms, templates and tests, and communicates with the others only through model relationships — there are no cross-app imports of view logic.

| App | Responsibility | Key models |
|---|---|---|
| `store` | Catalog, search, reviews, favorites, AI stylist | `Category`, `Artisan`, `Product`, `ProductVariant`, `Review`, `Favorite`, `Newsletter` |
| `cart` | Session-based shopping cart (no DB model) | — (cart lives in the session via the `Cart` class) |
| `orders` | Checkout, Stripe payment, fulfillment | `Order`, `OrderItem` |
| `account` | Registration, login, dashboard | uses Django's built-in `User` |
| `core` | Project settings, root URLs, shared views | — |

### Entity relationships

- **`Category` → self** (`parent`/`children`) — a self-referencing `ForeignKey` gives a two-level category tree (e.g. *Accessories → Wallets*).
- **`Product` → `Category`** and **`Product` → `Artisan`** — every product belongs to one category and one artisan (`ForeignKey`, `related_name='products'`).
- **`ProductVariant` → `Product`** — one product has many size variants, each with its own stock. `unique_together = ('product', 'size')` prevents duplicate sizes. This is the source of truth for stock; `Product.stock` is kept only as a legacy fallback.
- **`Review` → `Product` / `User`** and **`Favorite` → `Product` / `User`** — `Favorite` uses `unique_together = ('user', 'product')` so a product can't be favorited twice.
- **`Order` → `User`** (`on_delete=SET_NULL`, so deleting a user keeps the order record) and **`OrderItem` → `Order` / `Product`** — `OrderItem` snapshots `price` and `size` at purchase time, so later price or stock changes never alter historical orders.

### Request flow (checkout)

1. User adds a variant to the session cart (`cart.Cart.add`, stock-capped).
2. Checkout creates an unpaid `Order` + `OrderItem`s and redirects to **Stripe Checkout**.
3. Stripe calls the **webhook** (`orders/webhook/`), which is the *only* place that sets `paid=True` and deducts `ProductVariant.stock` — preventing double-processing if the redirect and webhook race.
4. A confirmation email is sent and the order appears in the user's history with delivery-stage tracking.

### Design choices

- **ORM efficiency** — list and detail views use `select_related('category', 'artisan')` and `prefetch_related` to avoid N+1 queries; `Category` and `Product` carry DB indexes on frequently filtered fields.
- **Security** — `django-axes` locks out brute-force login attempts, `django-ratelimit` throttles login and order endpoints, secrets are read from environment variables, and `DEBUG=False` in production.
- **Stateless cart** — keeping the cart in the session (not the DB) keeps anonymous browsing fast and avoids orphaned cart rows.

---

## Author

**Fikret Kangarli** — [GitHub](https://github.com/kengerli) · [LinkedIn](https://linkedin.com/in/your-profile)
