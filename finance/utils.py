
from decimal import Decimal
from django.utils import timezone
from accounting.models import JournalEntry, JournalEntryLine, Account,FiscalYear
from finance.models import PurchaseInvoice


def create_purchase_invoice_journal(invoice):
    fiscal_year = FiscalYear.get_active()

    journal_entry = JournalEntry.objects.create(
        date=timezone.now().date(),
        fiscal_year=fiscal_year,
        description=f"Purchase Invoice {invoice.invoice_number}",
        reference=f"purchase-invoice-{invoice.id}",
    )

    def get_account(code):
        try:
            return Account.objects.get(code=code)
        except Account.DoesNotExist:
            raise ValueError(f"Account with code {code} not found.")

    ap_account = get_account("2110")
    inventory_account = get_account("1150")
    vat_account = get_account("1180")
    ait_account = get_account("1190")

    amount = Decimal(invoice.amount_due or 0)
    vat_amount = Decimal(invoice.vat_amount or 0)
    ait_amount = Decimal(invoice.ait_amount or 0)

    # ----- Determine net amounts -----
    if invoice.VAT_type == 'inclusive':
        net_purchase = amount - vat_amount
    else:
        net_purchase = amount

    if invoice.AIT_type == 'inclusive':
        net_payable = net_purchase + vat_amount
        # AIT already included → no extra debit for AIT
        ait_debit = Decimal("0.00")
    else:
        net_payable = net_purchase + vat_amount - ait_amount
        ait_debit = ait_amount

    lines = [
        JournalEntryLine(
            entry=journal_entry,
            account=inventory_account,
            debit=net_purchase,
            description="Purchase goods"
        )
    ]

    if vat_amount > 0:
        lines.append(JournalEntryLine(
            entry=journal_entry,
            account=vat_account,
            debit=vat_amount,
            description="Input VAT receivable"
        ))

    if ait_debit > 0:
        lines.append(JournalEntryLine(
            entry=journal_entry,
            account=ait_account,
            debit=ait_debit,
            description="Advance Income Tax receivable"
        ))

    # Payable to supplier
    lines.append(JournalEntryLine(
        entry=journal_entry,
        account=ap_account,
        credit=net_payable,
        description="Accounts payable to supplier"
    ))

    JournalEntryLine.objects.bulk_create(lines)
    return journal_entry




from django.db import transaction
from decimal import Decimal
from django.utils import timezone

@transaction.atomic
def convert_quotation_to_invoice(supplier_quotation, user=None):
    if not supplier_quotation:
        raise ValueError("Supplier quotation is required to generate an invoice.")
    if supplier_quotation.status != 'approved':
        raise ValueError("Only approved quotations can be converted to invoices.")

    invoice = PurchaseInvoice.objects.create(
        user=user,
        supplier=supplier_quotation.supplier if hasattr(supplier_quotation, 'supplier') else None,
        VAT_rate=supplier_quotation.VAT_rate,
        VAT_type=supplier_quotation.VAT_type,
        AIT_rate=supplier_quotation.AIT_rate,
        AIT_type=supplier_quotation.AIT_type,
        vat_amount=Decimal(supplier_quotation.vat_amount or 0),
        ait_amount=Decimal(supplier_quotation.ait_amount or 0),
        amount_due=Decimal(supplier_quotation.total_amount or 0),
        net_due_amount=Decimal(supplier_quotation.net_due_amount or 0),
        issued_date=timezone.now(),
        status="SUBMITTED",
    )

    if not invoice.invoice_number:
        count = PurchaseInvoice.objects.count() + 1
        invoice.invoice_number = f"PI-{timezone.now().strftime('%Y%m%d')}-{count:04d}"
        invoice.save(update_fields=['invoice_number'])

    create_purchase_invoice_journal(invoice)

    return invoice



from .models import PurchaseInvoice
from purchase.models import PurchaseOrder, PurchaseOrderItem 
from decimal import Decimal, ROUND_HALF_UP


@transaction.atomic
def create_purchase_invoice_from_po(purchase_order_id, user, shipment=None):  
    po = PurchaseOrder.objects.select_related('supplier', 'supplier_quotation').prefetch_related('purchase_order_item').get(pk=purchase_order_id)

    # ✅ Validate PO status
    if po.approval_status not in ["APPROVED", "REVIEWED", "SUBMITTED"]:
        raise ValueError("Purchase Order must be approved or submitted before creating an invoice.")

    # ✅ Prevent duplicate invoice for same PO
    existing_invoice = PurchaseInvoice.objects.filter(purchase_shipment__purchase_order=po).first()
    if existing_invoice:
        return existing_invoice

    # ✅ Calculate total base amount from PO items
    total_base = Decimal('0.00')
    for item in po.purchase_order_item.all():
        total_base += Decimal(item.total_price or 0)

    # ✅ VAT / AIT calculations
    vat_amount = Decimal('0.00')
    ait_amount = Decimal('0.00')

  
    if po.AIT_type == "exclusive" and po.AIT_rate:
        ait_amount = (total_base * Decimal(po.AIT_rate) / Decimal('100')).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
    elif po.AIT_type == "inclusive" and po.AIT_rate:
        ait_amount = (total_base * Decimal(po.AIT_rate) / (Decimal('100') + Decimal(po.AIT_rate))).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)

    net_due = (total_base + vat_amount - ait_amount).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)

    # ✅ Create PurchaseInvoice
    invoice = PurchaseInvoice.objects.create(
        user=user,
        purchase_shipment=shipment,
        supplier=po.supplier,
        issued_date=timezone.now(),
        amount_due=po.total_amount,
        status="SUBMITTED",
        AIT_rate=po.AIT_rate,
        AIT_type=po.AIT_type,       
        vat_amount=po.vat_amount,
        ait_amount=po.ait_amount,
        net_due_amount=po.net_due_amount,
    )

    return invoice





from decimal import Decimal, ROUND_HALF_UP
from django.db import transaction
from django.utils import timezone
from django.core.exceptions import ObjectDoesNotExist
from logistics.models import SaleShipment
from sales.models import SaleOrder,SaleOrderItem

from .models import PurchaseInvoice,SaleInvoice

@transaction.atomic
def create_sale_invoice_from_so(sale_order_id, user, shipment=None):  
    so = (
        SaleOrder.objects
        .select_related('customer')
        .prefetch_related('sale_order')
        .get(pk=sale_order_id)
    )

    # ✅ Validate Sale Order status
    if not so.approver_approval_status == "APPROVED":
        raise ValueError("Sale Order must be approved or submitted before creating an invoice.")

 
    invoice = SaleInvoice.objects.create(
        user=user,       
        sale_shipment=shipment if isinstance(shipment, SaleShipment) else None,
        issued_date=timezone.now(),
        amount_due=so.total_amount,
        status="SUBMITTED",
        AIT_rate=so.AIT_rate,
        AIT_type=so.AIT_type,
        vat_amount=so.vat_amount,
        ait_amount=so.ait_amount,
        net_due_amount=so.net_due_amount,
        customer=so.customer
    )

    return invoice
