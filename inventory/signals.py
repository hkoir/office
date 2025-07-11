
from inventory.models import InventoryTransaction,Inventory

from django.core.mail import send_mail
from django.utils.timezone import now, timedelta
from django.db.models import F,Sum
from django.db import models
from django.conf import settings
from product.models import Product
from myproject.utils import create_notification

from django.db.models.signals import post_save, post_delete
from django.dispatch import Signal,receiver
inventory_update_signal = Signal()

from reporting.views import monitor_inventory_status



@receiver(inventory_update_signal, sender=monitor_inventory_status)
def handle_custom_notification(sender, instance, user, action, **kwargs):
    user = kwargs.get("user")
    message = kwargs.get("message")
    if user and message:
        create_notification(user=user, message=message,notification_type='WAREHOUSE-LOW-STOCK')



def send_test_email():
    subject = "Test Email from Django"
    message = "This is a test email sent from the Django project."
    from_email = settings.EMAIL_HOST_USER  
    recipient_list = [settings.ADMIN_EMAIL]  

    try:
        send_mail(subject, message, from_email, recipient_list)
        print("Email sent successfully!")
    except Exception as e:
        print(f"Error sending email: {e}")



def calculate_average_usage(product, days=30):
    start_date = now() - timedelta(days=days)
    usage = InventoryTransaction.objects.filter(
        product=product,
        transaction_type__in=['OUTBOUND','REPLACEMENT_OUT','OPERATIONS_OUT'],
        created_at__gte=start_date
    ).aggregate(total_usage=Sum('quantity'))['total_usage'] or 0

    return usage / days if usage else 0

def send_lead_time_alert(alerts):
    subject = "Lead Time Stock Alert"
    message = "The following products are at risk of stockout based on lead time and usage:\n\n"

    for alert in alerts:
        message += (
            f"Product: {alert['product']}\n"
            f"Warehouse: {alert['warehouse']}\n"
            f"Current Stock: {alert['current_stock']}\n"
            f"Required Stock (for {alert['lead_time']} days): {alert['required_stock']}\n"
            f"Average Daily Usage: {alert['average_usage']}\n\n"
        )
    send_mail(subject, message, 'noreply@yourcompany.com', ['admin@yourcompany.com'])

def send_warehouse_low_stock_alert(warehouse_wise_low_stock):
    subject = "Low Stock Alert (Warehouse-Wise)"
    message = "The following products have low stock in specific warehouses:\n\n"
    for item in warehouse_wise_low_stock:
        message += (
            f"Product: {item.product.name}\n"
            f"Warehouse: {item.warehouse.name if item.warehouse else 'N/A'}\n"
            f"Current Stock: {item.quantity}\n"
            f"Reorder Level: {item.product.reorder_level}\n\n"
        )
    send_mail(subject, message, 'noreply@yourcompany.com', ['admin@yourcompany.com'])

def send_total_low_stock_alert(low_stock_products):
    subject = "Low Stock Alert (Total)"
    message = "The following products have low total stock (across all warehouses):\n\n"
    for product in low_stock_products:
        message += (
            f"Product: {product['product_name']}\n"
            f"Total Stock: {product['total_quantity']}\n"
            f"Reorder Level: {product['reorder_level']}\n\n"
        )
    send_mail(subject, message, 'noreply@yourcompany.com', ['admin@yourcompany.com'])



@receiver(post_save, sender=Inventory)
@receiver(post_delete, sender=Inventory)
def update_inventory_status(sender, instance, **kwargs):
    low_stock_alerts = []

    for product in Product.objects.all():
        average_usage = calculate_average_usage(product)
        if average_usage is not None and product.lead_time is not None:
            required_stock = average_usage * product.lead_time
        warehouse_stocks = Inventory.objects.filter(product=product)

        for stock in warehouse_stocks:
            warehouse_reorder_level = stock.warehouse.reorder_level if stock.warehouse else product.reorder_level
            if stock.quantity < required_stock:
                low_stock_alerts.append({
                    'product': product.name,
                    'warehouse': stock.warehouse.name if stock.warehouse else 'N/A',
                    'current_stock': stock.quantity,
                    'required_stock': required_stock,
                    'average_usage': average_usage,
                    'lead_time': product.lead_time,
                })
            if stock.quantity <= warehouse_reorder_level:
                low_stock_alerts.append({
                    'product': product.name,
                    'warehouse': stock.warehouse.name if stock.warehouse else 'N/A',
                    'current_stock': stock.quantity,
                    'reorder_level': warehouse_reorder_level,
                })

        total_stock = warehouse_stocks.aggregate(total_quantity=Sum('quantity'))['total_quantity'] or 0
        if total_stock < required_stock:
            low_stock_alerts.append({
                'product': product.name,
                'warehouse': 'All Warehouses',
                'current_stock': total_stock,
                'required_stock': required_stock,
                'average_usage': average_usage,
                'lead_time': product.lead_time,
            })
        if total_stock <= product.reorder_level:
            low_stock_alerts.append({
                'product': product.name,
                'warehouse': 'All Warehouses',
                'current_stock': total_stock,
                'reorder_level': product.reorder_level,
            })

    warehouse_wise_low_stock = (
        Inventory.objects.values('warehouse', 'product')
        .annotate(total_quantity=Sum('quantity'))
        .filter(total_quantity__lte=F('warehouse__reorder_level'))
    )

    total_stock = (
        Inventory.objects.values('product')
        .annotate(total_quantity=Sum('quantity'))
    )

    low_stock_products = [
        {
            'product_name': Product.objects.get(id=stock['product']).name,
            'total_quantity': stock['total_quantity'],
            'reorder_level': Product.objects.get(id=stock['product']).reorder_level,
        }
        for stock in total_stock
        if stock['total_quantity'] <= Product.objects.get(id=stock['product']).reorder_level
    ]

    user = instance.user if hasattr(instance, 'user') else None

    if warehouse_wise_low_stock:
        # send_warehouse_low_stock_alert(warehouse_wise_low_stock)  
        if user:
            create_notification(user, message='Inventory low alert',notification_type='WAREHOUSE-LOW-STOCK')
    if low_stock_products:
        # send_total_low_stock_alert(low_stock_products)  
        if user:
            create_notification(user, message='Inventory low alert',notification_type='WAREHOUSE-LOW-STOCK')
    if low_stock_alerts:
        # send_lead_time_alert(low_stock_alerts)  
        if user:
            create_notification(user, message='Inventory low alert',notification_type='WAREHOUSE-LOW-STOCK')



