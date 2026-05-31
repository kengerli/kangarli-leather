from django.contrib import admin
from django.utils.html import format_html
from .models import Category, Artisan, Product, ProductVariant, Newsletter


class ProductVariantInline(admin.TabularInline):
    model = ProductVariant
    extra = 0
    fields = ['size', 'stock']


@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ['name', 'parent', 'slug']
    prepopulated_fields = {'slug': ('name',)}
    list_filter = ['parent']
    search_fields = ['name']
    autocomplete_fields = ['parent']


@admin.register(Artisan)
class ArtisanAdmin(admin.ModelAdmin):
    list_display = ['name', 'region']
    search_fields = ['name', 'region']
    list_filter = ['region']


@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = ['get_image', 'name', 'price', 'stock', 'is_available', 'category', 'artisan']
    list_display_links = ['name']
    list_filter = ['is_available', 'category', 'artisan', 'created']
    list_editable = ['price', 'stock', 'is_available']
    prepopulated_fields = {'slug': ('name',)}
    search_fields = ['name', 'description']
    readonly_fields = ['created']
    inlines = [ProductVariantInline]
    date_hierarchy = 'created'
    list_per_page = 20

    fieldsets = (
        ('Main info', {
            'fields': ('name', 'slug', 'image', 'category', 'artisan', 'description')
        }),
        ('Pricing & stock', {
            'fields': ('price', 'stock', 'is_available'),
            'description': 'stock — legacy fallback. Manage per-size stock via variants below.',
        }),
        ('System', {
            'fields': ('created',),
            'classes': ('collapse',)
        }),
    )

    def get_image(self, obj):
        if hasattr(obj, 'image') and obj.image:
            return format_html(
                '<img src="{}" style="width:40px;height:40px;border-radius:4px;object-fit:cover;" />',
                obj.image.url,
            )
        return '-'
    get_image.short_description = 'Photo'

    actions = ['make_available', 'make_unavailable', 'add_stock']

    @admin.action(description='Make selected available')
    def make_available(self, request, queryset):
        updated = queryset.update(is_available=True)
        self.message_user(request, f'{updated} products updated.')

    @admin.action(description='Make selected unavailable')
    def make_unavailable(self, request, queryset):
        updated = queryset.update(is_available=False)
        self.message_user(request, f'{updated} products hidden.')

    @admin.action(description='Add +10 to legacy stock')
    def add_stock(self, request, queryset):
        from django.db.models import F
        queryset.update(stock=F('stock') + 10)
        self.message_user(request, 'Stock bumped +10 for selected products.')


@admin.register(Newsletter)
class NewsletterAdmin(admin.ModelAdmin):
    list_display = ('email', 'subscribed_at', 'is_active')
    list_filter = ('is_active', 'subscribed_at')
    search_fields = ('email',)
    readonly_fields = ('subscribed_at',)
    actions = ['mark_inactive', 'mark_active']

    def mark_inactive(self, request, queryset):
        queryset.update(is_active=False)
    mark_inactive.short_description = 'Unsubscribe selected'

    def mark_active(self, request, queryset):
        queryset.update(is_active=True)
    mark_active.short_description = 'Subscribe selected'
