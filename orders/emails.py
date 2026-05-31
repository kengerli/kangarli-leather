from django.core.mail import EmailMultiAlternatives
from django.template.loader import render_to_string
from django.conf import settings

def send_premium_invoice(order):
    """
    Функция берет готовый заказ и отправляет клиенту красивый чек.
    """
    # 1. Формируем тему письма (то, что клиент видит до открытия)
    subject = f'Kangarli Leather - Receipt for Order #{order.id}'
    
    # 2. Обычный текст (на случай, если почта клиента блокирует HTML и картинки)
    text_content = f'Howdy {order.first_name}! Your order #{order.id} is confirmed. Total: {order.get_total_cost()} AZN.'
    
    # 3. Самое главное: превращаем наш красивый HTML-шаблон в текст, 
    # передавая в него данные конкретного заказа (чтобы подставилось имя и цена)
    html_content = render_to_string('orders/email/invoice.html', {'order': order})
    
    # 4. Собираем всё в один конверт (Тема, Текст, От кого, Кому)
    # Заглушку 'heritage@kangarli.com' потом поменяем на твою реальную почту
    msg = EmailMultiAlternatives(
        subject=subject, 
        body=text_content, 
        from_email=settings.DEFAULT_FROM_EMAIL, 
        to=[order.email]
    )
    
    # 5. Прикрепляем к письму нашу красивую HTML-версию
    msg.attach_alternative(html_content, "text/html")
    
    # 6. Отправляем!
    msg.send()