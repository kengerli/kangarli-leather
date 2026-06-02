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
    print(f'[WEBHOOK] event={event_type}')

    if event_type == 'checkout.session.completed':
        session = event.data.object if hasattr(event, 'data') else event['data']['object']
        order_id = getattr(session, 'client_reference_id', None)
        print(f'[WEBHOOK] checkout.session.completed client_reference_id={order_id!r}')

        if order_id:
            try:
                with transaction.atomic():
                    # select_for_update locks the row until end of transaction
                    # — prevents double-processing if Stripe sends the event twice
                    order = Order.objects.select_for_update().get(id=order_id)

                    # Mark paid + deduct stock only on the first transition.
                    # Duplicate deliveries skip this but still reach the email
                    # check below, which is guarded by its own flag.
                    if not order.paid:
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
                    else:
                        print(f'[WEBHOOK] order {order.id} already paid')

                # Invoice is sent exactly once, gated by invoice_sent (not paid),
                # so a duplicate webhook delivery cannot skip an unsent invoice.
                # Sent outside the transaction so SMTP errors do not roll back payment.
                if not order.invoice_sent:
                    try:
                        print(f'[WEBHOOK] sending invoice for order {order.id} to {order.email!r}')
                        send_premium_invoice(order)
                        order.invoice_sent = True
                        order.save(update_fields=['invoice_sent'])
                        print(f'[WEBHOOK] invoice SENT for order {order.id}')
                    except Exception as e:
                        import logging
                        logging.getLogger(__name__).error(
                            f'Invoice email failed for order {order.id}: {e}'
                        )
                        print(f'[WEBHOOK] invoice FAILED for order {order.id}: {e}')
                else:
                    print(f'[WEBHOOK] invoice already sent for order {order.id} -> skipping')

            except Order.DoesNotExist:
                print(f'[WEBHOOK] order {order_id} NOT FOUND in this database')
                return HttpResponse(status=404)

    return HttpResponse(status=200)
