from django.shortcuts import render,redirect,get_object_or_404
from django.contrib.auth.decorators import login_required,permission_required
from django.db import transaction
from django.utils import timezone
from django.contrib import messages
import uuid
import logging
logger = logging.getLogger(__name__)

from django.db.models import Sum,Q
from django.urls import reverse

from supplier.models import Supplier
from inventory.models import Warehouse,Location
from product.models import Product
from logistics.models import PurchaseDispatchItem

from.models import MaterialsRequestOrder,MaterialsRequestItem,MaterialsDeliveryItem,FinishedGoodsReadyFromProduction,ReceiveFinishedGoods
from.forms import MaterialsRequestForm,MaterialsDeliveryForm,QualityControlForm,MaterialsStatusForm,MaterialsOrderSearchForm,FinishedGoodsForm

from myproject.utils import create_notification
from core.forms import CommonFilterForm
from inventory.models import Inventory,InventoryTransaction
from django.core.paginator import Paginator


@login_required
def manufacture_dashboard(request):
    return render(request,'manufacture/materials_dashboard.html')


@login_required
def create_materials_request(request):
    if 'basket' not in request.session:
        request.session['basket'] = []
    form = MaterialsRequestForm(request.POST or None)
   
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
                        'product_type': form.cleaned_data['product_type'],
                        'category': category.name,
                        'quantity': quantity,
                        'sku': product_obj.sku,
                        'unit_price': float(product_obj.unit_price),
                        'total_amount': total_amount,
                       
                    })

                request.session['basket'] = basket
                request.session.modified = True
                messages.success(request, f"Added '{product_obj.name}' to the purchase basket")
                return redirect('manufacture:create_materials_request')
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
            messages.success(request, "Materials basket updated successfully.")
            return redirect('manufacture:create_materials_request')

        elif 'confirm_purchase' in request.POST:
            basket = request.session.get('basket', [])
            if not basket:
                messages.error(request, "Materials basket is empty. Add products before confirming the purchase.")
                return redirect('manufacture:create_manufacture_request')
            return redirect('manufacture:confirm_materials_request')  

    basket = request.session.get('basket', [])
    return render(request, 'manufacture/create_materials_request.html', {'form': form, 'basket': basket})



@login_required
def confirm_materials_request(request):
    basket = request.session.get('basket', [])
    if not basket:
        messages.error(request, "Materials basket is empty. Cannot confirm purchase.")
        return redirect('manufacture:create_materials_request')

    if request.method == 'POST':
        try:
            with transaction.atomic():
                from decimal import Decimal

                total_amount = sum(Decimal(item['quantity']) * Decimal(item['unit_price']) for item in basket)

                materials_request_order = MaterialsRequestOrder(
                    total_amount=total_amount,
                    status='PENDING',  
                    user=request.user
                )
                materials_request_order.save()
                for item in basket:
                    product = get_object_or_404(Product, id=item['id'])
                    materials_request_item = MaterialsRequestItem(
                        material_request_order=materials_request_order,
                        product=product,
                        quantity=item['quantity'],
                        user=request.user,
                    )
                    materials_request_item.save()
                request.session['basket'] = []
                request.session.modified = True
                messages.success(request, "Materials request order created successfully!")
                return redirect('manufacture:create_materials_request')

        except Exception as e:
            logger.error(f"Error creating materials order: {e}")
            messages.error(request, f"An error occurred while creating the materials request order: {e}")
            return redirect('manufacture:create_materials_request')
    return render(request, 'manufacture/confirm_materials_request.html', {'basket': basket})


@login_required
def materiala_request_order_list(request):
    request_order = None
    purchase_request_orders = MaterialsRequestOrder.objects.all().order_by("-created_at")
    form=CommonFilterForm(request.GET or None)
    if form.is_valid():
        request_order = form.cleaned_data['materials_order_id']
        if request_order:
            purchase_request_orders = purchase_request_orders.filter(order_id = request_order)

    is_requester = request.user.groups.filter(name="Requester").exists()
    is_reviewer = request.user.groups.filter(name="Reviewer").exists()
    is_approver = request.user.groups.filter(name="Approver").exists()

    pageinator = Paginator(purchase_request_orders,10)
    page_number = request.GET.get('page')
    page_obj = pageinator.get_page(page_number)

    form=CommonFilterForm()
            
    return render (request, 'manufacture/materials_request_order_list.html',                   
        {'purchase_request_orders':purchase_request_orders,
         
         'is_requester':is_requester,
         'is_reviewer':is_reviewer,
         'is_approver': is_approver,
         'user':request.user,
         'page_obj':page_obj,
         'form':form,
         'request_order':request_order
         })



@login_required
def materials_request_items(request,order_id):
    order_instance = get_object_or_404(MaterialsRequestOrder,id=order_id)
    return render(request,'manufacture/materials_request_items.html',{'order_instance':order_instance})



@login_required
def process_materials_request(request, order_id):
    order = get_object_or_404(MaterialsRequestOrder, id=order_id) 
    form = MaterialsStatusForm(request.POST)
    role_status_map = {
        "Requester": ["SUBMITTED", "CANCELLED"],
        "Reviewer": ["REVIEWED", "CANCELLED"],
        "Approver": ["APPROVED", "CANCELLED"],
    }

    if request.method == 'POST':        
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
                return redirect('manufacture:materials_request_order_list')

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
            return redirect('manufacture:materials_request_order_list')
        else:
            MaterialsStatusForm()

    return render(request, 'manufacture/materials_order_approval_form.html', {'form': form, 'order': order})



@login_required
def create_materials_delivery(request, request_id):
    request_instance = get_object_or_404(MaterialsRequestOrder, id=request_id)

    if 'basket' not in request.session:
        request.session['basket'] = []
    form = MaterialsDeliveryForm(request.POST or None, request_instance=request_instance)   
    if request.method == 'POST':
        if 'add_to_basket' in request.POST:
            if form.is_valid():
                category = form.cleaned_data['category']
                product_obj = form.cleaned_data['product']
                quantity = form.cleaned_data['quantity']   

                warehouse = form.cleaned_data['warehouse']
                location = form.cleaned_data['location']         
                
                item_request = form.cleaned_data['materials_request_item'] 
                item_request_id = item_request.id if item_request else None
               
                materials_request_order = form.cleaned_data.get('materials_request_order')
                materials_request_order_id = materials_request_order.id if materials_request_order else None

                total_requested_quantity = (
                    request_instance.material_request_order_for_item.filter(product=product_obj)
                    .aggregate(total_requested=Sum('quantity'))
                    .get('total_requested', 0)
                )

                if not total_requested_quantity:
                    messages.error(
                        request,
                        f"The product '{product_obj.name}' is not part of this purchase request."
                    )
                    return redirect('manufacture:create_materials_delivery', request_instance.id)
                                
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
                    return redirect('manufacture:create_materials_delivery', request_instance.id)
              
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
                        'unit_price': float(product_obj.unit_price),
                        'warehouse_id': warehouse.id,                        
                        'location_id': location.id,

                        'warehouse_name': warehouse.name,                        
                        'location_name': location.name,
                    
                        'total_amount': total_amount,
                        'materials_request_order_id': materials_request_order_id,
                    })
                request.session['basket'] = basket
                request.session.modified = True
                messages.success(request, f"Added '{product_obj.name}' to the purchase basket")
                return redirect('manufacture:create_materials_delivery', request_instance.id)
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
            return redirect('manufacture:create_materials_delivery', request_instance.id)

        elif 'confirm_purchase' in request.POST:
            basket = request.session.get('basket', [])
            if not basket:
                messages.error(request, "Delivery basket is empty. Add products before confirming the purchase.")
                return redirect('manufacture:create_materials_delivery', request_instance.id)
            return redirect(f"{reverse('manufacture:confirm_materials_delivery')}?request_id={request_instance.id}")

    form = MaterialsDeliveryForm(request_instance=request_instance)
    basket = request.session.get('basket', [])
    return render(request, 'manufacture/create_materials_delivery.html', {'form': form, 'basket': basket})




@login_required
def confirm_materilas_delivery(request):
    request_id = request.GET.get('request_id')
    basket = request.session.get('basket', [])

    if not basket:
        messages.error(request, "Purchase basket is empty. Cannot confirm purchase.")
        return redirect('manufacture:materials_request_order_list')
    if request.method == 'POST':
        try:
            with transaction.atomic(): 
                total_amount = sum(item['quantity'] * item['unit_price'] for item in basket)              

                location_id = basket[0].get('location_id')  
                warehouse_id = basket[0].get('warehouse_id') 
               
                materials_request_order = get_object_or_404(MaterialsRequestOrder, id=request_id)
                
                for item in basket:
                    logger.info(f"Basket item: {item}")
                    
                    product = get_object_or_404(Product, id=item['id'])
                    quantity = item['quantity']
                    order_item = get_object_or_404(MaterialsRequestItem, id=item['item_request_id'])
                   
                    warehouse = get_object_or_404(Warehouse, id=warehouse_id) 
                    location = get_object_or_404(Location, id=location_id) 

                    purchase_item = MaterialsDeliveryItem(
                        materials_request_order=materials_request_order,
                        product=product,
                        quantity=quantity,
                        warehouse=warehouse,
                        location=location,
                        total_amount=total_amount,
                        user=request.user,
                        materials_request_item=order_item, 
                    )
                    purchase_item.save()

                    if InventoryTransaction.objects.filter(
                        manufacture_order=materials_request_order,
                        transaction_type='MANUFACTURE_OUT',
                        product=product,
                    ).exists():
                        messages.error(request, "This transaction has already been recorded.")
                        return redirect('manufacture:qc_dashboard')

                    inventory_transaction = InventoryTransaction.objects.create(
                        user=request.user,
                        warehouse=warehouse,
                        location=location,
                        product=product,
                        transaction_type='MANUFACTURE_OUT',
                        quantity=quantity,
                        manufacture_order=materials_request_order,
                    )
                    inventory, created = Inventory.objects.get_or_create(
                        warehouse=warehouse,
                        location=location,
                        product=product,
                        user=request.user,
                        defaults={
                            'quantity': 0
                        }
                    )
        
                    if not created:
                        inventory.quantity -= quantity
                        inventory.save()
                        messages.success(request, "Inventory updated successfully.")
                    else:                       
                        messages.success(request, "something went wrong. inventory not updated.")
                    inventory_transaction.inventory_transaction =inventory
                    inventory_transaction.save()

                request.session['basket'] = []
                request.session.modified = True
                messages.success(request, "Delivery request created successfully!")
                return redirect('manufacture:create_materials_delivery', materials_request_order.id)

        except Exception as e: 
            logger.error("Error creating delivery: %s", e)
            messages.error(request, f"An error occurred while creating the delivery items: {str(e)}")
            return redirect('manufacture:create_materials_delivery', request_id)
    return render(request, 'manufacture/confirm_materials_delivery.html', {'basket': basket})


@login_required
def materials_delivered_items(request,order_id):
    order_instance = get_object_or_404(MaterialsRequestOrder,id=order_id)
    return render(request,'manufacture/materials_delivery_items.html',{'order_instance':order_instance})




@login_required
def qc_dashboard(request, material_request_order_id=None):
    if material_request_order_id:
        pending_items = FinishedGoodsReadyFromProduction.objects.filter(
            materials_request_order=material_request_order_id,
            status__in=['SUBMITTED','DELIVERED']
        ).select_related('materials_request_order')  
        materials_request_order = get_object_or_404(MaterialsRequestOrder, id=material_request_order_id)
    else:
        pending_items = FinishedGoodsReadyFromProduction.objects.filter(
            status__in=['SUBMITTED','DELIVERED']
        ).select_related('materials_request_order')  
        materials_request_order = None

    if not pending_items:
        messages.info(request, "No items pending for quality control inspection.")

    return render(request, 'manufacture/qc_dashboard.html', {
        'pending_items': pending_items,
        'materials_request_order': materials_request_order
    })


@login_required
def qc_inspect_item(request, item_id):
    finish_goods_item = get_object_or_404(FinishedGoodsReadyFromProduction, id=item_id)

    if not finish_goods_item.status == 'SUBMITTED':
        messages.error(request, "Goods not arrived yet.")
        return redirect('manufacture:qc_dashboard')

    if request.method == 'POST':
        form = QualityControlForm(request.POST)
        if form.is_valid():
            qc_entry = form.save(commit=False)
            qc_entry.finish_goods_from_production = finish_goods_item
            qc_entry.user = request.user
            qc_entry.inspection_date = timezone.now()
            qc_entry.save()

            good_quantity = qc_entry.good_quantity
            if good_quantity > 0:
                ReceiveFinishedGoods.objects.create(
                    user=request.user,
                    quality_control=qc_entry,
                    product=finish_goods_item.product,                    
                    quantity=good_quantity,
                    status='DELIVERED',
                    remarks=f"Received {good_quantity} after QC inspection.",
                )
                finish_goods_item.status = "DELIVERED"
                finish_goods_item.save()
              
                messages.success(
                    request, f"QC inspection recorded. {good_quantity} items received."
                )
            else:
                messages.warning(request, "No good quantity to receive.")           
            return redirect('manufacture:qc_dashboard')
        else:
            messages.error(request, "Error saving QC inspection.")
    else:
        form = QualityControlForm(initial={'total_quantity': finish_goods_item.quantity})

    return render(request, 'manufacture/qc_inspect_item.html', {
        'form': form,
        'finish_goods_item': finish_goods_item,
    })




@login_required
def materials_order_item(request):
    form = MaterialsOrderSearchForm(request.GET or None)
    materials_orders = None 
    if form.is_valid():  
        order_number = form.cleaned_data.get('order_number') 
        if order_number:  
            materials_orders = MaterialsRequestOrder.objects.prefetch_related(
                'materials_request_delivery'
            ).filter(order_id__icontains=order_number) 

    return render(request, 'manufacture/materials_order_item.html', {
        'materials_orders': materials_orders,
        'form': form,
    })




@login_required
def submit_finished_goods(request, request_id):
    materials_request_order = get_object_or_404(MaterialsRequestOrder, id=request_id)
    finished_goods = FinishedGoodsReadyFromProduction.objects.all().order_by('-created_at')

    if request.method == 'POST':
        form = FinishedGoodsForm(request.POST, request_order_queryset=MaterialsRequestOrder.objects.filter(id=request_id))
        if form.is_valid():
            product = form.cleaned_data['product']
            finished_goods = form.save(commit=False)
            finished_goods.user = request.user  
            finished_goods.save()
            messages.success(request, 'Finished goods submitted successfully!')
            create_notification(request.user,message=f'Production department has submitted{product} to receive',notification_type='PRODUCTION-NOTIFICATION')
            return redirect('manufacture:materials_request_order_list')  
    else:
        form = FinishedGoodsForm(request_order_queryset=MaterialsRequestOrder.objects.filter(id=request_id))

    paginator = Paginator(finished_goods,10)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    return render(request, 'manufacture/submit_finished_goods.html', {
        'form': form,
        'materials_request_order': materials_request_order,
        'finished_goods':finished_goods,
        'page_obj':page_obj
    })




@login_required
def purchase_order_item_dispatch(request, order_id):
    purchase_order = get_object_or_404(
        MaterialsRequestOrder.objects.prefetch_related(
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
    purchase_order = get_object_or_404(MaterialsRequestOrder, id=order_id)
 
    all_items = purchase_order.purchase_order_item.all()

    all_delivered = True
    for item in all_items:
        total_dispatched_quantity = item.order_dispatch_item.aggregate(
            total=Sum('dispatch_quantity', filter=Q(status='DELIVERED'))
        )['total'] or 0

        
        if total_dispatched_quantity < item.quantity:
            all_delivered = False
            break
   
    if all_delivered:
        purchase_order.status = 'DELIVERED'
        purchase_order.save()
        messages.success(request, "All items have been delivered. Purchase order status updated to DELIVERED.")
    else:
        messages.info(request, "Not all items have been delivered yet. Status remains unchanged.")
    
    return redirect('purchase:purchase_order_list')



@login_required
def direct_submit_finished_goods(request):   
    finished_goods = FinishedGoodsReadyFromProduction.objects.all().order_by('-created_at')

    if request.method == 'POST':
        form = FinishedGoodsForm(request.POST)
        if form.is_valid():
            product = form.cleaned_data['product']
            finished_goods = form.save(commit=False)
            finished_goods.user = request.user   
            finished_goods.status = 'SUBMITTED'
            finished_goods.save()
            messages.success(request, 'Finished goods submitted successfully!')
            create_notification(request.user,message=f'Production department has submitted{product} to receive',notification_type='PRODUCTION-NOTIFICATION')
            return redirect('manufacture:direct_submit-finished-goods')  
    else:
        form = FinishedGoodsForm()

    form = FinishedGoodsForm()
    paginator = Paginator(finished_goods,10)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    return render(request, 'manufacture/direct_submit_finished_goods.html', {
        'form': form,
        'finished_goods':finished_goods,
        'page_obj':page_obj
    })
