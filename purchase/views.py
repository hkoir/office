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
def create_purchase_request(request):
    
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








###########################################################################################@login_required

def create_rfq(request, request_order_id):
    purchase_request_order = get_object_or_404(PurchaseRequestOrder, id=request_order_id)

    if request.method == "POST":
        form = RFQForm(request.POST)
        formset = RFQItemFormSet(request.POST)

        if form.is_valid() and formset.is_valid():
            with transaction.atomic():
                rfq = form.save(commit=False)
                rfq.purchase_request_order = purchase_request_order
                rfq.save()       
                for form_data in formset.cleaned_data:
                    if not form_data or form_data.get("DELETE"):
                        continue
                    product = form_data.get("product")
                    qty_requested = form_data.get("quantity")

                    try:
                        pr_item = purchase_request_order.purchase_request_order.get(product=product)
                    except:
                        messages.error(request, f"{product} was not part of the purchase request.")
                        return redirect("purchase:purchase_request_order_list")
     
                    if qty_requested > pr_item.quantity:
                        messages.warning(
                            request,
                            f"Cannot assign {qty_requested} units for {product}, "
                            f"requested only {pr_item.quantity}."
                        )
                        return redirect("purchase:purchase_request_order_list")
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
        {"form": form, "formset": formset, "purchase_request_order": purchase_request_order},
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



@login_required
def create_supplier_quotation(request, pk):
    rfq = get_object_or_404(RFQ, pk=pk)
    supplier = Supplier.objects.filter(user=request.user).first()

    initial_data = [
        {"product": item.product, "quantity": item.quantity}
        for item in rfq.items.all()
    ]

    if request.method == "POST":
        form = SupplierQuotationForm(request.POST)
        formset = SupplierQuotationItemFormSet(request.POST)

        if form.is_valid() and formset.is_valid():
            quotation = form.save(commit=False)
            quotation.rfq = rfq
            quotation.save()  # Save first to get pk for formset

            formset.instance = quotation
            formset.save()  # Save items

            # --- Calculate totals AFTER items are saved ---
            quotation.calculate_tax_amounts()
            quotation.save(update_fields=['total_amount', 'vat_amount', 'ait_amount', 'net_due_amount'])

            messages.success(request, f"Quotation {quotation.quotation_number} created.")
            return redirect("purchase:supplier_quotation_detail", pk=quotation.pk)
        else:
            print("Form errors:", form.errors)
            print("Formset errors:", formset.errors)
    else:
        form = SupplierQuotationForm(initial={'supplier': supplier})
        formset = SupplierQuotationItemFormSet(initial=initial_data)

    return render(
        request,
        "purchase/quotations/create_supplier_quotation.html",
        {"form": form, "formset": formset, "rfq": rfq},
    )


def supplier_quotation_detail(request, pk):
    quotation = get_object_or_404(SupplierQuotation, pk=pk)
    return render(request, 'purchase/quotations/supplier_quotation_detail.html', {
        'quotation': quotation
    })



@login_required
def supplier_quotation_list(request):
    quotations = SupplierQuotation.objects.all().order_by('-date')
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
def convert_quotation_to_po(request, quotation_id):
    quotation = get_object_or_404(SupplierQuotation, pk=quotation_id)
    try:
        po = create_purchase_order_from_quotation(quotation_id, request.user)
        messages.success(request, f"Purchase Order {po.order_id} created. Please enter batch details.")
        return redirect("purchase:add_batch_details", po_id=po.id)
    except ValueError as e:
        messages.error(request, str(e))
        return redirect(request.META.get("HTTP_REFERER", "purchase:supplier_quotation_list"))


@login_required
def add_batch_details2(request, po_id):
    print('start adding batch')

    po_items = PurchaseOrderItem.objects.filter(
        purchase_order_id=po_id, batch__isnull=True
    )
    if not po_items.exists():
        print('no po items exist')
        messages.info(request, "All items already have batches.")
        return redirect("purchase:purchase_order_list")

    # ✅ Define formset factory first
    BatchFormSet = modelformset_factory(Batch, form=BatchFormShort, extra=len(po_items))

    # Prepare initial data
    initial_data = []
    for po_item in po_items:
        quotation_item = po_item.purchase_order.supplier_quotation.purchase_quotation_items.filter(
            product=po_item.product
        ).first()
        purchase_price = quotation_item.unit_price if quotation_item else 0
        initial_data.append({
            "quantity": po_item.quantity,
            "product": po_item.product,
            "purchase_price": purchase_price
        })

    # ✅ Now safely initialize the formset
    if request.method == "POST":
        formset = BatchFormSet(request.POST)
        if formset.is_valid():
            print("Formset is valid. Start saving batches...")
            for form, po_item in zip(formset.forms, po_items):
                batch = form.save(commit=False)
                batch.product = po_item.product
                batch.supplier = po_item.supplier
                batch.save()
                po_item.batch = batch
                po_item.save()
                print(f"Saved batch {batch.id}, product {batch.product.name}")
            print("All batches saved, now redirecting...")
            messages.success(request, "Batch details saved successfully.")
            return redirect("purchase:purchase_order_list")
        else:
            print('form errors', formset.errors)
            messages.error(request, "There was an error submitting the batch details. Check server logs for details.")
    else:
        formset = BatchFormSet(queryset=Batch.objects.none(), initial=initial_data)

    return render(request, "purchase/add_batch_details.html", {
        "formset": formset,
        "po": po_items.first().purchase_order,
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

                # Check if a similar batch exists (same product, same supplier, same dates)
                existing_batch = Batch.objects.filter(
                    product=product,
                    supplier__in=po_items.values_list('supplier', flat=True),
                    manufacture_date=manufacture_date,
                    expiry_date=expiry_date,
                    purchase_price = purchase_price
                ).first()

                if existing_batch:
                    # Update quantity
                    existing_batch.quantity += quantity
                    existing_batch.purchase_price = purchase_price  # optional: update price
                    existing_batch.regular_price = regular_price
                    existing_batch.discounted_price = discounted_price
                    existing_batch.save()
                else:
                    # Create new batch
                    batch = form.save(commit=False)
                    # Assuming each po_item has the same supplier as the product in the form
                    batch.supplier = po_items.filter(product=product).first().supplier
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
def create_purchase_order2(request, request_id):
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
def create_purchase_order(request, request_id):
    request_instance = get_object_or_404(PurchaseRequestOrder, id=request_id)
    PurchaseOrderFormSet = formset_factory(PurchaseOrderForm, extra=0, can_delete=True)

    if request.method == 'POST':        
        formset = PurchaseOrderFormSet(
            request.POST,
            form_kwargs={'request_instance': request_instance}
        )
        if formset.is_valid():
            try:
                with transaction.atomic():
                    # Create one PurchaseOrder per request instance
                    purchase_order = PurchaseOrder.objects.create(
                        purchase_request_order=request_instance,
                        total_amount=0,
                        status='IN_PROCESS',
                        user=request.user,
                        order_date=timezone.now()
                    )

                    total_amount = 0
                    for form in formset:
                        if form.cleaned_data and not form.cleaned_data.get('DELETE'):
                            order_item = form.cleaned_data['order_item_id']
                            product = form.cleaned_data['product']
                            batch = form.cleaned_data['batch']
                            supplier = form.cleaned_data['supplier']
                            quantity = form.cleaned_data['quantity']

                            item_total = float(quantity) * float(batch.purchase_price if batch else product.unit_price)
                            total_amount += item_total

                            # Save PurchaseOrderItem
                            PurchaseOrderItem.objects.create(
                                order_item_id=order_item,
                                purchase_order=purchase_order,
                                product=product,
                                batch=batch,
                                supplier=supplier,
                                quantity=quantity,
                                total_price=item_total,
                                user=request.user,
                                status='IN_PROCESS'
                            )

                    # Update total amount in purchase order
                    purchase_order.total_amount = total_amount
                    purchase_order.supplier=supplier
                    purchase_order.save()

                messages.success(request, "Purchase order created successfully!")
                return redirect('purchase:purchase_order_list')

            except Exception as e:
                messages.error(request, f"Error creating purchase order: {e}")
        else:
            print("❌ Formset errors:", formset.errors)

    else:
        # Pre-fill formset with all request items
        initial_data = [
            {
                'order_item_id': item,
                'category': item.product.category,
                'product': item.product,
                'quantity': item.quantity
            }
            for item in request_instance.purchase_request_order.all()
        ]
        formset = PurchaseOrderFormSet(
            initial=initial_data,
            form_kwargs={'request_instance': request_instance}
        )

    return render(
        request,
        'purchase/create_purchase_order.html',
        {'formset': formset, 'request_instance': request_instance}
    )



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
