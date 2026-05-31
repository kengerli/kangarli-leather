from django.urls import path
from . import views
from . import webhooks

app_name = 'orders'

urlpatterns = [
    path('create/', views.order_create, name='order_create'),
    path('history/', views.user_orders, name='user_orders'),
    path('payment/', views.payment_process, name='payment_process'),
    path('payment/done/', views.payment_done, name='payment_done'),
    path('webhook/', webhooks.stripe_webhook, name='stripe_webhook'),
]