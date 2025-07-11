from django.shortcuts import render,redirect,get_object_or_404
from django.db import transaction
from django.utils import timezone
from django.contrib import messages
from django.db.models import Sum,Q
from django.urls import reverse
import uuid
import logging
from django.contrib.auth.decorators import login_required,permission_required
logger = logging.getLogger(__name__)
from django.http import HttpResponseForbidden

from.forms import PurchaseStatusForm,QualityControlForm,PurchaseOrderSearchForm,PurchaseOrderForm,PurchaseRequestForm
from.models import PurchaseOrder,PurchaseOrderItem,PurchaseRequestOrder,PurchaseRequestItem
from product.models import Product
from logistics.models import PurchaseDispatchItem
from supplier.models import Supplier
from inventory.models import Warehouse,Location
from purchase.models import PurchaseOrder,PurchaseOrderItem,PurchaseRequestOrder
from core.forms import CommonFilterForm
from django.core.paginator import Paginator
from myproject.utils import create_notification
from.models import Batch
from.forms import BatchForm


@login_required
def purchase_dashboard(request):
    return render(request,'purchase/purchase_dashboard.html')

from django.db.models import F

@login_required
def manage_batch(request, id=None):  
    instance = get_object_or_404(Batch, id=id) if id else None
    message_text = "updated successfully!" if id else "added successfully!"  
    form = BatchForm(request.POST or None, request.FILES or None, instance=instance)

    if request.method == 'POST' and form.is_valid():
        product = form.cleaned_data['product']
        manufacture_date = form.cleaned_data['manufacture_date']
        expiry_date = form.cleaned_data['expiry_date']
        quantity = form.cleaned_data['quantity']
        unit_price = form.cleaned_data['unit_price']
        product_type= form.cleaned_data['product_type']  

        existing_batch = Batch.objects.filter(product=product, manufacture_date=manufacture_date).first()
        if existing_batch:              
            existing_batch.quantity += quantity
            existing_batch.remaining_quantity = F('remaining_quantity') + quantity
            #existing_batch.unit_price = unit_price  # Decide if price should be updated
        else:
            batch = form.save(commit=False)
            batch.user = request.user          
            batch.remaining_quantity = quantity
            batch.save()          
           
        messages.success(request, message_text)
        return redirect('purchase:create_batch')  

    datas = Batch.objects.all().order_by('-updated_at')
    paginator = Paginator(datas, 5)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    return render(request, 'purchase/manage_batch.html', {
        'form': form,
        'instance': instance,
        'datas': datas,
        'page_obj': page_obj
    })



@login_required
def delete_batch(request, id):
    instance = get_object_or_404(Batch, id=id)
    if request.method == 'POST':
        instance.delete()
        messages.success(request, "Deleted successfully!")
        return redirect('purchase:create_batch')      

    messages.warning(request, "Invalid delete request!")
    return redirect('purchase:create_batch') 



from datetime import timedelta
from inventory.models import InventoryTransaction,Inventory

def calculate_average_usage(product, warehouse=None, days=30):
    start_date = timezone.now() - timedelta(days=days)
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


@login_required
def create_purchase_request(request):
    if 'basket' not in request.session:
        request.session['basket'] = []
    form = PurchaseRequestForm(request.POST or None)
   
    if request.method == 'POST':
        if 'add_to_basket' in request.POST:
            if form.is_valid():

                category = form.cleaned_data['category']
                product_obj = form.cleaned_data['product']
                quantity = form.cleaned_data['quantity']

                product_stocks = Inventory.objects.filter(product=product_obj)

                total_available_stock = sum(stock.quantity for stock in product_stocks)
                product_average_usage = calculate_average_usage(product_obj)  
                product_required_stock = product_average_usage * product_obj.lead_time  

                if total_available_stock > product_required_stock:
                    messages.info(request, f'There is enough total stock for {product_obj.name}')
                    return redirect('purchase:create_purchase_request')

                warehouse_messages = []
                for stock in product_stocks:
                    warehouse_avg_usage = calculate_average_usage(product_obj, stock.warehouse)
                    warehouse_required_stock = warehouse_avg_usage * product_obj.lead_time

                    if stock.quantity > warehouse_required_stock:
                        warehouse_messages.append(f"{stock.product.name} in {stock.warehouse.name}")
              
                if warehouse_messages:
                    messages.info(request, f'There is enough stock in these warehouses: {", ".join(warehouse_messages)}')
                    return redirect('purchase:create_purchase_request')

                basket = request.session.get('basket', [])
                product_in_basket = next((item for item in basket if item['id'] == product_obj.id), None)
                total_amount = float(quantity) * float(product_obj.unit_price)

                if product_in_basket:
                    product_in_basket['quantity'] += quantity
                else:
                    basket.append({
                        'id': product_obj.id,
                        'name': product_obj.name,
                        'product_type': form.cleaned_data['product_type'],
                        'category': category.name,
                        'quantity': quantity,
                        'sku': product_obj.sku,
                        'unit_price': float(product_obj.unit_price),
                        'total_amount': total_amount
                    })

                request.session['basket'] = basket
                request.session.modified = True
                messages.success(request, f"Added '{product_obj.name}' to the purchase basket")
                return redirect('purchase:create_purchase_request')
            else:
                messages.error(request, "Form is invalid. Please check the details and try again.")

        elif 'action' in request.POST:
            action = request.POST['action']
            product_id = int(request.POST.get('product_id', 0))

            if action == 'update':
                new_quantity = int(request.POST.get('quantity', 1))
                for item in request.session['basket']:
                    if item['id'] == product_id:
                        item['quantity'] = new_quantity  

            elif action == 'delete':
                request.session['basket'] = [
                    item for item in request.session['basket'] if item['id'] != product_id
                ]  

            request.session.modified = True
            messages.success(request, "Purchase basket updated successfully.")
            return redirect('purchase:create_purchase_request')

        elif 'confirm_purchase' in request.POST:
            basket = request.session.get('basket', [])
            if not basket:
                messages.error(request, "Purchase basket is empty. Add products before confirming the purchase.")
                return redirect('purchase:create_purchase_request')
            return redirect('purchase:confirm_purchase_request')  

    basket = request.session.get('basket', [])
    return render(request, 'purchase/create_purchase_request.html', {'form': form, 'basket': basket})



@login_required
def confirm_purchase_request(request):
    basket = request.session.get('basket', [])
    if not basket:
        messages.error(request, "Purchase basket is empty. Cannot confirm purchase.")
        return redirect('purchase:create_purchase_request')

    if request.method == 'POST':
        try:
            with transaction.atomic(): 
                total_amount = sum(item['quantity'] * item['unit_price'] for item in basket)
                purchase_request_order = PurchaseRequestOrder(
                    total_amount=total_amount,
                    status='PENDING',  
                    user=request.user  
                )
                purchase_request_order.save()  
               
                for item in basket:
                    product = get_object_or_404(Product, id=item['id'])
                    quantity = item['quantity']

                    purchase_request_item = PurchaseRequestItem(
                        purchase_request_order=purchase_request_order,
                        product=product,
                        quantity=quantity,
                        user=request.user  
                    )
                    purchase_request_item.save()

                request.session['basket'] = []
                request.session.modified = True
                messages.success(request, "Purchase order created successfully!")
                return redirect('purchase:create_purchase_request')

        except Exception as e: 
            logger.error("Error creating purchase order: %s", e)
            messages.error(request, f"An error occurred while creating the purchase order: {str(e)}")
            return redirect('purchase:create_purchase_request')
    return render(request, 'purchase/confirm_purchase_request.html', {'basket': basket})



@login_required
def purchase_request_order_list(request):
    request_order = None
    purchase_request_orders = PurchaseRequestOrder.objects.all().order_by("-created_at")

    form = CommonFilterForm(request.GET or None)
    if form.is_valid():
        request_order = form.cleaned_data['purchase_request_order_id']
        if request_order:
            purchase_request_orders = purchase_request_orders.filter(order_id=request_order)

    is_requester = request.user.groups.filter(name="Requester").exists()
    is_reviewer = request.user.groups.filter(name="Reviewer").exists()
    is_approver = request.user.groups.filter(name="Approver").exists()

    paginator = Paginator(purchase_request_orders, 10)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    return render(request, 'purchase/purchase_request_order_list.html', {
        'purchase_request_orders': purchase_request_orders,           
        'user': request.user,
        'form': form,
        'page_obj': page_obj,
        'request_order': request_order,
        'is_requester': is_requester,
        'is_reviewer': is_reviewer,
        'is_approver': is_approver
    })


@login_required
def purchase_request_items(request,order_id):
    order_instance = get_object_or_404(PurchaseRequestOrder,id=order_id)
    total_amount = order_instance.total_amount
    return render(request,'purchase/purchase_request_items.html',{'order_instance':order_instance,'total_amount':total_amount})




@login_required
def process_purchase_request(request, order_id):
    order = get_object_or_404(PurchaseRequestOrder, id=order_id)

    role_status_map = {
        "Requester": ["SUBMITTED", "CANCELLED"],
        "Reviewer": ["REVIEWED", "CANCELLED"],
        "Approver": ["APPROVED", "CANCELLED"],
    }

    if request.method == 'POST':
        form = PurchaseStatusForm(request.POST)
        if form.is_valid():
            if order.approval_data is None:
                order.approval_data = {}

            approval_status = form.cleaned_data['approval_status']
            remarks = form.cleaned_data['remarks']
            role = None


            user_roles = []
            if request.user.groups.filter(name="Requester").exists():
                user_roles.append("Requester")
            if request.user.groups.filter(name="Reviewer").exists():
                user_roles.append("Reviewer")
            if request.user.groups.filter(name="Approver").exists():
                user_roles.append("Approver")

            for user_role in user_roles:
                if approval_status in role_status_map[user_role]:
                    role = user_role
                    break

            if not role:
                messages.error(
                    request,
                    "You do not have permission to perform this action or invalid status."
                )
                return redirect('purchase:purchase_request_order_list')

            if role == "Requester":
                order.requester_approval_status = approval_status
                order.Requester_remarks = remarks
            elif role == "Reviewer":
                order.reviewer_approval_status = approval_status
                order.Reviewer_remarks = remarks
            elif role == "Approver":
                order.approver_approval_status = approval_status
                order.Approver_remarks = remarks

            order.approval_data[role] = {
                'status': approval_status,
                'remarks': remarks,
                'date': timezone.now().isoformat(),
            }

            order.save()
            messages.success(request, f"Order {order.id} successfully updated.")
            return redirect('purchase:purchase_request_order_list')
        else:
            messages.error(request, "Invalid form submission.")
    else:
        form = PurchaseStatusForm()
    return render(request, 'purchase/purchase_order_approval_form.html', {'form': form, 'order': order})



@login_required
def create_purchase_order(request, request_id):
    request_instance = get_object_or_404(PurchaseRequestOrder, id=request_id)

    if 'basket' not in request.session:
        request.session['basket'] = []
    form = PurchaseOrderForm(request.POST,request_instance=request_instance)   
    if request.method == 'POST':
        if 'add_to_basket' in request.POST:
            if form.is_valid():
                category = form.cleaned_data['category']
                product_obj = form.cleaned_data['product']
                quantity = form.cleaned_data['quantity']
                supplier = form.cleaned_data['supplier']
                batch = form.cleaned_data['batch']

                item_request = form.cleaned_data['order_item_id'] 
                item_request_id = item_request.id if item_request else None

                purchase_request_order = form.cleaned_data.get('purchase_request_order')
                purchase_request_order_id = purchase_request_order.id if purchase_request_order else None

                total_requested_quantity = (
                    request_instance.purchase_request_order.filter(product=product_obj)
                    .aggregate(total_requested=Sum('quantity'))
                    .get('total_requested', 0)
                )

                if not total_requested_quantity:
                    messages.error(
                        request,
                        f"The product '{product_obj.name}' is not part of this purchase request."
                    )
                    return redirect('purchase:create_purchase_order', request_instance.id)
                                
                basket = request.session.get('basket', [])
                total_quantity_in_basket = sum(
                    item['quantity'] for item in basket if item['id'] == product_obj.id
                )              
                new_total_quantity = total_quantity_in_basket + quantity
                if new_total_quantity > total_requested_quantity:
                    messages.error(
                        request,
                        f"Cannot add {quantity} of '{product_obj.name}' to the basket. "
                        f"The total quantity ({new_total_quantity}) exceeds the requested quantity "
                        f"({total_requested_quantity})."
                    )
                    return redirect('purchase:create_purchase_order', request_instance.id)
                               

                product_in_basket = next(
                    (item for item in basket if item['id'] == product_obj.id),
                    None
                )
                total_amount = float(quantity) * float(product_obj.unit_price)

                if product_in_basket:
                    product_in_basket['quantity'] += quantity
                    product_in_basket['total_amount'] += total_amount
                else:
                    basket.append({
                        'item_request_id': item_request_id,
                        'id': product_obj.id,
                        'name': product_obj.name,
                        'product_type': product_obj.product_type,
                        'category': category.name,
                        'quantity': quantity,
                        'sku': product_obj.sku,
                        'unit_price': float(batch.unit_price),
                        'supplier_id': supplier.id,
                        'supplier': supplier.name,
                        'batch_id': batch.id,
                      
                        'total_amount': total_amount,
                        'purchase_request_order_id': purchase_request_order_id,
                    })
                request.session['basket'] = basket
                request.session.modified = True
                messages.success(request, f"Added '{product_obj.name}' to the purchase basket")
                return redirect('purchase:create_purchase_order', request_instance.id)
            else:
                messages.error(request, "Form is invalid. Please check the details and try again.")

        elif 'action' in request.POST:
            action = request.POST['action']
            product_id = int(request.POST.get('product_id', 0))   

            if action == 'update':
                new_quantity = int(request.POST.get('quantity', 1))
                for item in request.session['basket']:
                    if item['id'] == product_id:
                        item['quantity'] = new_quantity
                        break
            elif action == 'delete':
                request.session['basket'] = [
                    item for item in request.session['basket'] if item['id'] != product_id 
                ]
            request.session.modified = True
            messages.success(request, "Purchase basket updated successfully.")
            return redirect('purchase:create_purchase_order', request_instance.id)

        elif 'confirm_purchase' in request.POST:
            basket = request.session.get('basket', [])
            if not basket:
                messages.error(request, "Purchase basket is empty. Add products before confirming the purchase.")
                return redirect('purchase:create_purchase_order', request_instance.id)
            return redirect(f"{reverse('purchase:confirm_purchase_order')}?request_id={request_instance.id}")

    form = PurchaseOrderForm(request_instance=request_instance)
    basket = request.session.get('basket', [])
    return render(request, 'purchase/create_purchase_order.html', {'form': form, 'basket': basket})




@login_required
def confirm_purchase_order(request):
    request_id = request.GET.get('request_id')
    basket = request.session.get('basket', [])

    if not basket:
        messages.error(request, "Purchase basket is empty. Cannot confirm purchase.")
        return redirect('purchase:purchase_order_list')

    if request.method == 'POST':
        try:
            with transaction.atomic(): 
                total_amount = sum(item['quantity'] * item['unit_price'] for item in basket)
                supplier_id = basket[0]['supplier_id'] if basket else None                
                supplier = get_object_or_404(Supplier, id=supplier_id)

                purchase_request_order = get_object_or_404(PurchaseRequestOrder, id=request_id)

                purchase_order = PurchaseOrder(
                    total_amount=total_amount,
                    supplier=supplier,
                    status='IN_PROCESS',
                    user=request.user,
                    purchase_request_order=purchase_request_order,
                    
                )
                purchase_order.save()

                for item in basket:
                    logger.info(f"Basket item: {item}")
                    
                    product = get_object_or_404(Product, id=item['id'])
                    quantity = item['quantity']
                    order_item = get_object_or_404(PurchaseRequestItem, id=item['item_request_id'])
                    batch = get_object_or_404(Batch,id=item['batch_id'])

                    purchase_item = PurchaseOrderItem(
                        purchase_order=purchase_order,
                        product=product,
                        quantity=quantity,
                        batch = batch,
                        user=request.user,
                        order_item_id=order_item, 
                    )
                    purchase_item.save()

                request.session['basket'] = []
                request.session.modified = True
                messages.success(request, "Purchase order created successfully!")
                return redirect('purchase:create_purchase_order', purchase_request_order.id)

        except Exception as e: 
            logger.error("Error creating purchase order: %s", e)
            messages.error(request, f"An error occurred while creating the purchase order: {str(e)}")
            return redirect('purchase:create_purchase_order', request_id)
    return render(request, 'purchase/confirm_purchase_order.html', {'basket': basket})





@login_required
def purchase_order_list(request):
    purchase_order = None
    purchase_orders = PurchaseOrder.objects.all().order_by("-created_at")

    for order in purchase_orders:
        shipment = order.purchase_shipment.first()
        if shipment:
            invoice = shipment.shipment_invoices.first()
            if invoice:
                # Calculate total paid amount
                total_paid = invoice.total_paid_amount
                remaining_balance = invoice.remaining_balance
            else:
                total_paid = 0
                remaining_balance = 0
        else:
            total_paid = 0
            remaining_balance = 0

        # Add the variables to the context as needed
        order.total_paid = total_paid
        order.remaining_balance = remaining_balance


    form = CommonFilterForm(request.GET or None)
    if form.is_valid():
        purchase_order = form.cleaned_data['purchase_order_id']
        if purchase_order:
            purchase_orders = purchase_orders.filter(order_id=purchase_order)
    
    is_requester = request.user.groups.filter(name="Requester").exists()
    is_reviewer = request.user.groups.filter(name="Reviewer").exists()
    is_approver = request.user.groups.filter(name="Approver").exists()

    paginator = Paginator(purchase_orders, 10)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    return render(request, 'purchase/purchase_order_list.html', {
        'purchase_orders': purchase_orders,           
        'user': request.user,
        'form': form,
        'page_obj': page_obj,
        'purchase_order': purchase_order,
        'is_requester': is_requester,
        'is_reviewer': is_reviewer,
        'is_approver': is_approver
    })


@login_required
def purchase_order_items(request,order_id):
    order_instance = get_object_or_404(PurchaseOrder,id=order_id)
    total_amount = order_instance.total_amount
    return render(request,'purchase/purchase_order_items.html',{'order_instance':order_instance,'total_amount':total_amount})



@login_required
def process_purchase_order(request, order_id):
    order = get_object_or_404(PurchaseOrder, id=order_id)

    role_status_map = {
        "Requester": ["SUBMITTED", "CANCELLED"],
        "Reviewer": ["REVIEWED", "CANCELLED"],
        "Approver": ["APPROVED", "CANCELLED"],
    }

    if request.method == 'POST':
        form = PurchaseStatusForm(request.POST)
        if form.is_valid():
            if order.approval_data is None:
                order.approval_data = {}

            # Extract form data
            approval_status = form.cleaned_data['approval_status']
            remarks = form.cleaned_data['remarks']
            role = None

            user_roles = []
            if request.user.groups.filter(name="Requester").exists():
                user_roles.append("Requester")
            if request.user.groups.filter(name="Reviewer").exists():
                user_roles.append("Reviewer")
            if request.user.groups.filter(name="Approver").exists():
                user_roles.append("Approver")

            for user_role in user_roles:
                if approval_status in role_status_map[user_role]:
                    role = user_role
                    break

            if not role:
                messages.error(
                    request,
                    "You do not have permission to perform this action or invalid status."
                )
                return redirect('purchase:purchase_order_list')

            if role == "Requester":
                order.requester_approval_status = approval_status
                order.Requester_remarks = remarks
            elif role == "Reviewer":
                order.reviewer_approval_status = approval_status
                order.Reviewer_remarks = remarks
            elif role == "Approver":
                order.approver_approval_status = approval_status
                order.Approver_remarks = remarks

            order.approval_data[role] = {
                'status': approval_status,
                'remarks': remarks,
                'date': timezone.now().isoformat(),
            }

            order.save()
            messages.success(request, f"Order {order.id} successfully updated.")
            return redirect('purchase:purchase_order_list')
        else:
            messages.error(request, "Invalid form submission.")
    else:
        form = PurchaseStatusForm()

    return render(request, 'purchase/purchase_order_approval_form.html', {'form': form, 'order': order})





@login_required
def qc_dashboard(request, purchase_order_id=None):
    if purchase_order_id:
        pending_items = PurchaseDispatchItem.objects.filter(
            purchase_shipment__purchase_order=purchase_order_id,
            status__in=['REACHED', 'OBI']
        )
        create_notification(request.user,message='QC pending',notification_type='PURCHASE-NOTIFICATION')

        purchase_order = get_object_or_404(PurchaseOrder, id=purchase_order_id)
    else:
        pending_items = PurchaseDispatchItem.objects.filter(status__in=['REACHED', 'OBI'])
        purchase_order = None
        create_notification(request.user,message='QC pending',notification_type='PURCHASE-NOTIFICATION')
    if not pending_items:
        messages.info(request, "No items pending for quality control inspection.No new goods arrived yet")
    return render(request, 'purchase/qc_dashboard.html', {'pending_items': pending_items, 'purchase_order': purchase_order})


@login_required
def qc_inspect_item(request, item_id):
    purchase_dispatch_item = get_object_or_404(PurchaseDispatchItem, id=item_id)
    purchase_shipment = purchase_dispatch_item.purchase_shipment
    purchase_order = purchase_shipment.purchase_order
    purchase_request_order = purchase_order.purchase_request_order

    if not purchase_shipment:
        messages.error(request, "No shipment found for this order item.")
        return redirect('purchase:qc_dashboard')  
    if not purchase_dispatch_item.status in ['REACHED','OBI']:
        messages.error(request, "Goods not arrived yet found for this order item.")
        return redirect('purchase:qc_dashboard')  
    
    if purchase_shipment.status != 'REACHED':
                messages.info(request, "Cannot inspect due to delivery has not been done yet.")
                return redirect('purchase:qc_dashboard')

    if request.method == 'POST':
        form = QualityControlForm(request.POST)
        if form.is_valid():    
            good_quantity = form.cleaned_data['good_quantity']     
            bad_quantity = form.cleaned_data['bad_quantity']   
            if good_quantity + bad_quantity !=purchase_dispatch_item.dispatch_quantity:
                messages.warning(request,'dispatch quantity is more than selected quantity')
                return redirect('purchase:qc_inspect_item',item_id)
            qc_entry = form.save(commit=False)
            qc_entry.purchase_dispatch_item = purchase_dispatch_item
            qc_entry.user = request.user  
            qc_entry.inspection_date = timezone.now()
            qc_entry.save()

            purchase_dispatch_item.status = 'OBI'
            purchase_dispatch_item.save()          
                 
            messages.success(request, "Quality control inspection recorded successfully.")
            return redirect('purchase:qc_dashboard')
        else:
            messages.error(request, "Error saving QC inspection.")
    else:
        form = QualityControlForm(initial={'total_quantity': purchase_dispatch_item.dispatch_quantity})    
    return render(request, 'purchase/qc_inspect_item.html', {'form': form, 'purchase_order': purchase_order,'purchase_dispatch_item':purchase_dispatch_item,'purchase_shipment': purchase_shipment})



@login_required
def purchase_order_item(request):
    form = PurchaseOrderSearchForm(request.GET or None)
    purchase_orders = None 
    if form.is_valid():  
        order_number = form.cleaned_data.get('order_number') 
        if order_number:  
            purchase_orders = PurchaseOrder.objects.prefetch_related(
                'purchase_shipment__shipment_dispatch_item'
            ).filter(order_id__icontains=order_number) 

    return render(request, 'purchase/purchase_order_item.html', {
        'purchase_orders': purchase_orders,
        'form': form,
    })



@login_required
def purchase_order_item_dispatch(request, order_id):
    purchase_order = get_object_or_404(
        PurchaseOrder.objects.prefetch_related(
            'purchase_order_item',  
            'purchase_order_item__order_dispatch_item',             
        ),
        order_id=order_id
    )

    return render(request, 'purchase/purchase_order_item_dispatch.html', {
        'purchase_order': purchase_order,
    })



@login_required
def update_purchase_order_status(request, order_id):
    purchase_order = get_object_or_404(PurchaseOrder, id=order_id) 
    all_items = purchase_order.purchase_order_item.all()
    all_delivered = True
    for item in all_items:
        total_dispatched_quantity = item.dispatch_item.aggregate(
            total=Sum('dispatch_quantity', filter=Q(status='REACHED'))
        )['total'] or 0

        if total_dispatched_quantity < item.quantity:
            all_delivered = False
            break
   
    if all_delivered:
        purchase_order.status = 'REACHED'
        purchase_order.save()

        shipment = purchase_order.purchase_shipment.first()
        if shipment: 
            shipment.status = 'REACHED'
            shipment.save()  

        messages.success(request, "All items have been delivered. Purchase order status updated to DELIVERED.")
    else:
        messages.info(request, "Not all items have been delivered yet. Status remains unchanged.")
    
    return redirect('purchase:purchase_order_list')
