"""
Test settings — наследует боевые настройки, но отключает всё что мешает тестам.
Запуск: python manage.py test --settings=core.settings_test store.tests orders.tests
"""
from core.settings import *  # noqa: F401, F403

# Axes ломает self.client.login() в тестах (требует request в authenticate).
# В тестах используем только стандартный Django-бэкенд.
AUTHENTICATION_BACKENDS = [
    'django.contrib.auth.backends.ModelBackend',
]

# Убираем AxesMiddleware из цепочки
MIDDLEWARE = [m for m in MIDDLEWARE if 'axes' not in m.lower()]

# Быстрый хэшер паролей — ускоряет тесты в ~10x
PASSWORD_HASHERS = [
    'django.contrib.auth.hashers.MD5PasswordHasher',
]

# Отключаем rate-limiting для тестов
AXES_ENABLED = False
RATELIMIT_ENABLE = False

# Email в памяти — не шлём реальных писем
EMAIL_BACKEND = 'django.core.mail.backends.locmem.EmailBackend'

STORAGES = {
    "staticfiles": {
        "BACKEND": "django.contrib.staticfiles.storage.StaticFilesStorage",
    },
    "default": {
        "BACKEND": "django.core.files.storage.FileSystemStorage",
    },
}