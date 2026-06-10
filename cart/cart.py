from decimal import Decimal
from django.conf import settings
from store.models import Product, ProductVariant


class Cart(object):
    def __init__(self, request):
        # Read-only init: do NOT write to the session here, otherwise every
        # page view (via the context processor) would create an empty cart
        # key and undo clear(). save() persists the dict when it changes.
        self.session = request.session
        self.cart = self.session.get(settings.CART_SESSION_ID) or {}

    def add(self, product, quantity=1, size='Standard', override_quantity=False):
        product_id = str(product.id)
        item_key = f"{product_id}_{size}"

        if item_key not in self.cart:
            self.cart[item_key] = {
                'quantity': 0,
                'price': str(product.price),
                'size': size,
                'product_id': product_id
            }

        # Берём остаток из варианта; если варианта нет — fallback на product.stock
        try:
            variant_stock = ProductVariant.objects.get(product=product, size=size).stock
        except ProductVariant.DoesNotExist:
            variant_stock = product.stock

        if override_quantity:
            new_quantity = min(quantity, variant_stock)
            self.cart[item_key]['quantity'] = new_quantity
        else:
            current_quantity = self.cart[item_key]['quantity']
            new_quantity = min(current_quantity + quantity, variant_stock)
            self.cart[item_key]['quantity'] = new_quantity

        self.save()
        # Возвращаем итоговое количество чтобы view мог показать предупреждение
        return self.cart[item_key]['quantity']

    def save(self):
        self.session[settings.CART_SESSION_ID] = self.cart
        self.session.modified = True

    def remove(self, item_key):
        if item_key in self.cart:
            del self.cart[item_key]
            self.save()

    def clear(self):
        self.session.pop(settings.CART_SESSION_ID, None)
        self.cart = {}
        self.session.modified = True

    def __iter__(self):
        """
        Yield enriched COPIES of cart items so Product objects and Decimals
        never end up inside the session (they are not JSON-serialisable).
        Items whose product was deleted or hidden are pruned from the cart.
        """
        product_ids = [item['product_id'] for item in self.cart.values()]
        products = Product.objects.select_related('artisan').filter(
            id__in=product_ids, is_available=True
        )
        products_dict = {str(p.id): p for p in products}

        stale_keys = [
            key for key, item in self.cart.items()
            if item['product_id'] not in products_dict
        ]
        if stale_keys:
            for key in stale_keys:
                del self.cart[key]
            self.save()

        for key, stored in list(self.cart.items()):
            item = stored.copy()  # never mutate the session dict
            item['product'] = products_dict[item['product_id']]
            item['price'] = Decimal(item['price'])
            item['total_price'] = item['price'] * item['quantity']
            item['item_key'] = key
            yield item

    def __len__(self):
        return sum(item['quantity'] for item in self.cart.values())

    def get_total_price(self):
        return sum(Decimal(item['price']) * item['quantity'] for item in self.cart.values())
