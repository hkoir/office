
def compare_supplier_quotations(rfq_id):
    from purchase.models import SupplierQuotation
    rfq_quotations = SupplierQuotation.objects.filter(
        rfq_id=rfq_id
    ).prefetch_related('purchase_quotation_items__product', 'supplier')

    comparison_data = {}
    supplier_totals = []  # 👈 overall supplier-level totals

    for quotation in rfq_quotations:
        # Supplier-level total is already in `quotation.total_amount`
        supplier_totals.append({
            "supplier": quotation.supplier,
            "quotation_number": quotation.quotation_number,
            "total_amount": quotation.total_amount,
            "AIT_type": quotation.AIT_type,
            "AIT_rate":quotation.AIT_rate,
            'net_payable':quotation.net_due_amount
        })

        # Item-level details
        for item in quotation.purchase_quotation_items.all():
            product_id = item.product.id
            if product_id not in comparison_data:
                comparison_data[product_id] = {
                    'product': item.product,
                    'quotations': [],
                    'lowest_price': item.unit_price,
                }
            comparison_data[product_id]['quotations'].append({
                'supplier': quotation.supplier,
                'quotation_number': quotation.quotation_number,
                'unit_price': item.unit_price,
                'quantity': item.quantity,
                'total_price': item.total_price,
                'VAT_type': item.VAT_type,
                'VAT_rate':item.VAT_rate
                
            })
            if item.unit_price < comparison_data[product_id]['lowest_price']:
                comparison_data[product_id]['lowest_price'] = item.unit_price

    # Find the lowest total supplier
    lowest_total = min(supplier_totals, key=lambda x: x["total_amount"], default=None)

    return {
        "items": comparison_data,
        "suppliers": supplier_totals,
        "lowest_supplier": lowest_total,
    }



def create_units_for_batch(batch, start_index=1):
    from product.models import Unit
    units = []
    for i in range(start_index, start_index + batch.quantity):
        serial_number = f"{batch.batch_number}-{i:04d}"
        barcode_value = f"{batch.batch_number}-BC-{i:04d}"  # unique barcode per unit

        units.append(Unit(
            batch=batch,
            serial_number=serial_number,
            barcode=barcode_value,  # ✅ ensure uniqueness
            manufacture_date=batch.manufacture_date,
            expiry_date=batch.expiry_date
        ))

    Unit.objects.bulk_create(units)





from django.utils import timezone
from decimal import Decimal
from decimal import Decimal, ROUND_HALF_UP



def create_purchase_order_from_quotation(quotation_id, user):
    from .models import PurchaseOrder, PurchaseOrderItem, SupplierQuotation
    
    quotation = SupplierQuotation.objects.get(pk=quotation_id)
    if quotation.status != "approved":
        raise ValueError("Quotation must be approved before creating a purchase order.")

    po = PurchaseOrder.objects.create(
        order_id=f"PO-{timezone.now().strftime('%Y%m%d')}-{quotation.id:05d}",
        supplier=quotation.supplier,
        order_date=timezone.now().date(),
        user=user,
        status="IN_PROCESS",
        approval_status="SUBMITTED",
        supplier_quotation=quotation,
        purchase_request_order=quotation.rfq.purchase_request_order,
        VAT_rate=quotation.VAT_rate,
        VAT_type=quotation.VAT_type,
        AIT_rate=quotation.AIT_rate,
        AIT_type=quotation.AIT_type,
        vat_amount=quotation.vat_amount,
        ait_amount=quotation.ait_amount,
        total_amount=quotation.net_due_amount
    )

    total_amount = Decimal('0.00')
    for item in quotation.purchase_quotation_items.all():
        line_total = (item.quantity * item.unit_price).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
        PurchaseOrderItem.objects.create(
            purchase_order=po,
            product=item.product,
            quantity=item.quantity,
            total_price=line_total,
            supplier=quotation.supplier,
            user=user,
        )
        total_amount += line_total

    po.total_amount = total_amount.quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
    po.supplier_quotation = quotation
    po.save()
    return po

