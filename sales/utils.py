

from django.utils import timezone
from decimal import Decimal
from .models import CustomerQuotation
from .models import SaleRequestOrder, SaleRequestItem  # adjust your app path



def create_sale_request_from_quotation(quotation_id, user, department=None, remarks=None):
    quotation = CustomerQuotation.objects.get(pk=quotation_id)

    if quotation.status != "accepted":
        raise ValueError("Quotation must be accepted before creating a Sale Request Order.")

    # --- create SaleRequestOrder ---
    sro = SaleRequestOrder.objects.create(
        order_id=f"SREQ-{timezone.now().strftime('%Y%m%d')}-{quotation.id:05d}",
        department=department,
        user=user,
        order_date=timezone.now().date(),
        status="IN_PROCESS",
        total_amount=Decimal(0),
        customer=quotation.customer,
        remarks=remarks,
        customer_quotation=quotation
    )

    total_amount = Decimal(0)

    for item in quotation.items.all():
        line_total = item.quantity * item.unit_price
        SaleRequestItem.objects.create(
            sale_request_order=sro,
            product=item.product,
            quantity=item.quantity,
            unit_selling_price=item.unit_price,
            customer=quotation.customer,
            user=user,
            status="PENDING",
        )
        total_amount += line_total

    sro.total_amount = total_amount
    sro.save()

    return sro
