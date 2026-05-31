from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from .views import robots_txt


urlpatterns = [
    path('admin/', admin.site.urls),
    
    path('account/', include('account.urls', namespace='account')),
    path('cart/', include('cart.urls', namespace='cart')),
    path('orders/', include('orders.urls', namespace='orders')), 

    path('robots.txt', robots_txt, name='robots_txt'),
    
    # Store must be at the bottom because it catches root URLs
    path('', include('store.urls', namespace='store')),

    
    
] + static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)

handler404 = 'store.views.custom_404'