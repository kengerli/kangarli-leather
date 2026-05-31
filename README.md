# Kangarli Leather — E-Commerce Marketplace

A full-featured e-commerce platform for handcrafted Azerbaijani leather goods, built with Django.

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
git clone https://github.com/your-username/kangarli-leather.git
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

## Author

**Fikret Kangarli** — [GitHub](https://github.com/kengerli) · [LinkedIn](https://linkedin.com/in/your-profile)
