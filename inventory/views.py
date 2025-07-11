from django.shortcuts import render,redirect,get_object_or_404
from django.db.models import Sum, Avg,Count,Q,Case, When, IntegerField,F,Max,DurationField, DecimalField,FloatField
from django.db import transaction
from django.contrib import messages
from django.http import JsonResponse
from django.template.loader import render_to_string
from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger
from django.contrib.auth.decorators import login_required
import json
from itertools import groupby
from operator import itemgetter
from django.core.paginator import Paginator
from django.utils.timezone import now

from inventory.models import Product, InventoryTransaction
from manufacture.models import ManufactureQualityControl
from repairreturn.models import Replacement
from product.models import Product
from purchase.models import QualityControl
from sales.models import SaleQualityControl
from .models import Inventory,InventoryTransaction
from .models import InventoryTransaction, Inventory,Warehouse,Location
from .forms import QualityControlCompletionForm,InventoryTransactionForm,AddWarehouseForm,AddLocationForm
from .models import TransferItem,TransferOrder

from .forms import TransferProductForm
from operator import itemgetter

import logging
logger = logging.getLogger(__name__)


from myproject.utils import update_sale_shipment_status,update_sale_order,update_sale_request_order
from myproject.utils import get_warehouse_stock,calculate_stock_value,calculate_stock_value2
from myproject.utils import update_purchase_order,update_purchase_request_order,update_shipment_status

from core.forms import CommonFilterForm
from reporting.forms import SummaryReportChartForm
from django.utils import timezone
from datetime import timedelta

import uuid
from manufacture.models import MaterialsRequestOrder
 
from.forms import TransactionFilterForm
from django.db.models.functions import TruncDate

@login_required
def inventory_dashboard(request):
    return render(request,'inventory/inventory_dashboard.html')

@login_required
def manage_warehouse(request, id=None):  
    instance = get_object_or_404(Warehouse, id=id) if id else None
    message_text = "updated successfully!" if id else "added successfully!"
    form = AddWarehouseForm(request.POST or None, instance=instance)

    if request.method == 'POST' and form.is_valid():
        form_instance=form.save(commit=False)
        form_instance.user=request.user
        form_instance.save()
        messages.success(request, message_text)
        return redirect('inventory:create_warehouse')

    datas = Warehouse.objects.all().order_by('-created_at')
    paginator = Paginator(datas, 10)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    return render(request, 'inventory/manage_warehouse.html', {
        'form': form,
        'instance': instance,
        'datas': datas,
        'page_obj': page_obj
    })

@login_required
def delete_warehouse(request, id):
    instance = get_object_or_404(Warehouse, id=id)
    if request.method == 'POST':
        instance.delete()
        messages.success(request, "Deleted successfully!")
        return redirect('inventory:create_warehouse')

    messages.warning(request, "Invalid delete request!")
    return redirect('inventory:create_warehouse')



@login_required
def manage_location(request, id=None):   

    instance = get_object_or_404(Location, id=id) if id else None
    message_text = "updated successfully!" if id else "added successfully!"
    form = AddLocationForm(request.POST or None, instance=instance)

    if request.method == 'POST' and form.is_valid():
        form_instance = form.save(commit=False)
        form_instance.user=request.user
        form_instance.save()
        messages.success(request, message_text)
        return redirect('inventory:create_location')

    datas = Location.objects.all().order_by('-created_at')
    paginator = Paginator(datas, 10)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    return render(request, 'inventory/manage_location.html', {
        'form': form,
        'instance': instance,
        'datas': datas,
        'page_obj': page_obj
    })
@login_required
def delete_location(request, id):
    instance = get_object_or_404(Location, id=id)
    if request.method == 'POST':
        instance.delete()
        messages.success(request, "Deleted successfully!")
        return redirect('inventory:create_location')

    messages.warning(request, "Invalid delete request!")
    return redirect('inventory:create_location')


@login_required
def get_locations(request):
    warehouse_id = request.GET.get('warehouse_id')
    locations = Location.objects.filter(warehouse_id=warehouse_id)

    options = '<option value="">Select Location</option>'  
    for location in locations:
        options += f'<option value="{location.id}">{location.name}</option>'
    return JsonResponse(options, safe=False)




@login_required
def complete_quality_control(request, qc_id):
    quality_control = get_object_or_404(QualityControl, id=qc_id)
    
    good_quantity = quality_control.good_quantity

    purchase_dispatch_item = quality_control.purchase_dispatch_item
    purchase_shipment = purchase_dispatch_item.purchase_shipment
    purchase_order = purchase_shipment.purchase_order
    purchase_request_order = purchase_order.purchase_request_order
    purchase_order_item = purchase_dispatch_item.dispatch_item
    batch_fetch = purchase_order_item.batch
  
 

    if request.method == 'POST':
        selected_warehouse_id = request.POST.get('warehouse')
        selected_warehouse = Warehouse.objects.get(id=selected_warehouse_id) if selected_warehouse_id else None

        form = QualityControlCompletionForm(request.POST, warehouse=selected_warehouse)
        if form.is_valid():
            warehouse = form.cleaned_data['warehouse']
            location = form.cleaned_data['location']
           
            try:
                with transaction.atomic():

                    inventory_transaction = InventoryTransaction.objects.create(
                        user=request.user,
                        warehouse=warehouse,
                        location=location,
                        product=quality_control.product,
                        batch = batch_fetch,
                        transaction_type='INBOUND',
                        quantity=good_quantity,
                        purchase_order=purchase_dispatch_item.dispatch_item.purchase_order
                    )

                    inventory, created = Inventory.objects.get_or_create(
                        warehouse=warehouse,
                        location=location,
                        product=quality_control.product,
                        batch = batch_fetch,
                        user=request.user,
                        defaults={
                            'quantity': good_quantity 
                        }
                    )
        
                    if not created:
                        inventory.quantity += good_quantity
                        inventory.save()
                        messages.success(request, "Inventory updated successfully.")
                    else:
                        messages.success(request, "Inventory created successfully.")

                    inventory_transaction.inventory_transaction = inventory
                    inventory_transaction.save()
                    messages.success(request, "Inventory and inventory_transaction linking created successfully.")
                    

            except Exception as e: 
                logger.error("Error creating delivery: %s", e)
                messages.error(request, f"An error occurred {str(e)}")
                return redirect('purchase:qc_dashboard')
                 
            purchase_dispatch_item.status = 'DELIVERED'
            purchase_dispatch_item.save()   

            update_purchase_order(purchase_order.id)      
            update_shipment_status(purchase_shipment.id)
            update_purchase_request_order(purchase_request_order.id)  
            purchase_shipment.update_shipment_status()
       
            messages.success(request, "Quality control completed and product added to inventory.")
            return redirect('purchase:qc_dashboard')
        else:      
            print(form.errors)    
            messages.error(request, "Failed to update inventory. Form is not valid.")
  

    form = QualityControlCompletionForm(initial={'batch':batch_fetch})
    return render(request, 'inventory/complete_quality_control.html', {
        'form': form,
        'quality_control': quality_control,
    })




@login_required
def complete_manufacture_quality_control(request, qc_id):

    quality_control = get_object_or_404(ManufactureQualityControl, id=qc_id)

    total_quantity = quality_control.total_quantity
    good_quantity = quality_control.good_quantity
    bad_quantity = quality_control.bad_quantity

    if good_quantity + bad_quantity > total_quantity:
        messages.error(request, "Invalid quantities: good + bad exceeds total.")
        return redirect('manufacture:qc_dashboard')

    materials_request_order = quality_control.finish_goods_from_production.materials_request_order
    if not materials_request_order:
       materials_request_order = MaterialsRequestOrder.objects.create(
        order_id=f"DFGS-{uuid.uuid4().hex[:8].upper()}"
    )
   
    finish_goods_from_production = quality_control.finish_goods_from_production
    finish_goods_from_production.materials_request_order = materials_request_order
    finish_goods_from_production.save()

    if request.method == 'POST':
        selected_warehouse_id = request.POST.get('warehouse')
        selected_warehouse = get_object_or_404(Warehouse, id=selected_warehouse_id) if selected_warehouse_id else None

        form = QualityControlCompletionForm(request.POST, warehouse=selected_warehouse)
        if form.is_valid():
            warehouse = form.cleaned_data['warehouse']
            location = form.cleaned_data['location']

            try:
                with transaction.atomic(): 

                    if InventoryTransaction.objects.filter(
                        manufacture_order=materials_request_order,
                        transaction_type='MANUFACTURE_IN',
                        product=quality_control.product,
                    ).exists():
                        messages.error(request, "This transaction has already been recorded.")
                        return redirect('manufacture:qc_dashboard')

                    inventory_transaction = InventoryTransaction.objects.create(
                        user=request.user,
                        warehouse=warehouse,
                        location=location,
                        product=quality_control.product,
                        transaction_type='MANUFACTURE_IN',
                        quantity=good_quantity,
                        manufacture_order=materials_request_order,
                    )
                    inventory, created = Inventory.objects.get_or_create(
                        warehouse=warehouse,
                        location=location,
                        product=quality_control.product,
                        user=request.user,
                        defaults={
                            'quantity': good_quantity 
                        }
                    )
        
                    if not created:
                        inventory.quantity += good_quantity
                        inventory.save()
                        messages.success(request, "Inventory updated successfully.")
                    else:
                        messages.success(request, "Inventory created successfully.")
                
                    inventory_transaction.inventory_transaction = inventory
                    inventory_transaction.save()
                    messages.success(request, "Inventory and inventory_transaction linking created successfully.")
                
            except Exception as e: 
                logger.error("Error creating delivery: %s", e)
                messages.error(request, f"An error occurred {str(e)}")
                return redirect('manufacture:qc_dashboard')
         
            quality_control.finish_goods_from_production.status = 'RECEIVED'
            quality_control.finish_goods_from_production.save()

            messages.success(request, "Quality control completed and product added to inventory.")
            return redirect('manufacture:qc_dashboard')
        else:
            print("Form errors:", form.errors)
    else:
        form = QualityControlCompletionForm()

    return render(request, 'inventory/complete_quality_control.html', {
        'form': form,
        'quality_control': quality_control,
    })



####################  Transfer section ##############################################

@login_required
def create_transfer(request):
    if 'transfer_basket' not in request.session:
        request.session['transfer_basket'] = []

    form = TransferProductForm(request.POST or None)
    if request.method == 'POST':
        form = TransferProductForm(request.POST or None)
        if 'add_to_basket' in request.POST:
            if form.is_valid():
                product = form.cleaned_data['product']
                source_warehouse = form.cleaned_data['source_warehouse']
                target_warehouse = form.cleaned_data['target_warehouse']
                quantity = form.cleaned_data['quantity']
                batch = form.cleaned_data['batch']

                transfer_basket = request.session.get('transfer_basket', [])
                product_in_basket = next((item for item in transfer_basket if item['id'] == product.id and item['source_warehouse_id'] == source_warehouse.id and item['target_warehouse_id'] == target_warehouse.id), None)

                if product_in_basket:
                    product_in_basket['quantity'] += quantity
                else:
                    transfer_basket.append({
                        'id': product.id,
                        'product_name': product.name,
                        'sku': product.sku,
                        'quantity': quantity,
                        'source_warehouse_id': source_warehouse.id,
                        'source_warehouse_name': source_warehouse.name,
                        'target_warehouse_id': target_warehouse.id,
                        'target_warehouse_name': target_warehouse.name,
                        'batch_id':batch.id
                    })

                request.session['transfer_basket'] = transfer_basket
                request.session.modified = True
                messages.success(request, f"Added '{product.name}' to the transfer basket")
                return redirect('inventory:create_transfer')
            else:
                print(form.errors)
                messages.error(request, "Form is invalid. Please check the details and try again.")

        elif 'action' in request.POST:
            action = request.POST.get('action')
            product_id = int(request.POST.get('product_id', 0))
            source_warehouse_id = int(request.POST.get('source_warehouse_id', 0))
            target_warehouse_id = int(request.POST.get('target_warehouse_id', 0))

            if action == 'update':
                new_quantity = int(request.POST.get('quantity', 1))
                for item in request.session['transfer_basket']:
                    if item['id'] == product_id and item['source_warehouse_id'] == source_warehouse_id and item['target_warehouse_id'] == target_warehouse_id:
                        item['quantity'] = new_quantity
                        break
                messages.success(request, "Quantity updated successfully.")

            elif action == 'delete':
                request.session['transfer_basket'] = [
                    item for item in request.session['transfer_basket']
                    if not (item['id'] == product_id and item['source_warehouse_id'] == source_warehouse_id and item['target_warehouse_id'] == target_warehouse_id)
                ]
                messages.success(request, "Product removed successfully.")
                
            request.session.modified = True
            return redirect('inventory:create_transfer')

        elif 'confirm_transfer' in request.POST:
            transfer_basket = request.session.get('transfer_basket', [])
            if not transfer_basket:
                messages.error(request, "Transfer basket is empty. Add products before confirming the transfer.")
                return redirect('inventory:create_transfer')
            return redirect('inventory:confirm_transfer')
    transfer_basket = request.session.get('transfer_basket', [])
    return render(request, 'inventory/transfer/create_transfer.html', {'form': form, 'transfer_basket': transfer_basket})

from purchase.models import Batch

@login_required
def confirm_transfer(request):
    transfer_basket = request.session.get('transfer_basket', [])
    if not transfer_basket:
        messages.error(request, "Transfer basket is empty. Cannot confirm the transfer.")
        return redirect('inventory:create_transfer')

    if request.method == 'POST':
        try:
            with transaction.atomic():
                transfer_order = TransferOrder.objects.create(
                    order_number='TO-' + str(int(now().timestamp())),
                )

                for item in transfer_basket:
                    product = get_object_or_404(Product, id=item['id'])
                    source_warehouse = get_object_or_404(Warehouse, id=item['source_warehouse_id'])
                    target_warehouse = get_object_or_404(Warehouse, id=item['target_warehouse_id'])
                    transfer_quantity = item['quantity']
                    batch = get_object_or_404(Batch, id=item['batch_id'])

                    if transfer_quantity <= 0:
                        raise ValueError(f"Invalid transfer quantity for {product.name}. Quantity must be greater than zero.")

                    source_stock = get_warehouse_stock(source_warehouse, product)
                    if source_stock < transfer_quantity:
                        messages.error(
                            request,
                            f"Not enough stock for {product.name} in {source_warehouse.name}. "
                            f"Available: {source_stock}, Requested: {transfer_quantity}"
                        )
                        return redirect('inventory:create_transfer')

                    source_inventory, created = Inventory.objects.get_or_create(
                        warehouse=source_warehouse,
                        batch=batch,
                        product=product,
                        defaults={'quantity': 0}
                    )

                    if source_inventory.quantity < transfer_quantity:
                        raise ValueError(f"Insufficient quantity in {source_warehouse.name} for {product.name}")

                    source_inventory.quantity -= transfer_quantity
                    source_inventory.save()
                    batch.remaining_quantity -= transfer_quantity
                    batch.save()

                    transaction_out = InventoryTransaction.objects.create(
                        user=request.user,
                        warehouse=source_warehouse,
                        product=product,
                        transaction_type='TRANSFER_OUT',
                        quantity=transfer_quantity,
                        batch=batch,
                        transaction_date=now(),
                        remarks=f"Transferred {transfer_quantity} units of {product.name} to {target_warehouse.name}"
                    )
                    transaction_out.inventory_transaction = source_inventory
                    transaction_out.save()

                    target_inventory, created = Inventory.objects.get_or_create(
                        warehouse=target_warehouse,
                        product=product,
                        batch=batch,
                        defaults={'quantity': 0}
                    )

                    target_inventory.quantity += transfer_quantity
                    target_inventory.save()

                    transaction_in = InventoryTransaction.objects.create(
                        user=request.user,
                        warehouse=target_warehouse,
                        product=product,
                        transaction_type='TRANSFER_IN',
                        batch=batch,
                        quantity=transfer_quantity,
                        transaction_date=now(),
                        remarks=f"Received {transfer_quantity} units of {product.name} from {source_warehouse.name}"
                    )
                    transaction_in.inventory_transaction = target_inventory
                    transaction_in.save()

                    batch.remaining_quantity += transfer_quantity
                    batch.save() 
                                      

                    TransferItem.objects.create(
                        product=product,
                        transfer_order=transfer_order,
                        source_warehouse=source_warehouse,
                        target_warehouse=target_warehouse,
                        quantity=transfer_quantity,
                        batch=batch,
                        user=request.user,
                        remarks=f"Transferred {transfer_quantity} units of {product.name}"
                    )

                transfer_order.order_status = 'COMPLETED'
                transfer_order.save()

                request.session['transfer_basket'] = []
                request.session.modified = True
                messages.success(request, "Transfer order processed successfully!")
                return redirect('inventory:create_transfer')
        except Exception as e:
            logger.error(f"Error processing transfer order: {e}")    
            messages.error(request, f"An error occurred: {str(e)}")
            return redirect('inventory:create_transfer')

    return render(request, 'inventory/transfer/confirm_transfer.html', {'transfer_basket': transfer_basket})


@login_required
def transfer_order_list(request):
    transfer_order=None
    
    transfer_orders = TransferOrder.objects.all().order_by('-created_at') 
    form = CommonFilterForm(request.GET or None)
    if form.is_valid():
        transfer_order = form.cleaned_data['transfer_id']
        if transfer_order:
            transfer_orders = transfer_orders.filter(order_number = transfer_order)

    paginator = Paginator(transfer_orders,10)  
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    form=CommonFilterForm()

    return render(request, 'inventory/transfer/transfer_order_list.html', {
        'transfer_orders': transfer_orders,  
        'page_obj':page_obj,
        'form':form,
        'transfer_order':transfer_order
        
    })


@login_required
def transfer_order_detail(request,transfer_order_id):
    transfer_order = get_object_or_404(TransferOrder, id=transfer_order_id)
    transferred_products =TransferItem.objects.filter(transfer_order=transfer_order)
    return render(request, 'inventory/transfer/transfer_order_details.html', {
       
        'transferred_products': transferred_products,
    })




@login_required
def inventory_list(request):   
    products = Product.objects.all()
    warehouses = Warehouse.objects.all()
    data = []
    grand_total_stock_value = 0
    days = None
    start_date = None
    end_date = None
    date_filter = {}
    warehouse_name=None
   
    product_name=None
    grouped_data = []
    chart_data = {}     
    page_obj = None
    warehouse_json={}
  
    valuation_method = request.GET.get("valuation_method", "FIFO")
    form = SummaryReportChartForm(request.GET or None)

    if form.is_valid():
        start_date = form.cleaned_data.get('start_date')
        end_date = form.cleaned_data.get('end_date')
        days = form.cleaned_data.get('days')
        warehouse_name = form.cleaned_data.get('warehouse_name')
        product_name = form.cleaned_data.get('product_name')

        products = Product.objects.all() if not product_name else Product.objects.filter(id=product_name.id)
        warehouses = Warehouse.objects.all() if not warehouse_name else Warehouse.objects.filter(id=warehouse_name.id)
  
        date_filter = {}
        if start_date and end_date:
            date_filter = {'created_at__range': (start_date, end_date)}
        elif days:
            end_date = timezone.now()
            start_date = end_date - timedelta(days=days)
            date_filter = {'created_at__range': (start_date, end_date)}

        stock_results = []
        data = []
        grand_total_stock_value = 0 


        for product in products:
            inventories = product.product_inventories.filter(**date_filter) 

            if warehouse_name:
                inventories = inventories.filter(warehouse__in=warehouses)

            for inventory in inventories:
                stock_data = calculate_batch_stock_value(product, inventory.warehouse,valuation_method)
                stock_results.append(stock_data)

                order_by = "created_at" if valuation_method == "FIFO" else "-created_at"
                latest_transaction = InventoryTransaction.objects.filter(
                    product=product,
                    warehouse=warehouse_name,
                    transaction_type='INBOUND'
                ).order_by(order_by).first()

                unit_cost = latest_transaction.batch.unit_price if latest_transaction and latest_transaction.batch and latest_transaction.batch.unit_price is not None else 0

                total_available = stock_data['total_available']
                total_stock_value =float( total_available) * float(unit_cost)
                grand_total_stock_value += stock_data['stock_value']

                print(f'total_stock_value= { total_stock_value }  grand_total_stock_value={ grand_total_stock_value}')

                # Get reorder level
                inventory_reorder_level = Inventory.objects.filter(product=product, warehouse=inventory.warehouse).first()
                warehouse_reorder_level = inventory_reorder_level.reorder_level if inventory_reorder_level else 0

                data.append({
                    'product': product.name,
                    'product_reorder_level':product.reorder_level,
                    'reorder_level': warehouse_reorder_level,
                    'warehouse': inventory.warehouse,                 
                    'total_purchase': stock_data['total_purchase'],
                    'total_sold': stock_data['total_sold'],
                    'total_manufacture_in': stock_data['total_manufacture_in'],
                    'total_manufacture_out': stock_data['total_manufacture_out'],

                    'total_existing_in': stock_data['total_existing_in'],
                    'total_operations_out': stock_data['total_operations_out'],
                    'total_transfer_out': stock_data['total_transfer_out'],
                    'total_transfer_in': stock_data['total_transfer_in'],

                    'total_replacement_out': stock_data['total_replacement_out'],
                    'total_replacement_in': stock_data['total_replacement_in'], 
                    'total_scrapped_out': stock_data['total_scrapped_out'],
                    'total_scrapped_in': stock_data['total_scrapped_in'],     

                    'total_stock': stock_data['total_stock'],
                    'total_available': stock_data['total_available'],           
                    'stock_value': stock_data['stock_value'], 
                })

        # Ensure chart data is generated if there's valid data
        chart_data = {}
        if data:
            chart_data = {
                'labels': [f"{item['product']} ({item['warehouse'].name})" for item in data],            
                'product_reorder_level': [float(item['product_reorder_level']) for item in data],
                'reorder_level': [float(item['reorder_level']) for item in data],
                'total_purchase': [float(item['total_purchase']) for item in data],
                'total_sold': [float(item['total_sold']) for item in data],
                'total_manufacture_in': [float(item['total_manufacture_in']) for item in data],
                'total_manufacture_out': [float(item['total_manufacture_out']) for item in data],
                'total_existing_in': [float(item['total_existing_in']) for item in data],
                'total_operations_out': [float(item['total_operations_out']) for item in data],
                'total_transfer_in': [float(item['total_transfer_in']) for item in data],
                'total_transfer_out': [float(item['total_transfer_out']) for item in data],
                'total_replacement_out': [float(item['total_replacement_out']) for item in data],
                'total_replacement_in': [float(item['total_replacement_in']) for item in data],
                'total_scrapped_out': [float(item['total_scrapped_out']) for item in data],
                'total_scrapped_in': [float(item['total_scrapped_in']) for item in data],

                'total_stock': [float(item['total_stock']) for item in data],
                'total_available': [float(item['total_available']) for item in data],
                'total_stock_value': [float(item['stock_value']) for item in data],
            }

        warehouse_json = json.dumps(chart_data)


        warehouse_json = json.dumps(chart_data)

        # Paginate results
        paginator = Paginator(data, 10)
        page_number = request.GET.get('page')
        page_obj = paginator.get_page(page_number)

        # Group data by warehouse
        grouped_data = []
        for warehouse, items in groupby(sorted(data, key=lambda x: x['warehouse'].name), key=lambda x: x['warehouse'].name):
            items_list = list(items)
            warehouse_total_stock_value = sum(item['stock_value'] for item in items_list)
            grouped_data.append((warehouse, items_list, warehouse_total_stock_value))

        form = SummaryReportChartForm()

    context = {
        'grouped_data': grouped_data,
        'product_wise_data': page_obj,
        'warehouse_json': warehouse_json,
        'grand_total_stock_value': grand_total_stock_value,
        'form': form,
        'days': days,
        'start_date': start_date,
        'end_date': end_date,
        'warehouse_name':warehouse_name,
        'product_name':product_name
    }
    return render(request, 'inventory/inventory_list.html', context)



from myproject.utils import calculate_batch_stock_value

def inventory_aggregate_list(request):
    grand_total_stock_value = 0
    days = None
    start_date = None
    end_date = None
    aggregated_data = []
    chart_data = {}
    product_name=None
    warehouse_name=None
  
    form = SummaryReportChartForm(request.GET or None)  
    valuation_method = request.GET.get("valuation_method", "LIFO")
   

    if form.is_valid():
        start_date = form.cleaned_data.get('start_date')
        end_date = form.cleaned_data.get('end_date')
        days = form.cleaned_data.get('days')
        product_name = form.cleaned_data.get('product_name')
        warehouse_name = form.cleaned_data.get('warehouse_name')

        products = Product.objects.none()
        if product_name:
            products = Product.objects.filter(id=product_name.id)

        if start_date and end_date:
            products = Product.objects.filter(
                product_inventories__created_at__range=(start_date, end_date)
            ).distinct()

        elif days:
            end_date = timezone.now()
            start_date = end_date - timedelta(days=days)
            products = Product.objects.filter(
                product_inventories__created_at__range=(start_date, end_date)
            ).distinct()

        for product in products:
            inventories = product.product_inventories.all()

            if start_date and end_date:
                inventories = inventories.filter(created_at__range=(start_date, end_date))
            elif days:
                inventories = inventories.filter(created_at__range=(start_date, end_date))

            order_by = "created_at" if valuation_method == "LIFO" else "-created_at"
            latest_transaction = InventoryTransaction.objects.filter(
                    product=product,                    
                    transaction_type='INBOUND'
                ).order_by(order_by).first()

            unit_cost = (
                latest_transaction.batch.unit_price 
                if latest_transaction and latest_transaction.batch and latest_transaction.batch.unit_price is not None 
                else None
            )


            stock_data = calculate_stock_value2(product)
            total_available = stock_data['total_available']
            total_stock_value = total_available * float(unit_cost)
            grand_total_stock_value += total_stock_value
          

            aggregated_data.append({
                'product': product.name,
                'reorder_level': product.reorder_level,              
                'total_purchase': stock_data['total_purchase'],
                'total_sold': stock_data['total_sold'],
              
                'total_manufacture_in': stock_data['total_manufacture_in'],
                'total_manufacture_out': stock_data['total_manufacture_out'],
                'total_existing_in': stock_data['total_existing_in'],
                'total_operations_out': stock_data['total_operations_out'],
                'total_transfer_in': stock_data['total_transfer_in'],
                'total_transfer_out': stock_data['total_transfer_out'],
                'total_scrapped_in': stock_data['total_scrapped_in'],
                'total_scrapped_out': stock_data['total_scrapped_out'],
                'total_replacement_out': stock_data['total_replacement_out'],
                'total_replacement_in': stock_data['total_replacement_in'],

                'total_available': total_available,
                'total_stock': stock_data['total_stock'],
                'total_stock_value': total_stock_value,
            })


    if aggregated_data:
        chart_data = {
            'labels': [item['product'] for item in aggregated_data],          
            'reorder_level': [item['reorder_level'] for item in aggregated_data],
            'total_purchase': [item['total_purchase'] for item in aggregated_data],
            'total_sold': [item['total_sold'] for item in aggregated_data],
          
            'total_manufacture_in': [item['total_manufacture_in'] for item in aggregated_data],
            'total_manufacture_out': [item['total_manufacture_out'] for item in aggregated_data],
            'total_existing_in': [item['total_existing_in'] for item in aggregated_data],
            'total_operations_out': [item['total_operations_out'] for item in aggregated_data],
            'total_transfer_in': [item['total_transfer_in'] for item in aggregated_data],
            'total_transfer_out': [item['total_transfer_out'] for item in aggregated_data],
            'total_scrapped_in': [item['total_scrapped_in'] for item in aggregated_data],
            'total_scrapped_out': [item['total_scrapped_out'] for item in aggregated_data],
            'total_replacement_out': [item['total_replacement_out'] for item in aggregated_data],
            'total_replacement_in': [item['total_replacement_in'] for item in aggregated_data],

            'total_stock': [item['total_stock'] for item in aggregated_data],
            'total_available': [item['total_available'] for item in aggregated_data],
            'total_stock_value': [item['total_stock_value'] for item in aggregated_data],
        }

    warehouse_json = json.dumps(chart_data)

    paginator = Paginator(aggregated_data, 10)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    form = SummaryReportChartForm()
    context = {
        'page_obj': page_obj,
        'warehouse_json': warehouse_json,
        'grand_total_stock_value': grand_total_stock_value,
        'form': form,
        'days': days,
        'start_date': start_date,
        'end_date': end_date,
        'warehouse_name': warehouse_name,
        'product_name': product_name,
    }
    return render(request, 'inventory/inventory_aggregate_list.html', context)


def inventory_executive_sum(request):
    products = Product.objects.all()
    warehouse_data = {}
    grand_total_stock_value = 0
    chart_data = []  
    valuation_method = request.GET.get("valuation_method", "FIFO")

    for product in products:   
        inventories = product.product_inventories.all()

        for inventory in inventories:
            stock_data = calculate_batch_stock_value(product, inventory.warehouse,valuation_method)
            stock_value = stock_data['stock_value']
            grand_total_stock_value += stock_value

            if inventory.warehouse.name not in warehouse_data:
                warehouse_data[inventory.warehouse.name] = 0
            warehouse_data[inventory.warehouse.name] += stock_value
  
    for warehouse, stock_value in warehouse_data.items():
        chart_data.append({
            'warehouse': warehouse,
            'stock_value': float(stock_value),
        })   

    chart_data_json = json.dumps(chart_data)

    context = {
        'chart_data': chart_data,
        'chart_data_json': chart_data_json,
        'grand_total_stock_value': grand_total_stock_value,
    }
    return render(request, 'inventory/inventory_executive_sum.html', context)



def inventory_transaction_report(request):
    form = TransactionFilterForm(request.GET or None)
    transactions=[]
    transaction_type_form=None
    selected_product=None
    transaction_type_display=None
    chart_data={}
  
    if request.method == 'GET':
        form = TransactionFilterForm(request.GET or None)      

        if form.is_valid():      
            transaction_type_form = form.cleaned_data["transaction_type"]
            selected_product = form.cleaned_data["product"]    
            start_date = form.cleaned_data["start_date"]     
            end_date = form.cleaned_data["end_date"]     
            days = form.cleaned_data["days"]    

          
            if start_date and end_date and days:
                messages.info(request,'Please choose start date and end date or days but not both')          

            transaction_type_data =InventoryTransaction.objects.all()
            if start_date and end_date:
                transaction_type_data =transaction_type_data.filter(transaction_date__range=(start_date,end_date))  

            if days:
                end_date = timezone.now() 
                start_date = end_date - timedelta(days=days)  
                transaction_type_data = transaction_type_data.filter(transaction_date__range=(start_date, end_date))
                         
            transaction_type_display = transaction_type_data.filter(transaction_type=transaction_type_form).first()
            transaction_type_display =  transaction_type_display.get_transaction_type_display() if   transaction_type_data else transaction_type_form            

            if selected_product:    
                transactions = (
                    transaction_type_data.filter(
                        transaction_type=transaction_type_form ,
                        product__name=selected_product
                    )
                    .annotate(transaction_date_only=TruncDate("transaction_date"))  
                    .values("product__name", "transaction_date_only")
                    .annotate(total_quantity=Sum("quantity"))
                    .order_by("transaction_date_only")
                )     
            else:
                messages.info(request,'please choose product')         

                    
            labels = sorted(set(transaction["transaction_date_only"].strftime("%Y-%m-%d") for transaction in transactions))  # Convert date to string
            datasets = []

            products = {}
            for transaction in transactions:
                product_name = transaction["product__name"]
                transaction_date = transaction["transaction_date_only"].strftime("%Y-%m-%d")  
                
                if product_name not in products:
                    products[product_name] = {date: 0 for date in labels}  
                products[product_name][transaction_date] = transaction["total_quantity"]

            for product, quantities in products.items():
                datasets.append({
                    "label": product,
                    "data": [quantities[date] for date in labels],  
                    "backgroundColor": "rgba(75, 192, 192, 0.6)",
                    "borderColor": "rgba(75, 192, 192, 1)",
                    "borderWidth": 2,
                })

            chart_data = {
                "labels": labels,
                "datasets": datasets,
            }
           
        else:
            form = TransactionFilterForm()
            print(form.errors)
            print('form is not valid')

    context = {
        "form": form,
        "transaction_type": transaction_type_display,
        "selected_product": selected_product,
        "chart_data": json.dumps(chart_data),  
        "transactions": transactions,  
    }
    form = TransactionFilterForm()
    return render(request, "inventory/inventory_transaction_report.html", context)



from .forms import WarehouseReorderLevelForm


@login_required
def manage_warehouse_reorder_level(request, id=None):  
    instance = Inventory.objects.filter(id=id).first()  
    message_text = "Updated successfully!" if instance else "Added successfully!"  

    form = WarehouseReorderLevelForm(request.POST or None, instance=instance)

    if request.method == 'POST' and form.is_valid():
        form_instance = form.save(commit=False)
        form.instance.user = request.user
        form_instance.save()        
        messages.success(request, message_text)
        return redirect('inventory:create_warehouse_reorder_level')  

    datas = Inventory.objects.all().order_by('-created_at')
    paginator = Paginator(datas, 5)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    return render(request, 'inventory/assign_warehouse_reorder_level.html', 
    {
        'form': form,
        'instance': instance,
        'datas': datas,
        'page_obj': page_obj
    })



@login_required
def delete_warehouse_reorder_level(request, id):
    instance = get_object_or_404(Inventory, id=id)
    if request.method == 'POST':
        instance.delete()
        messages.success(request, "Deleted successfully!")
        return redirect('inventory:create_warehouse_reorder_level')     

    messages.warning(request, "Invalid delete request!")
    return redirect('inventory:create_warehouse_reorder_level')  
