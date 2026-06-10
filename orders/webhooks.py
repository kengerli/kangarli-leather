import logging

import stripe
from django.conf import settings
from django.db import transaction
from django.http import HttpResponse
from django.views.decorators.csrf import csrf_exempt
from .models import Order
from .emails import send_premium_invoice
from store.models import ProductVariant

logger = logging.getLogger(__name__)


@csrf_exempt
def stripe_webhook(request):
    """Stripe webhook - idempotent, race-safe via select_for_update()."""
    payload = request.body
    sig_header = request.META.get('HTTP_STRIPE_SIGNATURE')

    try:
        event = stripe.Webhook.construct_event(
            payload, sig_header, settings.STRIPE_WEBHOOK_SECRET
        )
    except ValueError:
        return HttpResponse(status=400)
    except stripe.error.SignatureVerificationError:
        return HttpResponse(status=400)

    event_type = event.type if hasattr(event, 'type') else event.get('type')
    logger.info('Stripe webhook event: %s', event_type)

    if event_type == 'checkout.session.completed':
        session = event.data.object if hasattr(event, 'data') else event['data']['object']
        order_id = getattr(session, 'client_reference_id', None)
        logger.info('checkout.session.completed for order %r', order_id)

        if order_id:
            try:
                with transaction.atomic():
                    # Lock the row for the duration of the transaction so two
                    # concurrent deliveries cannot both deduct stock.
                    order = Order.objects.select_for_update().get(id=order_id)

                    # Mark paid + deduct stock only on the first transition.
                    if not order.paid:
                        order.paid = True
                        order.save(update_fields=['paid'])

                        for item in order.items.select_related('product').all():
                            if item.product is None:
                                continue
                            try:
                                variant = ProductVariant.objects.select_for_update().get(
                                    product=item.product,
                                    size=item.size,
                                )
                                variant.stock = max(0, variant.stock - item.quantity)
                                variant.save(update_fields=['stock'])
                            except ProductVariant.DoesNotExist:
                                product = item.product
                                product.stock = max(0, product.stock - item.quantity)
                                product.save(update_fields=['stock'])
                    else:
                        logger.info('Order %s already paid', order.id)

                # Invoice is sent exactly once, gated by invoice_sent (not paid),
                # so a duplicate delivery cannot skip an unsent invoice. Sent
                # outside the transaction so SMTP errors do not roll back payment.
                if not order.invoice_sent:
                    try:
                        logger.info('Sending invoice for order %s to %r', order.id, order.email)
                        send_premium_invoice(order)
                        order.invoice_sent = True
                        order.save(update_fields=['invoice_sent'])
                        logger.info('Invoice sent for order %s', order.id)
                    except Exception as e:
                        logger.error('Invoice email failed for order %s: %s', order.id, e)
                else:
                    logger.info('Invoice already sent for order %s', order.id)

            except Order.DoesNotExist:
                logger.warning('Order %s not found', order_id)
                return HttpResponse(status=404)

    return HttpResponse(status=200)
