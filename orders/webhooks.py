import stripe
from django.conf import settings
from django.db import transaction
from django.http import HttpResponse
from django.views.decorators.csrf import csrf_exempt
from .models import Order
from .emails import send_premium_invoice
from store.models import ProductVariant


@csrf_exempt
def stripe_webhook(request):
    """Stripe webhook — idempotent, race-safe via select_for_update()."""
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

    if event_type == 'checkout.session.completed':
        session = event.data.object if hasattr(event, 'data') else event['data']['object']
        order_id = getattr(session, 'client_reference_id', None)

        if order_id:
            try:
                with transaction.atomic():
                    # select_for_update locks the row until end of transaction
                    # — prevents double-processing if Stripe sends the event twice
                    order = Order.objects.select_for_update().get(id=order_id)

                    if order.paid:
                        # Already processed — idempotent exit
                        return HttpResponse(status=200)

                    order.paid = True
                    order.save(update_fields=['paid'])

                    for item in order.items.select_related('product').all():
                        if item.product is None:
                            # Product was deleted (SET_NULL) — skip
                            continue
                        try:
                            variant = ProductVariant.objects.select_for_update().get(
                                product=item.product,
                                size=item.size,
                            )
                            variant.stock = max(0, variant.stock - item.quantity)
                            variant.save(update_fields=['stock'])
                        except ProductVariant.DoesNotExist:
                            # Fallback: deduct from legacy product.stock
                            product = item.product
                            product.stock = max(0, product.stock - item.quantity)
                            product.save(update_fields=['stock'])

                # Email is sent outside the transaction so SMTP errors
                # do not roll back the payment confirmation
                send_premium_invoice(order)

            except Order.DoesNotExist:
                return HttpResponse(status=404)

    return HttpResponse(status=200)
