from pathlib import Path
import os
from dotenv import load_dotenv
import dj_database_url

load_dotenv()

# Build paths inside the project like this: BASE_DIR / 'subdir'.
BASE_DIR = Path(__file__).resolve().parent.parent

SECRET_KEY = os.getenv('SECRET_KEY')
DEBUG = os.getenv('DEBUG', 'False') == 'True'
ALLOWED_HOSTS = ['localhost', '127.0.0.1', '.ngrok-free.app', '.onrender.com']
CSRF_TRUSTED_ORIGINS = ['https://*.ngrok-free.app', 'https://*.onrender.com']

# Application definition

INSTALLED_APPS = [
    'jazzmin',
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'cloudinary_storage',
    'cloudinary',
    'store',
    'cart',
    'orders',
    'account',
    'axes',
    'django_ratelimit',
]

# Silence django-ratelimit's allowlist check for DatabaseCache.
# Django's DatabaseCache.incr() is atomic (uses SELECT FOR UPDATE),
# so rate limiting works correctly even though it's not in ratelimit's
# official list. Switch CACHES to RedisCache in production for best performance.
SILENCED_SYSTEM_CHECKS = ['django_ratelimit.E003', 'django_ratelimit.W001']

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'whitenoise.middleware.WhiteNoiseMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
    'axes.middleware.AxesMiddleware',
]

ROOT_URLCONF = 'core.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
                'django.template.context_processors.csrf',
            ],
        },
    },
]

WSGI_APPLICATION = 'core.wsgi.application'


# Database
# https://docs.djangoproject.com/en/6.0/ref/settings/#databases

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': BASE_DIR / 'db.sqlite3',
    }
}

if os.getenv('DATABASE_URL'):
    DATABASES['default'] = dj_database_url.config(
        default=os.getenv('DATABASE_URL'),
        conn_max_age=600,
        conn_health_checks=True,
    )


# Cache — used by django-ratelimit
# Redis (preferred for production): set REDIS_URL in .env
# Fallback: database cache (supports atomic increment, no extra services needed)
REDIS_URL = os.getenv('CACHE_URL') or os.getenv('REDIS_URL')
if REDIS_URL:
    CACHES = {
        'default': {
            'BACKEND': 'django.core.cache.backends.redis.RedisCache',
            'LOCATION': REDIS_URL,
        }
    }
else:
    CACHES = {
        'default': {
            'BACKEND': 'django.core.cache.backends.db.DatabaseCache',
            'LOCATION': 'cache_table',  # run: python manage.py createcachetable
        }
    }


# Password validation
# https://docs.djangoproject.com/en/6.0/ref/settings/#auth-password-validators

AUTH_PASSWORD_VALIDATORS = [
    {
        'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator',
    },
]


AUTHENTICATION_BACKENDS = [
    'axes.backends.AxesBackend', # First, Axes checks the lock
    'django.contrib.auth.backends.ModelBackend', # Then the standard input works
]

# Internationalization
# https://docs.djangoproject.com/en/6.0/topics/i18n/


LANGUAGE_CODE = 'en-us'

TIME_ZONE = 'UTC'

USE_I18N = True

USE_TZ = True


# Static files (CSS, JavaScript, Images)
# https://docs.djangoproject.com/en/6.0/howto/static-files/

STATIC_URL = 'static/'

# Папка, куда Django соберет ВСЮ статику перед запуском на сервере
STATIC_ROOT = BASE_DIR / 'staticfiles'

# Твоя текущая папка с кастомной статикой (мы ее настраивали ранее)
STATICFILES_DIRS = [
    BASE_DIR / 'project pictures',
]

# Включаем кэширование и сжатие файлов (сайт будет летать)
MEDIA_URL = '/media/'

# Проверяем, есть ли ключ от Cloudinary в файле .env
if os.getenv('CLOUDINARY_URL'):
    # Настройки для сервера (сохраняем картинки в облако)
    STORAGES = {
        "default": {
            "BACKEND": "cloudinary_storage.storage.MediaCloudinaryStorage",
        },
        "staticfiles": {
            "BACKEND": "whitenoise.storage.CompressedStaticFilesStorage",
        },
    }
else:
    # Fallback for local development (no Cloudinary)
    MEDIA_ROOT = os.path.join(BASE_DIR, 'media/')
    STORAGES = {
        "default": {
            "BACKEND": "django.core.files.storage.FileSystemStorage",
        },
        "staticfiles": {
            "BACKEND": "whitenoise.storage.CompressedStaticFilesStorage",
        },
    }

# Global project variables
SITE_NAME = 'Kangarli Leather'

# Key for storing the cart in the user session
CART_SESSION_ID = 'cart'


# Where to redirect after login/logout
LOGIN_REDIRECT_URL = 'store:product_list'
LOGOUT_REDIRECT_URL = 'store:product_list'

LOGIN_URL = 'account:login'

# CSRF Configuration for AJAX requests
CSRF_COOKIE_HTTPONLY = False
CSRF_COOKIE_SECURE = False  # Set to True in production with HTTPS

if not DEBUG:
    #SECURE_SSL_REDIRECT = True
    SESSION_COOKIE_SECURE = True
    CSRF_COOKIE_SECURE = True
    SECURE_HSTS_SECONDS = 31536000
    SECURE_HSTS_INCLUDE_SUBDOMAINS = True
    SECURE_HSTS_PRELOAD = True

# --- AXES SETTINGS ---
AXES_FAILURE_LIMIT = 8            # Number of attempts before lockout
AXES_COOL_OFF_TIME = 0.25         # Lockout time in hours (can use fractions: 0.25 = 15 min)
AXES_RESET_ON_SUCCESS = True      # Reset counter after successful login
AXES_LOCKOUT_TEMPLATE = 'store/lockout.html'  

# --- STRIPE SETTINGS ---
STRIPE_PUBLISHABLE_KEY = os.getenv('STRIPE_PUBLISHABLE_KEY')
STRIPE_SECRET_KEY = os.getenv('STRIPE_SECRET_KEY')
STRIPE_WEBHOOK_SECRET = os.getenv('STRIPE_WEBHOOK_SECRET')


# --- GROQ SETTINGS ---
GROQ_API_KEY = os.getenv('GROQ_API_KEY', '')

# --- EMAIL SETTINGS ---
EMAIL_BACKEND = 'django.core.mail.backends.smtp.EmailBackend'
EMAIL_HOST = 'smtp.gmail.com'
EMAIL_PORT = 587
EMAIL_USE_TLS = True
# Fail fast if the SMTP host is unreachable (e.g. Render free tier blocks
# outbound SMTP). Without this the socket hangs until gunicorn kills the
# worker (WORKER TIMEOUT -> 500). 10s < gunicorn's 30s timeout, so the
# webhook's try/except can catch it and still return 200.
EMAIL_TIMEOUT = 10
EMAIL_HOST_USER = os.getenv('EMAIL_HOST_USER', '')
EMAIL_HOST_PASSWORD = os.getenv('EMAIL_HOST_PASSWORD', '')
DEFAULT_FROM_EMAIL = os.getenv('DEFAULT_FROM_EMAIL', EMAIL_HOST_USER)
CONTACT_EMAIL = os.getenv('CONTACT_EMAIL', EMAIL_HOST_USER)
