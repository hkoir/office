
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required

from django.contrib import messages
from django.db import transaction
import uuid
from django.db.models import Sum
from django.db import IntegrityError

from.models import ReturnOrRefund,FaultyProduct, Replacement
from sales.models import SaleOrder,SaleOrderItem
from .forms import ReturnOrRefundForm,ReplacementProductForm,ReturnOrRefundFormInternal,FaultyProductForm
from inventory.models import Inventory
from django.utils import timezone

from django.core.paginator import Paginator
from inventory.models import Inventory,InventoryTransaction
from myproject.utils import create_notification
from core.forms import CommonFilterForm
from.forms import ScrapProductForm,ScrapOrderListForm
from.models import ScrappedOrder,ScrappedItem
from product.models import Product
from inventory.models import Inventory, InventoryTransaction,Warehouse,Location
from django.core.paginator import Paginator
from purchase.forms import PurchaseStatusForm



@login_required
def repair_return_dashboard(request):
    return render(request,'repairreturn/dashboard.html')


@login_required
def sale_order_list(request):
    sale_order_number=None
    form = CommonFilterForm(request.GET or None)
    sale_orders = SaleOrder.objects.all().order_by('-created_at')

    if form.is_valid():
        sale_order_number = form.cleaned_data['sale_order_id']
        if sale_order_number:
            sale_orders = sale_orders.filter(order_id = sale_order_number)
    else:
        for field, errors in form.errors.items():
            for error in errors:
                messages.error(request, f"{field.capitalize()}: {error}")

    paginator = Paginator(sale_orders, 10)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    form=CommonFilterForm()

    return render(request, 'repairreturn/sale_order_list.html',
        {
            'sale_orders':sale_orders,
            'form':form,
            'sale_order_number':sale_order_number,
            'page_obj':page_obj,
            'sale_order_number':sale_order_number
        })

@login_required
def create_return_request(request, sale_order_id):
    sale_order = get_object_or_404(SaleOrder, id=sale_order_id)
    sales = sale_order.sale_order.all()
    return_requests = ReturnOrRefund.objects.prefetch_related('faulty_products__faulty_replacement').all()

    if request.method == 'POST':
        form = ReturnOrRefundForm(request.POST, sale_order_id=sale_order_id)  

        sale_id = request.POST.get('sale')
        try:
            sale = get_object_or_404(SaleOrderItem, id=sale_id)
        except:
            messages.error(request, "Invalid sale item selected.")
            return redirect(request.path)
        
        if form.is_valid():
            return_refund = form.save(commit=False)
            return_refund.sale = sale
            return_refund.user=request.user
            return_refund.save()

            create_notification(
                request.user,message=
                f"Customer {sale_order.customer} has placed a repair/return request for: {sale.product}",notification_type='RETURN-NOTIFICATION'
            )
            messages.success(request, "Return/Refund request submitted successfully!")
            return redirect('repairreturn:return_dashboard')
        else:
            messages.error(request, "There was an error with your submission. Please check the form.")
    else:
        form = ReturnOrRefundForm(sale_order_id=sale_order_id) 

    paginator = Paginator(return_requests, 10)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    return render(request, 'repairreturn/refund_return/user_create_return_request.html', {
        'form': form,
        'sale_order': sale_order,
        'sales': sales,
        'return_requests': return_requests,
        'page_obj': page_obj
    })



@login_required
def return_request_progress(request, sale_order_id):
    sale_order = get_object_or_404(SaleOrder, id=sale_order_id)
    sales = sale_order.sale_order.all()  
    return_requests = ReturnOrRefund.objects.prefetch_related('faulty_products__faulty_replacement').all().order_by('-created_at')
      
    paginator =Paginator(return_requests,10)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    return render(request, 'repairreturn/refund_return//return_request_progress.html', {
        'sale_order': sale_order,
        'sales': sales,
        'return_requests':return_requests,
        'page_obj':page_obj
    })


@login_required
def return_request_list(request):
    return_id=None
    returns = ReturnOrRefund.objects.all().order_by('-created_at')
    form = CommonFilterForm(request.GET or None)
    if form.is_valid():
        return_id = form.cleaned_data['sale_order_id']
        if return_id:
            returns = returns.filter(sale__sale_order__order_id = return_id)
    else:
        for field, errors in form.errors.items():
            for error in errors:
                messages.error(request, f"{field.capitalize()}: {error}")

    paginator =Paginator(returns ,10)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    form=CommonFilterForm()
    return render(request, 'repairreturn/refund_return//user_return_request_list.html',
         {
             'page_obj': page_obj,
             'form':form,
             'page_obj':page_obj,
             'return_id':return_id
        })

@login_required
def manage_return_request(request, return_id):
    return_request = get_object_or_404(ReturnOrRefund, id=return_id)

    if request.method == 'POST':
        form = ReturnOrRefundFormInternal(request.POST, instance=return_request)
        if form.is_valid():
            return_request = form.save(commit=False)
            return_request.processed_by = request.user
            return_request.user = request.user
            return_request.processed_date = timezone.now()

            if return_request.status == 'Acknowledged' and return_request.return_reason == 'DEFECTIVE':
                FaultyProduct.objects.create(
                    sale=return_request.sale,
                    product=return_request.sale.product,
                    faulty_product_quantity=return_request.quantity_refund,
                    reason_for_fault=return_request.return_reason,  
                    inspected_by=request.user,
                    user=request.user
                )
            
            return_request.save()
            messages.success(request, f'{return_request.sale.product.name} has been processed.')
            return redirect('repairreturn:return_request_list') 
        else:
            for field, errors in form.errors.items():
                for error in errors:
                    messages.error(request, f"{field.capitalize()}: {error}")
    else:
        form = ReturnOrRefundFormInternal(instance=return_request)

    return render(request, 'repairreturn/refund_return/manage_return_request.html', {
        'form': form,
        'return_request': return_request
    })


@login_required
def faulty_product_list(request):
    faulty_product_id=None
    faulty_products = FaultyProduct.objects.all().order_by('-created_at')

    form=CommonFilterForm(request.GET or None)
    if form.is_valid():
        faulty_product_id= form.cleaned_data['sale_order_id']
        if faulty_product_id:
              faulty_products =  faulty_products.filter(sale__sale_order__order_id= faulty_product_id)
    else:
        for field, errors in form.errors.items():
            for error in errors:
                messages.error(request, f"{field.capitalize()}: {error}")

    paginator = Paginator(faulty_products,10)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    form = CommonFilterForm()
    return render(request, 'repairreturn/refund_return//faulty_product_list.html', 
    {
        'faulty_products':faulty_products,
        'page_obj':page_obj,
        'form':form,
        'faulty_product_id':faulty_product_id
     })


@login_required
def repair_faulty_product(request, faulty_product_id):
    faulty_product = get_object_or_404(FaultyProduct, id=faulty_product_id)
    product = faulty_product.product
    if request.method == 'POST':
        form = FaultyProductForm(request.POST, instance=faulty_product)
        if form.is_valid():
            status = form.cleaned_data['status']
            faulty_product = form.save(commit=False)                               
            faulty_product.save()
            if status == 'REPAIRED_AND_READY':
                create_notification(request.user, message= f'Product {product} has been repaired and ready to return',notification_type='RETURN-NOTIFICATION')

            if status in ['UNREPAIRABLE','SCRAPPED']:                
                create_notification(request.user, message=f'Product {product} can not be repaired',notification_type='REPAIR-RETURN-NOTIFICATION')


            messages.success(request, f'{faulty_product.product.name} has been processed.')
            return redirect('repairreturn:faulty_product_list')  
        else:
            for field, errors in form.errors.items():
                for error in errors:
                    messages.error(request, f"{field.capitalize()}: {error}")
    else:
        form = FaultyProductForm(instance=faulty_product)

    return render(request, 'repairreturn/refund_return/repair_faulty_product.html', {
        'faulty_product': faulty_product,
        'form': form
    })


@login_required
def replacement_return_repaired_product(request, faulty_product_id):
    faulty_product = get_object_or_404(FaultyProduct, id=faulty_product_id)
    
    if request.method == 'POST':
        form = ReplacementProductForm(request.POST)
        if form.is_valid():
            warehouse = form.cleaned_data['warehouse']
            location = form.cleaned_data['location']
            quantity = form.cleaned_data['quantity']  # Fixed typo
            batch = form.cleaned_data['batch']

            if batch.remaining_quantity < quantity:
                messages.error(request, f"Not enough stock in batch {batch.batch_number} for {faulty_product.name}.")
                return redirect('repairreturn:faulty_product_list')  # Fixed redirect

            replacement = form.save(commit=False)
            replacement.customer = faulty_product.sale.sale_order.customer
            replacement.user = request.user
            replacement.faulty_product = faulty_product  

            if faulty_product.status in ['UNREPAIRABLE', 'SCRAPPED']:
                calculated_replacement_qty = faulty_product.faulty_product_quantity - (faulty_product.repair_quantity or 0)

                if calculated_replacement_qty > 0:
                    replacement.replacement_quantity = calculated_replacement_qty 

                    try:
                        with transaction.atomic():                 
                            inventory_transaction = InventoryTransaction.objects.create(
                                product=faulty_product.sale.product,
                                warehouse=warehouse,
                                location=location,
                                batch=batch,
                                transaction_type='REPLACEMENT_OUT',
                                quantity=calculated_replacement_qty,
                                user=request.user,
                                remarks=f"Replacement for Faulty Product ID {faulty_product.id}"
                            )

                            inventory, created = Inventory.objects.get_or_create(
                                warehouse=warehouse,
                                location=location,
                                batch=batch,
                                user=request.user,
                                product=faulty_product.sale.product,
                                defaults={'quantity': 0}
                            )
                
                            if not created:
                                if inventory.quantity < replacement.replacement_quantity:
                                    messages.error(request, "Not enough stock available in inventory for replacement.")
                                    return redirect('repairreturn:faulty_product_list')

                                inventory.quantity -= replacement.replacement_quantity
                                batch.remaining_quantity -= calculated_replacement_qty  # Fixed typo
                                batch.save()
                                inventory.save()
                                messages.success(request, "Inventory updated successfully.")
                            else:
                                messages.success(request, "Inventory created successfully.") 

                            inventory_transaction.inventory_transaction = inventory
                            inventory_transaction.save()
                            replacement.save()
                            return redirect('repairreturn:faulty_product_list')

                    except Exception as e:
                        messages.error(request, f"An error occurred: {e}")
                        return redirect('repairreturn:faulty_product_list')                

                else:
                    messages.warning(request, "Item has already been processed for repair/replacement.")
                    return redirect('repairreturn:faulty_product_list')            

            elif faulty_product.status == 'REPAIRED':
                messages.warning(request, "Item has been repaired, so replacement cannot be made.")
                return redirect('repairreturn:faulty_product_list')                

            else:
                messages.warning(request, "Unexpected product status for replacement.")
                return redirect('repairreturn:faulty_product_list')                

        else:
            for field, errors in form.errors.items():
                for error in errors:
                    messages.error(request, f"{field.capitalize()}: {error}")
    else:
        form = ReplacementProductForm()

    return render(request, 'repairreturn/refund_return/return_repaired_faulty_product.html', {
        'form': form,
        'faulty_product': faulty_product
    })


@login_required
def replacement_product_list(request):
    replacement_ID = None
    replacement_products =Replacement.objects.all().order_by('-created_at')
    
    form=CommonFilterForm(request.GET or None)
    if form.is_valid():
        replacement_ID= form.cleaned_data['sale_order_id']
        if replacement_ID:
              replacement_products =  replacement_products.filter(faulty_product__sale__sale_order__order_id= replacement_ID)

    else:
        for field, errors in form.errors.items():
            for error in errors:
                messages.error(request, f"{field.capitalize()}: {error}")

    paginator = Paginator(replacement_products,10)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    form=CommonFilterForm()

    return render(request, 'repairreturn/refund_return//replacement_product_list.html', {
    
    'replacement_products':replacement_products,
    'page_obj':page_obj,
    'form':form,
    'replacement_ID':replacement_ID
    
    })




################### Sarapping product #########################################################
@login_required
def create_scrap_request(request):
    if 'basket' not in request.session:
        request.session['basket'] = []

    form = ScrapProductForm(request.POST or None)

    if request.method == 'POST':
        if 'add_to_basket' in request.POST:
            if form.is_valid():

                product_obj = form.cleaned_data['scrapped_product']
                quantity = form.cleaned_data['quantity']                          
                source_inventory = form.cleaned_data['source_inventory']           
                basket = request.session.get('basket', [])
                product_in_basket = next((item for item in basket if item['id'] == product_obj.id), None)
                total_amount = float(quantity) * float(product_obj.unit_price)
              
                if product_in_basket:
                    product_in_basket['quantity'] += quantity
                else:
                    basket.append({
                        'id': product_obj.id,
                        'name': product_obj.name,
                        'quantity': quantity,
                        'unit_price': float(product_obj.unit_price),
                        'total_amount': total_amount,                       
                        'source_inventory_id':source_inventory.id

                    })

                request.session['basket'] = basket
                request.session.modified = True
                messages.success(request, f"Added '{product_obj.name}' to the scrap basket")
                return redirect('repairreturn:create_scrap_request')
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
            return redirect('repairreturn:create_scrap_request')

        elif 'confirm_purchase' in request.POST:
            basket = request.session.get('basket', [])
            if not basket:
                messages.error(request, "basket is empty. Add products before confirming the purchase.")
                return redirect('repairreturn:create_scrap_request')
            return redirect('repairreturn:confirm_scrap_request')

    basket = request.session.get('basket', [])
    return render(request, 'repairreturn/create_scrap_request.html', {'form': form, 'basket': basket})



@login_required
def confirm_scrap_request(request):
    basket = request.session.get('basket', [])    
    if not basket:
        messages.error(request, "basket is empty. Cannot confirm purchase.")
        return redirect('repairreturn:create_scrap_request')
    
    
    if request.method == 'POST':
        try:
            with transaction.atomic(): 
                total_amount = sum(item['quantity'] * item['unit_price'] for item in basket)               
                source_inventory_id = basket[0].get('source_inventory_id')               
                source_inventory = get_object_or_404(Inventory, id=source_inventory_id) 
              
                scrap_request_order = ScrappedOrder(
                    total_amount=total_amount,
                    status='PENDING',  
                    user=request.user,                    
                )
                scrap_request_order.save()  
               
                for item in basket:
                    product = get_object_or_404(Product, id=item['id'])
                    quantity = item['quantity']          
                 
                    scrapped_request_item = ScrappedItem(
                        scrapped_order=scrap_request_order,
                        scrapped_product=product,
                        quantity=quantity,
                        user=request.user,   
                        warehouse=source_inventory.warehouse,
                        location=source_inventory.location,
                        source_inventory= source_inventory                     
                    )
                    scrapped_request_item.save()

                request.session['basket'] = []
                request.session.modified = True
                messages.success(request, "Scrap order created successfully!")
                return redirect('repairreturn:scrap_order_list')
        except Exception as e:  
            messages.error(request, f"An error occurred while creating the scrap order: {str(e)}")
            return redirect('repairreturn:create_scrap_request')
    return render(request, 'repairreturn/confirm_scrap_request.html', {'basket': basket})


@login_required
def scrap_order_list(request):
    scrapped_orders = ScrappedOrder.objects.all().order_by('-created_at')
    form = ScrapOrderListForm(request.GET)

    if form.is_valid():
        order_id = form.cleaned_data['order_id']
        warehouse = form.cleaned_data['warehouse']

        if order_id:
            scrapped_orders = scrapped_orders.filter(order_id=order_id)
        if warehouse:
            scrapped_orders = scrapped_orders.filter(warehouse__name=warehouse)  
    else:
        for field, errors in form.errors.items():
            for error in errors:
                messages.error(request, f"{field.capitalize()}: {error}")
   
    paginator = Paginator (scrapped_orders,8)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    form=ScrapOrderListForm()       
    return render(request, 'repairreturn/scrap_order_list.html',{'scrapped_orders':scrapped_orders,'form':form,'page_obj':page_obj})



def scrap_request_items(request,order_id):
    order_instance = get_object_or_404(ScrappedOrder,id=order_id)
    return render(request,'repairreturn/scrap_request_items.html',{'order_instance':order_instance})



@login_required
def process_scrap_order(request, order_id):
    order = get_object_or_404(ScrappedOrder, id=order_id)

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
                return redirect('repairreturn:scrap_order_list')

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
            return redirect('repairreturn:scrap_order_list')
        else:
            for field, errors in form.errors.items():
                for error in errors:
                    messages.error(request, f"{field.capitalize()}: {error}")
    else:
        form = PurchaseStatusForm()
    return render(request, 'purchase/purchase_order_approval_form.html', {'form': form, 'order': order})


from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db import transaction

@login_required
def scrap_confirmation(request, order_id):
    request_instance = get_object_or_404(ScrappedOrder, id=order_id)
    scrap_items = request_instance.scrap_request_items.all()

    if request.method == 'GET':
        return render(
            request,
            'repairreturn/scrap_deletion_message.html',
            {'scrap_items': scrap_items}
        )

    try:
        with transaction.atomic():
            for item in scrap_items:
                if not item.source_inventory:
                    messages.warning(
                        request,
                        "No source inventory linked to this scrap order. Please review the order before confirming."
                    )
                    return redirect('repairreturn:scrap_order_list')

                warehouse = item.source_inventory.warehouse
                location = item.source_inventory.location
                quantity = item.quantity
                product = item.scrapped_product
                batch = item.batch

                # Fetch inventory item
                inventory_item = Inventory.objects.filter(
                    warehouse=warehouse,
                    location=location,
                    product=product,
                    batch=batch,
                    user=request.user
                ).first()

                if not inventory_item:
                    messages.error(
                        request,
                        f"Inventory not found for {product.name} in {warehouse.name}. "
                        "Please review the source inventory."
                    )
                    raise ValueError(f"Inventory not found for {product.name} in {warehouse.name}.")

                if inventory_item.quantity < quantity:
                    messages.warning(
                        request,
                        f"Insufficient quantity for {product.name} in {warehouse.name}. Scrap process aborted."
                    )
                    raise ValueError(f"Insufficient inventory for {product.name} in {warehouse.name}.")

                # Update inventory
                inventory_item.quantity -= quantity
                inventory_item.save()

                # Create inventory transaction
                inventory_transaction = InventoryTransaction.objects.create(
                    user=request.user,
                    warehouse=warehouse,
                    location=location,
                    batch=batch,
                    product=product,
                    transaction_type='SCRAPPED_OUT',
                    quantity=quantity,
                    scrapped_order=request_instance,
                    inventory_transaction=inventory_item
                )

                # Ensure batch quantity is reduced safely
                if batch.remaining_quantity is not None and batch.remaining_quantity >= quantity:
                    batch.remaining_quantity -= quantity
                    batch.save()

                messages.success(
                    request,
                    f"Inventory updated for {product.name} in {warehouse.name}."
                )

            # Update order status
            request_instance.status = 'SCRAPPED_OUT'
            request_instance.save()

            messages.success(request, "Scrapped order processed successfully.")
            return redirect('repairreturn:scrap_order_list')

    except Exception as e:
        messages.error(request, f"An error occurred: {str(e)}")
        return redirect('repairreturn:scrap_order_list')


        
############### end of product scrapping #################################################
