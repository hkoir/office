from django.shortcuts import render,redirect,get_object_or_404
from django.db import transaction
from django.utils import timezone
from django.contrib import messages

import uuid
from django.urls import reverse
from django.contrib.auth.decorators import login_required
from myproject.utils import update_sale_order,update_sale_request_order,update_sale_shipment_status,create_notification
import logging
logger = logging.getLogger(__name__)

from inventory.models import Inventory, InventoryTransaction
from .forms import SaleRequestForm,SaleOrderForm,QualityControlForm,SaleOrderSearchForm,QualityControlForm 
from .models import SaleRequestOrder,SaleRequestItem,SaleOrder,SaleOrderItem
from product.models import Product
from customer.models import Customer
from inventory.models import Warehouse,Location
from logistics.models import SaleDispatchItem
from core.forms import CommonFilterForm
from django.core.paginator import Paginator
from.forms import PurchaseStatusForm,SalesReportForm

from django.db.models import Sum, F,Q
from django.db.models.functions import TruncDate
from collections import defaultdict
import json

from decimal import Decimal

from django.core.exceptions import PermissionDenied
from .models import CustomerQuotation
from .utils import create_sale_request_from_quotation
from.forms import CustomerQuotationItemForm,CustomerQuotationForm,CustomerQuotationItemFormSet


@login_required
def sale_dashboard(request):
    return render(request,'sales/sale_dashboard.html')








import logging
from django.utils import timezone
import uuid

logger = logging.getLogger(__name__)
@login_required
def create_customer_quotation(request):
    if request.method == "POST":
        logger.debug("Received POST request for CustomerQuotationForm and Formset.")
        form = CustomerQuotationForm(request.POST)
        formset = CustomerQuotationItemFormSet(request.POST)

        if form.is_valid() and formset.is_valid():
            logger.debug("Both form and formset are valid. Saving quotation...")
            quotation = form.save(commit=False)

            if not quotation.quotation_number:
                quotation.quotation_number = f"SQ-{timezone.now().strftime('%Y%m%d%H%M%S')}-{uuid.uuid4().hex[:6]}"
            quotation.save()  # Save the main instance first
            formset.instance = quotation
            formset.save()
            quotation.calculate_totals()
            quotation.save(update_fields=['subtotal', 'vat_amount', 'ait_amount', 'total_amount', 'net_due_amount'])

            logger.debug("Quotation and related items saved successfully.")
            messages.success(request, f"Quotation {quotation.quotation_number} created successfully.")
            return redirect("sales:customer_quotation_detail", pk=quotation.pk)

        else:
            logger.warning("Form submission failed validation.")
            logger.warning(f"Form errors: {form.errors.as_json()}")
            logger.warning(f"Formset errors: {formset.errors}")
            messages.error(request, f"Please correct the errors below and resubmit.")
    else:
        logger.debug("Rendering empty quotation form and formset.")
        form = CustomerQuotationForm()
        formset = CustomerQuotationItemFormSet()

    return render(
        request,
        "sales/quotations/create_customer_quotation.html",
        {"form": form, "formset": formset},
    )





def customer_quotation_detail(request, pk):
    quotation = get_object_or_404(CustomerQuotation, pk=pk)
    return render(request, 'sales/quotations/customer_quotation_detail.html', {
        'quotation': quotation
    })




@login_required
def customer_quotation_list(request):
    quotations = CustomerQuotation.objects.all().order_by('-date')
    return render(request, "sales/quotations/customer_quotation_list.html", {"quotations": quotations})



@login_required
def change_customer_quotation_status(request, pk, status):
    quotation = get_object_or_404(CustomerQuotation, pk=pk)
    valid_statuses = [choice[0] for choice in CustomerQuotation.STATUS_CHOICES]

    if status not in valid_statuses:
        messages.error(request, f"Invalid status '{status}'.")
        return redirect("sales:customer_quotation_detail", pk=pk)
    
    user = request.user
    if status == "sent" and not user.is_authenticated:
        raise PermissionDenied("You are not authorized to send quotations.")
    #if status in ["accepted", "rejected"] and not user.groups.filter(name="sales_manager").exists():
     #   raise PermissionDenied("Only a sales manager can accept or reject quotations.")

    quotation.status = status
    quotation.save()
    messages.success(request, f"Quotation {quotation.quotation_number} status updated to {status.capitalize()}.")
    return redirect("sales:customer_quotation_detail", pk=pk)





from .models import CustomerQuotation, SaleRequestOrder, SaleRequestItem
from decimal import Decimal, ROUND_HALF_UP
from django.db import transaction
from django.contrib import messages
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.contrib.auth.decorators import login_required
import uuid



@login_required
@transaction.atomic
def convert_quotation_to_sale_request(request, pk):
    quotation = get_object_or_404(CustomerQuotation, pk=pk)
    quotation_items = quotation.sale_quotation_items.all()

    if quotation.status != "approved":
        messages.error(request, "Quotation must be approved before creating a Sale Request Order.")
        return redirect("sales:customer_quotation_detail", pk=quotation.pk)
   
    if request.method == "POST":
        try:
            order_id = f"SRO-{timezone.now().year}-{uuid.uuid4().hex[:6].upper()}"

            sro = SaleRequestOrder.objects.create(
                customer_quotation=quotation,
                order_id=order_id,
                department="Sales",
                user=request.user,
                order_date=timezone.now().date(),
                status="IN_PROCESS",
                AIT_rate=quotation.AIT_rate,
                AIT_type=quotation.AIT_type,
                subtotal=Decimal(quotation.subtotal or 0),
                total_amount=Decimal(quotation.total_amount or 0),
                vat_amount=Decimal(quotation.vat_amount or 0),
                ait_amount=Decimal(quotation.ait_amount or 0),
                net_due_amount=Decimal(quotation.net_due_amount or 0),
                currency=quotation.currency,

                remarks=f"Converted from Quotation #{quotation.quotation_number}",
            )

            # Copy quotation items
            for item in quotation.sale_quotation_items.all():
                SaleRequestItem.objects.create(
                    sale_request_order=sro,
                    user=request.user,
                    product=item.product,
                    quantity=item.quantity,
                    unit_selling_price=item.unit_price,
                    unit_price=item.unit_price,
                    unit_of_measure=item.unit_of_measure,
                    quoted_delivery_date=item.quoted_delivery_date,
                    currency=item.currency,
                    specification=item.specification,
                    notes=item.notes,
                    VAT_rate=item.VAT_rate,
                    VAT_type=item.VAT_type,
                    vat_amount=item.vat_amount,
                    total_price=item.total_price or ((item.unit_price or 0) * (item.quantity or 0)),
                    status="PENDING",
                )

            messages.success(request, f"Sale Request Order {sro.order_id} created successfully.")
            return redirect("sales:sale_request_order_list")

        except Exception as e:
            transaction.set_rollback(True)
            messages.error(request, f"Error while creating Sale Request: {e}")
            return redirect("sales:customer_quotation_detail", pk=quotation.pk)

    # ✅ Otherwise (GET) — show preview confirmation page
    context = {
        "quotation": quotation,
        "quotation_items": quotation_items,
        "total_amount": quotation.total_amount,
        "vat_amount": quotation.vat_amount,
        "ait_amount": quotation.ait_amount,
        "net_due_amount": quotation.net_due_amount,
    }
    return render(request, "sales/confirm_quotation_conversion.html", context)

import uuid
from decimal import Decimal
from django.db import transaction
from django.contrib import messages



@login_required
@transaction.atomic
def convert_sale_request_to_sale_order(request, request_order_id):
    sale_request_order = get_object_or_404(SaleRequestOrder, id=request_order_id)
    sale_request_items = sale_request_order.sale_request_order.all()

    existing_order = SaleOrder.objects.filter(sale_request_order=sale_request_order).first()
    if existing_order:
        messages.warning(
            request,
            f"This Sale Request Order is already converted to Sale Order {existing_order.order_id}."
        )
        return redirect("sales:sale_order_list")

    if request.method == "POST":
        try:
            order_id = f"SO-{timezone.now().year}-{uuid.uuid4().hex[:6].upper()}"

            sale_order = SaleOrder.objects.create(
                sale_request_order=sale_request_order,
                order_id=order_id,               
                user=request.user,
                order_date=timezone.now().date(),
                status="IN_PROCESS",
                AIT_rate=sale_request_order.AIT_rate,
                AIT_type=sale_request_order.AIT_type,
                subtotal=Decimal(sale_request_order.subtotal or 0),
                total_amount=Decimal(sale_request_order.total_amount or 0),
                vat_amount=Decimal(sale_request_order.vat_amount or 0),
                ait_amount=Decimal(sale_request_order.ait_amount or 0),
                net_due_amount=Decimal(sale_request_order.net_due_amount or 0),
                currency=sale_request_order.currency,
                customer=sale_request_order.customer,
                remarks=f"Converted from Sale Request #{sale_request_order.order_id}",
            )

            total_amount = Decimal(0)
            for item in sale_request_items:
                # Get warehouse/location input from POST
                warehouse_id = request.POST.get(f'warehouse_{item.id}')
                location_id = request.POST.get(f'location_{item.id}')
                batch_id = request.POST.get(f'batch_{item.id}')

                total_price = (item.unit_selling_price or 0) * (item.quantity or 0)
                SaleOrderItem.objects.create(
                    sale_order=sale_order,
                    sale_request_item=item,
                    user=request.user,
                    product=item.product,
                    quantity=item.quantity,
                    unit_selling_price=item.unit_selling_price,
                    unit_price=item.unit_price,
                    unit_of_measure=item.unit_of_measure,
                    quoted_delivery_date=item.quoted_delivery_date,
                    currency=item.currency,
                    specification=item.specification,
                    notes=item.notes,
                    VAT_rate=item.VAT_rate,
                    VAT_type=item.VAT_type,
                    vat_amount=item.vat_amount,
                    total_price=total_price,
                    status="PENDING",
                    warehouse_id=warehouse_id or None,
                    location_id=location_id or None,
                    batch_id=batch_id or None,
                )
                total_amount += total_price

            sale_order.total_amount = total_amount
            sale_order.save(update_fields=["total_amount"])

            sale_request_order.status = "READY_FOR_DISPATCH"
            sale_request_order.save(update_fields=["status"])

            messages.success(request, f"Sale Order {sale_order.order_id} created successfully.")
            return redirect("sales:sale_order_list")

        except Exception as e:
            transaction.set_rollback(True)
            messages.error(request, f"Error while creating Sale Order: {e}")
            return redirect("sales:sale_request_order_list")

    # GET — show preview with warehouse/location inputs
    from inventory.models import Warehouse, Location
    context = {
        "sale_request_order": sale_request_order,
        "sale_request_items": sale_request_items,
        "warehouses": Warehouse.objects.all(),
        "locations": Location.objects.all(),
        "batches": Batch.objects.all(),
        "total_amount": sale_request_order.total_amount,
        "vat_amount": sale_request_order.vat_amount,
        "ait_amount": sale_request_order.ait_amount,
        "net_due_amount": sale_request_order.net_due_amount,
    }
    return render(request, "sales/confirm_sale_request_conversion.html", context)





@login_required
def create_sale_request(request):
    if 'basket' not in request.session:
        request.session['basket'] = []

    form = SaleRequestForm(request.POST or None)

    if request.method == 'POST':
        if 'add_to_basket' in request.POST:
            if form.is_valid():
                category = form.cleaned_data['category']
                product_obj = form.cleaned_data['product']
                quantity = form.cleaned_data['quantity']
                customer = form.cleaned_data['customer']
                warehouse = form.cleaned_data['warehouse']
                location = form.cleaned_data['location']
                batch= form.cleaned_data['batch']
                unit_selling_price = form.cleaned_data['unit_selling_price']


                customer_id = customer.id if customer else None              

                basket = request.session.get('basket', [])
                product_in_basket = next((item for item in basket if item['id'] == product_obj.id), None)
                total_amount = float(quantity) * float(product_obj.unit_price)

                warehouse_quantity = (
                    InventoryTransaction.objects.filter(
                        warehouse=warehouse.id,
                        product=product_obj.id
                    )
                    .aggregate(
                        total_inbound=Sum(
                            'quantity', filter=Q(transaction_type__in=['INBOUND', 'TRANSFER_IN','MANUFACTURE','REPLACEMENT_IN','EXISTING_ITEM_IN'])
                        ),
                        total_outbound=Sum(
                            'quantity', filter=Q(transaction_type__in=['OUTBOUND', 'TRANSFER_OUT','REPLACEMENT_OUT','OPERATIONS_OUT'])
                        ),
                    )
                )
                warehouse_quantity = (warehouse_quantity['total_inbound'] or 0) - (warehouse_quantity['total_outbound'] or 0)


                current_basket_quantity = sum(
                    item['quantity'] for item in request.session['basket'] if item['id'] == product_obj.id
                )               

                if current_basket_quantity + quantity > warehouse_quantity:
                    messages.error(request, f"There is not enough quantity in the warehouse for '{product_obj.name}'.")
                    return redirect('sales:create_sale_request')
                

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
                        'unit_price': float(batch.unit_price),
                        'unit_selling_price': float(unit_selling_price), 
                        'total_amount': total_amount,
                        'customer_id': customer_id,
                        'batch_id': batch.id
                    })

                request.session['basket'] = basket
                request.session.modified = True
                messages.success(request, f"Added '{product_obj.name}' to the purchase basket")
                return redirect('sales:create_sale_request')
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
            messages.success(request, "Sale basket updated successfully.")
            return redirect('sales:create_sale_request')

        elif 'confirm_purchase' in request.POST:
            basket = request.session.get('basket', [])
            if not basket:
                messages.error(request, "Sale basket is empty. Add products before confirming the purchase.")
                return redirect('sales:create_sale_request')
            return redirect('sales:confirm_sale_request')  

    basket = request.session.get('basket', [])
    return render(request, 'sales/create_sale_request.html', {'form': form, 'basket': basket})



@login_required
def confirm_sale_request(request):
    basket = request.session.get('basket', [])    
    if not basket:
        messages.error(request, "sale basket is empty. Cannot confirm purchase.")
        return redirect('sales:create_sale_request')

    if request.method == 'POST':
        try:
            with transaction.atomic(): 
                total_amount = sum(item['quantity'] * item['unit_selling_price'] for item in basket)
                customer_id = basket[0].get('customer_id')
                batch_id = basket[0].get('batch_id')
                customer = get_object_or_404(Customer, id=customer_id)
                batch = get_object_or_404(Batch,id = batch_id)

                sale_request_order = SaleRequestOrder(
                    total_amount=total_amount,
                    status='PENDING',  
                    user=request.user,
                    customer=customer,
                   
                )
                sale_request_order.save()  
               
                for item in basket:
                    product = get_object_or_404(Product, id=item['id'])
                    quantity = item['quantity']   
                    total_price = quantity * item['unit_selling_price']     
                                   
                    sale_request_item = SaleRequestItem(
                        sale_request_order=sale_request_order,
                        product=product,
                        quantity=quantity,
                        batch=batch,
                        user=request.user,                        
                    )
                    sale_request_item.save()                 
                   
                request.session['basket'] = []
                request.session.modified = True
                messages.success(request, "Sale order created successfully!")
                return redirect('sales:create_sale_request')
        except Exception as e: 
            logger.error("Error creating sale order: %s", e)
            messages.error(request, f"An error occurred while creating the sale order: {str(e)}")
            return redirect('sales:create_sale_request')
    return render(request, 'sales/confirm_sale_request.html', {'basket': basket})





@login_required
def sale_request_order_list(request):
    sale_request_order=None
    sale_request_orders = SaleRequestOrder.objects.all().order_by("-created_at")
    form = CommonFilterForm(request.GET or None)
    if form.is_valid():
        sale_request_order = form.cleaned_data['sale_request_order_id']
        if sale_request_order:
            sale_request_orders = sale_request_orders.filter(order_id=sale_request_order)

    paginator= Paginator( sale_request_orders,10)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    form=CommonFilterForm()
    return render (request, 'sales/sale_request_order_list.html',
        {
            'sale_request_orders':sale_request_orders,
            'form':form,
            'sale_request_order':sale_request_order,
            'page_obj':page_obj
        })


from decimal import Decimal
@login_required
def sale_request_items(request,order_id):
    order_instance = get_object_or_404(SaleRequestOrder,id=order_id)
    total_amount = 0
    items = order_instance.sale_request_order.all()
    for item in items:
        item_price = Decimal(item.unit_selling_price) * Decimal(item.quantity) if item.unit_selling_price else 0
        total_amount += item_price

    return render(request,'sales/sale_request_items.html',{'order_instance':order_instance,'total_amount':total_amount})



@login_required
def process_sale_request(request, order_id):
    order = get_object_or_404(SaleRequestOrder, id=order_id)

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
                return redirect('sales:sale_request_order_list')

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
            return redirect('sales:sale_request_order_list')
        else:
            messages.error(request, "Invalid form submission.")
    else:
        form = PurchaseStatusForm()

    return render(request, 'sales/sale_order_approval_form.html', {'form': form, 'order': order})





@login_required
def create_sale_order(request, request_id):
    request_instance = get_object_or_404(SaleRequestOrder, id=request_id)
    if 'basket' not in request.session:
        request.session['basket'] = []
    form = SaleOrderForm(request.POST, request_instance=request_instance)

    if request.method == 'POST':
        if 'add_to_basket' in request.POST:
            if form.is_valid():
                product_obj = form.cleaned_data['product']
                quantity = form.cleaned_data['quantity']
                warehouse = form.cleaned_data['warehouse']
                location = form.cleaned_data['location']
                sale_request_item = form.cleaned_data['sale_request_item']
                batch = form.cleaned_data['batch']
                unit_selling_price= form.cleaned_data['unit_selling_price']

                total_requested_quantity = (
                    request_instance.sale_request_order.filter(product=product_obj)
                    .aggregate(total_requested=Sum('quantity'))
                    .get('total_requested', 0)
                )

                if not total_requested_quantity:
                    messages.error(
                        request,
                        f"The product '{product_obj.name}' is not part of this sale request."
                    )
                    return redirect('sales:create_sale_order', request_instance.id)

                warehouse_quantity = (
                    InventoryTransaction.objects.filter(
                        warehouse=warehouse.id,
                        product=product_obj.id
                    )
                    .aggregate(
                        total_inbound=Sum(
                            'quantity', filter=Q(transaction_type__in=['INBOUND', 'TRANSFER_IN','MANUFACTURE','REPLACEMENT_IN','EXISTING_ITEM_IN'])
                        ),
                        total_outbound=Sum(
                            'quantity', filter=Q(transaction_type__in=['OUTBOUND', 'TRANSFER_OUT','REPLACEMENT_OUT','OPERATIONS_OUT'])
                        ),
                    )
                )
                warehouse_quantity = (warehouse_quantity['total_inbound'] or 0) - (warehouse_quantity['total_outbound'] or 0)


                current_basket_quantity = sum(
                    item['quantity'] for item in request.session['basket'] if item['id'] == product_obj.id
                )

                new_total_quantity = current_basket_quantity + quantity
                if new_total_quantity > total_requested_quantity:
                    messages.error(
                        request,
                        f"Quantity exceeds the requested quantity for '{product_obj.name}' ({total_requested_quantity})."
                    )
                    return redirect('sales:create_sale_order', request_instance.id)

                if new_total_quantity > warehouse_quantity:
                    messages.error(
                        request,
                        f"There is not enough stock in the warehouse for '{product_obj.name}'. "
                        f"Available: {warehouse_quantity}, Requested: {new_total_quantity}."
                    )
                    return redirect('sales:create_sale_order', request_instance.id)

                total_amount = float(quantity) * float(unit_selling_price)
                basket = request.session['basket']
                product_in_basket = next((item for item in basket if item['id'] == product_obj.id), None)

                if product_in_basket:
                    product_in_basket['quantity'] += quantity
                    product_in_basket['total_amount'] += total_amount
                else:
                    basket.append({
                        'sale_request_item_id': sale_request_item.id,
                        'id': product_obj.id,
                        'name': product_obj.name,
                        'product_type': product_obj.product_type,
                        'category': form.cleaned_data['category'].name,
                        'warehouse': warehouse.name,
                        'warehouse_id': warehouse.id,
                        'batch': batch.batch_number,
                        'batch_id': batch.id,
                        'location': location.name,
                        'location_id': location.id,
                        'quantity': quantity,
                        'sku': product_obj.sku,
                        'unit_price': float(batch.sale_price),
                        'unit_selling_price':unit_selling_price,
                        'customer_id': form.cleaned_data['customer'].id,
                        'customer': form.cleaned_data['customer'].name,
                        'total_amount': total_amount,
                        'sale_request_order_id': request_instance.id,
                    })

                request.session['basket'] = basket
                request.session.modified = True
                messages.success(request, f"Added '{product_obj.name}' to the purchase basket.")
                return redirect('sales:create_sale_order', request_instance.id)
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
            messages.success(request, "Sale basket updated successfully.")
            return redirect('sales:create_sale_order', request_instance.id)

        elif 'confirm_purchase' in request.POST:
            basket = request.session.get('basket', [])
            if not basket:
                messages.error(request, "Sale basket is empty. Add products before confirming the purchase.")
                return redirect('sales:create_sale_order', request_instance.id)
            return redirect(f"{reverse('sales:confirm_sale_order')}?request_id={request_instance.id}")

    form = SaleOrderForm(
    initial={
        'sale_request_order': request_instance,
        'customer': request_instance.customer,  
        'sale_request_item':request_instance.sale_request_order.first()
    },
    request_instance=request_instance
)

    basket = request.session.get('basket', [])
    return render(request, 'sales/create_sale_order.html', {'form': form, 'basket': basket})



@login_required
def confirm_sale_order(request):
    basket = request.session.get('basket', [])
    if not basket:
        messages.error(request, "Sale basket is empty. Cannot confirm purchase.")
        return redirect('sales:create_sale_order')

    if request.method == 'POST':
        try:
            with transaction.atomic():
                sale_request_order_id = basket[0].get('sale_request_order_id')
                if not sale_request_order_id:
                    messages.error(request, "Sale Request Order is required.")
                    return redirect('sales:create_sale_order')

                order_id = f"SOID-{uuid.uuid4().hex[:8].upper()}"
                customer_id = basket[0].get('customer_id')  
                warehouse_id = basket[0].get('warehouse_id') 
                location_id = basket[0].get('location_id') 
                batch_id =basket[0].get('batch_id')
                total_amount = basket[0]('total_amount')
                if not customer_id:
                    messages.error(request, "Customer ID is required.")
                    return redirect('sales:create_sale_order')

                customer = get_object_or_404(Customer, id=customer_id) 
                warehouse = get_object_or_404(Warehouse, id=warehouse_id) 
                location = get_object_or_404(Location, id=location_id) 
                batch = get_object_or_404(Batch,id=batch_id)

                sale_order = SaleOrder(
                    order_id=order_id,
                    sale_request_order_id=sale_request_order_id,
                    customer=customer,
                    warehouse=warehouse,
                    location= location,
                    
                    total_amount=0,
                    status='IN_PROCESS',
                    user=request.user
                )
                sale_order.save() 

                total_amount = 0
                for item in basket:
                    product = get_object_or_404(Product, id=item['id'])
                    total_price = item['quantity'] * item['unit_selling_price']
                    sale_request_item_id = get_object_or_404(SaleRequestItem, id=item['sale_request_item_id'])
                    
                    warehouse = get_object_or_404(Warehouse, id=item['warehouse_id'])
                    location = get_object_or_404(Location, id=item['location_id'])
                    batch = get_object_or_404(Batch, id=item['batch_id'])  

                    if batch.remaining_quantity < item['quantity']:
                        messages.error(request, f"Not enough stock in batch {batch.batch_number} for {product.name}.")
                        return redirect('sales:create_sale_order')                 
                  
                    total_amount += total_price

                    SaleOrderItem.objects.create(
                        sale_order=sale_order,
                        product=product,
                        quantity=item['quantity'],
                        warehouse=warehouse,
                        location= location,
                        total_price=total_price,
                        batch=batch,
                        unit_selling_price =item['sale_unit_cost'],
                        user=request.user,
                        sale_request_item =sale_request_item_id 
                    )                  

                sale_order.total_amount = total_amount
                sale_order.save(update_fields=['total_amount'])  

                request.session['basket'] = []
                request.session.modified = True
                messages.success(request, "Sale order created successfully!")
                return redirect('sales:create_sale_order',sale_request_order_id)

        except Exception as e:
            messages.error(request, f"An error occurred while creating the sale order: {str(e)}")
            return redirect('sales:create_sale_order',sale_request_order_id)

    return render(request, 'sales/confirm_sale_order.html', {'basket': basket})


@login_required
def sale_order_list(request):
    sale_order =None
    sale_orders = SaleOrder.objects.all().order_by("-created_at")   

    form = CommonFilterForm(request.GET or None)
    if form.is_valid():
        sale_order = form.cleaned_data['sale_order_id']
        if sale_order:
            sale_orders = sale_orders.filter(order_id=sale_order)
   
        for order in sale_orders:
            order.has_payment_attachment = (
                order.sale_shipment.first()
                and order.sale_shipment.first().sale_shipment_invoices.first()
                and order.sale_shipment.first().sale_shipment_invoices.first().sale_payment_invoice.exists()
            )
    else:
        for field, errors in form.errors.items():
            for error in errors:
                messages.error(request, f"{field.capitalize()}: {error}")


    paginator= Paginator( sale_orders,10)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    form = CommonFilterForm()
    return render (request, 'sales/sale_order_list.html',
        {
            'sale_orders':sale_orders,
            'form':form,
            'sale_order':sale_order,
            'page_obj':page_obj
        })


@login_required
def sale_order_list_report(request):
    sale_order =None
    sale_orders = SaleOrder.objects.all().order_by("-created_at")    
    form = CommonFilterForm(request.GET or None)
    if form.is_valid():
        sale_order = form.cleaned_data['ID_number']
        if sale_order:
            sale_orders = sale_orders.filter(order_id=sale_order)
   
    else:
        for field, errors in form.errors.items():
            for error in errors:
                messages.error(request, f"{field.capitalize()}: {error}")

    paginator= Paginator( sale_orders,10)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    return render (request, 'sales/sale_order_list_report.html',
      {
            'sale_orders':sale_orders,
            'form':form,
            'sale_order':sale_order,
            'page_obj':page_obj
        })
    

@login_required
def sale_order_items(request,order_id):
    order_instance = get_object_or_404(SaleOrder,id=order_id)
    items = order_instance.sale_order.all()
    total_amount = 0
    for item in items:
        item_price = item.unit_selling_price * item.quantity
        total_amount += item_price
   
    return render(request,'sales/sale_order_items.html',{'order_instance':order_instance,'total_amount':total_amount})




@login_required
def process_sale_order(request, order_id):
    order = get_object_or_404(SaleOrder, id=order_id)

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
                return redirect('sales:sale_order_list')

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
            return redirect('sales:sale_order_list')
        else:
            messages.error(request, "Invalid form submission.")
    else:
        form = PurchaseStatusForm()
    return render(request, 'sales/sale_order_approval_form.html', {'form': form, 'order': order})




@login_required
def sale_order_item(request):
    total_sale = 0
    form = SaleOrderSearchForm(request.GET or None)
    sale_orders = SaleOrder.objects.prefetch_related(
        'sale_shipment__shipment_dispatch_item'
    ).all()
    for sale in sale_orders:
        total_sale  = sale.total_amount

    return render(request, 'sales/sale_order_item.html', {
        'sale_orders': sale_orders,
        'form': form,
        'total_sale':total_sale
    })


@login_required
def sale_order_item_dispatch(request, order_id):
    purchase_order = get_object_or_404(
        SaleOrder.objects.prefetch_related(
            'sale_order_item',  
            'sale_order_item__order_dispatch_item', 
            
        ),
        order_id=order_id
    )
    return render(request, 'sales/sale_order_item_dispatch.html', {
        'purchase_order': purchase_order,
    })





@login_required
def update_sale_order_status(request, order_id):
    sale_order = get_object_or_404(SaleOrder, id=order_id)
 
    all_items = sale_order.sale_order.all()

    all_delivered = True
    for item in all_items:
        total_dispatched_quantity = item.sale_dispatch_item.aggregate(
            total=Sum('dispatch_quantity', filter=Q(status='DELIVERED'))
        )['total'] or 0

        
        if total_dispatched_quantity < item.quantity:
            all_delivered = False
            break
   
    if all_delivered:
        sale_order.status = 'DELIVERED'
        sale_order.save()
        messages.success(request, "All items have been delivered. Purchase order status updated to DELIVERED.")
    else:
        messages.info(request, "Not all items have been delivered yet. Status remains unchanged.")
    
    return redirect('sales:sale_order_list')



@login_required
def qc_dashboard(request, sale_order_id=None):
    if sale_order_id:
        pending_items = SaleDispatchItem.objects.filter(
            sale_shipment__sales_order=sale_order_id,  
            status = 'READY_FOR_DISPATCH'
        )
        sale_order = get_object_or_404(SaleOrder, id=sale_order_id)
    else:
        pending_items = SaleDispatchItem.objects.filter(status='READY_FOR_DISPATCH')
        sale_order = None

    if not pending_items:
        messages.info(request, "No items pending for quality control inspection.")
    return render(request, 'sales/qc_dashboard.html', {'pending_items': pending_items, 'sale_order': sale_order})



from purchase.models import Batch

@login_required
def qc_inspect_item(request, item_id):
    sale_dispatch_item = get_object_or_404(SaleDispatchItem, id=item_id)
    sale_order = sale_dispatch_item.dispatch_item.sale_order
    sale_request_order = sale_order.sale_request_order
    shipment = sale_dispatch_item.sale_shipment   
    sale_order_item = sale_dispatch_item.dispatch_item
    sale_request_item = sale_order_item.sale_request_item

    batch = sale_dispatch_item.batch or sale_order_item.batch

    if request.method == 'POST':
        form = QualityControlForm(request.POST,initial_warehouse=sale_dispatch_item.warehouse,initial_location=sale_dispatch_item.location)

        if form.is_valid():
            qc_entry = form.save(commit=False)
            qc_entry.sale_dispatch_item = sale_dispatch_item
            qc_entry.user = request.user
            qc_entry.quality_checked_by = 'BY-EMPLOYEE'
            qc_entry.inspection_date = timezone.now()
            qc_entry.save()

            sale_dispatch_item.status = 'DISPATCHED' 
            sale_dispatch_item.save()

            good_quantity = qc_entry.good_quantity
            warehouse = sale_dispatch_item.warehouse
            location = sale_dispatch_item.location
            qty_to_deduct = good_quantity  
           
            if InventoryTransaction.objects.filter(
                sales_order=sale_order,
                transaction_type='OUTBOUND',
                product=qc_entry.product
            ).exists():
                messages.error(request, "This transaction has already been recorded.")
                return redirect('sales:qc_dashboard')

            if warehouse and location:
                try:
                    with transaction.atomic():                 
                        if batch.remaining_quantity >= qty_to_deduct:
                            batch.remaining_quantity -= qty_to_deduct
                            qty_to_deduct = 0  
                        else:
                            qty_to_deduct -= batch.remaining_quantity
                            batch.remaining_quantity = 0  
                        batch.save()

                        inventory = Inventory.objects.filter(
                        warehouse=warehouse,
                        location=location,
                        product=qc_entry.product,
                        ).first()

                        if inventory:
                            if inventory.quantity >= good_quantity:
                                inventory.quantity -= good_quantity
                                inventory.save()
                                messages.success(request, "Inventory updated successfully.")
                            else:
                                messages.error(request, "Not enough stock in inventory.")
                                return redirect('sales:qc_dashboard')
                        else:
                            messages.error(request, "No inventory record found for this product, warehouse, and batch.")
                            return redirect('sales:qc_dashboard')
                                                # Record the transaction
                        inventory_transaction = InventoryTransaction.objects.create(
                            user=request.user,
                            warehouse=warehouse,
                            location=location,
                            product=qc_entry.product,
                            batch=batch,
                            transaction_type='OUTBOUND',
                            quantity=good_quantity,
                            sales_order=sale_order
                        )

                        inventory_transaction.inventory_transaction = inventory
                        inventory_transaction.save()

                except Inventory.DoesNotExist:
                    messages.error(request, f"Product {qc_entry.product.name} not found in {warehouse.name} at {location.name}.")
                    return redirect('sales:qc_dashboard')
                except ValueError as ve:
                    messages.error(request, str(ve))
                    return redirect('sales:qc_dashboard')
                except Exception as e:
                    messages.error(request, f"Unexpected error: {e}")
                    return redirect('sales:qc_dashboard')

            sale_order.status = 'DISPATCHED'
            sale_order.save()

            sale_order_item.status ='DISPATCHED'
            sale_order_item.save()

            sale_request_order.status ='DISPATCHED'
            sale_request_order.save()

            sale_request_item.status = 'DISPATCHED'
            sale_request_item.save()

            all_items_delivered = sale_order.sale_order.filter(status='DELIVERED').count() == sale_order.sale_order.count()
            if all_items_delivered:
                sale_order.status = 'DELIVERED'
                sale_order.save()

            total_requested_quantity = sale_request_order.sale_request_order.aggregate(Sum('quantity'))['quantity__sum']
            total_ordered_quantity = SaleOrderItem.objects.filter(
                sale_request_item__sale_request_order=sale_request_order
            ).aggregate(total_ordered=Sum('quantity'))['total_ordered']

            if total_ordered_quantity >= total_requested_quantity:
                sale_request_order.status = 'DELIVERED'
                sale_request_order.save()

            update_sale_order(sale_order.id)          
            update_sale_request_order(sale_request_order.id)

            create_notification(request.user, message=f'Sale request order number: {sale_request_order} has been dispatched', notification_type='SALES-NOTIFICATION')

            messages.success(request, "Quality control inspection recorded and inventory updated successfully.")
            return redirect('sales:qc_dashboard')
        else:  
            for field, errors in form.errors.items():
                for error in errors:
                    messages.error(request, f"{field.capitalize()}: {error}")
    else:
        form = QualityControlForm(
            initial={
                'total_quantity': sale_dispatch_item.dispatch_quantity,
                'warehouse': sale_dispatch_item.warehouse,
                'location': sale_dispatch_item.location,
            },
            initial_warehouse=sale_dispatch_item.warehouse,
            initial_location=sale_dispatch_item.location
        )

    return render(request, 'sales/qc_inspect_item.html', {
        'form': form,
        'sale_dispatch_item': sale_dispatch_item
    })



def product_sales_report(request):
    chart_data={}
    sales_table_data = []
    products = set()
    dates = set()
    product_name = None
    sales_data={}
   

    form=SalesReportForm(request.GET or None)
    if form.is_valid():
        start_date = form.cleaned_data['start_date']
        end_date = form.cleaned_data['end_date']
        product_name = form.cleaned_data.get('product_name')
        sales_data = SaleOrderItem.objects.all()
        if start_date and end_date:
            sales_data = sales_data.filter(sale_order__order_date__range=(start_date,end_date))        
        if product_name:
            sales_data = sales_data.filter(product=product_name)
        sales_data = (
            sales_data.annotate(order_date=TruncDate(F('sale_order__order_date')))
            .values('order_date', 'product__name')
            .annotate(total_sold=Sum('quantity'))
            .order_by('order_date', 'product__name')
        )

        sales_dict = defaultdict(lambda: defaultdict(int))
        for sale in sales_data:
            product_name = sale['product__name']
            order_date = sale['order_date'].strftime('%Y-%m-%d')
            total_sold = sale['total_sold']
            products.add(product_name)
            dates.add(order_date)
            sales_dict[product_name][order_date] = total_sold
        products = sorted(products)
        dates = sorted(dates)        
        for product in products:
            product_sales = [sales_dict[product].get(date, 0) for date in dates]
            sales_table_data.append({
                'product': product,
                'sales': product_sales
            })
        chart_data = {
            'labels': dates,
            'datasets': []
        }
        for product in products:
            chart_data['datasets'].append({
                'label': product,
                'data': [sales_dict[product].get(date, 0) for date in dates],
                'backgroundColor': f'rgba({hash(product) % 255}, {hash(product) // 255 % 255}, 150, 0.6)',
                'borderColor': f'rgba({hash(product) % 255}, {hash(product) // 255 % 255}, 150, 1)',
                'borderWidth': 2
            })       
    else:
        print('form is invalid',form.errors)
        form=SalesReportForm()

    paginator=Paginator(sales_table_data,8)
    page_number=request.GET.get('page')
    page_obj=paginator.get_page(page_number)

    form=SalesReportForm()
    return render(request, 'sales/sales_report.html', {
        'chart_data': json.dumps(chart_data),
        'sales_table_data': sales_table_data,
        'dates': dates,
        'page_obj':page_obj,
        'form':form,
        'sales_data': sales_data,
        'product_name':product_name
    })
