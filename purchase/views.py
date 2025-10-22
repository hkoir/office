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




from django.forms import formset_factory
from .utils import create_purchase_order_from_quotation
from .models import SupplierQuotation 
from .forms import SupplierQuotationForm,SupplierQuotationItemFormSet,RFQForm,RFQItemFormSet,Batch,BatchForm
from .models import RFQ
from django.forms import modelformset_factory
from.forms import BatchFormShort
from inventory.models import InventoryTransaction,Inventory

from django.core.files.base import ContentFile
import qrcode
from barcode import Code128
from barcode.writer import ImageWriter
from io import BytesIO
from datetime import timedelta



@login_required
def purchase_dashboard(request):
    return render(request,'purchase/purchase_dashboard.html')

from django.db.models import F




@login_required
def manage_batch(request, id=None):  
    instance = get_object_or_404(Batch, id=id) if id else None
    is_edit = bool(instance)
    message_text = "Batch updated successfully!" if is_edit else "Batch created successfully!"
    next_url = request.GET.get('next') or request.POST.get('next')

    form = BatchForm(request.POST or None, request.FILES or None, instance=instance)

    if request.method == 'POST':
        if form.is_valid():
            product = form.cleaned_data['product']
            manufacture_date = form.cleaned_data['manufacture_date']
            expiry_date = form.cleaned_data['expiry_date']
            quantity = form.cleaned_data['quantity']
            purchase_price = form.cleaned_data.get('purchase_price')

            if not is_edit:
                # Try to find an existing batch with same attributes
                existing_batch = Batch.objects.filter(
                    product=product,
                    manufacture_date=manufacture_date,
                    expiry_date=expiry_date,
                    purchase_price=purchase_price
                ).first()

                if existing_batch:
                    # Update existing batch quantities safely
                    existing_batch.quantity = F('quantity') + quantity
                    existing_batch.remaining_quantity = F('remaining_quantity') + quantity
                    existing_batch.save(update_fields=['quantity', 'remaining_quantity'])
                    existing_batch.refresh_from_db()
                    messages.info(
                        request, 
                        f"Existing batch for {product.name} updated with +{quantity} units. "
                        f"Total now: {existing_batch.quantity}"
                    )
                else:
                    # Create a new batch
                    batch = form.save(commit=False)
                    batch.user = request.user
                    batch.remaining_quantity = quantity
                    batch.save()
                    messages.success(request, "New batch created successfully!")
            else:
                # Editing existing batch
                batch = form.save()
                messages.success(request, message_text)
      
            if next_url:
                return redirect(next_url)
            return redirect('purchase:create_batch')

        else:       
            messages.error(request, "Form invalid — please check the highlighted fields.")
            print(form.errors)

    # List all batches for context
    datas = Batch.objects.all().order_by('-updated_at')
    paginator = Paginator(datas, 10)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    return render(request, 'purchase/manage_batch.html', {
        'form': form,
        'instance': instance,
        'page_obj': page_obj,
        'next': next_url,  
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



@login_required
def batch_list(request):
    query = request.GET.get("q", "")
    batches = Batch.objects.all().order_by("-created_at")

    if query:
        batches = batches.filter(
            Q(batch_number__icontains=query) |
            Q(product__name__icontains=query)
        )

    datas = batches
    paginator = Paginator(datas, 5)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    return render(request, "purchase/batch_list.html", {
        "batches": batches,
        "query": query,
        'page_obj':page_obj
    })



@login_required
def generate_batch_codes(request, batch_id):
    batch = get_object_or_404(Batch, id=batch_id)
    if not batch.barcode:
        batch.barcode = f"{batch.product.product_id}-{batch.batch_number}"
    qr = qrcode.QRCode(version=1, box_size=10, border=2)
    qr.add_data(batch.barcode)
    qr.make(fit=True)
    img = qr.make_image(fill="black", back_color="white")
    buffer = BytesIO()
    img.save(buffer, format="PNG")
    batch.qr_code_image.save(f"{batch.batch_number}_qr.png", ContentFile(buffer.getvalue()), save=False)
    barcode_img = Code128(batch.barcode, writer=ImageWriter())
    barcode_buffer = BytesIO()
    barcode_img.write(barcode_buffer)
    batch.barcode_image.save(f"{batch.batch_number}_barcode.png", ContentFile(barcode_buffer.getvalue()), save=False)
    batch.save(update_fields=['barcode', 'barcode_image', 'qr_code_image'])
    messages.success(request, f"Barcode and QR code generated for batch {batch.batch_number}.")
    return redirect("product:print_unit_labels", batch_id=batch.id)




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
def create_purchase_request2(request):
    
    if 'basket' not in request.session:
        request.session['basket'] = []
    form = PurchaseRequestForm(request.POST or None)
   
    if request.method == 'POST':
        if 'add_to_basket' in request.POST:
            if form.is_valid():

                category = form.cleaned_data['category']
                product_obj = form.cleaned_data['product']
                batch_obj = form.cleaned_data['batch']
                quantity = form.cleaned_data['quantity']

                product_stocks = Inventory.objects.filter(product=product_obj)

                total_available_stock = sum(stock.quantity for stock in product_stocks)
                product_average_usage = calculate_average_usage(product_obj)  
                product_required_stock = product_average_usage * product_obj.lead_time  

                if total_available_stock > product_required_stock:
                    messages.info(request, f'There is enough total stock for {product_obj.name}, current stock qty={total_available_stock}')
                    return redirect('purchase:create_purchase_request')

                warehouse_messages = []
                for stock in product_stocks:
                    warehouse_avg_usage = calculate_average_usage(product_obj, stock.warehouse)
                    warehouse_required_stock = warehouse_avg_usage * product_obj.lead_time

                    if stock.quantity > warehouse_required_stock:
                        warehouse_messages.append(f"{stock.product.name} in {stock.warehouse.name}, total avaailable stoc={stock.quantity}")
              
                if warehouse_messages:
                    messages.info(request, f'There is enough stock in these warehouses: {", ".join(warehouse_messages)}')
                    return redirect('purchase:create_purchase_request')

                basket = request.session.get('basket', [])
                product_in_basket = next((item for item in basket if item['id'] == product_obj.id), None)
                unit_price = (
                    float(batch_obj.purchase_price)
                    if batch_obj and batch_obj.purchase_price is not None
                    else float(product_obj.unit_price or 0)
                )

                total_amount = float(quantity) * unit_price

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
                        'unit_price':  unit_price,
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



from datetime import date, datetime

@login_required
def create_purchase_request(request):
    # Ensure basket exists in session
    if 'basket' not in request.session:
        request.session['basket'] = []

    form = PurchaseRequestForm(request.POST or None)

    if request.method == 'POST':

        # --- Add to basket ---
        if 'add_to_basket' in request.POST:
            if form.is_valid():
                category = form.cleaned_data['category']
                product_obj = form.cleaned_data['product']
                batch_obj = form.cleaned_data['batch']
                quantity = form.cleaned_data['quantity']
                supplier = form.cleaned_data['supplier']
                unit_price = form.cleaned_data['unit_price']
                unit_of_measure = form.cleaned_data['unit_of_measure']
                currency = form.cleaned_data['currency']
                required_delivery_date = form.cleaned_data['required_delivery_date']
                specification = form.cleaned_data['specification']
                notes= form.cleaned_data['notes']

                # ✅ Convert non-serializable data
                if isinstance(required_delivery_date, (date, datetime)):
                    required_delivery_date = required_delivery_date.isoformat()  # Convert date to string

                # --- Stock check logic ---
                product_stocks = Inventory.objects.filter(product=product_obj)
                total_available_stock = sum(stock.quantity for stock in product_stocks)
                product_average_usage = calculate_average_usage(product_obj)
                product_required_stock = product_average_usage * product_obj.lead_time

                if total_available_stock > product_required_stock:
                    messages.info(
                        request,
                        f"There is enough total stock for {product_obj.name}, current stock qty={total_available_stock}"
                    )
                    return redirect('purchase:create_purchase_request')

                warehouse_messages = []
                for stock in product_stocks:
                    warehouse_avg_usage = calculate_average_usage(product_obj, stock.warehouse)
                    warehouse_required_stock = warehouse_avg_usage * product_obj.lead_time
                    if stock.quantity > warehouse_required_stock:
                        warehouse_messages.append(
                            f"{stock.product.name} in {stock.warehouse.name}, total available stock={stock.quantity}"
                        )

                if warehouse_messages:
                    messages.info(
                        request,
                        f"There is enough stock in these warehouses: {', '.join(warehouse_messages)}"
                    )
                    return redirect('purchase:create_purchase_request')

                # --- Determine unit price ---
                if batch_obj:
                    unit_price = float(batch_obj.purchase_price or 0)
                else:
                    latest_batch = (
                        Batch.objects.filter(product=product_obj)
                        .order_by('-created_at')
                        .first()
                    )
                    unit_price = float(
                        (latest_batch.purchase_price if latest_batch and latest_batch.purchase_price else product_obj.unit_price) or 0
                    )

                # --- Basket update logic ---
                basket = request.session.get('basket', [])
                product_in_basket = next((item for item in basket if item['id'] == product_obj.id), None)
                total_amount = float(quantity) * unit_price

                if product_in_basket:
                    product_in_basket['quantity'] += quantity
                    product_in_basket['total_amount'] = product_in_basket['quantity'] * unit_price
                else:
                    basket.append({
                        'id': product_obj.id,
                        'name': product_obj.name,
                        'product_type': form.cleaned_data['product_type'],
                        'category': category.name,
                        'quantity': quantity,
                        'sku': product_obj.sku,
                        'unit_price': unit_price,
                        'total_amount': total_amount,
                        'supplier': supplier.name if supplier else None,
                        'required_delivery_date': required_delivery_date,
                        'unit_of_measure': unit_of_measure,
                        'specification': specification,
                        'currency': currency,
                        'notes':notes
                    })

                # --- Grand total update ---
                grand_total = sum(float(item['total_amount']) for item in basket)
                request.session['basket'] = basket
                request.session['grand_total'] = grand_total
                request.session.modified = True

                messages.success(request, f"✅ Added '{product_obj.name}' to the purchase basket.")
                return redirect('purchase:create_purchase_request')

            else:
                messages.error(request, "⚠️ Form is invalid. Please check the details and try again.")

        # --- Update/Delete from basket ---
        elif 'action' in request.POST:
            action = request.POST['action']
            product_id = int(request.POST.get('product_id', 0))
            basket = request.session.get('basket', [])

            if action == 'update':
                new_quantity = int(request.POST.get('quantity', 1))
                for item in basket:
                    if item['id'] == product_id:
                        item['quantity'] = new_quantity
                        item['total_amount'] = new_quantity * float(item['unit_price'])

            elif action == 'delete':
                basket = [item for item in basket if item['id'] != product_id]

            # Recalculate grand total after update/delete
            request.session['basket'] = basket
            request.session['grand_total'] = sum(float(i['total_amount']) for i in basket)
            request.session.modified = True

            messages.success(request, "🧺 Purchase basket updated successfully.")
            return redirect('purchase:create_purchase_request')

        # --- Confirm Purchase ---
        elif 'confirm_purchase' in request.POST:
            basket = request.session.get('basket', [])
            if not basket:
                messages.error(request, "⚠️ Purchase basket is empty. Add products before confirming.")
                return redirect('purchase:create_purchase_request')
            return redirect('purchase:confirm_purchase_request')

    # --- Default page load ---
    basket = request.session.get('basket', [])
    grand_total = request.session.get('grand_total', 0)
    return render(
        request,
        'purchase/create_purchase_request.html',
        {'form': form, 'basket': basket, 'grand_total': grand_total}
    )





@login_required
def confirm_purchase_request(request):   
    basket = request.session.get('basket', [])
    grand_total = 0

    # Ensure basket is a list
    if not isinstance(basket, list):
        basket = []
        request.session['basket'] = basket

    # Handle empty basket
    if not basket:
        messages.error(request, "Purchase basket is empty. Cannot confirm purchase.")
        return redirect('purchase:create_purchase_request')

    # Calculate total
    for item in basket:       
        line_total = float(item['total_amount'])        
        grand_total += line_total  

    if request.method == 'POST':
        try:
            with transaction.atomic():
                total_amount = sum(float(item['quantity']) * float(item['unit_price']) for item in basket)
                supplier_name = basket[0].get('supplier') if basket else None                
                supplier = get_object_or_404(Supplier, name=supplier_name)
                required_delivery_date =basket[0].get('required_delivery_date') if basket else None  

                # Create PurchaseRequestOrder
                purchase_request_order = PurchaseRequestOrder.objects.create(
                    total_amount=float(total_amount),
                    status='IN_PROCESS',   # ✅ match your model choices
                    approval_status='SUBMITTED',
                    user=request.user,
                    supplier=supplier,
                    required_delivery_date=required_delivery_date

                )

                # Create PurchaseRequestItems
                for item in basket:
                    product = get_object_or_404(Product, id=item['id'])
                    quantity = float(item['quantity'])
                    unit_price = float(item['unit_price'])
                    total_price = float(quantity) * unit_price
                    unit_of_measure=item['unit_of_measure']
                    currency=item['currency']
                    item_required_delivery_date=item['required_delivery_date']
                    specification = item['specification']

                    PurchaseRequestItem.objects.create(
                        purchase_request_order=purchase_request_order,
                        product=product,
                        quantity=quantity,
                        user=request.user,
                        supplier=supplier,
                        unit_price=unit_price,
                        total_price=total_price,
                        priority='MEDIUM',
                        unit_of_measure=unit_of_measure,
                        currency=currency,
                        required_delivery_date = item_required_delivery_date,
                        specification=specification,
                        notes=item['notes']

                    )

                # Clear basket
                request.session['basket'] = []
                request.session.modified = True

                messages.success(request, "Purchase request order created successfully!")
                return redirect('purchase:purchase_request_order_list')

        except Exception as e:
            logger.error("Error creating purchase order: %s", e)
            messages.error(request, f"An error occurred while creating the purchase order: {str(e)}")
            return redirect('purchase:purchase_request_order_list')

    return render(request, 'purchase/confirm_purchase_request.html', {
        'basket': basket,
        'grand_total': grand_total
    })






from .forms import PurchaseRequestOrderForm, PurchaseRequestItemFormSet
from .models import PurchaseRequestOrder



@transaction.atomic
def create_purchase_request_order(request):
    if request.method == "POST":
        order_form = PurchaseRequestOrderForm(request.POST)
        formset = PurchaseRequestItemFormSet(request.POST)

        if order_form.is_valid() and formset.is_valid():
            order = order_form.save(commit=False)
            order.user = request.user
            order.save()  # save parent first
            items = formset.save(commit=False)

            for item in items:
                item.purchase_request_order = order
                # ensure unit_price and quantity are not None
                item.unit_price = item.unit_price or 0
                item.quantity = item.quantity or 0
                item.total_price = item.unit_price * item.quantity
                item.save()

            # calculate total_amount safely
            total_amount = sum(
                (item.unit_price or 0) * (item.quantity or 0) 
                for item in order.purchase_request_order.all()
            )
            order.total_amount = total_amount
            order.save()

            messages.success(request, f"Purchase Request Order {order.order_id or order.id} created successfully.")
            return redirect('purchase:purchase_request_order_list')

        else:
            messages.error(request, "Please correct the errors in the form or items.")
    else:
        order_form = PurchaseRequestOrderForm()
        formset = PurchaseRequestItemFormSet()

    return render(request, 'purchase/create_purchase_request_order.html', {
        'order_form': order_form,
        'formset': formset,
    })


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








###########################################################################################@login_required

@login_required
def create_rfq(request, request_order_id):
    purchase_request_order = get_object_or_404(PurchaseRequestOrder, id=request_order_id)

    if request.method == "POST":
        form = RFQForm(request.POST)
        formset = RFQItemFormSet(request.POST)

        if form.is_valid() and formset.is_valid():
            with transaction.atomic():
                # Save RFQ instance
                rfq = form.save(commit=False)
                rfq.purchase_request_order = purchase_request_order
                rfq.save()

                # ✅ Save selected suppliers (ManyToManyField)
                form.save_m2m()

                # Validate each RFQ item against PurchaseRequestOrder
                for form_data in formset.cleaned_data:
                    if not form_data or form_data.get("DELETE"):
                        continue

                    product = form_data.get("product")
                    qty_requested = form_data.get("quantity")

                    try:
                        pr_item = purchase_request_order.purchase_request_order.get(product=product)
                    except PurchaseRequestItem.DoesNotExist:
                        messages.error(
                            request,
                            f"{product} was not part of the purchase request."
                        )
                        return redirect("purchase:purchase_request_order_list")

                    if qty_requested > pr_item.quantity:
                        messages.warning(
                            request,
                            f"Cannot assign {qty_requested} units for {product}, "
                            f"requested only {pr_item.quantity}."
                        )
                        return redirect("purchase:purchase_request_order_list")

                # Save RFQ items
                formset.instance = rfq
                formset.save()

            messages.success(request, f"RFQ {rfq.rfq_number} created successfully.")
            return redirect("purchase:rfq_detail", pk=rfq.pk)

    else:
        form = RFQForm(initial={'purchase_request_order': purchase_request_order})
        initial_data = [
            {"product": item.product, "quantity": item.quantity}
            for item in purchase_request_order.purchase_request_order.all()
        ]
        formset = RFQItemFormSet(initial=initial_data)

    return render(
        request,
        "purchase/rfq/create_rfq.html",
        {
            "form": form,
            "formset": formset,
            "purchase_request_order": purchase_request_order
        }
    )


@login_required
def rfq_detail(request, pk):
    rfq = get_object_or_404(RFQ, pk=pk)
    return render(request, "purchase/rfq/rfq_detail.html", {"rfq": rfq})


@login_required
def rfq_list(request):
    rfqs = RFQ.objects.all().order_by('-date')
    return render(request, "purchase/rfq/rfq_list.html", {"rfqs": rfqs})



@login_required
def send_rfq(request, pk):
    rfq = get_object_or_404(RFQ, pk=pk)
    if rfq.status == "draft":
        rfq.status = "sent"
        rfq.save()
        messages.success(request, f"RFQ {rfq.rfq_number} marked as sent.")
    else:
        messages.warning(request, f"RFQ {rfq.rfq_number} is already {rfq.status}.")
    return redirect("purchase:rfq_detail", pk=pk)



import logging
from django.utils import timezone
import uuid

logger = logging.getLogger(__name__)

@login_required
def create_supplier_quotation(request, pk):
    rfq = get_object_or_404(RFQ, pk=pk)
    supplier = Supplier.objects.filter(user=request.user).first()
    if not supplier:
        messages.warning(request, "No supplier found for the logged-in user.")
        logger.warning(f"User {request.user} tried to access create_supplier_quotation but has no supplier linked.")
    logger.debug(f"Accessed create_supplier_quotation view | RFQ ID: {rfq.id}, Supplier: {supplier}")

    existing_quotation = rfq.rfq_quotation.filter(supplier=supplier).first()
    if existing_quotation:
        messages.info(request, "You have already submitted a quotation for this RFQ.")
        logger.info(f"Supplier {supplier} already has quotation {existing_quotation.id} for RFQ {rfq.id}")
        return redirect("customerportal:supplier_quotation_detail", pk=existing_quotation.id)

    initial_data = [{"product": item.product, "quantity": item.quantity} for item in rfq.items.all()]
    logger.debug(f"Initial formset data: {initial_data}")

    if request.method == "POST":
        logger.debug("Received POST request for SupplierQuotationForm and Formset.")
        form = SupplierQuotationForm(request.POST)
        formset = SupplierQuotationItemFormSet(request.POST)

        if form.is_valid() and formset.is_valid():
            logger.debug("Both form and formset are valid. Saving quotation...")
            quotation = form.save(commit=False)
            quotation.rfq = rfq

            if not quotation.quotation_number:
                quotation.quotation_number = f"SQ-{timezone.now().strftime('%Y%m%d%H%M%S')}-{uuid.uuid4().hex[:6]}"

            quotation.save()
            logger.info(f"Created new SupplierQuotation: {quotation.quotation_number} (ID: {quotation.id})")

            formset.instance = quotation
            formset.save()
            quotation.calculate_totals()  # Recalculate totals now that items exist
            quotation.save(update_fields=['subtotal', 'vat_amount', 'ait_amount', 'total_amount', 'net_due_amount'])
            logger.debug("Formset saved successfully.")

            messages.success(request, f"Quotation {quotation.quotation_number} created.")
            return redirect("customerportal:supplier_quotation_detail", pk=quotation.pk)
        else:
            logger.info("Form submission failed validation.")
            logger.info(f"Form errors: {form.errors.as_json()}")
            logger.info(f"Formset errors: {formset.errors}")
            messages.error(request, f"Please correct the errors below and resubmit.{formset.errors}--{form.errors.as_json()}")
    else:
        logger.debug("Rendering empty quotation form and formset.")
        form = SupplierQuotationForm(initial={'supplier': supplier})
        formset = SupplierQuotationItemFormSet(initial=initial_data)

    return render(
        request,
         "purchase/quotations/create_supplier_quotation.html",
        {
            "form": form,
            "formset": formset,
            "rfq": rfq,
        },
    )


def supplier_quotation_detail(request, pk):
    quotation = get_object_or_404(SupplierQuotation, pk=pk)
    return render(request, 'purchase/quotations/supplier_quotation_detail.html', {
        'quotation': quotation
    })



@login_required
def supplier_quotation_list(request):
    quotations = SupplierQuotation.objects.filter(status__in=['sent','approved']).order_by('-date')
    return render(request, "purchase/quotations/supplier_quotation_list.html", {"quotations": quotations})



from.utils import compare_supplier_quotations

@login_required
def supplier_quotation_comparison(request, rfq_id):
    comparison_data = compare_supplier_quotations(rfq_id)
    rfq = RFQ.objects.get(pk=rfq_id)
    
    return render(request, "purchase/quotations/supplier_quotation_comparison.html", {
        "comparison_data": comparison_data,
        "rfq": rfq,
    })




@login_required
def send_supplier_quotation(request, pk):
    quotation = get_object_or_404(SupplierQuotation, pk=pk)
    if quotation.status == "draft":
        quotation.status = "sent"
        quotation.save()
        messages.success(request, f"Quotation {quotation.quotation_number} has been sent to supplier.")
    else:
        messages.warning(request, f"Quotation {quotation.quotation_number} is not in draft status.")
    return redirect("purchase:supplier_quotation_detail", pk=pk)

from django.db import models

@login_required
def approve_supplier_quotation(request, pk):
    quotation = get_object_or_404(SupplierQuotation, pk=pk)
    if quotation.status in ["sent", "draft"]:
        quotation.status = "approved"
        # ✅ update total_amount if needed
        total = quotation.purchase_quotation_items.aggregate(
            total=models.Sum('total_price')
        )['total'] or 0
        quotation.total_amount = total
        quotation.save()
        messages.success(request, f"Quotation {quotation.quotation_number} has been approved.")
    else:
        messages.warning(request, f"Quotation {quotation.quotation_number} cannot be approved (current: {quotation.status}).")
    return redirect("purchase:supplier_quotation_detail", pk=pk)


@login_required
def reject_supplier_quotation(request, pk):
    quotation = get_object_or_404(SupplierQuotation, pk=pk)
    if quotation.status in ["sent", "draft"]:
        quotation.status = "rejected"
        quotation.save()
        messages.success(request, f"Quotation {quotation.quotation_number} has been rejected.")
    else:
        messages.warning(request, f"Quotation {quotation.quotation_number} cannot be rejected (current: {quotation.status}).")
    return redirect("purchase:supplier_quotation_detail", pk=pk)




@login_required
def convert_quotation_to_po2(request, quotation_id):
    quotation = get_object_or_404(SupplierQuotation.objects.prefetch_related('purchase_quotation_items'), pk=quotation_id)

    if request.method == "GET":
        return render(request, "purchase/confirm_quotation_to_po_conversion.html", {
            "quotation": quotation,
        })

    if request.method == "POST":
        try:
            po = create_purchase_order_from_quotation(quotation_id, request.user)
            messages.success(request, f"Purchase Order {po.order_id} created successfully.")
            return redirect("purchase:add_batch_details", po_id=po.id)
        except ValueError as e:
            messages.error(request, str(e))
            return redirect(request.META.get("HTTP_REFERER", "purchase:supplier_quotation_list"))


@login_required
def convert_quotation_to_po(request, quotation_id):
    quotation = get_object_or_404(
        SupplierQuotation.objects.prefetch_related('purchase_quotation_items'),
        pk=quotation_id)
    if request.method == "GET":
        return render(request, "purchase/confirm_quotation_to_po_conversion.html", {
            "quotation": quotation,})

    if request.method == "POST":
        try:
            po = create_purchase_order_from_quotation(quotation_id, request.user)
            messages.success(request, f"Purchase Order {po.order_id} created successfully.")
            return redirect("purchase:select_or_create_batch", po_id=po.id)
        except ValueError as e:
            messages.error(request, str(e))
            return redirect(request.META.get("HTTP_REFERER", "purchase:supplier_quotation_list"))


@login_required
def select_or_create_batch(request, po_id):
    po_items = PurchaseOrderItem.objects.filter(purchase_order_id=po_id).select_related('product')
    if not po_items.exists():
        messages.info(request, "No items found for this purchase order.")
        return redirect("purchase:purchase_order_list")

    if request.method == "POST":
        missing_batches = []
        for item in po_items:
            batch_id = request.POST.get(f'batch_{item.id}')
            if batch_id:
                batch = Batch.objects.filter(id=batch_id).first()
                if batch:
                    item.batch = batch
                    item.save()
            else:
                missing_batches.append(item.product.name)

        if missing_batches:
            messages.warning(request, f"No batch selected for: {', '.join(missing_batches)}. Please create batch first.")
            return redirect("purchase:add_batch_details", po_id=po_id)

        messages.success(request, "Batches linked successfully to purchase order.")
        return redirect("purchase:purchase_order_list")

    batches = Batch.objects.all().select_related('product').order_by('-updated_at')
    return render(request, "purchase/select_or_create_batch.html", {
        "po_items": po_items,
        "batches": batches,
    })



@login_required
def add_batch_details(request, po_id):
    po_items = PurchaseOrderItem.objects.filter(purchase_order_id=po_id)

    if not po_items.exists():
        messages.info(request, "No items found for this purchase order.")
        return redirect("purchase:purchase_order_list")

    # Formset for all PO items
    BatchFormSet = modelformset_factory(Batch, form=BatchFormShort, extra=len(po_items))

    # Prepare initial data for the formset
    initial_data = []
    for po_item in po_items:
        quotation_item = po_item.purchase_order.supplier_quotation.purchase_quotation_items.filter(
            product=po_item.product
        ).first()
        purchase_price = quotation_item.unit_price if quotation_item else 0
        initial_data.append({
            "product": po_item.product,
            "quantity": po_item.quantity,
            "purchase_price": purchase_price,
        })

    if request.method == "POST":
        formset = BatchFormSet(request.POST)
        if formset.is_valid():
            for form in formset:
                # Extract form data
                product = form.cleaned_data.get("product")
                quantity = form.cleaned_data.get("quantity") or 0
                manufacture_date = form.cleaned_data.get("manufacture_date")
                expiry_date = form.cleaned_data.get("expiry_date")
                purchase_price = form.cleaned_data.get("purchase_price")
                regular_price = form.cleaned_data.get("regular_price")
                discounted_price = form.cleaned_data.get("discounted_price")
                vat_percentage = form.cleaned_data.get("vat_percentage")

                # Check if a similar batch exists (same product, same supplier, same dates)
                existing_batch = Batch.objects.filter(
                    product=product,
                    supplier__in=po_items.values_list('supplier', flat=True),
                    manufacture_date=manufacture_date,
                    expiry_date=expiry_date,
                    purchase_price = purchase_price
                ).first()

                if existing_batch:                    
                    existing_batch.quantity += quantity                   
                    existing_batch.save()
                    batch = existing_batch
                else:
                    # Create new batch
                    batch = form.save(commit=False)                   
                    po_item = po_items.filter(product=product).first()
                    if po_item:                     
                        batch.supplier = po_item.supplier or po_item.purchase_order.supplier
                    else:
                        batch.supplier = None  
                    batch.user = request.user                                     
                    batch.save()

                # Link PO items to the batch
                po_item = po_items.filter(product=product).first()
                if po_item:
                    po_item.batch = existing_batch if existing_batch else batch
                    po_item.save()

            messages.success(request, "Batch details saved/updated successfully.")
            return redirect("purchase:purchase_order_list")
        else:
            messages.error(request, "There was an error in the batch form. Check input data.")
    else:
        formset = BatchFormSet(queryset=Batch.objects.none(), initial=initial_data)

    return render(request, "purchase/add_batch_details.html", {
        "formset": formset,
        "po": po_items.first().purchase_order,
    })




@login_required
def batch_details(request, batch_id):
    batch = get_object_or_404(Batch, id=batch_id)
    
    context = {
        'batch': batch
    }
    return render(request, 'purchase/batch_details.html', context)



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
            if (good_quantity or 0) + (bad_quantity or 0) !=purchase_dispatch_item.dispatch_quantity:
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
