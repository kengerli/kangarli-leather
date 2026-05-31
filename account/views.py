from django.shortcuts import render, redirect
from .forms import UserRegistrationForm
from django.contrib.auth.decorators import login_required
from store.models import Favorite
from orders.models import Order
from .forms import UserEditForm
from django.contrib import messages
from django.contrib.auth import logout
from django.contrib.auth import login
from django_ratelimit.decorators import ratelimit


# 5 registration attempts per minute per IP — returns 429 when exceeded
@ratelimit(key='ip', rate='5/m', method='POST', block=True)
def register(request):
    if request.method == 'POST':
        user_form = UserRegistrationForm(request.POST)
        if user_form.is_valid():
            new_user = user_form.save(commit=False)
            new_user.set_password(user_form.cleaned_data['password'])
            new_user.save()

            login(request, new_user, backend='django.contrib.auth.backends.ModelBackend')

            next_url = request.GET.get('next')
            if next_url:
                return redirect(next_url)
            return redirect('account:dashboard')
    else:
        user_form = UserRegistrationForm()

    return render(request, 'account/register.html', {'user_form': user_form})


@login_required
def dashboard(request):
    favorites = Favorite.objects.filter(user=request.user).select_related('product')
    orders = Order.objects.filter(user=request.user).order_by('-created')
    return render(request, 'account/dashboard.html', {
        'favorites': favorites,
        'orders': orders,
    })


@login_required
def settings_view(request):
    if request.method == 'POST':
        form = UserEditForm(instance=request.user, data=request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, 'Profile updated successfully.')
            return redirect('account:settings')
    else:
        form = UserEditForm(instance=request.user)
    return render(request, 'account/settings.html', {'form': form})


def logged_out_page(request):
    return render(request, 'account/logged_out.html')
