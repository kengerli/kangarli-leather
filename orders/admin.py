from django.contrib import admin
from .models import Order, OrderItem

class OrderItemInline(admin.TabularInline):
    model = OrderItem
    # raw_id_fields создает виджет поиска вместо огромного выпадающего списка товаров
    raw_id_fields = ['product']

@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    # Добавляем 'get_total_cost' прямо в список колонок
    list_display = ['id', 'first_name', 'last_name', 'email', 'paid', 'get_total_cost', 'created']
    list_filter = ['paid', 'created', 'updated']
    inlines = [OrderItemInline]
    
    # Запрещаем редактировать дату создания и обновления
    readonly_fields = ['created', 'updated']

    # Переименовываем колонку get_total_cost для красоты
    def get_total_cost(self, obj):
        return f"{obj.get_total_cost()} AZN"
    get_total_cost.short_description = 'Total Revenue'