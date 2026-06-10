from django.shortcuts import render, get_object_or_404, redirect
from .models import Category, Product, Newsletter, Favorite, Review
from cart.forms import CartAddProductForm
from django.db.models import Q, Sum
from django.contrib import messages
from django.views.decorators.http import require_POST, require_GET
import json
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_protect
from cart.cart import Cart
from django.conf import settings
from .forms import ReviewForm
from orders.models import OrderItem
from django.core.paginator import Paginator
from django.contrib.auth.decorators import login_required
from django.http import HttpResponseRedirect
from groq import Groq
import re


# ==================== STORE VIEWS ====================

def product_list(request, category_slug=None):
    """Display list of products with filtering, searching, and sorting"""
    category = None
    categories = Category.objects.all()
    products = Product.objects.select_related('category', 'artisan').filter(is_available=True)
    search_query = None

    if category_slug:
        category = get_object_or_404(Category, slug=category_slug)
        products = (
            products.filter(category__in=category.children.all()) |
            products.filter(category=category)
        )

    min_price = request.GET.get('min_price')
    max_price = request.GET.get('max_price')
    if min_price:
        try:
            products = products.filter(price__gte=float(min_price))
        except ValueError:
            pass
    if max_price:
        try:
            products = products.filter(price__lte=float(max_price))
        except ValueError:
            pass

    query = request.GET.get('q')
    if query:
        search_query = query
        products = products.filter(
            Q(name__icontains=query) |
            Q(description__icontains=query) |
            Q(category__name__icontains=query) |
            Q(artisan__name__icontains=query)
        )

    sort_by = request.GET.get('sort_by')
    if sort_by == 'price_asc':
        products = products.order_by('price')
    elif sort_by == 'price_desc':
        products = products.order_by('-price')
    else:
        products = products.order_by('-created')

    products = products.distinct()

    paginator = Paginator(products, 12)
    page_obj = paginator.get_page(request.GET.get('page'))

    favorite_product_ids = []
    if request.user.is_authenticated:
        favorite_product_ids = Favorite.objects.filter(
            user=request.user
        ).values_list('product_id', flat=True)

    return render(request, 'store/product/list.html', {
        'category': category,
        'categories': categories,
        'products': page_obj,
        'search_query': search_query,
        'favorite_product_ids': favorite_product_ids,
    })


def product_detail(request, id, slug):
    """Display product detail page — ЕДИНСТВЕННАЯ версия этой функции"""
    product = get_object_or_404(
        Product.objects.select_related('category', 'artisan'),
        id=id,
        slug=slug,
        is_available=True
    )

    cart_product_form = CartAddProductForm(product=product)
    reviews = product.reviews.all()

    # Проверка: купил ли пользователь этот товар
    has_bought = False
    if request.user.is_authenticated:
        has_bought = OrderItem.objects.filter(
            order__user=request.user,
            order__paid=True,
            product=product
        ).exists()

    # Обработка формы отзыва (один отзыв на пользователя — повторный обновляет старый)
    if request.method == 'POST' and has_bought:
        review_form = ReviewForm(data=request.POST)
        if review_form.is_valid():
            Review.objects.update_or_create(
                product=product,
                user=request.user,
                defaults={
                    'content': review_form.cleaned_data['content'],
                    'rating': review_form.cleaned_data['rating'],
                },
            )
            messages.success(request, 'Thank you! Your review has been published.')
            return redirect('store:product_detail', id=product.id, slug=product.slug)
    else:
        review_form = ReviewForm()

    # Проверка: в избранном ли товар
    is_favorite = False
    if request.user.is_authenticated:
        is_favorite = Favorite.objects.filter(
            user=request.user,
            product=product
        ).exists()

    return render(request, 'store/product/detail.html', {
        'product': product,
        'cart_product_form': cart_product_form,
        'reviews': reviews,
        'review_form': review_form,
        'has_bought': has_bought,
        'is_favorite': is_favorite,
    })


@login_required
def toggle_favorite(request, product_id):
    product = get_object_or_404(Product, id=product_id)
    favorite, created = Favorite.objects.get_or_create(
        user=request.user,
        product=product
    )
    if not created:
        favorite.delete()
        messages.info(request, f'"{product.name}" removed from your wishlist.')
    else:
        messages.success(request, f'"{product.name}" added to your wishlist.')

    return HttpResponseRedirect(request.META.get('HTTP_REFERER', '/'))


# ==================== API ENDPOINTS ====================

@require_GET
def search_autocomplete(request):
    """Autocomplete suggestions for search"""
    query = request.GET.get('q', '').strip()
    if len(query) < 2:
        return JsonResponse({'results': []})

    products = Product.objects.filter(
        Q(name__icontains=query) | Q(description__icontains=query),
        is_available=True
    )[:6]

    return JsonResponse({
        'results': [{'id': p.id, 'name': p.name} for p in products]
    })


@require_POST
@csrf_protect
def newsletter_subscribe(request):
    """Newsletter subscription via AJAX"""
    try:
        data = json.loads(request.body)
        email = data.get('email', '').strip().lower()

        if not email or '@' not in email or '.' not in email.split('@')[1]:
            return JsonResponse({
                'success': False,
                'message': 'Please enter a valid email address'
            }, status=400)

        if Newsletter.objects.filter(email=email).exists():
            return JsonResponse({
                'success': False,
                'message': 'This email is already subscribed'
            }, status=400)

        Newsletter.objects.create(email=email)
        return JsonResponse({'success': True, 'message': 'Successfully subscribed!'})

    except json.JSONDecodeError:
        return JsonResponse({'success': False, 'message': 'Invalid request'}, status=400)
    except Exception:
        return JsonResponse({
            'success': False,
            'message': 'An error occurred. Please try again.'
        }, status=500)



# ==================== AI STYLIST ====================

def ai_stylist(request):
    """Render AI Stylist chat page"""
    return render(request, 'store/ai_stylist.html')


@require_POST
@csrf_protect
@login_required
def ai_stylist_api(request):
    if not settings.GROQ_API_KEY:
        return JsonResponse({'success': False, 'message': 'AI Stylist is currently unavailable.'}, status=503)

    try:
        data = json.loads(request.body)
        user_message = data.get('message', '').strip()
        conversation_history = data.get('history', [])

        if not user_message:
            return JsonResponse({'success': False, 'message': 'Empty message'}, status=400)

        base_products = (
            Product.objects
            .select_related('category', 'artisan')
            .annotate(total_stock=Sum('variants__stock'))
            .filter(is_available=True, total_stock__gt=0)
            .distinct()
        )

        clean_message = re.sub(r'[^\w\s]', ' ', user_message.lower())
        words = clean_message.split()
        search_words = [w for w in words if len(w) > 2]

        query = Q()
        if search_words:
            for word in search_words:
                query |= Q(name__icontains=word)
                query |= Q(description__icontains=word)
                query |= Q(category__name__icontains=word)
                query |= Q(artisan__name__icontains=word)
                query |= Q(artisan__region__icontains=word)
            products = base_products.filter(query).distinct().order_by('-created')[:20]
        else:
            products = Product.objects.none()

        if not products.exists():
            products = base_products.order_by('-created')[:15]

        # Строим каталог для промпта И словарь для карточек
        catalog_items = []
        products_dict = {}  # id -> данные для карточки

        for p in products:
            short_desc = (p.description[:120] + '...') if p.description else "Premium leather."
            catalog_items.append(
                f"- [ID:{p.id}] {p.name} | Category: {p.category.name} | "
                f"Artisan: {p.artisan.name} | Price: {p.price} AZN | "
                f"In Stock: {p.total_stock or 0} pcs | Style: {short_desc}"
            )
            products_dict[p.id] = {
                'id': p.id,
                'name': p.name,
                'price': str(p.price),
                'artisan': p.artisan.name,
                'image': p.image.url if p.image else None,
                'url': f"/product/{p.id}/{p.slug}/",
            }

        product_catalog = "\n".join(catalog_items)

        system_prompt = f"""You are Fiko, an expert leather goods stylist for Kangarli Leather — a premium handcrafted leather store based in Azerbaijan.

Your personality: sophisticated, warm, and highly knowledgeable about premium leather craftsmanship, western aesthetics, and heritage goods. You speak like a trusted personal stylist from an upscale boutique.

CURRENT LIVE CATALOG:
{product_catalog}

RULES:
- Only recommend products from the catalog above.
- ALWAYS reference products by their exact ID in square brackets like [ID:42] when mentioning them.
- If stock is low (1-2 pcs), mention exclusivity.
- Keep responses concise (3-5 sentences max).
- Ask clarifying questions if needed.
- If nothing matches, say so honestly.
- Respond in the same language the customer uses (English, Russian, Azerbaijani)."""

        chat_messages = []
        for item in conversation_history[-6:]:
            if item.get('role') in ('user', 'assistant'):
                chat_messages.append({'role': item['role'], 'content': item['content']})
        chat_messages.append({'role': 'user', 'content': user_message})

        client = Groq(api_key=settings.GROQ_API_KEY)
        completion = client.chat.completions.create(
            model='llama-3.1-8b-instant',
            messages=[{'role': 'system', 'content': system_prompt}] + chat_messages,
            max_tokens=400,
            temperature=0.6,
        )

        reply_text = completion.choices[0].message.content

        # Извлекаем ID упомянутых товаров из ответа
        mentioned_ids = [int(x) for x in re.findall(r'\[ID:(\d+)\]', reply_text)]
        # Убираем [ID:xx] теги из текста — пользователь их не должен видеть
        clean_reply = re.sub(r'\s*\[ID:\d+\]', '', reply_text).strip()

        # Собираем карточки только упомянутых товаров (сохраняем порядок)
        recommended_products = []
        seen = set()
        for pid in mentioned_ids:
            if pid in products_dict and pid not in seen:
                recommended_products.append(products_dict[pid])
                seen.add(pid)

        return JsonResponse({
            'success': True,
            'reply': clean_reply,
            'products': recommended_products,
        })

    except Exception as e:
        return JsonResponse({
            'success': False,
            'message': 'Stylist is unavailable right now. Please try again.'
        }, status=500)
    
def custom_404(request, exception):
    return render(request, 'store/404.html', status=404)

def leather_care(request):
    return render(request, 'store/leather_care.html')
from django.core.mail import EmailMessage

def contact(request):
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            name = data.get('name', '').strip()
            email = data.get('email', '').strip()
            subject = data.get('subject', 'General Inquiry').strip()
            message = data.get('message', '').strip()

            if not all([name, email, message]):
                return JsonResponse({'success': False, 'message': 'Please fill in all fields.'}, status=400)

            email_body = f"""
New contact form submission — Kangarli Leather
{'─' * 40}

Name:     {name}
Email:    {email}
Subject:  {subject}

Message:
{message}

{'─' * 40}
Sent via kangarli.az contact form
            """

            msg = EmailMessage(
                subject=f'[Kangarli] {subject} — from {name}',
                body=email_body,
                from_email=settings.DEFAULT_FROM_EMAIL,
                to=[settings.CONTACT_EMAIL],
                reply_to=[email],
            )
            msg.send()

            return JsonResponse({'success': True})

        except Exception as e:
            return JsonResponse({'success': False, 'message': 'Something went wrong. Please try again.'}, status=500)

    return render(request, 'store/contact.html')

def about(request):
    return render(request, 'store/about.html')