
from django.shortcuts import render, get_object_or_404,redirect
from django.db.models import Sum
import json,csv
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas
from num2words import num2words
import os
from django.conf import settings
from django.utils import timezone
from django.utils.timezone import now, timedelta
from datetime import timedelta
from django.http import HttpResponse
from django.contrib import messages

from django.core.paginator import Paginator
from django.db.models.signals import post_save, post_delete

from.forms import SummaryReportChartForm
from core.models import Employee
from product.models import Product
from inventory.models import Inventory,TransferOrder,Warehouse,InventoryTransaction
from purchase.models import PurchaseOrder
from repairreturn.models import Replacement
from sales.models import SaleOrder
from.models import Notification

from myproject.utils import mark_notification_as_read,calculate_stock_value2

from django.core.mail import send_mail
from core.forms import CommonFilterForm
from django.contrib.auth.decorators import login_required,permission_required



@login_required
def report_dashboard(request):
    return render(request, 'report/report_dashboard.html')


@login_required
def notification_list(request):
    notifications = Notification.objects.all().order_by('-created_at')
    unread_notifications = notifications.filter(user=request.user, is_read=False)
    paginator = Paginator(notifications, 10)  
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    return render(request,'report/notification_list.html',{'notifications':notifications,'page_obj':page_obj,'unread_notifications':unread_notifications})

@login_required
def mark_notification_read_view(request, notification_id):
    mark_notification_as_read(notification_id)
    return redirect('reporting:notification_list')


from datetime import timedelta
from django.utils.timezone import now
from.forms import NotificationArchieveForm
from.models import ArchivedNotification


def archive_old_notifications(request):
    form = NotificationArchieveForm(request.GET or None)  
    notification_list = Notification.objects.all()
  

    if form.is_valid():
        start_date = form.cleaned_data.get('start_date')
        end_date = form.cleaned_data.get('end_date')
        no_of_days = form.cleaned_data.get('days')
   
        notifications = Notification.objects.all()

        if start_date and end_date:
            notifications = notifications.filter(created_at__range=(start_date, end_date))
        elif no_of_days:
            target_date = timezone.now() - timedelta(days=no_of_days)
            notifications = notifications.filter(created_at__lte=target_date)


        archived_count = 0
        for notification in notifications:
            ArchivedNotification.objects.create(
                message=notification.message,
                created_at=notification.created_at
            )
            notification.delete()
            archived_count += 1

        messages.success(request, f"{archived_count} notifications archived successfully.")
        return redirect('reporting:notification_list')  # Change to the appropriate redirect
    paginator = Paginator(notification_list, 10)  
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    return render(request, 'report/archieve_old_notifications.html', {'form': form,'page_obj':page_obj})




    


@login_required
def product_list(request):
    product = None
    products = Product.objects.all().order_by('-created_at')
    form = CommonFilterForm(request.GET or None)  
    if form.is_valid():
        product = form.cleaned_data.get('product_name')
        if product:
            products = products.filter(name__icontains=product.name)  
    
    paginator = Paginator(products, 10)  
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    form=CommonFilterForm()

    return render(request, 'report/product_list.html', {
        'products': products,
        'page_obj': page_obj,
        'product': product,
        'form': form,
    })



from purchase.models import Batch
from django.db.models import Sum, F
from django.http import JsonResponse
from inventory.models import Inventory

def get_batch_warehouse_data(request):
    batch_id = request.GET.get('batch_id', '').strip() 
    if not batch_id.isdigit():
        return JsonResponse({'error': 'Invalid batch ID'}, status=400)
    try:
        warehouses = Inventory.objects.filter(batch__id=batch_id).values(
            'warehouse__name', 'quantity'
        )
        warehouses_list = list(warehouses)     
        if not warehouses_list:
            return JsonResponse([], safe=False) 
        return JsonResponse(warehouses_list, safe=False)
    except Exception as e:
        print(f"Error: {str(e)}")
        return JsonResponse({'error': 'Server error'}, status=500)


def batchwise_product_status(request):
    product_id = request.GET.get('product') 
    products = Product.objects.all()  
    batchs_in_product = Batch.objects.all()
    batch_data = []
    batch_price_data=[]
    total_remaining_stock_value = 0
    total_purchase_stock_value = 0

    if product_id:
        batchs_in_product =  batchs_in_product.filter(product_id=product_id)

        selected_product = Product.objects.filter(id=product_id).first()
        if selected_product:
            batch_transactions = (
                InventoryTransaction.objects.filter(batch__product=selected_product)
                .values('batch__batch_number','batch_id', 'transaction_type',)
                .annotate(
                    total_quantity=Sum('quantity'),
                    remaining_quantity=Sum('batch__remaining_quantity'),
                    unit_price=F('batch__unit_price')
                )
                .order_by('batch__batch_number')
            )
            batch_summary = {}           

            for batch in batch_transactions:              
                batch_number = batch['batch__batch_number']
                batch_id = batch['batch_id']
                transaction_type = batch['transaction_type']
                quantity = batch['total_quantity']
                remaining = batch['remaining_quantity']
                unit_price = batch['unit_price'] or 0              

                total_remaining_stock_value += remaining * unit_price

                if batch_number not in batch_summary:
                    batch_summary[batch_number] = {
                        "inbound": 0,
                        "outbound": 0,
                        "manufacture_in": 0,
                        "manufacture_out": 0,
                        "replacement_in": 0,
                        "replacement_out": 0,
                        "transfer_in": 0,
                        "transfer_out": 0,
                        "scrapped_out": 0,
                        "operations_out": 0,
                        "remaining": 0
                    }

                if transaction_type == "INBOUND":
                    batch_summary[batch_number]["inbound"] = quantity
                    total_purchase_stock_value += quantity * unit_price
                elif transaction_type == "OUTBOUND":
                    batch_summary[batch_number]["outbound"] = quantity
                elif transaction_type == "MANUFACTURE_IN":
                    batch_summary[batch_number]["manufacture_in"] = quantity
                elif transaction_type == "MANUFACTURE_OUT":
                    batch_summary[batch_number]["manufacture_out"] = quantity
                elif transaction_type == "REPLACEMENT_OUT":
                    batch_summary[batch_number]["replacement_out"] = quantity
                elif transaction_type == "REPLACEMENT_IN":
                    batch_summary[batch_number]["replacement_in"] = quantity
                elif transaction_type == "SRAPPED_OUT":
                    batch_summary[batch_number]["scrapped_out"] = quantity
                elif transaction_type == "OPERATIONS_OUT":
                    batch_summary[batch_number]["operations_out"] = quantity
                elif transaction_type == "TRANSFER_IN":
                    batch_summary[batch_number]["transfer_in"] = quantity
                elif transaction_type == "TRANSFER_OUT":
                    batch_summary[batch_number]["transfer_out"] = quantity

                batch_summary[batch_number]["remaining"] = remaining  # Store remaining quantity

            batch_data = [
                {
                    "batch_id":batch_id,
                    "batch": batch_number,
                    "inbound": values["inbound"],
                    "outbound": values["outbound"],
                    "manufacture_in": values["manufacture_in"],
                    "manufacture_out": values["manufacture_out"],
                    "replacement_in": values["replacement_in"],
                    "replacement_out": values["replacement_out"],
                    "transfer_in": values["transfer_in"],
                    "operations_out": values["operations_out"],
                    "scrapped_out": values["scrapped_out"],
                    "remaining": values["remaining"]
                }
                for batch_number, values in batch_summary.items()
            ]       
       
        batch_price_data = [
        {
            "batch_number": batch.batch_number,
            "unit_price": float(batch.unit_price),
            "created_at": batch.created_at.strftime('%Y-%m-%d'),
        }
        for batch in batchs_in_product
    ]

    return render(request, 'report/batch_wise_product.html', {
        'products': products,
        'batch_data':batch_data,
        'batch_data_json': json.dumps(batch_data),  
        'batch_price_data': json.dumps(batch_price_data), 
        'selected_product_id': product_id,
        "total_remaining_stock_value": total_remaining_stock_value,
        "total_purchase_stock_value": total_purchase_stock_value,
    })



@login_required
def product_report(request, product_id):
    product = get_object_or_404(Product, id=product_id)
    warehouses = Warehouse.objects.all()
    grand_total_stock =0

    valuation_method = request.GET.get('valuation_method','FIFO')

    form = SummaryReportChartForm(request.GET or {'days': 60}) 

    if form.is_valid():
        batch = form.cleaned_data['batch']

    warehouse_data = []
    for warehouse in warehouses:
        stock_data = calculate_stock_value2(product=product, warehouse=warehouse)

        order_by = "created_at" if valuation_method == "FIFO" else "-created_at"
        latest_transaction = InventoryTransaction.objects.filter(
            product=product,
            warehouse=warehouse,
            transaction_type='INBOUND'
        ).order_by(order_by).first()
        unit_cost = latest_transaction.batch.unit_price if latest_transaction and latest_transaction.batch and latest_transaction.batch.unit_price is not None else 0

        stock_value = stock_data['total_available'] * float( unit_cost)
        grand_total_stock += stock_value

        inventory = Inventory.objects.filter(product=product, warehouse=warehouse).first()
        warehouse_reorder_level = inventory.reorder_level if inventory else 0

      
        warehouse_entry = {
            'reorder_level': warehouse_reorder_level,
            'warehouse_name': warehouse.name,
            'warehouse_id': warehouse.id,
            'total_available': stock_data['total_available'],
            'total_purchased': stock_data['total_purchase'],
            'total_manufacture_in': stock_data['total_manufacture_in'],
            'total_manufacture_out': stock_data['total_manufacture_out'],
            'total_existing_in': stock_data['total_existing_in'],

            'total_sold': stock_data['total_sold'],
            'total_refund_out': stock_data['total_replacement_out'],
            'total_refund_in': stock_data['total_replacement_in'],
            'total_incoming': stock_data['total_transfer_in'],
            'total_outgoing': stock_data['total_transfer_out'],
            'total_scrapped_in': stock_data['total_scrapped_in'],
            'total_scrapped_out': stock_data['total_scrapped_out'],
            'total_operations_out': stock_data['total_operations_out'],

            'total_stock_value': stock_data['total_available'] * float(product.unit_price),
            'total_stock': stock_data['total_stock'],
             
        }
        warehouse_data.append(warehouse_entry)

    total_data = calculate_stock_value2(product=product)

    warehouse_data_json = json.dumps(warehouse_data)

    return render(request, 'report/product_report.html', {
        'product': product,
        'warehouse_data': warehouse_data,
        'total_data': total_data,
        'warehouse_data_json': warehouse_data_json,
        'grand_total_stock':grand_total_stock
    })


from inventory.models import TransferItem

@login_required
def warehouse_report(request):
    warehouses = Warehouse.objects.all()
    warehouse_data = []
    product_details=[]
    warehouse_json = None
    days = None
    start_date = None
    end_date = None
    warehouse_name=None
    product_name =None
    transactions=[]
    form = SummaryReportChartForm(request.GET or {'days': 60}) 
    
    if form.is_valid():
        start_date = form.cleaned_data.get('start_date')
        end_date = form.cleaned_data.get('end_date')
        days = form.cleaned_data.get('days')
        warehouse_name = form.cleaned_data.get('warehouse_name') 
        product_name = form.cleaned_data.get('product_name')  

        if start_date and end_date:           
            warehouses = warehouses.filter(created_at__range=(start_date, end_date))
        elif days:
            end_date = timezone.now()
            start_date = end_date - timedelta(days=days)
            warehouses = warehouses.filter(created_at__range=(start_date, end_date))

        filter_conditions = {}

        if warehouse_name:
            filter_conditions["warehouse"] = warehouse_name  

        if product_name:
            filter_conditions["product__name"] = product_name

        transactions = InventoryTransaction.objects.filter(**filter_conditions).values(
            "product_id", "transaction_type"
        ).annotate(total=Sum("quantity"))

 
        transaction_lookup = {}
        for t in transactions:
            key = (t['product_id'], t['transaction_type'])
            transaction_lookup[key] = transaction_lookup.get(key, 0) + t['total']
  
        product_ids = set(t['product_id'] for t in transactions)

        product_data = []

        for product_id in product_ids:
            product_instance = Product.objects.get(id=product_id)

            product_data.append({
                'product_name': product_instance.name,
                'reorder_level': product_instance.reorder_level,
                'total_available': (
                    transaction_lookup.get((product_id, 'EXISTING_ITEM_IN'), 0) +
                    transaction_lookup.get((product_id, 'REPLACEMENT_IN'), 0) +
                    transaction_lookup.get((product_id, 'TRANSFER_IN'), 0) +
                    transaction_lookup.get((product_id, 'INBOUND'), 0) +
                    transaction_lookup.get((product_id, 'MANUFACTURE_IN'), 0) -
                    transaction_lookup.get((product_id, 'REPLACEMENT_OUT'), 0) -
                    transaction_lookup.get((product_id, 'TRANSFER_OUT'), 0) -
                    transaction_lookup.get((product_id, 'OUTBOUND'), 0) -
                    transaction_lookup.get((product_id, 'OPERATIONS_OUT'), 0) -
                    transaction_lookup.get((product_id, 'MANUFACTURE_OUT'), 0)
                ),
                'total_existing_product': transaction_lookup.get((product_id, 'EXISTING_ITEM_IN'), 0),
                'total_replacement_in': transaction_lookup.get((product_id, 'REPLACEMENT_IN'), 0),
                'total_replacement_out': transaction_lookup.get((product_id, 'REPLACEMENT_OUT'), 0),
                'total_transfer_in': transaction_lookup.get((product_id, 'TRANSFER_IN'), 0),
                'total_transfer_out': transaction_lookup.get((product_id, 'TRANSFER_OUT'), 0),
                'total_purchased': transaction_lookup.get((product_id, 'INBOUND'), 0),
                'total_sold': transaction_lookup.get((product_id, 'OUTBOUND'), 0),
                'total_operation_used': transaction_lookup.get((product_id, 'OPERATIONS_OUT'), 0),
                'total_manufacture_in': transaction_lookup.get((product_id, 'MANUFACTURE_IN'), 0),
                'total_manufacture_out': transaction_lookup.get((product_id, 'MANUFACTURE_OUT'), 0),
            })

        product_json = json.dumps(product_data)
 
            
    paginator = Paginator(product_data, 10)  
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    form = SummaryReportChartForm() 
    return render(request, 'report/warehouse_report.html', {
        'warehouse_data': warehouse_data,
        'warehouse_data': page_obj, 
        'page_obj': page_obj,
        'warehouse_json': warehouse_json,
        'product_json': product_json,
         'product_data': product_data,
        'form': form,
        'days': days,
        'start_date': start_date,
        'end_date': end_date,
        'product_details': product_details,
        'warehouse_name':warehouse_name,
        'product_name':product_name
    })



@login_required
def warehouse_report_nofilter(request):
    warehouses = Warehouse.objects.all()
    warehouse_data = []
    warehouse_json = None  
        
    for warehouse in warehouses:
        products_in_warehouse = Inventory.objects.filter(warehouse=warehouse)      
        products_in_warehouse = products_in_warehouse.values('product__id', 'product__product_name').annotate(
            total_available=Sum('quantity')
        )
        
        product_details = []
        for product in products_in_warehouse:
            product_id = product['product__id']
            product_name = product['product__product_name']
            
            total_purchased = PurchaseOrder.objects.filter(product_id=product_id, warehouse=warehouse).aggregate(total=Sum('quantity'))['total'] or 0
            total_sold = SaleOrder.objects.filter(product_id=product_id, warehouse=warehouse).aggregate(total=Sum('quantity'))['total'] or 0
            total_incoming = TransferOrder.objects.filter(product_id=product_id, target_warehouse=warehouse).aggregate(total=Sum('quantity'))['total'] or 0
            total_outgoing = TransferOrder.objects.filter(product_id=product_id, source_warehouse=warehouse).aggregate(total=Sum('quantity'))['total'] or 0
            
            product_details.append({
                'product_name': product_name,
                'total_available': product['total_available'],
                'total_purchased': total_purchased,
                'total_sold': total_sold,
                'total_incoming': total_incoming,
                'total_outgoing': total_outgoing
            })
        
        warehouse_data.append({
            'warehouse_name': warehouse.warehouse_name,
            'products': product_details
        })

    warehouse_json = json.dumps(warehouse_data)

    paginator = Paginator(warehouse_data, 10)  
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    form = SummaryReportChartForm() 
    return render(request, 'report/warehouse_report.html', {
        'warehouse_data': warehouse_data,
        'warehouse_data': page_obj, 
        'page_obj': page_obj,
        'warehouse_json': warehouse_json,
        'form': form,

    })

@login_required
def sale_order_detail(request, sale_order_id):
    sale_order = get_object_or_404(SaleOrder, id=sale_order_id)
    sold_products = SaleOrder.objects.filter(sale_order=sale_order)
    return render(request, 'invmanagement/purchase/purchase_order_details.html', {
        'sale_order': sale_order,
        'psold_products': sold_products,
    })


@login_required
def download_sale_delivery_order_csv(request, order_id):
    sale_order = get_object_or_404(SaleOrder, id=order_id)    

    if 'download' in request.GET:
        response = HttpResponse(content_type='text/csv')
        response['Content-Disposition'] = f'attachment; filename="delivery_order_{sale_order.order_id}.csv"'
        
        writer = csv.writer(response)
        writer.writerow(['Order Number', 'Date', 'customer', 'Product','category', 'Quantity','Unit Price','toatl_price'])

        for sale in sale_order.sale_order.all():
            writer.writerow([
                sale_order.order_id,
                sale_order.order_date,
                 sale_order.customer.name,
                sale.product.name,
                sale.product.category,
                sale.quantity,             
                sale.product.unit_price,
                sale.total_price
            ])
        
        return response
    
    return render(request, 'report/download_sale_delivery_order_csv.html', {'sale_order': sale_order})



@login_required
def generate_sale_challan(request, order_id):
    logo_path2 = os.path.join(settings.MEDIA_ROOT, 'profile_pictures', '5.jpg')  # Alternate option for image
    sale_order = get_object_or_404(SaleOrder, id=order_id)

    if 'download' in request.GET:
        response = HttpResponse(content_type='application/pdf')
        response['Content-Disposition'] = f'attachment; filename="challan_{sale_order.order_id}.pdf"'
       
        p = canvas.Canvas(response, pagesize=A4)
        width, height = A4

        # Header Information
        p.setFont("Helvetica-Bold", 16)
        p.drawString(140, height - 80, f"Challan/Invoice for Order Number: {sale_order.order_id}")
        p.drawString(140, height - 90, f".......................................................................................")
               
        # Logo
        logo_path = 'D:/SCM/dscm/media/logo.png'  
        
        logo_width = 60 
        logo_height = 60  
        p.drawImage(logo_path, 50, height - 110, width=logo_width, height=logo_height)

        # Customer Info
        p.setFont("Helvetica", 12)
        p.drawString(50, height - 150, f"Order Date: {sale_order.order_date}")
        p.drawString(50, height - 170, f"Customer: {sale_order.customer.name}")
        p.drawString(260, height - 170, f"Phone: {sale_order.customer.phone}")
        p.drawString(50, height - 190, f"Address: {sale_order.customer.website}")

        # Table Headers
        p.setFont("Helvetica-Bold", 12)
        p.drawString(50, height - 250, "Product")
        p.drawString(200, height - 250, "Quantity")
        p.drawString(280, height - 250, "Product Type")
        p.drawString(380, height - 250, "Unit Price")
        p.drawString(480, height - 250, "Total Price")

        # Product Lines
        y = height - 280
        p.setFont("Helvetica", 12)
        grand_total = 0  # Initialize grand total

        for sale in sale_order.sale_order.all():
            p.drawString(50, y, sale.product.name)
            p.drawString(225, y, str(sale.quantity))
            p.drawString(290, y, sale.product.product_type if sale.product.product_type else 'N/A')
            p.drawString(390, y, f"{sale.product.unit_price:,.2f}" if sale.product.unit_price else 'N/A')
            p.drawString(480, y, f"{sale.total_price:,.2f}" if sale.total_price else 'N/A')


            grand_total += sale.total_price if sale.total_price else 0
            y -= 20

        p.setFont("Helvetica-Bold", 12)
        p.drawString(380, y - 20, "Grand Total:")
        p.drawString(480, y - 20, f"{grand_total:,.2f}")

        grand_total_words = num2words(grand_total, to='currency', lang='en').replace("euro", "Taka").replace("cents", "paisa").capitalize()

        p.setFont("Helvetica", 14)
        p.drawString(50, y - 40, f"Amount in words: {grand_total_words}")        
   
        cfo_employee = Employee.objects.filter(position__name='CFO').first()
        if cfo_employee:
            p.drawString(50,height - 660, f"Autorized Signature________________")  
            p.drawString(50, height - 680, f"Name:{cfo_employee.name}")  
            p.drawString(50,height - 700, f"Designation:{cfo_employee.position}")  
        else:
            p.drawString(50,height - 660, f"Autorized Signature________________")  
            p.drawString(50, height - 680, f"Name:........") 
            p.drawString(50, height - 700, f"Designation:.....")  
            p.setFont("Helvetica-Bold", 10)
            p.setFillColor('green')
            p.drawString(50,height - 730, f"(Signature is not mandatory due to computerized authorization)")
            
            p.setFont("Helvetica", 10)    
            p.setFillColor('black')       
            p.drawString(50,height - 780, f" Company's address: Block-D, House-123, Road# W2, Eastern Housing 2nd phase,Pallabi,Mirpur")
            p.drawString(50,height - 800, f" Dhaka North, Dhaka-1216, Phone: 01743800705, email:mymeplustech@gmail.com, web:www.mymeplus.com")        

        p.showPage()
        p.save()
        return response
    return render(request, 'report/generate_sale_challan_pdf.html', {'sale_order': sale_order})




@login_required
def download_purchase_delivery_order_csv(request, order_id):
    purchase_order = get_object_or_404(PurchaseOrder, id=order_id)    

    if 'download' in request.GET:
        response = HttpResponse(content_type='text/csv')
        response['Content-Disposition'] = f'attachment; filename="delivery_order_{purchase_order.purchase_order_id}.csv"'
        
        writer = csv.writer(response)
        writer.writerow(['Order Number', 'Date', 'Product', 'Quantity', 'Product Type', 'Unit Price'])

        for purchase in purchase_order.purchases_order.all():
            writer.writerow([
                purchase_order.purchase_order_id,
                purchase_order.order_date,
                purchase.product.product_name,
                purchase.quantity,
                purchase.product.product_type,
                purchase.product.unit_price
            ])
        
        return response
    
    return render(request, 'report/download_purchase_delivery_order_csv.html', {'purchase_order': purchase_order})


@login_required
def generate_purchase_challan(request, order_id): 
    purchase_order = get_object_or_404(PurchaseOrder, id=order_id)
    if 'download' in request.GET:
        response = HttpResponse(content_type='application/pdf')
        response['Content-Disposition'] = f'attachment; filename="challan_{purchase_order.purchase_order_id}.pdf"'
       
        p = canvas.Canvas(response, pagesize=A4)
        width, height = A4

        p.setFont("Helvetica-Bold", 16)
        p.drawString(150, height - 80, f"Challan/Invoice for Order: {purchase_order.purchase_order_id}")

        p.setFont("Helvetica", 12)
        p.drawString(50, height - 120, f"Order Date: {purchase_order.order_date}")
        p.drawString(50, height - 140, f"Customer: {purchase_order.supplier.supplier_name}")
        p.drawString(50, height - 160, f"Address: {purchase_order.supplier.address}")

        p.setFont("Helvetica-Bold", 12)
        p.drawString(50, height - 230, "Product")
        p.drawString(250, height - 230, "Quantity")
        p.drawString(350, height - 230, "product Type")
        p.drawString(450, height - 230, "Unit price")

        y = height - 260
        p.setFont("Helvetica", 12)
        for purchase in purchase_order.purchases_order.all():
            p.drawString(50, y, purchase.product.product_name)
            p.drawString(250, y, str(purchase.quantity))
            p.drawString(350, y, purchase.product.product_type if purchase.product.product_type else 'N/A')
            p.drawString(450, y, str(purchase.product.unit_price) if purchase.product.unit_price else 'N/A')
            y -= 20
   

        cfo_employee = Employee.objects.filter(position='CFO').first()
        if cfo_employee:
            p.drawString(50,height - 700, f"Autorized Signature________________")  
            p.drawString(50, height - 720, f"Name:{cfo_employee.name}")  
            p.drawString(50,height - 740, f"Designation:{cfo_employee.position}")  
        else:
            p.drawString(50,height - 700, f"Autorized Signature________________")  
            p.drawString(50, height - 720, f"Name:........") 
            p.drawString(50, height - 740, f"Designation:.....")  
            p.setFont("Helvetica-Bold", 10)
            p.setFillColor('green')
            p.drawString(50,height - 780, f"Signature is not mandatory due to computerized authorization")  

        p.showPage()
        p.save()

        return response
  
    return render(request, 'report/generate_purchase_challan_pdf.html', {'purchase_order': purchase_order})




################## Reorder level and lead time notifications ###############################


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


def calculate_average_usage(product, warehouse=None, days=30):
    start_date = now() - timedelta(days=days)
    filters = {
        'product': product,
        'transaction_type': 'OUTBOUND',
        'created_at__gte': start_date
    }
    if warehouse:
        filters['warehouse'] = warehouse
    
    usage = InventoryTransaction.objects.filter(**filters).aggregate(
        total_usage=Sum('quantity')
    )['total_usage'] or 0

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


@login_required
def monitor_inventory_status(request):
    low_stock_alerts = []
    warehouse_wise_low_stock = []
    low_stock_products = []

    for product in Product.objects.all():    
        product_average_usage = calculate_average_usage(product)  
        product_required_stock = product_average_usage * product.lead_time   
        warehouse_stocks = Inventory.objects.filter(product=product)

        for stock in warehouse_stocks:
            warehouse_avg_usage = calculate_average_usage(product, stock.warehouse)
            warehouse_required_stock = warehouse_avg_usage * product.lead_time
            warehouse_reorder_level=stock.reorder_level
            
            if stock.quantity < warehouse_required_stock:  # Warehouse-based stock check
                warehouse_wise_low_stock.append({
                    'product': product.name,
                    'warehouse': stock.warehouse.name if stock.warehouse else 'N/A',
                    'current_stock': stock.quantity,
                    'required_stock': warehouse_required_stock,
                    'average_usage': warehouse_avg_usage,
                    'lead_time': product.lead_time,
                })

            elif stock.quantity <= warehouse_reorder_level:
                warehouse_wise_low_stock.append({
                    'product': product.name,
                    'warehouse': stock.warehouse.name,
                    'average_usage': warehouse_avg_usage,
                    'current_stock': stock.quantity,
                    'required_stock': warehouse_required_stock,
                    'reorder_level': warehouse_reorder_level,
                    'lead_time': product.lead_time,
                })
    
        total_stock = warehouse_stocks.aggregate(total_quantity=Sum('quantity'))['total_quantity'] or 0
        if total_stock <= product.reorder_level:
            low_stock_products.append({
                'product': product.name,
                'warehouse': 'All Warehouses',
                'current_stock': total_stock,
                'reorder_level': product.reorder_level,
                'lead_time': product.lead_time,
            })
        if total_stock < product_required_stock:
            low_stock_alerts.append({
                'product': product.name,
                'warehouse': 'All Warehouses',
                'current_stock': total_stock,
                'required_stock': product_required_stock,
                'average_usage': product_average_usage,
                'lead_time': product.lead_time,
            })
      

    context = {
        'low_stock_alerts': low_stock_alerts,  # Product-Level Low Stock
        'warehouse_wise_low_stock': warehouse_wise_low_stock,  # Warehouse-Level Low Stock
        'low_stock_products': low_stock_products,  # Reorder-Level Products
    }

    return render(request, 'report/monitor_inventory_status.html', context)





from decimal import Decimal
from django.db.models import Sum, F, ExpressionWrapper, DecimalField
from django.db.models.functions import Coalesce


def Calculate_sales_profit(request):    
   
    purchases = InventoryTransaction.objects.filter(
        transaction_type='INBOUND',
        quantity__gt=0
    ).annotate(
        purchase_line_total=ExpressionWrapper(
            F('quantity') * F('batch__unit_price'),
            output_field=DecimalField(max_digits=20, decimal_places=2)
        )
    ).values('product__name').annotate(
        purchase_item_total=Sum('purchase_line_total')
    )

    total_purchase_cost = sum([item['purchase_item_total'] for item in purchases]) or Decimal('0.00')


    sales_product_cost = InventoryTransaction.objects.filter(
        transaction_type='OUTBOUND',
        quantity__gt=0
    ).annotate(
        sale_product_line_total=ExpressionWrapper(
            F('quantity') * F('batch__unit_price'),  
            output_field=DecimalField(max_digits=20, decimal_places=2)
        )
    ).values('product__name').annotate(
        sale_item_cost_total=Sum('sale_product_line_total')
    )

    total_sold_product_cost = sum([item['sale_item_cost_total'] for item in sales_product_cost]) or Decimal('0.00')


    sales_revenue = InventoryTransaction.objects.filter(
        transaction_type='OUTBOUND',
        quantity__gt=0
    ).annotate(
        sale_revenue_line_total=ExpressionWrapper(
            F('quantity') * Coalesce(F('sale_unit_cost'), F('batch__sale_price')),  # prioritize unit_selling_price
            output_field=DecimalField(max_digits=20, decimal_places=2)
        )
    ).values('product__name').annotate(
        sale_revenue_item_total=Sum('sale_revenue_line_total')
    )

    total_revenue = sum([item['sale_revenue_item_total'] for item in sales_revenue]) or Decimal('0.00')

    total_profit = total_revenue - total_sold_product_cost



    chart_data = {
        'total_purchased': float(total_purchase_cost),
        'total_revenue': float(total_revenue),
        'total_cost': float(total_sold_product_cost),
        'total_profit': float(total_profit),
    }

  
  
    return render(request, 'report/calculate_profit.html', {
        'chart_data': json.dumps(chart_data),
       'total_purchased': float(total_purchase_cost),
        'total_revenue': float(total_revenue),
        'total_cost': float(total_sold_product_cost),
        'total_profit': float(total_profit),

    })


from django.db.models import Sum, F, DecimalField, ExpressionWrapper, Value as V
from django.db.models.functions import Coalesce
from decimal import Decimal

def calculate_product_wise_revenue(request):
        # Step 1: Aggregate purchases by product
    purchases = InventoryTransaction.objects.filter(
        transaction_type='INBOUND',
        quantity__gt=0
    ).values('product_id', 'product__name').annotate(
        total_purchased_qty=Sum('quantity'),
        total_purchase_cost=Sum(
            ExpressionWrapper(
                F('quantity') * F('batch__unit_price'),
                output_field=DecimalField(max_digits=20, decimal_places=2)
            )
        )
    )

    # Step 2: Aggregate sales by product
    sales = InventoryTransaction.objects.filter(
        transaction_type='OUTBOUND',
        quantity__gt=0
    ).values('product_id', 'product__name').annotate(
        total_sold_qty=Sum('quantity'),
        total_revenue=Sum(
            ExpressionWrapper(
                F('quantity') * Coalesce(F('sale_unit_cost'), F('batch__sale_price')),
                output_field=DecimalField(max_digits=20, decimal_places=2)
            )
        ),
        total_cost_of_sold=Sum(
            ExpressionWrapper(
                F('quantity') * F('batch__unit_price'),
                output_field=DecimalField(max_digits=20, decimal_places=2)
            )
        )
    )
    grand_total_profit = Decimal('0.00')

    for sale in sales:
        revenue = sale.get('total_revenue') or Decimal('0.00')
        cost = sale.get('total_cost_of_sold') or Decimal('0.00')
        profit = revenue - cost
        grand_total_profit += profit

    # Step 3: Build a merged product dictionary
    product_map = {}

    # Add purchases
    for item in purchases:
        pid = item['product_id']
        product_map[pid] = {
            'product': item['product__name'],
            'purchased_qty': item['total_purchased_qty'] or 0,
            'purchase_cost': item['total_purchase_cost'] or Decimal('0.00'),
            'sold_qty': 0,
            'revenue': Decimal('0.00'),
            'cost_of_sold': Decimal('0.00'),
            'profit': Decimal('0.00'),
            'purchase_unit_price': Decimal('0.00'),
            'sale_unit_price': Decimal('0.00'),
        }

    # Add/merge sales
    for item in sales:
        pid = item['product_id']
        if pid not in product_map:
            product_map[pid] = {
                'product': item['product__name'],
                'purchased_qty': 0,
                'purchase_cost': Decimal('0.00'),
                'sold_qty': 0,
                'revenue': Decimal('0.00'),
                'cost_of_sold': Decimal('0.00'),
                'profit': Decimal('0.00'),
            }

        product_map[pid]['sold_qty'] = item['total_sold_qty'] or 0
        product_map[pid]['revenue'] = item['total_revenue'] or Decimal('0.00')
        product_map[pid]['cost_of_sold'] = item['total_cost_of_sold'] or Decimal('0.00')
        product_map[pid]['profit'] = product_map[pid]['revenue'] - product_map[pid]['cost_of_sold']

    # Step 4: Convert to list for template rendering or export
    product_report = list(product_map.values())

    return render(request,'report/product_wise_details_revenue.html',{'product_report': product_report,'grand_total_profit':grand_total_profit})

