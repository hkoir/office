
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
from accounting.models import JournalEntry, JournalEntryLine, Account,FiscalYear
from purchase.models import SupplierQuotation,PurchaseOrder
from.utils import convert_quotation_to_invoice,create_purchase_invoice_from_po




@login_required
def create_purchase_invoice(request, order_id):
    purchase_shipment = get_object_or_404(PurchaseShipment, id=order_id)

    if purchase_shipment.shipment_invoices.count() > 0:
        if purchase_shipment.shipment_invoices.filter(
            status__in=['SUBMITTED', 'PARTIALLY_PAID', 'FULLY_PAID']
        ).count() == purchase_shipment.shipment_invoices.count():
            messages.error(request, "All invoices for this shipment have already been submitted or paid.")
            return redirect('purchase:purchase_order_list')

    if purchase_shipment.status != 'DELIVERED':
        messages.error(request, "Cannot create an invoice: Shipment status is not 'Delivered yet'.")
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
            invoice.status = 'SUBMITTED'
            invoice.save()

            # ---------------------------
            # Create Journal Entry for Purchase Invoice
            # ---------------------------
            fiscal_year = FiscalYear.get_active()
            journal_entry = JournalEntry.objects.create(
                date=timezone.now().date(),
                fiscal_year=fiscal_year,
                description=f"Purchase Invoice {invoice.invoice_number}",
                reference=f"purchase-invoice-{invoice.id}",
            )

            # Accounts
            ap_account = Account.objects.get(code="2110")    # Accounts Payable
            purchase_account = Account.objects.get(code="5140")  # Purchase Expense
            inventory_account = Account.objects.get(code="1150")  # Purchase Expense
            vat_account = Account.objects.get(code="1180")   # VAT Receivable (Input VAT, asset)
            ait_account = Account.objects.get(code="1190")   # AIT Receivable (asset)

            # Amounts
            amount_due = invoice.amount_due or 0
            vat_amount = invoice.vat_amount or 0
            ait_amount = invoice.ait_amount or 0
            total_invoice_amount = amount_due + vat_amount - ait_amount

            # --- Debit Purchase Expense ---
            JournalEntryLine.objects.create(
                entry=journal_entry,
                account=inventory_account,
                debit=amount_due,
                credit=0
            )

            # --- Debit VAT (if any) ---
            if vat_amount > 0:
                JournalEntryLine.objects.create(
                    entry=journal_entry,
                    account=vat_account,
                    debit=vat_amount,
                    credit=0
                )

            # --- Debit AIT Receivable (if any) ---
            if ait_amount > 0:
                JournalEntryLine.objects.create(
                    entry=journal_entry,
                    account=ait_account,
                    debit=ait_amount,
                    credit=0
                )

            # --- Credit Accounts Payable ---
            JournalEntryLine.objects.create(
                entry=journal_entry,
                account=ap_account,
                debit=0,
                credit=total_invoice_amount
            )

            messages.success(request, "Invoice created and submitted successfully with journal entry.")
            return redirect('purchase:purchase_order_list')
        else:
            messages.error(request, "Error creating invoice.")
    else:
        form = PurchaseInvoiceForm(initial=initial_data)
    return render(request, 'finance/purchase/create_invoice.html', {'form': form})




@login_required
def create_purchase_invoice_from_quotation(request, quotation_id):
    quotation = get_object_or_404(SupplierQuotation, id=quotation_id)
    shipment = quotation.supplier_quotations.first().purchase_shipment.first()
    purchase_orders = quotation.supplier_quotations.all()
    first_po = purchase_orders.first()
    if not first_po:
        messages.error(request, "No Purchase Order linked to this quotation.")
        return redirect("purchase:quotation_detail", pk=quotation.id)

    first_shipment = first_po.purchase_shipment.first()
    if not first_shipment:
        messages.error(request, "No Purchase Shipment linked to this Purchase Order.")
        return redirect("purchase:purchase_order_detail", pk=first_po.id)
    invoice = convert_quotation_to_invoice(quotation, user=request.user)   
    invoice.purchase_shipment = first_shipment
    invoice.save() 
    messages.success(request, f"Invoice {invoice.invoice_number} created from quotation {quotation.quotation_number}.")
    return redirect("finance:purchase_invoice_list")



@login_required
def create_purchase_invoice_from_purchase_order(request, po_id):
    po = get_object_or_404(PurchaseOrder, id=po_id)
    try:
        invoice = create_purchase_invoice_from_po(po_id, request.user)
        messages.success(request, f"Purchase Invoice {invoice.invoice_number} created successfully.")
        return redirect("purchase:purchase_order_list")
    except ValueError as e:
        messages.error(request, str(e))
        return redirect("purchase:purchase_order_list")
    except Exception as e:
        messages.error(request, f"Error creating invoice: {e}")
        return redirect("purchase:purchase_order_list")



from decimal import Decimal

@login_required
def create_purchase_payment(request, invoice_id):
    if not request.user.groups.filter(name="Approver").exists():
        messages.error(request, "You are not authorized to create invoices. Only approvers can perform this action.")
        return redirect('purchase:purchase_order_list')
    invoice = get_object_or_404(PurchaseInvoice, id=invoice_id)

    if invoice.status not in ["SUBMITTED", "PARTIALLY_PAID"]:
        messages.error(request, "Cannot create a payment: Invoice is not submitted or is already fully paid.")
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

            payment.status = "PARTIALLY_PAID" if payment.amount < remaining_balance else "FULLY_PAID"
            payment.save()

            # ---------------------------
            # Create Journal Entry for Payment
            # ---------------------------
            fiscal_year = FiscalYear.get_active()
            journal_entry = JournalEntry.objects.create(
                date=timezone.now().date(),
                fiscal_year=fiscal_year,
                description=f"Payment for Purchase Invoice {invoice.invoice_number}",
                reference=f"purchase-invoice-{invoice.id}",
            )

            ap_account = Account.objects.get(code="2110")    # Accounts Payable
            cash_account = Account.objects.get(code="1110")  # Cash/Bank
            ait_account = Account.objects.get(code="1190")   # AIT Receivable

            payment_amount = Decimal(payment.amount or 0)
            ait_amount = Decimal(invoice.ait_amount or 0)
            vat_amount = Decimal(invoice.vat_amount or 0)
            purchase_amount = Decimal(invoice.amount_due or 0)

            # Full liability includes VAT (AIT is separate)
            total_ap = purchase_amount + vat_amount

            # ---------------------------
            # Journal Lines
            # ---------------------------
            journal_lines = [
                # Dr Accounts Payable - clear full supplier liability
                JournalEntryLine(
                    entry=journal_entry,
                    account=ap_account,
                    debit=total_ap,
                    credit=0,
                    description="Clear accounts payable for supplier"
                ),
                # Cr Cash/Bank - actual cash paid
                JournalEntryLine(
                    entry=journal_entry,
                    account=cash_account,
                    debit=0,
                    credit=payment_amount,
                    description="Cash/Bank payment to supplier"
                )
            ]

            # Cr AIT Receivable (if applicable)
            if ait_amount > 0:
                journal_lines.append(JournalEntryLine(
                    entry=journal_entry,
                    account=ait_account,
                    debit=0,
                    credit=ait_amount,
                    description="AIT withheld and adjusted"
                ))

            JournalEntryLine.objects.bulk_create(journal_lines)

            # ---------------------------
            # Update Invoice Status
            # ---------------------------
            if invoice.is_fully_paid:
                invoice.status = "FULLY_PAID"
            elif invoice.remaining_balance > 0:
                invoice.status = "PARTIALLY_PAID"
            invoice.save()

            messages.success(request, "Payment created successfully with journal entry.")
            return redirect('finance:purchase_invoice_list')
    else:
        form = PurchasePaymentForm(initial={
            'purchase_invoice': invoice,
            'amount': remaining_balance
        })

    return render(request, 'finance/purchase/create_payment.html', {
        'form': form,
        'purchase_invoice': invoice.invoice_number,
        'remaining_balance': remaining_balance,
        'invoice':invoice
    })



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





from django.db.models import F, Sum, Value, DecimalField
from django.db.models.functions import Coalesce
from django.contrib.auth.decorators import login_required



@login_required
def generate_purchase_invoice(purchase_order):   
    # --- Get delivered shipments ---
    valid_shipments = PurchaseShipment.objects.filter(
        purchase_order=purchase_order, status='DELIVERED'
    )

    # --- Get delivered dispatch items ---
    valid_dispatch_items = PurchaseDispatchItem.objects.filter(
        purchase_shipment__in=valid_shipments, status='DELIVERED'
    )

    # --- Get unpaid invoices ---
    unpaid_invoices = PurchaseInvoice.objects.filter(
        purchase_shipment__in=valid_shipments
    ).exclude(status='CANCELLED')

    if not unpaid_invoices.exists():
        return {
            "error": "No pending invoices for this purchase order",
            "purchase_order": purchase_order,
            "valid_shipments": valid_shipments,
            "valid_dispatch_items": valid_dispatch_items,
            "product_summary": [],
            "grand_total": 0,
            "vat_amount": 0,
            "ait_amount": 0,
            "net_payable": 0,
            "paid_amount": 0,
            "due_amount": 0,
            "invoice_status": [],
        }

    # --- Aggregate invoice summary ---
    invoice_summary = unpaid_invoices.aggregate(
        total_vat=Sum('vat_amount'),
        total_ait=Sum('ait_amount'),
        total_net=Sum('net_due_amount'),
        total_paid=Sum('purchase_payment_invoice__amount'),
        total_due=Sum(F('net_due_amount') - F('purchase_payment_invoice__amount'))
    )

    # --- Prepare product summary with correct unit_price ---
    product_data = valid_dispatch_items.annotate(
        unit_price=Coalesce(
            F('dispatch_item__batch__purchase_price'),
            F('dispatch_item__product__unit_price'),
            Value(0),
            output_field=DecimalField()
        ),
        total_amount=F('dispatch_quantity') * Coalesce(
            F('dispatch_item__batch__purchase_price'),
            F('dispatch_item__product__unit_price'),
            Value(0),
            output_field=DecimalField()
        )
    ).values(
        'dispatch_item__product__name',
        'unit_price',
        'dispatch_quantity',
        'total_amount'
    )

    # --- Build product summary list ---
    product_summary = [
        {
            "product_name": item['dispatch_item__product__name'],
            "unit_price": item['unit_price'] or 0,
            "quantity": item['dispatch_quantity'] or 0,
            "amount": item['total_amount'] or 0,
        }
        for item in product_data
    ]

    # --- Calculate grand total ---
    grand_total = sum(item['amount'] or 0 for item in product_summary)

    # --- Return final invoice data ---
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






import os
from django.conf import settings
from core.models import Employee
from customer.models import Customer
from supplier.models import Supplier


@login_required
def generate_purchase_invoice_pdf(request, purchase_order, mode="download"):
    # Supplier info
    supplier = purchase_order.supplier
    supplier_name = supplier.name if supplier else 'Unknown Supplier'
    supplier_phone = supplier.phone if supplier else ''
    supplier_email = supplier.email if supplier else ''
    supplier_website = supplier.website if supplier else ''
    supplier_address = supplier.supplier_locations.first().address if supplier and supplier.supplier_locations.exists() else 'Unknown'
    supplier_logo_path = supplier.logo.path if supplier and supplier.logo else None

    # Company info (from CFO or request.user employee)
    cfo_data = Employee.objects.filter(position__name='CFO').first()
    employee = Employee.objects.filter(user=request.user).first()
    if cfo_data:
        company_name = cfo_data.location.company.name
        company_address = cfo_data.location.address
        company_email = cfo_data.location.email
        company_phone = cfo_data.location.phone
        company_website = cfo_data.location.company.website
        company_logo_path = cfo_data.location.company.logo.path if cfo_data.location.company.logo else None
    elif employee and employee.company:
        company_name = employee.company.name
        company_address = getattr(employee.company, 'address', '')
        company_email = getattr(employee.company, 'email', '')
        company_phone = getattr(employee.company, 'phone', '')
        company_website = getattr(employee.company, 'website', '')
        company_logo_path = os.path.join(settings.MEDIA_ROOT, str(employee.company.logo)) if employee.company.logo else None
    else:
        company_name = company_address = company_email = company_phone = company_website = company_logo_path = None

    # Generate purchase invoice data
    invoice_data = generate_purchase_invoice(purchase_order)
    if 'product_summary' not in invoice_data:
        invoice_data['product_summary'] = []
        invoice_data['grand_total'] = 0.0

    # Prepare PDF
    buffer = BytesIO()
    c = canvas.Canvas(buffer, pagesize=letter)
    page_width, page_height = letter
    logo_width, logo_height = 60, 60
    y_top = page_height - 50

    # Draw logos
    if company_logo_path and os.path.exists(company_logo_path):
        c.drawImage(company_logo_path, 50, y_top - logo_height, width=logo_width, height=logo_height, preserveAspectRatio=True)
    if supplier_logo_path and os.path.exists(supplier_logo_path):
        c.drawImage(supplier_logo_path, page_width - 110, y_top - logo_height, width=logo_width, height=logo_height, preserveAspectRatio=True)

    # Big PURCHASE INVOICE title
    c.setFont("Helvetica-Bold", 24)
    c.drawCentredString(page_width / 2, y_top, "PURCHASE INVOICE")

    # Company info (center top)
    c.setFont("Helvetica-Bold", 12)
    c.drawString(50, y_top - 80, f"Company: {company_name or ''}")
    c.setFont("Helvetica", 10)
    c.drawString(50, y_top - 95, f"Address: {company_address or ''}")
    c.drawString(50, y_top - 110, f"Phone: {company_phone or ''} | Email: {company_email or ''}")
    c.drawString(50, y_top - 125, f"Website: {company_website or ''}")

    # Supplier info (right top)
    c.setFont("Helvetica-Bold", 12)
    c.drawString(page_width / 2 + 20, y_top - 80, f"Supplier: {supplier_name}")
    c.setFont("Helvetica", 10)
    c.drawString(page_width / 2 + 20, y_top - 95, f"Address: {supplier_address}")
    c.drawString(page_width / 2 + 20, y_top - 110, f"Phone: {supplier_phone} | Email: {supplier_email}")
    c.drawString(page_width / 2 + 20, y_top - 125, f"Website: {supplier_website}")

    # PO info
    c.setFont("Helvetica-Bold", 12)
    y_position = y_top - 150
    c.drawString(50, y_position, f"PO: {purchase_order.order_id} | Date: {purchase_order.updated_at.strftime('%Y-%m-%d')}")
    shipment_id = purchase_order.purchase_shipment.first().shipment_id if purchase_order.purchase_shipment.exists() else "N/A"
    c.drawString(50, y_position - 15, f"Shipment ID: {shipment_id}")
    c.drawString(50, y_position - 30, f"Invoice Date: {timezone.now().date()}")

    # Table header
    y_position -= 60
    c.setFont("Helvetica-Bold", 12)
    c.drawString(30, y_position, "Product Name")
    c.drawString(200, y_position, "Unit Price")
    c.drawString(350, y_position, "Quantity")
    c.drawString(450, y_position, "Amount")
    y_position -= 10
    c.line(30, y_position, 580, y_position)
    y_position -= 20

    # Table rows
    c.setFont("Helvetica", 10)
    for item in invoice_data['product_summary']:
        if y_position < 100:
            c.showPage()
            y_position = page_height - 50
        c.drawString(30, y_position, item["product_name"])
        unit_price = item.get('unit_price') or 0
        c.drawString(200, y_position, f"${unit_price:.2f}")
        c.drawString(350, y_position, str(item.get('quantity', 0)))
        amount = item.get('amount') or 0
        c.drawString(450, y_position, f"${amount:.2f}")
        y_position -= 20

    # Totals
    y_position -= 20
    c.setFont("Helvetica-Bold", 12)
    c.drawString(350, y_position, "Grand Total:")
    c.drawString(450, y_position, f"${invoice_data.get('grand_total', 0.0):.2f}")
    y_position -= 20
    c.drawString(350, y_position, "AIT:")
    c.drawString(450, y_position, f"${invoice_data.get('ait_amount', 0.0):.2f}")
    y_position -= 20
    c.drawString(350, y_position, "VAT:")
    c.drawString(450, y_position, f"${invoice_data.get('vat_amount', 0.0):.2f}")
    y_position -= 20
    c.drawString(350, y_position, "Net Due:")
    c.drawString(450, y_position, f"${invoice_data.get('net_payable', 0.0):.2f}")

    # Amount in words
    y_position -= 20
    c.setFont("Helvetica", 10)
    net_words = num2words(invoice_data.get('net_payable', 0.0), to='currency', lang='en').replace("euro", "Taka").replace("cents", "paisa").capitalize()
    c.drawString(50, y_position, f"Amount in Words: {net_words}")

    # Authorized signature
    y_position -= 60
    c.setFont("Helvetica-Bold", 12)
    c.drawString(50, y_position, "Authorized Signature: ___________________")
    y_position -= 20
    c.drawString(50, y_position, f"Name: {supplier.name if supplier else '...............'}")
    y_position -= 20
    supplier_user = supplier.user
    c.drawString(50, y_position, f"Designation: {supplier_user.user_position if supplier_user else '...............'}")
    
    # Footer note
    y_position -= 40
    c.setFont("Helvetica", 9)
    c.setFillColor('gray')
    c.drawString(50, y_position, "Note: Signature not mandatory due to computerized authorization.")
    c.drawString(50, y_position - 15, "For inquiries, contact: support@mymeplus.com | Phone: 01743800705")

    # Finalize
    c.showPage()
    c.save()
    pdf = buffer.getvalue()
    buffer.close()

    response = HttpResponse(pdf, content_type='application/pdf')
    if mode == 'preview':
        response['Content-Disposition'] = f'inline; filename="purchase_invoice_{purchase_order.id}.pdf"'
    else:
        response['Content-Disposition'] = f'attachment; filename="purchase_invoice_{purchase_order.id}.pdf"'
    return response


@login_required
def download_purchase_invoice(request, purchase_order_id):
    purchase_order = get_object_or_404(PurchaseOrder, id=purchase_order_id)   
    mode = request.GET.get('mode', 'download')     
    return generate_purchase_invoice_pdf(request,purchase_order,mode=mode)




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





from sales.models import SaleOrder
from finance.utils import create_sale_invoice_from_so 
@login_required
def create_sale_invoice_from_sale_order(request, so_id):
    so = get_object_or_404(SaleOrder, id=so_id)

    shipment = so.sale_shipment.first() 

       # ✅ Prevent duplicate invoice for same SO
    existing_invoice = SaleInvoice.objects.filter(sale_shipment=shipment).first()
    if existing_invoice:
        messages.warning(request,'Invoice exist')
        return redirect('sales:sale_order_list')

    # Calculate financial summary
    so_items = so.sale_order.all()     
   
    total_vat_amount = so.vat_amount
    total_ait_amount = so.ait_amount
    total_amount = so.total_amount
    net_due_amount =so.net_due_amount
    AIT_rate = so.AIT_rate
    AIT_type = so.AIT_type

    if request.method == "POST":
        # User confirmed creation
        try:
            invoice = create_sale_invoice_from_so(so_id, request.user, shipment=shipment)
            messages.success(request, f"Purchase Invoice {invoice.invoice_number} created successfully.")
            return redirect("sales:sale_order_list")
        except ValueError as e:
            messages.error(request, str(e))
        except Exception as e:
            messages.error(request, f"Error creating invoice: {e}")
        return redirect("sales:sale_order_list")

    # Render preview before confirming
    context = {
        "so": so,
        "so_items": so_items,
        "total_amount": total_amount,
        'net_due_amount':net_due_amount,
        "vat_amount": total_vat_amount,
        "ait_amount": total_ait_amount,
        "AIT_rate":AIT_rate,
        "AIT_type":AIT_type,
        
    }
    return render(request, "finance/sales/confirm_financial_summary.html", context)





@login_required
def create_sale_invoice(request, order_id):
    sale_shipment = get_object_or_404(SaleShipment, id=order_id)

    # Prevent duplicate invoicing
    if sale_shipment.is_fully_invoiced:
        messages.error(request, "All invoices for this shipment have already been submitted or paid.")
        return redirect('sales:sale_order_list')

    # Only allow invoicing for delivered shipments
    if sale_shipment.status not in ['DELIVERED', 'REACHED']:
        messages.error(request, "Cannot create an invoice: Shipment status is not 'Delivered' yet.")
        return redirect('sales:sale_order_list')

    # Prepare initial form data
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

            # ---------------------------
            # Create Journal Entry for Sales Invoice
            # ---------------------------
            fiscal_year = FiscalYear.get_active()
            journal_entry = JournalEntry.objects.create(
                date=timezone.now().date(),
                fiscal_year=fiscal_year,
                description=f"Sales Invoice {invoice.invoice_number}",
                reference=f"Sale invoice-{invoice.id}",
                created_by=request.user,
            )

            # Accounts
            ar_account = Account.objects.get(code="1140")         # Accounts Receivable
            sales_account = Account.objects.get(code="4100")      # Sales Revenue
            vat_account = Account.objects.get(code="2131")        # Output VAT Payable
            inventory_account = Account.objects.get(code="1150")  # Inventory
            cogs_account = Account.objects.get(code="5100")       # COGS

            # Amounts
            invoice_amount = invoice.amount_due
            vat_amount = invoice.vat_amount or 0

            # 1️⃣ Debit Accounts Receivable (total amount including VAT)
            JournalEntryLine.objects.create(
                entry=journal_entry,
                account=ar_account,
                debit=invoice_amount + vat_amount,
                credit=0
            )

            # 2️⃣ Credit Sales Revenue (excluding VAT)
            JournalEntryLine.objects.create(
                entry=journal_entry,
                account=sales_account,
                debit=0,
                credit=invoice_amount
            )

            # 3️⃣ Credit VAT Payable
            if vat_amount > 0:
                JournalEntryLine.objects.create(
                    entry=journal_entry,
                    account=vat_account,
                    debit=0,
                    credit=vat_amount
                )

            # ---------------------------
            # 4️⃣ Record COGS and reduce Inventory
            # ---------------------------
            for item in sale_shipment.sales_order.sale_order.all():
                cogs_amount = item.batch.discounted_price * item.quantity  # COGS = unit cost * quantity

                # Debit COGS
                JournalEntryLine.objects.create(
                    entry=journal_entry,
                    account=cogs_account,
                    debit=cogs_amount,
                    credit=0
                )

                # Credit Inventory
                JournalEntryLine.objects.create(
                    entry=journal_entry,
                    account=inventory_account,
                    debit=0,
                    credit=cogs_amount
                )

            messages.success(request, "Invoice created and journal entry recorded successfully.")
            return redirect('sales:sale_order_list')
    else:
        form = SaleInvoiceForm(initial=initial_data)

    return render(request, 'finance/sales/create_invoice.html', {'form': form})



@login_required
def create_sale_payment(request, invoice_id):
    invoice = get_object_or_404(SaleInvoice, id=invoice_id)
    remaining_balance = invoice.remaining_balance

    if remaining_balance <= 0:
        messages.error(request, "All payments for this invoice have already been made.")
        return redirect('sales:sale_order_list')

    if request.method == 'POST':
        form = SalePaymentForm(request.POST)
        if form.is_valid():
            payment = form.save(commit=False)
            payment.sale_invoice = invoice
            payment.user = request.user

            # Validate payment amount
            if payment.amount > remaining_balance:
                messages.error(
                    request,
                    f"Payment cannot exceed the remaining balance of {remaining_balance}."
                )
                return redirect('sales:create_sale_payment', invoice_id=invoice.id)

            # Determine payment status
            payment.status = "FULLY_PAID" if payment.amount == remaining_balance else "PARTIALLY_PAID"
            payment.save()

            # ---------------------------
            # Journal Entry for Sale Payment
            # ---------------------------
            fiscal_year = FiscalYear.get_active()
            journal_entry = JournalEntry.objects.create(
                date=timezone.now().date(),
                fiscal_year=fiscal_year,
                description=f"Payment received for Invoice {invoice.invoice_number}",
                reference=f"Sale invoice-{invoice.id}",
                created_by=request.user,
            )

            # Accounts
            ar_account = Account.objects.get(code="1140")    # Accounts Receivable
            cash_account = Account.objects.get(code="1110")  # Cash/Bank
            ait_account = Account.objects.get(code="2132")   # AIT Payable (withholding tax)

            # Amounts
            payment_amount = payment.amount
            ait_amount = invoice.ait_amount or 0
            net_cash = payment_amount - ait_amount

            # 1. Debit Cash/Bank
            JournalEntryLine.objects.create(
                entry=journal_entry,
                account=cash_account,
                debit=net_cash,
                credit=0
            )

            # 2. Debit AIT Payable if any
            if ait_amount > 0:
                JournalEntryLine.objects.create(
                    entry=journal_entry,
                    account=ait_account,
                    debit=ait_amount,
                    credit=0
                )

            # 3. Credit Accounts Receivable
            JournalEntryLine.objects.create(
                entry=journal_entry,
                account=ar_account,
                debit=0,
                credit=payment_amount
            )

            # Update Invoice Status
            invoice.status = "FULLY_PAID" if invoice.remaining_balance == 0 else "PARTIALLY_PAID"
            invoice.save()

            messages.success(request, "Payment recorded successfully with journal entry.")
            return redirect('finance:sale_invoice_list')
    else:
        # Pre-fill form with remaining balance
        form = SalePaymentForm(initial={'amount': remaining_balance})

    return render(request, 'finance/sales/create_payment.html', {
        'form': form,
        'invoice': invoice,
        'remaining_balance': remaining_balance
    })





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
    # --- Valid shipments ---
    valid_shipments = SaleShipment.objects.filter(
        sales_order=sale_order,
        status__in=['DELIVERED', 'REACHED']
    )

    valid_dispatch_items = SaleDispatchItem.objects.filter(
        sale_shipment__in=valid_shipments,
        status__in=['DELIVERED', 'REACHED']
    )

    # --- Include ALL invoices except cancelled ones ---
    all_invoices = SaleInvoice.objects.filter(
        sale_shipment__in=valid_shipments
    ).exclude(status='CANCELLED')

    if not all_invoices.exists():
        return {
            "error": "No invoices found for this sale order.",
            "product_summary": [],
            "grand_total": 0,
            "vat_amount": 0,
            "ait_amount": 0,
            "net_payable": 0,
            "paid_amount": 0,
            "due_amount": 0,
            "invoice_status": [],
        }

    # --- Aggregate all invoices ---
    invoice_summary = all_invoices.aggregate(
        total_vat=Sum('vat_amount'),
        total_ait=Sum('ait_amount'),
        total_net=Sum('net_due_amount'),
        total_paid=Sum('sale_payment_invoice__amount'),
    )

    total_vat = invoice_summary['total_vat'] or 0
    total_ait = invoice_summary['total_ait'] or 0
    total_net = invoice_summary['total_net'] or 0
    total_paid = invoice_summary['total_paid'] or 0
    total_due = total_net - total_paid

    # --- Product summary ---
    product_data = valid_dispatch_items.values(
        'dispatch_item__product__name',
        'dispatch_item__batch__sale_price'
    ).annotate(
        total_quantity=Sum('dispatch_quantity'),
        total_amount=Sum(F('dispatch_quantity') * F('dispatch_item__batch__sale_price'))
    )

    product_summary = [
        {
            "product_name": item['dispatch_item__product__name'],
            "unit_price": item['dispatch_item__batch__sale_price'] or 0,
            "quantity": item['total_quantity'],
            "amount": item['total_amount'] or 0
        }
        for item in product_data
    ]

    grand_total = sum(item['amount'] for item in product_summary)

    # --- Return structured invoice data ---
    return {
        "sale_order": sale_order,
        "valid_shipments": valid_shipments,
        "valid_dispatch_items": valid_dispatch_items,
        "product_summary": product_summary,
        "grand_total": grand_total,
        "vat_amount": total_vat,
        "ait_amount": total_ait,
        "net_payable": total_net,
        "paid_amount": total_paid,
        "due_amount": total_due,
        "invoice_status": list(all_invoices.values_list('status', flat=True).distinct())
    }






@login_required
def generate_sale_invoice_pdf2(request,sale_order, mode="download"):
    customer = sale_order.customer
    customer_address = 'Unknown'
    customer_logo_path=None
    customer_name = None
    customer_phone=None
    customer_email=None
    customer_address=None
    customer_website=None

    customer_info = Customer.objects.filter(id=sale_order.customer.id).first()    
    if customer_info:
        customer_name = customer_info.name
        customer_phone = customer_info.phone
        customer_email = customer_info.email
        customer_website = customer_info.website
        if customer_info.customer_locations.first():
            customer_address = customer_info.customer_locations.first().address
        customer_logo_path = customer_info.logo.path

    company_name = None
    company_address = None
    company_email = None
    company_phone = None
    company_website = None
    company_logo_path = None

    cfo_data = Employee.objects.filter(position__name='CFO').first()
    if cfo_data:
        location = cfo_data.location.name
        company_name = cfo_data.location.company.name
        company_address = cfo_data.location.address
        company_email = cfo_data.location.email
        company_phone = cfo_data.location.phone
        company_website = cfo_data.location.company.website
        company_logo_path = cfo_data.location.company.logo.path
    else:
        employee = Employee.objects.filter(user = request.user).first()
        if employee and employee.company and employee.company.logo:
            company_logo_path = os.path.join(settings.MEDIA_ROOT, str(employee.company.logo))
        else:
           print("no log found")

    invoice_data = generate_sale_invoice(sale_order)

    buffer = BytesIO()
    c = canvas.Canvas(buffer, pagesize=letter)

    styles = getSampleStyleSheet()
    title_style = styles['Title']
    normal_style = styles['Normal']

    logo_width, logo_height = 60, 60
    page_width, page_height = letter
    y_position = page_height - 100 

    if company_logo_path and os.path.exists(company_logo_path):
        c.drawImage(company_logo_path, 50, y_position, width=logo_width, height=logo_height, preserveAspectRatio=True)
    else:
        print("Company logo not found:", company_logo_path)
    if customer_logo_path and os.path.exists(customer_logo_path):
        c.drawImage(customer_logo_path, page_width - 110, y_position, width=logo_width, height=logo_height, preserveAspectRatio=True)
    else:
        print("Customer logo not found:", customer_logo_path)

    center_x = page_width / 2
    text_y = y_position + 30

    c.setFont("Helvetica-Bold", 16)
    c.drawCentredString(center_x, text_y + 30, f"{company_name or ''}")

    c.setFont("Helvetica", 10)
    if company_address:
        c.drawCentredString(center_x, text_y + 15, f"Address: {company_address}")
    if company_phone or company_email:
        c.drawCentredString(center_x, text_y, f"Phone: {company_phone or ''} | Email: {company_email or ''}")
    if company_website:
        c.drawCentredString(center_x, text_y - 15, f"Website: {company_website}")
    
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


from django.conf import settings
from django.http import HttpResponse
from django.utils import timezone
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas
from io import BytesIO
from num2words import num2words
from core.models import Employee
from customer.models import Customer
import os
from django.contrib.auth.decorators import login_required


@login_required
def generate_sale_invoice_pdf(request, sale_order, mode="download"):
    """Generate a professional invoice PDF with logos aligned and big INVOICE title."""

    # ==== Customer Info ====
    customer_info = Customer.objects.filter(id=sale_order.customer.id).first()
    customer_name = customer_info.name if customer_info else "Unknown"
    customer_phone = customer_info.phone if customer_info else ""
    customer_email = customer_info.email if customer_info else ""
    customer_website = customer_info.website if customer_info else ""
    customer_address = (
        customer_info.customer_locations.first().address
        if customer_info and customer_info.customer_locations.exists()
        else ""
    )
    customer_logo_path = customer_info.logo.path if customer_info and customer_info.logo else None

    # ==== Company Info ====
    cfo_data = Employee.objects.filter(position__name='CFO').first()
    if cfo_data:
        company = cfo_data.location.company
        company_name = company.name
        company_address = cfo_data.location.address
        company_email = cfo_data.location.email
        company_phone = cfo_data.location.phone
        company_website = company.website
        company_logo_path = company.logo.path if company.logo else None
    else:
        employee = Employee.objects.filter(user=request.user).first()
        company_name = employee.company.name if employee and employee.company else "My Company"
        company_logo_path = (
            os.path.join(settings.MEDIA_ROOT, str(employee.company.logo))
            if employee and employee.company and employee.company.logo
            else None
        )
        company_address = getattr(employee.company, "address", "")
        company_phone = getattr(employee.company, "phone", "")
        company_email = getattr(employee.company, "email", "")
        company_website = getattr(employee.company, "website", "")

    invoice_data = generate_sale_invoice(sale_order)

    buffer = BytesIO()
    c = canvas.Canvas(buffer, pagesize=letter)
    page_width, page_height = letter

    logo_width, logo_height = 70, 70
    top_y = page_height - 90

    # ==== Header Section ====
    if company_logo_path and os.path.exists(company_logo_path):
        c.drawImage(company_logo_path, 50, top_y, width=logo_width, height=logo_height, preserveAspectRatio=True)
    else:
        c.setFont("Helvetica-Bold", 12)
        c.drawString(50, top_y + 25, company_name)

    if customer_logo_path and os.path.exists(customer_logo_path):
        c.drawImage(customer_logo_path, page_width - 120, top_y, width=logo_width, height=logo_height, preserveAspectRatio=True)
    else:
        c.setFont("Helvetica-Bold", 12)
        c.drawRightString(page_width - 50, top_y + 25, customer_name)

    # ==== Title ====
    c.setFont("Helvetica-Bold", 22)
    c.drawCentredString(page_width / 2, page_height - 50, "INVOICE")

    # ==== Company Info (Left) ====
    c.setFont("Helvetica", 10)
    company_y = top_y - 20
    c.drawString(50, company_y, company_name)
    c.drawString(50, company_y - 15, f"Address: {company_address}")
    c.drawString(50, company_y - 30, f"Phone: {company_phone}")
    c.drawString(50, company_y - 45, f"Email: {company_email}")
    c.drawString(50, company_y - 60, f"Website: {company_website}")

    # ==== Customer Info (Right) ====
    customer_y = top_y - 20
    right_x = page_width - 250
    c.drawRightString(page_width - 50, customer_y, f"Customer: {customer_name}")
    c.drawRightString(page_width - 50, customer_y - 15, f"Phone: {customer_phone}")
    c.drawRightString(page_width - 50, customer_y - 30, f"Email: {customer_email}")
    c.drawRightString(page_width - 50, customer_y - 45, f"Website: {customer_website}")
    c.drawRightString(page_width - 50, customer_y - 60, f"Address: {customer_address}")

    # ==== Invoice Meta ====
    c.setFont("Helvetica-Bold", 12)
    c.drawString(50, 550, f"PO No: {sale_order.order_id}")
    c.drawString(200, 550, f"PO Date: {sale_order.updated_at.strftime('%Y-%m-%d')}")
    shipment_id = (
        sale_order.sale_shipment.first().shipment_id if sale_order.sale_shipment.exists() else "N/A"
    )
    c.drawString(350, 550, f"Shipment ID: {shipment_id}")

    # ==== Table Header ====
    y_position = 520
    c.line(40, y_position, 570, y_position)
    y_position -= 15
    c.setFont("Helvetica-Bold", 11)
    c.drawString(45, y_position, "Product Name")
    c.drawString(230, y_position, "Unit Price")
    c.drawString(340, y_position, "Quantity")
    c.drawString(440, y_position, "Amount")
    y_position -= 10
    c.line(40, y_position, 570, y_position)

    # ==== Table Content ====
    c.setFont("Helvetica", 10)
    y_position -= 20
    for item in invoice_data['product_summary']:
        if y_position < 100:
            c.showPage()
            y_position = 750
        c.drawString(45, y_position, item["product_name"])
        c.drawRightString(310, y_position, f"{item['unit_price']:.2f}")
        c.drawRightString(400, y_position, str(item['quantity']))
        c.drawRightString(550, y_position, f"{item['amount']:.2f}")
        y_position -= 20

    # ==== Totals ====
    y_position -= 10
    c.line(300, y_position, 570, y_position)
    y_position -= 20
    c.setFont("Helvetica-Bold", 11)
    c.drawRightString(450, y_position, "Grand Total:")
    c.drawRightString(550, y_position, f"{invoice_data['grand_total']:.2f}")

    y_position -= 20
    c.drawRightString(450, y_position, "VAT:")
    c.drawRightString(550, y_position, f"{invoice_data['vat_amount']:.2f}")

    y_position -= 20
    c.drawRightString(450, y_position, "AIT:")
    c.drawRightString(550, y_position, f"{invoice_data['ait_amount']:.2f}")

    y_position -= 20
    c.drawRightString(450, y_position, "Net Payable:")
    c.drawRightString(550, y_position, f"{invoice_data['net_payable']:.2f}")

    y_position -= 30
    net_due_words = num2words(invoice_data['net_payable'], to='currency', lang='en').replace("euro", "Taka")
    c.setFont("Helvetica", 10)
    c.drawString(45, y_position, f"Amount in words: {net_due_words.capitalize()}")

    # ==== Signature Section ====
    y_position -= 80
    c.setFont("Helvetica", 11)
    c.drawString(50, y_position, "Authorized Signature: __________________________")
    y_position -= 20
    c.setFont("Helvetica", 9)
    c.setFillColor("gray")
    c.drawString(50, y_position, "Note: Computer generated invoice, signature not required.")

    # ==== Footer ====
    y_position -= 20
    c.drawCentredString(page_width / 2, y_position, "For inquiries, contact: support@mymeplus.com | 01743800705")

    c.showPage()
    c.save()
    pdf = buffer.getvalue()
    buffer.close()

    response = HttpResponse(pdf, content_type='application/pdf')
    if mode == "preview":
        response['Content-Disposition'] = f'inline; filename="invoice_{sale_order.id}.pdf"'
    else:
        response['Content-Disposition'] = f'attachment; filename="invoice_{sale_order.id}.pdf"'
    return response



@login_required
def download_sale_invoice(request, sale_order_id):
    sale_order = get_object_or_404(SaleOrder, id=sale_order_id)       
    mode = request.GET.get('mode', 'download') 
    return generate_sale_invoice_pdf(request,sale_order, mode=mode)




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









###################################### Direct sales ###############################################

from .models import DirectInvoiceItem, DirectInvoice
from .forms import DirectInvoiceForm, DirectInvoiceItemFormSet
from django.db import transaction
from inventory.models import Inventory,InventoryTransaction
import qrcode
from io import BytesIO
import base64
import logging
logger = logging.getLogger(__name__)


def create_direct_invoice(request, pk=None):
    invoice = None
    if pk:
        invoice = get_object_or_404(DirectInvoice, pk=pk)
        invoice.status = "UPDATED"

    if request.method == "POST":
        invoice_form = DirectInvoiceForm(request.POST, instance=invoice)
        formset = DirectInvoiceItemFormSet(request.POST, instance=invoice)

        if invoice_form.is_valid() and formset.is_valid():
            with transaction.atomic():
                invoice = invoice_form.save(commit=False)
                invoice.user = request.user
                invoice.save()
                total = 0             
                for form in formset:                 
                    if form.cleaned_data.get('DELETE') or not form.cleaned_data.get('product'):
                        continue
                    item = form.save(commit=False)
                    item.invoice = invoice
                    item.save()
                    total += item.total_price

                invoice.total_amount = total
                invoice.final_amount = total - invoice.discount_amount - invoice.advance_amount
                invoice.save()

                messages.success(
                    request,
                    f"Invoice {invoice.invoice_number} {'updated' if pk else 'created'} successfully!"
                )
                return redirect("finance:direct_invoice_list")
        else:
            messages.error(request, "There were errors in your submission.")
            print("Form errors:", invoice_form.errors)
            print("Formset errors:", formset.errors)

    else:
        invoice_form = DirectInvoiceForm(instance=invoice, initial={"created_at": timezone.now().date()})
        formset = DirectInvoiceItemFormSet(instance=invoice)

    return render(request, "finance/direct_sales/create_direct_sale_invoice.html", {
        "form": invoice_form,
        "formset": formset,
        "submit_label": "Update Invoice" if pk else "Create Invoice"
    })




@login_required
def confirm_or_update_direct_invoice(request, invoice_id):
    invoice = get_object_or_404(DirectInvoice, id=invoice_id)
    is_update = invoice.status == 'CONFIRMED'
    action = 'updated' if is_update else 'confirmed'

    if request.method == "POST":
        with transaction.atomic():
            for item in invoice.items.all():
                if not item.product or item.quantity is None:
                    continue
                inventory, _ = Inventory.objects.get_or_create(
                    warehouse=item.warehouse,
                    location=item.location,
                    product=item.product,
                    batch=item.batch,
                    defaults={'quantity': 0}
                )
                prev_confirmed = item.confirmed_quantity or 0
                delta_qty = item.quantity - prev_confirmed
                if delta_qty == 0:
                    continue  
                InventoryTransaction.objects.filter(
                    direct_sale_invoice=invoice,
                    product=item.product,
                    warehouse=item.warehouse,
                    location=item.location,
                    batch=item.batch
                ).delete()

                inventory.quantity -= delta_qty
                inventory.save()
                if item.batch:
                    item.batch.remaining_quantity -= delta_qty
                    if item.batch.remaining_quantity < 0:
                        item.batch.remaining_quantity = 0 
                    item.batch.save(update_fields=["remaining_quantity"])

                if item.usage_purpose == "factory":
                    transaction_type = "MANUFACTURE_OUT"
                elif item.usage_purpose == "sale":
                    transaction_type = "DIRECT_SALE_OUT"

                InventoryTransaction.objects.create(
                    user=request.user,
                    warehouse=item.warehouse,
                    location=item.location,
                    product=item.product,
                    product_type=item.product_type,
                    batch=item.batch,
                    quantity=item.quantity, 
                    transaction_type=transaction_type,
                    direct_sale_invoice=invoice,
                    inventory_transaction=inventory,
                    transaction_date=timezone.now(),
                    remarks=(
                        f"Invoice #{invoice.invoice_number} {action} | "
                        f"prev confirmed: {prev_confirmed}, new: {item.quantity}"
                    )
                )
                item.confirmed_quantity = item.quantity
                item.save(update_fields=['confirmed_quantity'])
            invoice.status = 'CONFIRMED'
            invoice.save()
            messages.success(request, f"Direct Invoice {invoice.invoice_number} {action} successfully!")
        return redirect("finance:direct_invoice_list")
    return render(
        request,
        "finance/direct_sales/confirm_direct_sale_invoice.html",
        {"invoice": invoice}
    )


def direct_invoice_list(request):   
    invoices = DirectInvoice.objects.select_related('user').order_by('-id')
    datas = invoices
    paginator = Paginator(datas, 5)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    return render(request, 'finance/direct_sales/direct_invoice_list.html', {'invoices': invoices,'page_obj':page_obj})




def generate_qr(invoice):
    data = f"Invoice:{invoice.invoice_number}|Customer:{invoice.customer_name}|Total:{invoice.final_amount}"
    qr = qrcode.QRCode(box_size=4)
    qr.add_data(data)
    qr.make(fit=True)
    img = qr.make_image(fill_color="black", back_color="white")
    buffer = BytesIO()
    img.save(buffer, format="PNG")
    qr_base64 = base64.b64encode(buffer.getvalue()).decode()
    return f"data:image/png;base64,{qr_base64}"




def direct_invoice_detail(request, pk):
    invoice = get_object_or_404(DirectInvoice, pk=pk)
    items = invoice.items.all()  
    customer = getattr(invoice, "customer_name", None) 
    employee = Employee.objects.filter(user=invoice.user).first()
    company = Company.objects.first()
    company_logo_url = company.logo.url    
    authorized_signature = employee.signature.url
    
    amount = invoice.final_amount
    taka = int(amount)
    poisha = int(round((amount - taka) * 100))

    if poisha:
        total_in_words = f"{num2words(taka, lang='en').title()} Taka and {num2words(poisha, lang='en').title()} Poisha Only"
    else:
        total_in_words = f"{num2words(taka, lang='en').title()} Taka Only"

    context = {
        "invoice": invoice,
        "items": items,
        "qr_code_url": generate_qr(invoice),
        "signature_url":authorized_signature,
        "company_logo_url": company_logo_url ,  
        "customer": customer,
        "company":company,
        "total_in_words": total_in_words,
    }
    return render(request, "finance/direct_sales/direct_invoice_detail.html", context)


@transaction.atomic
def mark_invoice_paid(request, pk):
    invoice = get_object_or_404(DirectInvoice, pk=pk)

    if invoice.status != 'PAID':
        invoice.status = 'PAID'
        invoice.save()
        messages.success(request, f"Invoice {invoice.invoice_number} marked as Paid.")
    else:
        messages.info(request, f"Invoice {invoice.invoice_number} is already Paid.")

    return redirect('finance:direct_invoice_list')


###################################### Direct Purchase ###############################################

from .models import DirectPurchaseInvoiceItem, DirectPurchaseInvoice
from .forms import DirectPurchaseInvoiceForm, DirectPurchaseInvoiceItemFormSet 



def create_direct_purchase_invoice(request, pk=None):
    invoice = None
    if pk:
        invoice = get_object_or_404(DirectPurchaseInvoice, pk=pk)
        invoice.status = "UPDATED"

    if request.method == "POST":
        invoice_form = DirectPurchaseInvoiceForm(request.POST, instance=invoice)
        formset = DirectPurchaseInvoiceItemFormSet(request.POST, instance=invoice)

        if invoice_form.is_valid() and formset.is_valid():
            with transaction.atomic():
                invoice = invoice_form.save(commit=False)
                invoice.user = request.user
                invoice.save()

                items = formset.save(commit=False)
                for item in items:
                    if not item.quantity or not item.unit_price:
                        continue
                    item.invoice = invoice
                    item.save()
                for obj in formset.deleted_objects:
                    obj.delete()
                total = sum(i.total_price for i in invoice.direct_purchase_items.all())
                invoice.total_amount = total
                invoice.final_amount = total - invoice.discount_amount - invoice.advance_amount
                invoice.save()

                msg = "updated" if pk else "created"
                messages.success(request, f"Invoice {invoice.invoice_number} {msg} successfully!")
                return redirect("finance:direct_purchase_invoice_list")

        else:
            messages.error(request, "Please correct the errors in the form.")
            print("Invoice Form Errors:", invoice_form.errors)
            print("Formset Errors:", formset.errors)

    else:
        invoice_form = DirectPurchaseInvoiceForm(
            instance=invoice,
            initial={"created_at": timezone.now().date()}
        )
        formset = DirectPurchaseInvoiceItemFormSet(instance=invoice)

    return render(request, "finance/direct_purchase/create_direct_sale_invoice.html", {
        "form": invoice_form,
        "formset": formset,
        "submit_label": "Update" if pk else "Create"
    })




@login_required
def confirm_or_update_direct_purchase_invoice(request, invoice_id):
    invoice = get_object_or_404(DirectPurchaseInvoice, id=invoice_id)
    is_update = invoice.status == 'CONFIRMED'
    action = "updated" if is_update else "confirmed"

    if request.method == "POST":
        with transaction.atomic():
            for item in invoice.direct_purchase_items.all():
                if not item.product or item.quantity is None:
                    continue
                inventory, _ = Inventory.objects.get_or_create(
                    warehouse=item.warehouse,
                    location=item.location,
                    product=item.product,
                    batch=item.batch,
                    defaults={'quantity': 0}
                )
                prev_confirmed = item.confirmed_quantity or 0
                delta_qty = item.quantity - prev_confirmed
                if delta_qty == 0:
                    continue
                if item.batch: 
                    if prev_confirmed > 0:
                        item.batch.remaining_quantity -= prev_confirmed
                        item.batch.quantity -= prev_confirmed  # reverse previous purchase qty
                    item.batch.quantity += item.quantity
                    if item.batch.remaining_quantity < 0:
                        item.batch.remaining_quantity = 0
                    item.batch.save()

                InventoryTransaction.objects.filter(
                    direct_purchase_invoice=invoice,
                    product=item.product,
                    warehouse=item.warehouse,
                    location=item.location,
                    batch=item.batch,
                ).delete()
                inventory.quantity += delta_qty
                inventory.save(update_fields=["quantity"])
                InventoryTransaction.objects.create(
                    user=request.user,
                    warehouse=item.warehouse,
                    location=item.location,
                    product=item.product,
                    product_type=item.product_type,
                    batch=item.batch,
                    quantity=item.quantity,
                    transaction_type="DIRECT_PURCHASE_IN",
                    direct_purchase_invoice=invoice,
                    inventory_transaction=inventory,
                    transaction_date=timezone.now(),
                    remarks=(
                        f"Invoice #{invoice.invoice_number} {action} | "
                        f"prev confirmed: {prev_confirmed}, new: {item.quantity}, delta: {delta_qty}"
                    )
                )
         
                item.confirmed_quantity = item.quantity
                item.save(update_fields=['confirmed_quantity'])  
            invoice.status = "CONFIRMED"
            invoice.save(update_fields=["status"])

            messages.success(request, f"Direct Purchase Invoice {invoice.invoice_number} {action} successfully!")

        return redirect("finance:direct_purchase_invoice_list")

    return render(
        request,
        "finance/direct_purchase/confirm_direct_sale_invoice.html",
        {"invoice": invoice}
    )



def direct_purchase_invoice_list(request):
    invoices = DirectPurchaseInvoice.objects.select_related('user').order_by('-created_at')
    datas = invoices
    paginator = Paginator(datas, 5)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    return render(request, 'finance/direct_purchase/direct_invoice_list.html', {'invoices': invoices,'page_obj':page_obj})





def generate_direct_purchase_qr(invoice):
    data = f"Invoice:{invoice.invoice_number}|Customer:{invoice.supplier_name}|Total:{invoice.final_amount}"
    qr = qrcode.QRCode(box_size=4)
    qr.add_data(data)
    qr.make(fit=True)
    img = qr.make_image(fill_color="black", back_color="white")
    buffer = BytesIO()
    img.save(buffer, format="PNG")
    qr_base64 = base64.b64encode(buffer.getvalue()).decode()
    return f"data:image/png;base64,{qr_base64}"



def direct_purchase_invoice_detail(request, pk):
    invoice = get_object_or_404(DirectPurchaseInvoice, pk=pk)
    items = invoice.direct_purchase_items.all()  
    supplier = getattr(invoice, "supplier_name", None) 
    company = Company.objects.first()
    employee = Employee.objects.filter(user=invoice.user).first()
    authorized_signature = employee.signature.url
    
    amount = invoice.final_amount
    taka = int(amount)
    poisha = int(round((amount - taka) * 100))

    if poisha:
        total_in_words = f"{num2words(taka, lang='en').title()} Taka and {num2words(poisha, lang='en').title()} Poisha Only"
    else:
        total_in_words = f"{num2words(taka, lang='en').title()} Taka Only"

    context = {
        "invoice": invoice,
        "items": items,
        "qr_code_url": generate_direct_purchase_qr(invoice),
        "signature_url":authorized_signature,
        "company_logo_url": "/static/images/company_log.png",  
        "supplier": supplier,
        "company":company,
        "total_in_words": total_in_words,
        'employee':employee
    }
    return render(request, "finance/direct_purchase/direct_invoice_detail.html", context)


@transaction.atomic
def mark_direct_purchase_invoice_paid(request, pk):
    invoice = get_object_or_404(DirectPurchaseInvoice, pk=pk)

    if invoice.status != 'PAID':
        invoice.status = 'PAID'
        invoice.save()
        messages.success(request, f"Invoice {invoice.invoice_number} marked as Paid.")
    else:
        messages.info(request, f"Invoice {invoice.invoice_number} is already Paid.")

    return redirect('finance:direct_purchase_invoice_list')
