from django.http import HttpResponse
from django.views.decorators.http import require_GET

@require_GET
def robots_txt(request):
    """
    Представление, которое отдает файл robots.txt.
    """
    lines = [
        "User-agent: *",           # Для всех роботов
        "Disallow: /admin/",      # Скрыть админку
        "Disallow: /accounts/",   # Скрыть профили пользователей
        "Disallow: /cart/",       # Скрыть корзину
        "Disallow: /search?",     # Скрыть поиск/фильтры
        "",
        "# Разрешить индексацию статики",
        "Allow: /static/",
        "",
        "# Плейсхолдер для будущего ситмапа",
        "# Sitemap: https://kangarli.az/sitemap.xml", # Заменишь на реальный домен
    ]
    content = "\n".join(lines)
    return HttpResponse(content, content_type="text/plain; charset=utf-8")