from django.shortcuts import render,get_object_or_404
from django.contrib.auth.decorators import user_passes_test
from django.contrib import messages
from django.shortcuts import redirect
import logging
logger=logging.getLogger(__name__)

from django.db import transaction
from django.db.models import Sum
from django.urls import reverse

from.models import ExistingOrder,ExistingOrderItems,OperationsDeliveryItem,OperationsRequestItem,OperationsRequestOrder
from product.models import Product
from.forms import ExistingOrderForm,OperationsDeliveryForm,OperationsRequestForm

from inventory.models import InventoryTransaction,Warehouse,Location
from myproject.utils import create_notification
from core.forms import CommonFilterForm
from django.core.paginator import Paginator
from inventory.models import Inventory
from django.contrib.auth.decorators import login_required,permission_required
from purchase.models import Batch


@login_required
def operations_dashboard(request):
    return render(request,'operations/operations_dashboard.html')



def permission_required_with_message(perm, redirect_url='/', message=None):
    def decorator(view_func):
        def _wrapped_view(request, *args, **kwargs):
            if not request.user.has_perm(perm):
                if message:
                    messages.error(request, message)
                else:
                    messages.error(request, "You do not have the required permission to access this page.")
                return redirect(redirect_url)
            return view_func(request, *args, **kwargs)
        return _wrapped_view
    return decorator



@permission_required_with_message('operations.can_review', redirect_url='/operations/operations_dashboard/', message="You don't have permission to review.")
def add_existing_items(request):
    if 'basket' not in request.session:
        request.session['basket'] = []
    form =ExistingOrderForm(request.POST or None)
   
    if request.method == 'POST':
        if 'add_to_basket' in request.POST:
            if form.is_valid():

                category = form.cleaned_data['category']
                product_obj = form.cleaned_data['product']
                quantity = form.cleaned_data['quantity']
                warehouse = form.cleaned_data['warehouse']
                location = form.cleaned_data['location']
                batch= form.cleaned_data['batch']

                basket = request.session.get('basket', [])
                product_in_basket = next((item for item in basket if item['id'] == product_obj.id), None)
                total_amount = float(quantity) * float(product_obj.unit_price)

                if product_in_basket:
                    product_in_basket['quantity'] += quantity
                else:
                    basket.append({
                        'id': product_obj.id,
                        'name': product_obj.name,
                        'category': category.name,
                        'quantity': quantity,
                        'warehouse_id': warehouse.id,
                        'location_id': location.id,
                        'sku': product_obj.sku,
                        'unit_price': float(product_obj.unit_price),
                        'total_amount': total_amount,
                        'batch_id':batch.id,
                        'warehouse_name': warehouse.name,
                        'location_name': location.name,
                        'batch_number':batch.batch_number
                    })

                request.session['basket'] = basket
                request.session.modified = True
                messages.success(request, f"Added '{product_obj.name}' to the  basket")
                return redirect('operations:add_existing_items')
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
            messages.success(request, "basket updated successfully.")
            return redirect('operations:add_existing_items')

        elif 'confirm_purchase' in request.POST:
            basket = request.session.get('basket', [])
            if not basket:
                messages.error(request, "basket is empty. Add products before confirming the purchase.")
                return redirect('operations:add_existing_items')
            return redirect('operations:confirm_add_existing_items')  

    basket = request.session.get('basket', [])
    return render(request, 'operations/create_add_existing_items.html', {'form': form, 'basket': basket})



@login_required
def confirm_add_existing_items(request):
    basket = request.session.get('basket', [])
    if not basket:
        messages.error(request, "Basket is empty. Cannot confirm purchase.")
        return redirect('operations:add_existing_items')

    logger.debug("Basket before confirming: %s", basket)

    if request.method == 'POST':
        try:
            with transaction.atomic():
                # Calculate total amount
                total_amount = sum(item['quantity'] * item['unit_price'] for item in basket)

                # Create existing order
                existing_order = ExistingOrder.objects.create(
                    total_amount=total_amount,
                    status='ADDED',
                    user=request.user
                )

                for item in basket:
                    product = get_object_or_404(Product, id=item['id'])
                    quantity = item['quantity']
                    warehouse_id = item.get('warehouse_id')
                    location_id = item.get('location_id')
                    batch_id = item.get('batch_id')

                    if not warehouse_id or not location_id or not batch_id:
                        raise ValueError("Warehouse, location, or batch data is missing.")

                    warehouse = get_object_or_404(Warehouse, id=warehouse_id)
                    location = get_object_or_404(Location, id=location_id)
                    batch = get_object_or_404(Batch, id=batch_id)  # Fixed: use Batch

                    # Create order item
                    existing_order_item = ExistingOrderItems.objects.create(
                        existing_order=existing_order,
                        product=product,
                        quantity=quantity,
                        batch=batch,
                        total_amount=total_amount,
                        user=request.user
                    )              
                   
                    inventory, _ = Inventory.objects.get_or_create(
                        warehouse=warehouse,
                        location=location,
                        product=product,
                        batch=batch,
                        user=request.user,
                        defaults={'quantity': 0}
                    )
                    inventory.quantity += quantity
                    inventory.save()

                    # Record inventory transaction
                    InventoryTransaction.objects.create(
                        user=request.user,
                        warehouse=warehouse,
                        location=location,
                        product=product,
                        batch=batch,
                        transaction_type='EXISTING_ITEM_IN',
                        quantity=quantity,
                        existing_items_order=existing_order,
                        inventory_transaction=inventory
                    )

                    # Send notification per item
                    create_notification(
                        request.user,
                        message=f'{quantity} units of {product.name} from existing stock have been added to inventory',
                        notification_type='OPERATIONS-NOTIFICATION'
                    )

                # Clear basket after success
                request.session['basket'] = []
                request.session.modified = True

                messages.success(request, "Order created successfully!")
                return redirect('operations:add_existing_items')

        except Exception as e:
            logger.error("Error creating order: %s", e)
            messages.error(request, f"An error occurred while creating the order: {str(e)}")
            return redirect('operations:add_existing_items')

    return render(request, 'operations/confirm_add_existing_items.html', {'basket': basket})




@permission_required_with_message('operations.can_submit', redirect_url='/operations/operations_dashboard/', message="You don't have permission to review.")
def existing_items_list(request):
    order_id = None
    existing_orders = ExistingOrder.objects.all().order_by('-created_at')
    form = CommonFilterForm(request.GET or None)
    if form.is_valid():
        order_id = form.cleaned_data['ID_number']
        if order_id:
             existing_orders =  existing_orders.filter(order_id = order_id)

    paginator = Paginator(existing_orders, 10)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    form=CommonFilterForm()
            
    return render(request,'operations/existing_items_list.html',
        {
        'existing_orders':existing_orders,
        'page_obj':page_obj,
        'form':form,
        'order_id':order_id

        })



@login_required
def create_operations_items_request(request):
    if 'basket' not in request.session:
        request.session['basket'] = []
    form = OperationsRequestForm(request.POST or None)
   
    if request.method == 'POST':
        if 'add_to_basket' in request.POST:
            if form.is_valid():

                category = form.cleaned_data['category']
                product_obj = form.cleaned_data['product']
                quantity = form.cleaned_data['quantity']    
                
                        
                basket = request.session.get('basket', [])
                product_in_basket = next((item for item in basket if item['id'] == product_obj.id), None)
                total_amount = float(quantity) * float(product_obj.unit_price)

               
                if product_in_basket:
                    product_in_basket['quantity'] += quantity
                else:
                    basket.append({
                        'id': product_obj.id,
                        'name': product_obj.name,                     
                        'category': category.name,
                        'category_id': category.id,
                        'quantity': quantity,
                        'sku': product_obj.sku,
                        'unit_price': float(product_obj.unit_price),
                        'total_amount': total_amount,
                       
                       
                    })

                request.session['basket'] = basket
                request.session.modified = True
                messages.success(request, f"Added '{product_obj.name}' to the purchase basket")
                return redirect('operations:create_operations_items_request')
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
            messages.success(request, "basket updated successfully.")
            return redirect('operations:create_operations_items_request')

        elif 'confirm_purchase' in request.POST:
            basket = request.session.get('basket', [])
            if not basket:
                messages.error(request, " basket is empty. Add products before confirming the purchase.")
                return redirect('operations:create_operations_items_request')
            return redirect('operations:confirm_operations_items_request') 

    basket = request.session.get('basket', [])
    return render(request, 'operations/create_operations_items_request.html', {'form': form, 'basket': basket})




@login_required
def confirm_operations_items_request(request):
    basket = request.session.get('basket', [])
    if not basket:
        messages.error(request, "Materials basket is empty. Cannot confirm purchase.")
        return redirect('operations:create_operations_items_request')

    if request.method == 'POST':
        try:
            with transaction.atomic():
                from decimal import Decimal
                total_amount = sum(Decimal(item['quantity']) * Decimal(item['unit_price']) for item in basket)

                operations_request_order = OperationsRequestOrder(
                    total_amount=total_amount,
                    status='PENDING',
                    user=request.user
                )
                operations_request_order.save()
                for item in basket:
                    product = get_object_or_404(Product, id=item['id']) 
                            
                    operations_request_item = OperationsRequestItem(
                        operations_request_order=operations_request_order,
                        product=product,
                        quantity=item['quantity'],
                        user=request.user,
                    )
                    operations_request_item.save()

                create_notification(request.user, message= f"Operations has submitted a request for {len(basket)} products.",notification_type='OPERATIONS-NOTIFICATION')
                    
                request.session['basket'] = []
                request.session.modified = True
                messages.success(request, "Materials request order created successfully!")
                return redirect('operations:create_operations_items_request')

        except Exception as e:
            logger.error(f"Error creating materials order: {e}")
            messages.error(request, f"An error occurred while creating the materials request order: {e}")
            return redirect('operations:create_operations_items_request')
        
    return render(request, 'operations/confirm_operations_items_request.html', {'basket': basket})



@login_required
def operation_request_order_list(request):
    request_order = None
    orders = OperationsRequestOrder.objects.all().order_by('-created_at')
    form=CommonFilterForm(request.GET or None)
    if form.is_valid():
        request_order = form.cleaned_data['operations_request_order_id']
        if request_order:
            orders = orders.filter(order_id = request_order)

    paginator = Paginator(orders, 10)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    form = CommonFilterForm()

    return render (request,'operations/operations_request_order_list.html',
    {
     'orders':orders,
     'page_obj':page_obj,
     'form':form,
     'request_order':request_order
,    })



@login_required
def operation_request_order_items(request,order_id):
    order=get_object_or_404(OperationsRequestOrder,id=order_id)     
        
    return render (request,'operations/operations_request_order_items.html',{'order':order})



@login_required
def create_operations_items_delivery(request, request_id):
    request_instance = get_object_or_404(OperationsRequestOrder, id=request_id)

    initial_data = {
        'operations_request_order': request_instance,
        'operations_request_item': request_instance.operations_request_items.first(),
        'quantity': request_instance.operations_request_items.first().quantity,
        'product': request_instance.operations_request_items.first().product
    }

    form = OperationsDeliveryForm(request.POST or None, request_instance=request_instance, initial=initial_data)

    if 'basket' not in request.session:
        request.session['basket'] = []
    form = OperationsDeliveryForm(request.POST or None, request_instance=request_instance, initial=initial_data)  
    if request.method == 'POST':
        if 'add_to_basket' in request.POST:
            if form.is_valid():             
                product_obj = form.cleaned_data['product']
                quantity = form.cleaned_data['quantity']   
                warehouse = form.cleaned_data['warehouse']
                location = form.cleaned_data['location']     
                batch = form.cleaned_data['batch']      
                item_request = form.cleaned_data['operations_request_item'] 
                item_request_id = item_request.id if item_request else None
               
                operations_request_order = form.cleaned_data.get('materials_request_order')
                operations_request_order_id = operations_request_order.id if operations_request_order else None

                total_requested_quantity = (
                    request_instance.operations_request_items.filter(product=product_obj)
                    .aggregate(total_requested=Sum('quantity'))
                    .get('total_requested', 0)
                )

                if not total_requested_quantity:
                    messages.error(
                        request,
                        f"The product '{product_obj.name}' is not part of this purchase request."
                    )
                    return redirect('operations:create_operations_items_delivery', request_instance.id)
                                
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
                    return redirect('operations:create_operations_items_delivery', request_instance.id)
              
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
                        'quantity': quantity,
                        'sku': product_obj.sku,
                        'unit_price': float(product_obj.unit_price),
                        'warehouse_id': warehouse.id,                        
                        'location_id': location.id,
                        'batch_id':batch.id,
                        'batch_number':batch.batch_number,
                        'warehouse_name': warehouse.name,                        
                        'location_name': location.name,                    
                        'total_amount': total_amount,
                        'operations_request_order_id': operations_request_order_id,
                    })
                request.session['basket'] = basket
                request.session.modified = True
                messages.success(request, f"Added '{product_obj.name}' to the purchase basket")
                return redirect('operations:create_operations_items_delivery', request_instance.id)
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
            messages.success(request, "Delivery basket updated successfully.")
            return redirect('operations:create_operations_items_delivery', request_instance.id)

        elif 'confirm_purchase' in request.POST:
            basket = request.session.get('basket', [])
            if not basket:
                messages.error(request, "Delivery basket is empty. Add products before confirming the purchase.")
                return redirect('operations:create_operations_items_delivery', request_instance.id)
            return redirect(f"{reverse('operations:confirm_operations_items_delivery')}?request_id={request_instance.id}")


    form = OperationsDeliveryForm(request_instance=request_instance, initial=initial_data)
    basket = request.session.get('basket', [])
    return render(request, 'operations/create_operations_items_delivery.html', {'form': form, 'basket': basket})


@login_required
def confirm_operations_items_delivery(request):
    request_id = request.GET.get('request_id')
    basket = request.session.get('basket', [])
    if not basket:
        messages.error(request, " basket is empty. Cannot confirm purchase.")
        return redirect('operations:operations_request_order_list')
    if request.method == 'POST':
        try:
            with transaction.atomic(): 
                total_amount = sum(item['quantity'] * item['unit_price'] for item in basket)           
                location_id = basket[0].get('location_id')  
                warehouse_id = basket[0].get('warehouse_id') 
                batch_id = basket[0].get('batch_id') 
            
                operations_request_order = get_object_or_404(OperationsRequestOrder, id=request_id)
                
                for item in basket:
                    logger.info(f"Basket item: {item}")                    
                    product = get_object_or_404(Product, id=item['id'])
                    quantity = item['quantity']
                    order_item = get_object_or_404(OperationsRequestItem, id=item['item_request_id'])
                
                    warehouse = get_object_or_404(Warehouse, id=warehouse_id) 
                    location = get_object_or_404(Location, id=location_id) 
                    batch = get_object_or_404(Batch, id=batch_id) 

                    delivery_item = OperationsDeliveryItem(
                        operations_request_order=operations_request_order,
                        product=product,
                        quantity=quantity,
                        warehouse=warehouse,
                        batch=batch,
                        location=location,
                        total_amount=total_amount,
                        user=request.user,
                        operations_request_item=order_item, 
                    )
                    delivery_item.save()

                    inventory, created = Inventory.objects.get_or_create(
                        warehouse=warehouse,
                        location=location,
                        batch=batch,
                        product=product,
                        user=request.user,
                        defaults={'quantity': 0}
                    )

                    inventory.quantity += item['quantity']
                    inventory.save()
                    messages.success(request, "Inventory updated successfully.")

                    inventory_transaction = InventoryTransaction.objects.create(
                        user=request.user,
                        warehouse=warehouse,
                        location=location,
                        product=product,
                        batch=batch,
                        transaction_type='OPERATIONS_OUT',
                        quantity=item['quantity'],
                        operations_request_order=operations_request_order,
                        inventory_transaction=inventory
                    )                           
                  
                    batch.remaining_quantity = (batch.remaining_quantity or 0) - item['quantity']
                    batch.save()       
                    
                    create_notification(request.user,message=f'request from operations for{product} has been delivered',notification_type='OPERATION-NOTIFICATION')

                request.session['basket'] = []
                request.session.modified = True
                messages.success(request, "Delivery request created successfully!")
                return redirect('operations:create_operations_items_delivery', operations_request_order.id)

        except Exception as e: 
            logger.error("Error creating delivery: %s", e)
            messages.error(request, f"An error occurred while creating the delivery items: {str(e)}")
            return redirect('operations:create_operations_items_delivery', request_id)
    return render(request, 'operations/confirm_operations_items_delivery.html', {'basket': basket})
