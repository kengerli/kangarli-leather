import stripe
import datetime
from django.conf import settings
from django.db import transaction
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.urls import reverse
from django.core.mail import EmailMultiAlternatives
from django.template.loader import render_to_string
from django.utils import timezone
from django.core.paginator import Paginator
from django_ratelimit.decorators import ratelimit

from .models import OrderItem, Order
from .forms import OrderCreateForm
from .emails import send_premium_invoice
from cart.cart import Cart

stripe.api_key = settings.STRIPE_SECRET_KEY


# 10 order submissions per minute per authenticated user
@login_required
@ratelimit(key='user', rate='10/m', method='POST', block=True)
def order_create(request):
    cart = Cart(request)
    if len(cart) == 0:
        return redirect('store:product_list')

    if request.method == 'POST':
        form = OrderCreateForm(request.POST)
        if form.is_valid():
            with transaction.atomic():
                order = form.save(commit=False)
                order.user = request.user
                order.save()

                OrderItem.objects.bulk_create([
                    OrderItem(
                        order=order,
                        product=item['product'],
                        price=item['price'],
                        quantity=item['quantity'],
                        size=item['size'],
                    )
                    for item in cart
                ])

            request.session['order_id'] = order.id
            return redirect('orders:payment_process')
    else:
        form = OrderCreateForm(initial={
            'first_name': request.user.first_name,
            'last_name': request.user.last_name,
            'email': request.user.email,
        })

    return render(request, 'orders/order/create.html', {'cart': cart, 'form': form})


@login_required
def payment_process(request):
    order_id = request.session.get('order_id')
    order = get_object_or_404(Order, id=order_id, user=request.user)

    if request.method == 'POST':
        success_url = request.build_absolute_uri(reverse('orders:payment_done'))
        cancel_url = request.build_absolute_uri(reverse('store:product_list'))

        line_items = []
        subtotal = 0
        for item in order.items.all():
            if item.product is None:
                continue
            line_items.append({
                'price_data': {
                    'currency': 'azn',
                    'unit_amount': int(item.price * 100),
                    'product_data': {'name': item.product.name},
                },
                'quantity': item.quantity,
            })
            subtotal += item.price * item.quantity

        # Delivery fee: free above the threshold (single source of truth: Order)
        if subtotal < Order.FREE_DELIVERY_THRESHOLD:
            line_items.append({
                'price_data': {
                    'currency': 'azn',
                    'unit_amount': Order.DELIVERY_FEE * 100,
                    'product_data': {'name': 'Delivery'},
                },
                'quantity': 1,
            })

        try:
            checkout_session = stripe.checkout.Session.create(
                payment_method_types=['card'],
                line_items=line_items,
                mode='payment',
                success_url=success_url,
                cancel_url=cancel_url,
                client_reference_id=order.id,
            )
            return redirect(checkout_session.url, code=303)
        except Exception as e:
            return render(request, 'store/error.html', {'error': str(e)})

    delivery_fee = order.get_delivery_fee()
    total_with_delivery = order.get_total_with_delivery()
    return render(request, 'orders/payment/process.html', {
        'order': order,
        'delivery_fee': delivery_fee,
        'total_with_delivery': total_with_delivery,
    })


@login_required
def payment_done(request):
    """
    Stripe redirects the customer here after payment.
    Stock deduction and paid=True happen in the webhook (stripe_webhook)
    to avoid double-processing.
    """
    order_id = request.session.get('order_id')
    if order_id:
        cart = Cart(request)
        cart.clear()
        del request.session['order_id']
    return render(request, 'store/success.html')


@login_required
def user_orders(request):
    orders_qs = Order.objects.filter(user=request.user).order_by('-created')
    now = timezone.now()

    for order in orders_qs:
        order.estimated_delivery = order.created + datetime.timedelta(days=5)
        if not order.paid:
            order.ship_stage = 0  # Awaiting payment
        else:
            days_passed = (now - order.created).days
            if days_passed < 1:
                order.ship_stage = 1   # Placed
            elif days_passed < 2:
                order.ship_stage = 2   # Processing
            elif days_passed < 5:
                order.ship_stage = 3   # Shipped
            else:
                order.ship_stage = 4   # Delivered

    paginator = Paginator(orders_qs, 5)
    page_obj = paginator.get_page(request.GET.get('page'))
    return render(request, 'orders/order/list.html', {'orders': page_obj})

