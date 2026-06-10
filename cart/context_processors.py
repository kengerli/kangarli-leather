from .cart import Cart


def cart_summary(request):
    """Expose the cart and its item count to every template (header badge)."""
    cart = Cart(request)
    return {
        'cart_items_count': len(cart),
    }
