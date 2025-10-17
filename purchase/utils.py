
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
from django.db import transaction


from decimal import Decimal
from django.utils import timezone
from django.db import transaction
from decimal import Decimal
from django.db import transaction
from django.utils import timezone


@transaction.atomic
def create_purchase_order_from_quotation(quotation_id, user):
    from.models import SupplierQuotation,PurchaseOrder,PurchaseOrderItem   
    quotation = SupplierQuotation.objects.prefetch_related('purchase_quotation_items').get(pk=quotation_id)

    if quotation.status.lower() != "approved":
        raise ValueError("Quotation must be approved before creating a Purchase Order.")

    # Prevent duplicate PO
    existing_po = PurchaseOrder.objects.filter(supplier_quotation=quotation).first()
    if existing_po:
        return existing_po

    # Create PurchaseOrder by copying totals
    po = PurchaseOrder.objects.create(
        order_id=f"PO-{timezone.now().strftime('%Y%m%d')}-{quotation.id:05d}",
        supplier=quotation.supplier,
        order_date=timezone.now().date(),
        user=user,
        status="IN_PROCESS",
        approval_status="SUBMITTED",
        supplier_quotation=quotation,
        purchase_request_order=getattr(quotation.rfq, 'purchase_request_order', None),
        AIT_rate=quotation.AIT_rate,
        AIT_type=quotation.AIT_type,
        vat_amount=quotation.vat_amount,
        ait_amount=quotation.ait_amount,
        total_amount=quotation.total_amount,
        net_due_amount=quotation.net_due_amount,
        remarks=quotation.notes or "",
        currency=quotation.currency or "BDT",
        required_delivery_date=quotation.quoted_delivery_date
    )

    # Copy quotation items to PO items
    for q_item in quotation.purchase_quotation_items.all():
        PurchaseOrderItem.objects.create(
            purchase_order=po,
            product=q_item.product,
            quantity=q_item.quantity,
            unit_of_measure=q_item.unit_of_measure,
            required_delivery_date=q_item.quoted_delivery_date,
            currency=q_item.currency or "BDT",
            specification=q_item.specification,
            remarks=q_item.notes or "",
            total_price=q_item.total_price,
            VAT_rate=q_item.VAT_rate,
            VAT_type=q_item.VAT_type,
            vat_amount=q_item.vat_amount,
            supplier=quotation.supplier,
            batch = None,
          
        )

    return po
