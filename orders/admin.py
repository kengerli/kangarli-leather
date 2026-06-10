from django.contrib import admin
from django.utils.html import format_html
from django.utils.safestring import mark_safe  
from .models import Order, OrderItem
from .emails import send_premium_invoice
from django.db.models import Sum, F
from django.template.response import TemplateResponse
from .models import SalesStatistic, OrderItem
import json
from datetime import timedelta
from django.utils import timezone
from django.db.models import Sum, F
from django.template.response import TemplateResponse
from django.contrib import admin



class OrderItemInline(admin.TabularInline):
    model = OrderItem
    raw_id_fields = ['product']
    extra = 0
    readonly_fields = ['get_cost']

    def get_cost(self, obj):
        if obj.pk:
            return f'{obj.get_cost()} AZN'
        return '-'
    get_cost.short_description = 'Line total'


@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    list_display = ['id', 'customer', 'email', 'paid_badge', 'invoice_badge', 'total_cost', 'created']
    list_filter = ['paid', 'invoice_sent', 'created']
    search_fields = ['id', 'first_name', 'last_name', 'email']
    date_hierarchy = 'created'
    list_per_page = 25
    inlines = [OrderItemInline]
    readonly_fields = ['created', 'updated']
    actions = ['mark_as_paid', 'resend_invoice']

    @admin.display(description='Customer')
    def customer(self, obj):
        return f'{obj.first_name} {obj.last_name}'

    @admin.display(description='Total')
    def total_cost(self, obj):
        return f'{obj.get_total_cost()} AZN'

    @admin.display(description='Paid')
    def paid_badge(self, obj):
        color, label = ('#1a7f37', 'PAID') if obj.paid else ('#b35900', 'UNPAID')
        return format_html('<b style="color:#fff;background:{};padding:2px 8px;border-radius:10px;font-size:11px;">{}</b>', color, label)

    @admin.display(description='Invoice')
    def invoice_badge(self, obj):
        if obj.invoice_sent:
            return mark_safe('<span style="color:#1a7f37;">&#10003; sent</span>')
        return mark_safe('<span style="color:#999;">&mdash;</span>')

    @admin.action(description='Mark selected orders as PAID')
    def mark_as_paid(self, request, queryset):
        updated = queryset.update(paid=True)
        self.message_user(request, f'{updated} order(s) marked as paid.')

    @admin.action(description='Resend invoice email')
    def resend_invoice(self, request, queryset):
        sent, failed = 0, 0
        for order in queryset:
            try:
                send_premium_invoice(order)
                order.invoice_sent = True
                order.save(update_fields=['invoice_sent'])
                sent += 1
            except Exception:
                failed += 1
        msg = f'{sent} invoice(s) sent.'
        if failed:
            msg += f' {failed} failed (check email settings).'
        self.message_user(request, msg)

@admin.register(SalesStatistic)
class SalesStatisticAdmin(admin.ModelAdmin):
    change_list_template = 'admin/orders/sales_statistics.html'

    def has_add_permission(self, request):
        return False

    def changelist_view(self, request, extra_context=None):
        PROFIT_MARGIN = 0.20  # 20% маржа

        # 1. Получаем период из URL (по умолчанию 'all')
        period = request.GET.get('period', 'all')
        now = timezone.now()
        date_filter = None

        # Определяем дату начала для фильтрации
        if period == 'today':
            date_filter = now.replace(hour=0, minute=0, second=0, microsecond=0)
        elif period == 'week':
            date_filter = now - timedelta(days=7)
        elif period == 'month':
            date_filter = now - timedelta(days=30)
        elif period == 'year':
            date_filter = now - timedelta(days=365)

        # 2. Базовые запросы (только оплаченные)
        orders_qs = Order.objects.filter(paid=True)
        items_qs = OrderItem.objects.filter(order__paid=True)

        # Применяем фильтр по дате, если выбран не 'all'
        if date_filter:
            orders_qs = orders_qs.filter(created__gte=date_filter)
            items_qs = items_qs.filter(order__created__gte=date_filter)

        # 3. Считаем основные цифры
        revenue_data = items_qs.aggregate(total_revenue=Sum(F('price') * F('quantity')))
        total_revenue = revenue_data['total_revenue'] or 0
        net_profit = float(total_revenue) * PROFIT_MARGIN
        total_orders = orders_qs.count()

        # 4. Статистика по категориям
        category_stats = items_qs.values('product__category__name')\
            .annotate(total_sales=Sum(F('price') * F('quantity')))\
            .order_by('-total_sales')

        # 5. Подготавливаем данные для графика (Chart.js требует формат JSON)
        chart_labels = [stat['product__category__name'] for stat in category_stats]
        chart_data = [float(stat['total_sales']) for stat in category_stats]

        context = {
            **self.admin_site.each_context(request),
            'title': 'Sales & Profit Statistics',
            'total_revenue': total_revenue,
            'net_profit': net_profit,
            'profit_margin_percent': int(PROFIT_MARGIN * 100),
            'total_orders': total_orders,
            'category_stats': category_stats,
            'current_period': period,  # Передаем текущий период для подсветки активной кнопки
            'chart_labels': chart_labels,  # JSON для JS
            'chart_data': chart_data,        }
        return TemplateResponse(request, self.change_list_template, context)