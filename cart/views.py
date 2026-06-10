from django.shortcuts import render, redirect, get_object_or_404
from django.views.decorators.http import require_POST
from django.contrib import messages

from store.models import Product, ProductVariant
from .cart import Cart
from .forms import CartAddProductForm


@require_POST
def cart_add(request, product_id):
    cart = Cart(request)
    product = get_object_or_404(Product, id=product_id)
    form = CartAddProductForm(request.POST, product=product)

    if form.is_valid():
        cd = form.cleaned_data
        requested_quantity = cd['quantity']

        actual_quantity = cart.add(
            product=product,
            quantity=requested_quantity,
            size=cd['size'],
            override_quantity=cd['override']
        )

        try:
            variant_stock = ProductVariant.objects.get(
                product=product, size=cd['size']
            ).stock
        except ProductVariant.DoesNotExist:
            variant_stock = product.stock

        if cd['override']:
            if actual_quantity < requested_quantity:
                messages.warning(
                    request,
                    f'Only {variant_stock} piece(s) available. '
                    f'Quantity set to {actual_quantity}.'
                )
            else:
                messages.info(request, f'Quantity updated for "{product.name}".')
        else:
            if actual_quantity < requested_quantity:
                messages.warning(
                    request,
                    f'Only {variant_stock} piece(s) in stock. '
                    f'Added maximum available quantity.'
                )
            else:
                messages.success(request, f'"{product.name}" added to your cart.')

    return redirect(request.META.get('HTTP_REFERER', 'cart:cart_detail'))


@require_POST
def cart_remove(request, item_key):
    cart = Cart(request)
    cart.remove(item_key)
    return redirect('cart:cart_detail')


def cart_detail(request):
    cart = Cart(request)
    # Materialise once: __iter__ yields fresh copies, so forms must be
    # attached to a concrete list that the template will iterate.
    cart_items = list(cart)
    for item in cart_items:
        item['update_quantity_form'] = CartAddProductForm(
            initial={
                'quantity': item['quantity'],
                'size': item['size'],
                'override': True
            },
            product=item['product']
        )
    return render(request, 'cart/detail.html', {
        'cart': cart,
        'cart_items': cart_items,
    })
