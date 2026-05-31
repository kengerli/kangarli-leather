from django.urls import path
from . import views

app_name = 'store'

urlpatterns = [
    # ===== AI STYLIST =====
    path('stylist/', views.ai_stylist, name='ai_stylist'),
    path('api/stylist/', views.ai_stylist_api, name='stylist_api'),

    # ===== LEATHER CARE =====
    path('care/', views.leather_care, name='leather_care'),  

    # ===== STORE VIEWS =====
    path('', views.product_list, name='product_list'),
    path('product/<int:id>/<slug:slug>/', views.product_detail, name='product_detail'),
    path('contact/', views.contact, name='contact'),
    path('about/', views.about, name='about'),

    # ===== API ENDPOINTS =====
    path('api/search/', views.search_autocomplete, name='search_api'),
    path('api/newsletter/subscribe/', views.newsletter_subscribe, name='newsletter_api'),
    path('favorite/<int:product_id>/', views.toggle_favorite, name='toggle_favorite'),

    # ===== CATEGORIES (LAST) =====
    path('<slug:category_slug>/', views.product_list, name='product_list_by_category'),


]