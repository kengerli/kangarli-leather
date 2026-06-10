from django.core.mail import EmailMultiAlternatives
from django.template.loader import render_to_string
from django.conf import settings

def send_premium_invoice(order):
    """
    Takes a completed order and sends a beautiful invoice to the customer.
    """
    # 1. Form the email subject (what the customer sees before opening)
    subject = f'Kangarli Leather - Receipt for Order #{order.id}'
    
    # 2. Plain text (in case the customer's email blocks HTML and images)
    text_content = f'Howdy {order.first_name}! Your order #{order.id} is confirmed. Total: {order.get_total_cost()} AZN.'
    
    # 3. Most important: convert our beautiful HTML template to text,
    # passing the specific order data to it (so the name and price are substituted)
    html_content = render_to_string('orders/email/invoice.html', {'order': order})
    
    # 4. Pack everything into one envelope (Subject, Text, From, To)
    msg = EmailMultiAlternatives(
        subject=subject, 
        body=text_content, 
        from_email=settings.DEFAULT_FROM_EMAIL, 
        to=[order.email]
    )
    
    # 5. Attach our HTML version to the email
    msg.attach_alternative(html_content, "text/html")
    
    # 6. Send it!
    msg.send()