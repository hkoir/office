
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


