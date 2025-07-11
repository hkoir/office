
from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db.models import Sum, F
from io import BytesIO
from reportlab.lib.pagesizes import letter
from reportlab.lib import colors
from reportlab.pdfgen import canvas
from reportlab.lib.styles import getSampleStyleSheet
from django.http import HttpResponse
from django.utils import timezone
from num2words import num2words

from customer.models import Customer
from core.models import Employee,Company
from supplier.models import Supplier
from logistics.models import PurchaseShipment,SaleShipment,SaleDispatchItem,PurchaseDispatchItem
from sales.models import SaleOrder
from purchase.models import PurchaseOrder
from .models import PurchaseInvoice,SaleInvoice, PurchasePayment,SalePayment
from .forms import PurchaseInvoiceForm, PurchasePaymentForm,SaleInvoiceForm,SalePaymentForm

from core.forms import CommonFilterForm
from django.core.paginator import Paginator

from .models import PurchaseInvoice, PurchaseInvoiceAttachment
from .forms import PurchaseInvoiceAttachmentForm,PurchasePaymentAttachmentForm,SaleInvoiceAttachmentForm,SalePaymentAttachmentForm


@login_required
def create_purchase_invoice(request, order_id):
    purchase_shipment = get_object_or_404(PurchaseShipment, id=order_id) 

    if purchase_shipment.shipment_invoices.count() > 0:
        if purchase_shipment.shipment_invoices.filter(status__in=['SUBMITTED', 'PARTIALLY_PAYMENT', 'FULLY_PAYMENT']).count() == purchase_shipment.shipment_invoices.count():
            messages.error(request, "All invoices for this shipment have already been submitted or paid.")
            return redirect('purchase:purchase_order_list')
    else:
         pass     

    try:       
        if purchase_shipment.status != 'DELIVERED':
            messages.error(request, "Cannot create an invoice: Shipment status is not 'Delivered yet'.")
            return redirect('purchase:purchase_order_list') 
    except PurchaseShipment.DoesNotExist:
        messages.error(request, "Cannot create an invoice: No shipment found for this order.")
        return redirect('purchase:purchase_order_list') 

    initial_data = {
        'purchase_shipment': purchase_shipment,
        'amount_due': purchase_shipment.purchase_order.total_amount
    }

    if request.method == 'POST':
        form = PurchaseInvoiceForm(request.POST)
        if form.is_valid():
            invoice = form.save(commit=False)
            invoice.user = request.user
            invoice.status ='SUBMITTED'
            invoice.save()
            messages.success(request, "Invoice created and submitted successfully.")
            return redirect('purchase:purchase_order_list')  
        else:
            messages.error(request, "Error creating invoice.")
    else:
        form = PurchaseInvoiceForm(initial=initial_data)
    return render(request, 'finance/purchase/create_invoice.html', {'form': form})


@login_required
def add_purchase_invoice_attachment(request, invoice_id):
    invoice = get_object_or_404(PurchaseInvoice, id=invoice_id)    
    if request.method == 'POST':
        form = PurchaseInvoiceAttachmentForm(request.POST, request.FILES)
        if form.is_valid():
            attachment = form.save(commit=False)
            attachment.purchase_invoice = invoice  
            attachment.user=request.user
            attachment.save()
            return redirect('purchase:purchase_order_list')
    else:
        form = PurchaseInvoiceAttachmentForm()

    return render(request, 'finance/attachmenet/add_invoice_attachment.html', {'form': form, 'invoice': invoice})



@login_required
def create_purchase_payment(request, invoice_id):
    invoice = get_object_or_404(PurchaseInvoice, id=invoice_id)

    if invoice.status not in ["SUBMITTED", "PARTIALLY_PAID"]:
        messages.error(request, "Cannot create a payment: Invoice is not submitted or partially paid.")
        return redirect('purchase:purchase_order_list')

    remaining_balance = invoice.remaining_balance

    if request.method == 'POST':
        form = PurchasePaymentForm(request.POST)
        if form.is_valid():
            payment = form.save(commit=False)
            payment.purchase_invoice = invoice
            payment.user = request.user

            if payment.amount > remaining_balance:
                messages.error(request, f"Payment cannot exceed the remaining balance of {remaining_balance}.")
                return redirect('finance:create_purchase_payment', invoice_id=invoice.id)
            
            if payment.amount < remaining_balance:
                payment.status = "PARTIALLY_PAID"
            else:
                payment.status = "FULLY_PAID"

            payment.save()
            if invoice.is_fully_paid:
                invoice.status = "FULLY_PAID"
            elif invoice.remaining_balance > 0:
                invoice.status = "PARTIALLY_PAID"
            invoice.save()

            messages.success(request, "Payment created successfully.")
            return redirect('finance:purchase_invoice_list')
    else:       
        form = PurchasePaymentForm(initial={
            'purchase_invoice': invoice,  
            'amount': remaining_balance
        })

    return render(request, 'finance/purchase/create_payment.html', {
        'form': form,
        'purchase_invoice': invoice.invoice_number,
        'remaining_balance': remaining_balance
    })


@login_required
def add_purchase_payment_attachment(request, invoice_id):
    invoice = get_object_or_404(PurchaseInvoice, id=invoice_id)    
    if request.method == 'POST':
        form = PurchasePaymentAttachmentForm(request.POST, request.FILES)
        if form.is_valid():
            attachment = form.save(commit=False)
            attachment.purchase_invoice = invoice  
            attachment.user=request.user
            attachment.save()
            messages.success(request,'attachement success')
            return redirect('purchase:purchase_order_list')
    else:
        form = PurchasePaymentAttachmentForm()
    return render(request, 'finance/attachmenet/add_invoice_attachment.html', {'form': form, 'invoice': invoice})


from django.db.models import Sum, F, Q


@login_required
def generate_purchase_invoice(purchase_order):
    valid_shipments = PurchaseShipment.objects.filter(
        purchase_order=purchase_order, status='DELIVERED'
    )

    valid_dispatch_items = PurchaseDispatchItem.objects.filter(
        purchase_shipment__in=valid_shipments, status='DELIVERED'
    )

    unpaid_invoices = PurchaseInvoice.objects.filter(
        purchase_shipment__in=valid_shipments
    ).exclude(status__in=['FULLY_PAID', 'CANCELLED']) 

    if not unpaid_invoices.exists():
        return {"error": "No pending invoices for this purchase order"}

    invoice_summary = unpaid_invoices.aggregate(
        total_vat=Sum('vat_amount'),
        total_ait=Sum('ait_amount'),
        total_net=Sum('net_due_amount'),
        total_paid=Sum('purchase_payment_invoice__amount'),
        total_due=Sum(F('net_due_amount') - F('purchase_payment_invoice__amount'))
    )

    product_data = valid_dispatch_items.values(
        'dispatch_item__product__name', 'dispatch_item__product__unit_price', 'dispatch_item__batch__unit_price'
    ).annotate(
        total_quantity=Sum('dispatch_quantity'),
        total_amount=Sum(
            F('dispatch_quantity') * F('dispatch_item__batch__unit_price')  
        )
    )

    product_summary = [
        {
            "product_name": item['dispatch_item__product__name'],
            "unit_price": item['dispatch_item__batch__unit_price'], 
            "quantity": item['total_quantity'],
            "amount": item['total_amount']
        }
        for item in product_data
    ]

    grand_total = sum(item['amount'] for item in product_summary)

    return {
        "purchase_order": purchase_order,
        "valid_shipments": valid_shipments,
        "valid_dispatch_items": valid_dispatch_items,
        "product_summary": product_summary,
        "grand_total": grand_total,
        "vat_amount": invoice_summary['total_vat'] or 0,
        "ait_amount": invoice_summary['total_ait'] or 0,
        "net_payable": invoice_summary['total_net'] or 0,
        "paid_amount": invoice_summary['total_paid'] or 0,
        "due_amount": invoice_summary['total_due'] or 0, 
        "invoice_status": list(unpaid_invoices.values_list('status', flat=True).distinct())  
    }



@login_required
def generate_purchase_invoice_pdf(purchase_order, mode="download"):
    supplier = purchase_order.supplier
    supplier_address = 'Unknown'
    supplier_info = Supplier.objects.filter(id=purchase_order.supplier_id).first()
    if supplier_info:
        supplier_name = supplier_info.name
        supplier_phone = supplier_info.phone
        supplier_email = supplier_info.email
        supplier_website = supplier_info.website
        if supplier_info.supplier_locations.first():
            supplier_address = supplier_info.supplier_locations.first().address
        supplier_logo_path = supplier_info.logo.path if supplier_info.logo else 'D:/SCM/dscm/media/company_logo/Logo.png'

    company_name = None
    company_address = None
    company_email = None
    company_phone = None
    company_website = None
    logo_path = None

    cfo_data = Employee.objects.filter(position__name='CFO').first()
    if cfo_data:
        location = cfo_data.location.name
        company_name = cfo_data.location.company.name
        company_address = cfo_data.location.address
        company_email = cfo_data.location.email
        company_phone = cfo_data.location.phone
        company_website = cfo_data.location.company.website
        company_logo_path = cfo_data.location.company.logo.path if cfo_data.location.company.logo else 'D:/SCM/dscm/media/company_logo/Logo.png'

    invoice_data = generate_purchase_invoice(purchase_order)

    buffer = BytesIO()
    c = canvas.Canvas(buffer, pagesize=letter)

    styles = getSampleStyleSheet()
    title_style = styles['Title']
    normal_style = styles['Normal']

    if supplier_logo_path:
        logo_width, logo_height = 60, 60
        c.drawImage(supplier_logo_path, 50, 710, width=logo_width, height=logo_height)

    c.setFont("Helvetica-Bold", 14)
    c.drawString(130, 750, f'{supplier_name}')
    c.setFont("Helvetica", 10)
    c.drawString(130, 735, f' Address:{supplier_address}')
    c.drawString(130, 720, f' Phone: {supplier_phone} | Email: {supplier_email}')
    c.drawString(130, 705, f"Website: {supplier_website}")

    # Customer Info
    c.setFont("Helvetica-Bold", 12)
    c.drawString(50, 670, "Customer Information:")
    c.setFont("Helvetica", 10)
    c.drawString(50, 655, f"Customer: {company_name}")
    c.drawString(50, 640, f"Phone: {company_phone}")
    c.drawString(50, 625, f"Website: {company_website}")

    PO_updated_at_date = purchase_order.updated_at.strftime("%Y-%m-%d")
    c.setFont("Helvetica-Bold", 12)
    c.drawString(50, 600, f"PO: {purchase_order.order_id} | Date: {PO_updated_at_date}")
    shipment_id = purchase_order.purchase_shipment.first().shipment_id if purchase_order.purchase_shipment.exists() else "N/A"
    c.drawString(50, 585, f"Shipment ID: {shipment_id}")
    c.drawString(50, 570, f"Invoice Date: {timezone.now().date()}")

    c.line(30, 550, 580, 550)
    y_position = 530
    c.setFont("Helvetica-Bold", 12)
    c.drawString(30, y_position, "Product Name")
    c.drawString(200, y_position, "Unit Price")
    c.drawString(350, y_position, "Quantity")
    c.drawString(450, y_position, "Amount")
    y_position -= 10
    c.line(30, y_position, 580, y_position)

    y_position -= 20
    c.setFont("Helvetica", 10)
    for item in invoice_data['product_summary']:
        if y_position < 100:
            c.showPage()
            y_position = 750  

        c.drawString(30, y_position, item["product_name"])
        c.drawString(200, y_position, f"${item['unit_price']:.2f}")
        c.drawString(350, y_position, str(item['quantity']))
        c.drawString(450, y_position, f"${item['amount']:.2f}")
        y_position -= 20

    # Adding VAT, AIT, and Net Due to the PDF
    y_position -= 30
    c.setFont("Helvetica-Bold", 12)

    c.drawString(350, y_position,"Grand Total:")
    c.drawString(450, y_position, f"${invoice_data['grand_total']:.2f}")

    y_position -= 20
    c.setFont("Helvetica-Bold", 12)

    c.drawString(350, y_position, "AIT:")
    c.drawString(450, y_position, f"${invoice_data['ait_amount']:.2f}")

    y_position -= 20
    c.setFont("Helvetica-Bold", 12)
    
    c.drawString(350, y_position, "VAT:")
    c.drawString(450, y_position, f"${invoice_data['vat_amount']:.2f}")
    
    y_position -= 20
    c.setFont("Helvetica-Bold", 12)
    c.drawString(350, y_position, "Net Due:")
    c.drawString(450, y_position, f"${invoice_data['net_payable']:.2f}")

    y_position -= 20
    c.setFont("Helvetica", 10)
    Net_total = num2words(invoice_data['net_payable'], to='currency', lang='en').replace("euro", "Taka").replace("cents", "paisa").capitalize()
    c.drawString(50, y_position, f"Amount in Words: {Net_total}")

    y_position -= 60
    c.setFont("Helvetica", 12)
    c.drawString(50, y_position, "Authorized Signature: ___________________")
    y_position -= 20
    c.drawString(50, y_position, f"Name: {cfo_data.name if cfo_data else '...............'}")
    y_position -= 20
    c.drawString(50, y_position, f"Designation: {cfo_data.position.name if cfo_data else '...............'}")

    y_position -= 40
    c.setFont("Helvetica", 9)
    c.setFillColor('gray')
    c.drawString(50, y_position, "Note: Signature not mandatory due to computerized authorization.")
    c.drawString(50, y_position - 15, "For inquiries, contact: support@mymeplus.com | Phone: 01743800705")
    c.showPage()
    c.save()
    pdf = buffer.getvalue()
    buffer.close()

    response = HttpResponse(pdf, content_type='application/pdf')
    if mode == 'preview':
        response['Content-Disposition'] = f'inline; filename="invoice_{purchase_order.id}.pdf"'
    else:  # Default to download
        response['Content-Disposition'] = f'attachment; filename="invoice_{purchase_order.id}.pdf"'
    return response



@login_required
def download_purchase_invoice(request, purchase_order_id):
    purchase_order = get_object_or_404(PurchaseOrder, id=purchase_order_id)   
    mode = request.GET.get('mode', 'download')     
    return generate_purchase_invoice_pdf(purchase_order,mode=mode)




@login_required
def purchase_invoice_list(request):
    invoice_number = None
    invoice_list = PurchaseInvoice.objects.all().order_by('-created_at')
    invoices = invoice_list.annotate(total_paid=Sum('purchase_payment_invoice__amount'))
    form = CommonFilterForm(request.GET or None)
    if form.is_valid():
        invoice_number = form.cleaned_data['purchase_invoice_id']
        if invoice_number:
            invoices = invoices.filter(invoice_number = invoice_number)

    paginator = Paginator(invoices, 10)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    form=CommonFilterForm()

    return render(request, 'finance/purchase/invoice_list.html',
     {
      'invoices': invoices,
      'page_obj':page_obj,
      'form':form,
      'invoice_number':invoice_number

    })


@login_required
def purchase_invoice_detail(request, invoice_id):
    invoice = get_object_or_404(PurchaseInvoice, id=invoice_id)
    payments = invoice.purchase_payment_invoice.all() 
    return render(request, 'finance/purchase/invoice_details.html', {
        'invoice': invoice,
        'payments': payments,
    })



# ########################### sale invoices #################################################################

@login_required
def create_sale_invoice(request, order_id):
    sale_shipment = get_object_or_404(SaleShipment, id=order_id)   
    
    if sale_shipment.is_fully_invoiced:
        messages.error(request, "All invoices for this shipment have already been submitted or paid.")
        return redirect('sales:sale_order_list')

    if not sale_shipment.status in ['DELIVERED','REACHED']:
        messages.error(request, "Cannot create an invoice: Shipment status is not 'Delivered' yet.")
        return redirect('sales:sale_order_list')
    
    initial_data = {
        'sale_shipment': sale_shipment,
        'amount_due': sale_shipment.sales_order.total_amount
    }

    if request.method == 'POST':
        form = SaleInvoiceForm(request.POST)
        if form.is_valid():
            invoice = form.save(commit=False)
            invoice.user = request.user
            invoice.status = 'SUBMITTED'
            invoice.save()
            messages.success(request, "Invoice created and submitted successfully.")
            return redirect('sales:sale_order_list')  
    else:
        form = SaleInvoiceForm(initial=initial_data)
    
    return render(request, 'finance/sales/create_invoice.html', {'form': form})



@login_required
def add_sale_invoice_attachment(request, invoice_id):
    invoice = get_object_or_404(SaleInvoice, id=invoice_id)    
    if request.method == 'POST':
        form = SaleInvoiceAttachmentForm(request.POST, request.FILES)
        if form.is_valid():
            attachment = form.save(commit=False)
            attachment.sale_invoice = invoice  
            attachment.user=request.user
            attachment.save()
            return redirect('purchase:purchase_order_list')
    else:
        form = SaleInvoiceAttachmentForm()
    return render(request, 'finance/attachmenet/add_invoice_attachment.html', {'form': form, 'invoice': invoice})



@login_required
def create_sale_payment(request, invoice_id):
    invoice = get_object_or_404(SaleInvoice, id=invoice_id)
    invoice_amount = invoice.net_due_amount

    if invoice.sale_payment_invoice.first():
        if invoice.sale_payment_invoice.first().is_fully_paid:
            messages.error(request, "All payment already paid")
            return redirect('sales:sale_order_list')

    remaining_balance = invoice.remaining_balance

    if request.method == 'POST':
        form = SalePaymentForm(request.POST)
        if form.is_valid():
            payment = form.save(commit=False)
            payment.sale_invoice = invoice       
            payment.user = request.user

            if payment.amount > remaining_balance:
                messages.error(request, f"Payment cannot exceed the remaining balance of {remaining_balance}.")
                return redirect('sales:create_sale_payment', invoice_id=invoice.id)
                     
            if payment.amount < remaining_balance:
                payment.status = "PARTIALLY_PAID"
            else:
                payment.status = "FULLY_PAID"
            
            payment.save()

            invoice.status = "FULLY_PAID" if invoice.is_fully_paid else "PARTIALLY_PAID"
            invoice.save()

            messages.success(request, "Payment created successfully.")
            return redirect('finance:sale_invoice_list')
    else:
         form = SalePaymentForm(initial={
            'sale_invoice': invoice,
            'amount': remaining_balance
        })

    return render(request, 'finance/sales/create_payment.html', {
        'form': form,
        'invoice': invoice,
        'invoice_amount':invoice_amount,
        'remaining_balance': remaining_balance
    })


@login_required
def add_sale_payment_attachment(request, invoice_id):
    invoice = get_object_or_404(SaleInvoice, id=invoice_id)    
    if request.method == 'POST':
        form = SalePaymentAttachmentForm(request.POST, request.FILES)
        if form.is_valid():
            attachment = form.save(commit=False)
            attachment.sale_invoice = invoice  
            attachment.user=request.user
            attachment.save()
            return redirect('sales:sale_order_list')
    else:
        form =SalePaymentAttachmentForm()
    return render(request, 'finance/attachmenet/add_invoice_attachment.html', {'form': form, 'invoice': invoice})





@login_required
def generate_sale_invoice(sale_order):
    valid_shipments = SaleShipment.objects.filter(sales_order=sale_order, status__in=['DELIVERED','REACHED'])
    valid_dispatch_items = SaleDispatchItem.objects.filter(sale_shipment__in=valid_shipments, status__in=['DELIVERED','REACHED'])


    unpaid_invoices = SaleInvoice.objects.filter(
        sale_shipment__in=valid_shipments
    ).exclude(status__in=['FULLY_PAID', 'CANCELLED']) 

    if not unpaid_invoices.exists():
        return {"error": "No pending invoices for this purchase order"}
    
    invoice_summary = unpaid_invoices.aggregate(
        total_vat=Sum('vat_amount'),
        total_ait=Sum('ait_amount'),
        total_net=Sum('net_due_amount'),
        total_paid=Sum('sale_payment_invoice__amount'),
        total_due=Sum(F('net_due_amount') - F('sale_payment_invoice__amount'))
    )

    product_data = valid_dispatch_items.values(
        'dispatch_item__product__name', 'dispatch_item__product__unit_price', 'dispatch_item__batch__sale_price'
    ).annotate(
        total_quantity=Sum('dispatch_quantity'),
        total_amount=Sum(
            F('dispatch_quantity') * F('dispatch_item__batch__sale_price')  
        )
    )

    product_summary = [
        {
            "product_name": item['dispatch_item__product__name'],
            "unit_price": item['dispatch_item__batch__sale_price'], 
            "quantity": item['total_quantity'],
            "amount": item['total_amount'] if item['total_amount'] is not None else 0 
        }
        for item in product_data
    ]

    grand_total = (
        sum(item['amount'] for item in product_summary)
      
    )


    return {
        "sale_order": sale_order,
        "valid_shipments": valid_shipments,
        "valid_dispatch_items": valid_dispatch_items,
        "product_summary": product_summary,
        "grand_total": grand_total,
        "vat_amount": invoice_summary['total_vat'] or 0,
        "ait_amount": invoice_summary['total_ait'] or 0,
        "net_payable": invoice_summary['total_net'] or 0,
        "paid_amount": invoice_summary['total_paid'] or 0,
        "due_amount": invoice_summary['total_due'] or 0, 
        "invoice_status": list(unpaid_invoices.values_list('status', flat=True).distinct())  
    }







@login_required
def generate_sale_invoice_pdf(sale_order, mode="download"):
    customer = sale_order.customer
    customer_address = 'Unknown'
    customer_info = Customer.objects.filter(id=sale_order.customer_id).first()
    if customer_info:
        customer_name = customer_info.name
        customer_phone = customer_info.phone
        customer_email = customer_info.email
        customer_website = customer_info.website
        if customer_info.customer_locations.first():
            customer_address = customer_info.customer_locations.first().address
        customer_logo_path = customer_info.logo.path if customer_info.logo else 'D:/SCM/dscm/media/company_logo/Logo.png'

    company_name = None
    company_address = None
    company_email = None
    company_phone = None
    company_website = None
    logo_path = None

    cfo_data = Employee.objects.filter(position__name='CFO').first()
    if cfo_data:
        location = cfo_data.location.name
        company_name = cfo_data.location.company.name
        company_address = cfo_data.location.address
        company_email = cfo_data.location.email
        company_phone = cfo_data.location.phone
        company_website = cfo_data.location.company.website
        company_logo_path = cfo_data.location.company.logo.path if cfo_data.location.company.logo else 'D:/SCM/dscm/media/company_logo/Logo.png'

    invoice_data = generate_sale_invoice(sale_order)

    buffer = BytesIO()
    c = canvas.Canvas(buffer, pagesize=letter)

    styles = getSampleStyleSheet()
    title_style = styles['Title']
    normal_style = styles['Normal']

    if customer_logo_path:
        logo_width, logo_height = 60, 60
        c.drawImage(customer_logo_path, 50, 710, width=logo_width, height=logo_height)

    c.setFont("Helvetica-Bold", 14)
    c.drawString(130, 750, f'{company_name}')
    c.setFont("Helvetica", 10)
    c.drawString(130, 735, f' Address:{company_address}')
    c.drawString(130, 720, f' Phone: {company_phone} | Email: {company_email}')
    c.drawString(130, 705, f"Website: {company_website}")

    # Customer Info
    c.setFont("Helvetica-Bold", 12)
    c.drawString(50, 670, "Customer Information:")
    c.setFont("Helvetica", 10)
    c.drawString(50, 655, f"Customer: {customer_name}")
    c.drawString(50, 640, f' Phone: {customer_phone} | Email: {customer_email}')
    c.drawString(50, 625, f"Website: {customer_website}")

    PO_updated_at_date = sale_order.updated_at.strftime("%Y-%m-%d")
    c.setFont("Helvetica-Bold", 12)
    c.drawString(50, 600, f"PO: {sale_order.order_id} | Date: {PO_updated_at_date}")
    shipment_id = sale_order.sale_shipment.first().shipment_id if sale_order.sale_shipment.exists() else "N/A"
    c.drawString(50, 585, f"Shipment ID: {shipment_id}")
    c.drawString(50, 570, f"Invoice Date: {timezone.now().date()}")

    c.line(30, 550, 580, 550)
    y_position = 530
    c.setFont("Helvetica-Bold", 12)
    c.drawString(30, y_position, "Product Name")
    c.drawString(200, y_position, "Unit Price")
    c.drawString(350, y_position, "Quantity")
    c.drawString(450, y_position, "Amount")
    y_position -= 10
    c.line(30, y_position, 580, y_position)

    y_position -= 20
    c.setFont("Helvetica", 10)
    for item in invoice_data['product_summary']:
        if y_position < 100:
            c.showPage()
            y_position = 750  

        c.drawString(30, y_position, item["product_name"])
        sale_price = item['unit_price'] if item['unit_price'] is not None else 0
        c.drawString(200, y_position, f"${sale_price:.2f}")
        c.drawString(350, y_position, str(item['quantity']))
        c.drawString(450, y_position, f"${item['amount']:.2f}")
        y_position -= 20

    # Adding VAT, AIT, and Net Due to the PDF
    y_position -= 30
    c.setFont("Helvetica-Bold", 12)

    c.drawString(350, y_position, "Grand Total:")
    grand_total = invoice_data['grand_total'] 
    c.drawString(450, y_position, f"${grand_total:.2f}")

    y_position -= 20
    c.setFont("Helvetica-Bold", 12)
    c.drawString(350, y_position, "AIT:")
    c.drawString(450, y_position, f"${invoice_data['ait_amount']:.2f}")
    y_position -= 20
    c.setFont("Helvetica-Bold", 12)

    c.drawString(350, y_position, "VAT:")
    c.drawString(450, y_position,f"${invoice_data['vat_amount']:.2f}")

    y_position -= 30
    c.setFont("Helvetica-Bold", 12)
    c.drawString(350, y_position, "Net Due:")   
    c.drawString(450, y_position, f"${invoice_data['net_payable']:.2f}" )
    y_position -= 20
    c.setFont("Helvetica", 10)
    Net_due = num2words(invoice_data['net_payable'], to='currency', lang='en').replace("euro", "Taka").replace("cents", "paisa").capitalize()
    c.drawString(50, y_position, f"Amount in Words: {Net_due}")

    y_position -= 60
    c.setFont("Helvetica", 12)
    c.drawString(50, y_position, "Authorized Signature: ___________________")
    y_position -= 20
    c.drawString(50, y_position, f"Name: {cfo_data.name if cfo_data else '...............'}")
    y_position -= 20
    c.drawString(50, y_position, f"Designation: {cfo_data.position.name if cfo_data else '...............'}")

    y_position -= 40
    c.setFont("Helvetica", 9)
    c.setFillColor('gray')
    c.drawString(50, y_position, "Note: Signature not mandatory due to computerized authorization.")
    c.drawString(50, y_position - 15, "For inquiries, contact: support@mymeplus.com | Phone: 01743800705")
    c.showPage()
    c.save()
    pdf = buffer.getvalue()
    buffer.close()

    response = HttpResponse(pdf, content_type='application/pdf')
    if mode == 'preview':
        response['Content-Disposition'] = f'inline; filename="invoice_{sale_order.id}.pdf"'
    else:  # Default to download
        response['Content-Disposition'] = f'attachment; filename="invoice_{sale_order.id}.pdf"'
    return response





@login_required
def download_sale_invoice(request, sale_order_id):
    sale_order = get_object_or_404(SaleOrder, id=sale_order_id)       
    mode = request.GET.get('mode', 'download') 
    return generate_sale_invoice_pdf(sale_order, mode=mode)




@login_required
def sale_invoice_list(request):  
    invoice_number = None
    invoice_list = SaleInvoice.objects.all().order_by('-created_at')
    invoices = invoice_list.annotate(total_paid=Sum('sale_payment_invoice__amount'))
    form = CommonFilterForm(request.GET or None)
    if form.is_valid():
        invoice_number = form.cleaned_data['sale_invoice_id']
        if invoice_number:
            invoices = invoices.filter(invoice_number = invoice_number)

    paginator = Paginator(invoices, 10)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    form=CommonFilterForm()

    return render(request, 'finance/sales/invoice_list.html',
     {
      'invoices': invoices,
      'page_obj':page_obj,
      'form':form,
      'invoice_number':invoice_number

    })

   
@login_required
def sale_invoice_detail(request, invoice_id):
    invoice = get_object_or_404(SaleInvoice, id=invoice_id)
    payments = invoice.sale_payment_invoice.all()  

    return render(request, 'finance/sales/invoice_details.html', {
        'invoice': invoice,
        'payments': payments,
    })



