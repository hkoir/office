from django.db import models
from django.db.models import Sum
from django.utils import timezone
from django.contrib.auth.models import User
from simple_history.models import HistoricalRecords
import uuid
from django.apps import apps
from django.core.exceptions import ValidationError

import logging
logger = logging.getLogger(__name__)

from supplier.models import Supplier
from product.models import Product,Component
from django.apps import apps
from accounts.models import CustomUser
from finance.models import PurchaseInvoice,PurchasePayment

from.utils import create_units_for_batch

import uuid
import qrcode
from io import BytesIO
from barcode import Code128
from barcode.writer import ImageWriter
from decimal import Decimal
from django.utils import timezone
from django.core.files.base import ContentFile




class Batch(models.Model):
    NEW_PURCHASE = 'NEW'
    EXISTING_PRODUCT = 'EXISTING'
    
    PRODUCT_TYPE_CHOICES = [
        (NEW_PURCHASE, 'New Purchase'),
        (EXISTING_PRODUCT, 'Existing Product'),
    ]

    user = models.ForeignKey(CustomUser, on_delete=models.CASCADE, null=True, blank=True, related_name='batch_user')
    batch_number = models.CharField(max_length=50, unique=True, editable=False)
    product_type = models.CharField(max_length=10, choices=PRODUCT_TYPE_CHOICES, default=NEW_PURCHASE)
    product = models.ForeignKey('product.Product', on_delete=models.CASCADE, related_name='product_batches')   
    manufacture_date = models.DateField()
    expiry_date = models.DateField()
    vat_percentage = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    purchase_price = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)
    selling_price = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)
    regular_price = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)
    discounted_price = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)
    image = models.ImageField(upload_to="product_image_batches/", null=True, blank=True)
    returned_quantity = models.DecimalField(max_digits=12, decimal_places=2, default=0, null=True, blank=True)
    brand = models.CharField(max_length=200, null=True, blank=True)
    shelf = models.ForeignKey('inventory.Shelf', on_delete=models.SET_NULL, null=True, blank=True, related_name="purchase_product_batch_shelf")
    supplier = models.ForeignKey(Supplier, on_delete=models.CASCADE, related_name='batch_item_supplier', null=True, blank=True)
    quantity = models.PositiveIntegerField()
    remaining_quantity = models.PositiveIntegerField(null=True, blank=True)
    unit_price = models.DecimalField(max_digits=20, decimal_places=2, null=True, blank=True)
    sale_price = models.DecimalField(max_digits=20, decimal_places=2, null=True, blank=True)
    barcode = models.CharField(max_length=100, unique=True, null=True, blank=True)
    barcode_image = models.ImageField(upload_to="barcodes/", null=True, blank=True)
    qr_code_image = models.ImageField(upload_to="qrcodes/", null=True, blank=True)
    created_at = models.DateField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def save(self, *args, **kwargs):
        if not self.batch_number:
            timestamp = timezone.now().strftime('%Y%m%d%H%M%S')
            unique_id = str(uuid.uuid4().hex)[:6]
            self.batch_number = f"BATCH-{timestamp}-{unique_id}"

        if not self.barcode:
            self.barcode = f"{self.product.product_id}-{self.batch_number}"          
            qr = qrcode.QRCode(version=1, box_size=10, border=2)
            qr.add_data(self.barcode)
            qr.make(fit=True)
            img = qr.make_image(fill="black", back_color="white")
            buffer = BytesIO()
            img.save(buffer, format="PNG")
            self.qr_code_image.save(f"{self.batch_number}.png", ContentFile(buffer.getvalue()), save=False)
 
            barcode_img = Code128(self.barcode, writer=ImageWriter())
            barcode_buffer = BytesIO()
            barcode_img.write(barcode_buffer)
            self.barcode_image.save(f"{self.batch_number}.png", ContentFile(barcode_buffer.getvalue()), save=False)

        if not self.sale_price or self.sale_price == 0:
            self.sale_price = self.discounted_price or 0
        if not self.selling_price or self.selling_price == 0:
            self.selling_price = self.discounted_price 
        if not self.unit_price or self.unit_price == 0:
            self.unit_price = self.discounted_price

        if not self.discounted_price:
            self.discounted_price = self.regular_price
       

        is_new = not self.pk
        if is_new:
            self.remaining_quantity = self.quantity
        super().save(*args, **kwargs)
        
        if is_new and self.quantity > 0:
            create_units_for_batch(batch=self)




    def __str__(self):
        inventory = self.batch_inventory.first()  
        warehouse_name = inventory.warehouse.name if inventory else "No Warehouse"  
        return f'{self.product}:Batch - {self.batch_number} - selling Price={self.discounted_price} - Available: {self.remaining_quantity}'





class PurchaseRequestOrder(models.Model):
    order_id = models.CharField(max_length=50,null=True,blank=True)
    department = models.CharField(max_length=50,null=True, blank=True)
    user = models.ForeignKey(CustomUser, on_delete=models.CASCADE, null=True, blank=True, related_name='purchase_request_user')
    order_date = models.DateField(null=True, blank=True)
    STATUS_CHOICES = [
        ('IN_PROCESS', 'In Process'),
        ('READY_FOR_QC', 'Ready for QC'),
        ('DISPATCHED', 'Dispatched'),
        ('ON_BOARD', 'On Board'),
        ('IN_TRANSIT', 'In Transit'),
        ('CUSTOM_CLEARANCE_IN_PROCESS', 'Custom Clearance In Process'),   
        ('REACHED', 'Reached'),         
        ('OBI','OBI done'),
        ('DELIVERED', 'Delivered'),     
        ('CANCELLED', 'Cancelled'),
        ]
    status = models.CharField(max_length=50, choices=STATUS_CHOICES, default='SUBMITTED',null=True, blank=True) 

    APPROVAL_STATUS_CHOICES = [
    ('SUBMITTED', 'Submitted'),
     ('REVIEWED', 'Reviewed'),
    ('APPROVED', 'Approved'),   
    ('CANCELLED','Cancelled'),
        ]
    approval_status = models.CharField(max_length=20, choices=APPROVAL_STATUS_CHOICES, default='SUBMITTED',null=True, blank=True) 
    requester = models.ForeignKey(CustomUser, on_delete=models.SET_NULL, null=True, blank=True, related_name='requester_orders')
    reviewer = models.ForeignKey(CustomUser, on_delete=models.SET_NULL, null=True, blank=True, related_name='reviewer_orders')
    approver = models.ForeignKey(CustomUser, on_delete=models.SET_NULL, null=True, blank=True, related_name='approver_orders')
    
    total_amount = models.DecimalField(max_digits=15, decimal_places=2,null=True, blank=True)
    created_at = models.DateField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    remarks=models.TextField(null=True,blank=True)
   
    approval_data = models.JSONField(default=dict,null=True,blank=True)

    requester_approval_status = models.CharField(max_length=20, null=True, blank=True)
    reviewer_approval_status = models.CharField(max_length=20, null=True, blank=True)
    approver_approval_status = models.CharField(max_length=20, null=True, blank=True)

    Requester_remarks=models.TextField(null=True,blank=True)
    Reviewer_remarks=models.TextField(null=True,blank=True)
    Approver_remarks=models.TextField(null=True,blank=True)
    

    class Meta:
        permissions = [
            ("can_request", "can request"),
            ("can_review", "Can review"),
            ("can_approve", "Can approve"),
        ]

    
    def save(self, *args, **kwargs):
        if not self.requester:
            self.requester = CustomUser.objects.filter(groups__name='Requester').first()
        if not self.reviewer:
            self.reviewer = CustomUser.objects.filter(groups__name='Reviewer').first()
        if not self.approver:
            self.approver = CustomUser.objects.filter(groups__name='Approver').first()

        if not self.order_id:
            self.order_id= f"PRID-{uuid.uuid4().hex[:8].upper()}"
        super().save(*args, **kwargs)



    @property
    def is_fully_delivered(self):  
        total_delivered = self.purchase_order_request_order.all().aggregate(
            total_dispatched=Sum('purchase_order_item__order_dispatch_item__dispatch_quantity')  # Adjust related names
        )['total_dispatched'] or 0

        total_ordered = self.purchase_request_order.all().aggregate(
            total_ordered=Sum('quantity')  
        )['total_ordered'] or 0

        return total_delivered >= total_ordered

    def __str__(self):
        product_details = ", ".join(
            f"{item.product.name} (Qty: {item.quantity})"
            for item in self.purchase_request_order.all()
        )
        return self.order_id
       

class PurchaseRequestItem(models.Model):
    item_request_id = models.CharField(max_length=20,null=True,blank=True)
    user = models.ForeignKey(CustomUser, on_delete=models.CASCADE, null=True, blank=True, related_name='purchase_request_item_user')
    purchase_request_order=models.ForeignKey(PurchaseRequestOrder,related_name='purchase_request_order',on_delete=models.CASCADE)
    product = models.ForeignKey(Product,related_name='purchase_request_item', on_delete=models.CASCADE)   
    quantity = models.PositiveIntegerField() 
    priority = models.CharField(max_length=20, choices=[('LOW', 'Low'), ('MEDIUM', 'Medium'), ('HIGH', 'High')])
    total_price = models.DecimalField(max_digits=15,decimal_places=2, null=True,blank=True)
    created_at = models.DateField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)


    def save(self,*args,**kwargs):
        if not self.item_request_id:
            self.item_request_id= f"RIID-{uuid.uuid4().hex[:8].upper()}"
        super().save(*args,*kwargs)

    def __str__(self):
        return f" {self.item_request_id}:{self.product.name}:{self.quantity}nos"


from django.db.models import Q
import uuid
from django.utils.timezone import now



class RFQ(models.Model):
    rfq_number = models.CharField(max_length=30, unique=True, blank=True)
    purchase_request_order = models.ForeignKey(PurchaseRequestOrder, on_delete=models.CASCADE, related_name="rfqs")
    date = models.DateField(default=timezone.now)
    valid_until = models.DateField(null=True, blank=True)
    notes = models.TextField(blank=True, null=True)

    STATUS_CHOICES = [
        ("draft", "Draft"),
        ("sent", "Sent"),
        ("closed", "Closed"),
    ]
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="draft")

    def save(self, *args, **kwargs):
        if not self.rfq_number:
            count = SupplierQuotation.objects.count() + 1
            self.rfq_number = f"RFQ-{timezone.now().strftime('%Y%m%d')}-{count:04d}"
        super().save(*args, **kwargs)

    

    def __str__(self):
        return f"{self.rfq_number} - {self.purchase_request_order}"


class RFQItem(models.Model):
    rfq = models.ForeignKey(RFQ, on_delete=models.CASCADE, related_name="items")
    product = models.ForeignKey('product.Product', on_delete=models.CASCADE)
    quantity = models.PositiveIntegerField()
    notes = models.TextField(blank=True, null=True) 
    
    def __str__(self):
        return f"{self.product} - {self.quantity}"


from decimal import Decimal, ROUND_HALF_UP
from django.db import models
from django.utils import timezone

from decimal import Decimal, ROUND_HALF_UP
from django.db import models
from django.utils import timezone

class SupplierQuotation(models.Model):
    rfq = models.ForeignKey(
        "RFQ", on_delete=models.CASCADE, null=True, blank=True, related_name="rfq_quotation"
    )
    supplier = models.ForeignKey("supplier.Supplier", on_delete=models.CASCADE)
    quotation_number = models.CharField(max_length=30, unique=True, blank=True)
    date = models.DateField(default=timezone.now)
    valid_until = models.DateField(null=True, blank=True)

    STATUS_CHOICES = [
        ("draft", "Draft"),
        ("sent", "Sent"),
        ("approved", "Approved"),
        ("rejected", "Rejected"),
    ]
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="draft")

    # TAX SETTINGS
    AIT_rate = models.DecimalField(max_digits=5, decimal_places=2, blank=True, null=True)
    AIT_type = models.CharField(
        max_length=50,
        choices=[('inclusive', 'Inclusive'), ('exclusive', 'Exclusive')],
        null=True, blank=True, default='exclusive'
    )
    VAT_rate = models.DecimalField(max_digits=5, decimal_places=2, blank=True, null=True)
    VAT_type = models.CharField(
        max_length=50,
        choices=[('inclusive', 'Inclusive'), ('exclusive', 'Exclusive')],
        null=True, blank=True, default='exclusive'
    )

    # AMOUNTS
    total_amount = models.DecimalField(max_digits=15, decimal_places=2, default=0)  # before tax
    net_due_amount = models.DecimalField(max_digits=15, decimal_places=2, blank=True, null=True)
    vat_amount = models.DecimalField(max_digits=15, decimal_places=2, default=0)
    ait_amount = models.DecimalField(max_digits=15, decimal_places=2, default=0)
    notes = models.TextField(blank=True, null=True)


    def calculate_tax_amounts(self):  
        base_total = Decimal('0.00')
        vat_total = Decimal('0.00')

        # --- Calculate item-wise base and VAT ---
        for item in self.purchase_quotation_items.all():
            qty = Decimal(item.quantity or 0)
            unit_price = Decimal(item.unit_price or 0)
            line_total = qty * unit_price

            item_vat_rate = Decimal(item.VAT_rate or 0) / 100
            vat_type = (item.VAT_type or "exclusive").lower()

            if vat_type == "inclusive" and item_vat_rate > 0:
                # VAT included in line_total
                item_vat = (line_total - (line_total / (1 + item_vat_rate))).quantize(Decimal("0.01"), ROUND_HALF_UP)
                item_base = line_total - item_vat
            else:
                # VAT exclusive or no VAT
                item_vat = (line_total * item_vat_rate).quantize(Decimal("0.01"), ROUND_HALF_UP)
                item_base = line_total

            base_total += item_base
            vat_total += item_vat

        self.total_amount = base_total.quantize(Decimal("0.01"), ROUND_HALF_UP)
        self.vat_amount = vat_total.quantize(Decimal("0.01"), ROUND_HALF_UP)

        # --- Calculate AIT (withholding tax on total base) ---
        ait_rate = Decimal(self.AIT_rate or 0) / 100
        ait_type = (self.AIT_type or "exclusive").lower()

        if ait_rate > 0:
            if ait_type == "inclusive":
                # AIT included in total_amount (rare case)
                ait_amount = (self.total_amount - (self.total_amount / (1 + ait_rate))).quantize(Decimal("0.01"), ROUND_HALF_UP)
                net_base = self.total_amount - ait_amount
            else:
                # AIT exclusive (deducted from supplier)
                ait_amount = (self.total_amount * ait_rate).quantize(Decimal("0.01"), ROUND_HALF_UP)
                net_base = self.total_amount
        else:
            ait_amount = Decimal('0.00')
            net_base = self.total_amount

        self.ait_amount = ait_amount

        # --- Net payable to supplier ---
        # Supplier receives base + VAT − AIT
        if ait_type == "inclusive":
            self.net_due_amount = (net_base + self.vat_amount).quantize(Decimal("0.01"), ROUND_HALF_UP)
        else:
            self.net_due_amount = (net_base + self.vat_amount - ait_amount).quantize(Decimal("0.01"), ROUND_HALF_UP)

    def save(self, *args, **kwargs):
        # Auto-generate quotation number
        if not self.quotation_number:
            count = SupplierQuotation.objects.count() + 1
            self.quotation_number = f"SQ-{timezone.now().strftime('%Y%m%d')}-{count:04d}"

        super().save(*args, **kwargs)


class SupplierQuotationItem(models.Model):
    VAT_CHOICES = [
        ('inclusive', 'Inclusive'),
        ('exclusive', 'Exclusive'),
    ]

    quotation = models.ForeignKey(SupplierQuotation, related_name="purchase_quotation_items", on_delete=models.CASCADE)
    product = models.ForeignKey("product.Product", on_delete=models.CASCADE)
    quantity = models.DecimalField(max_digits=10, decimal_places=2)
    unit_price = models.DecimalField(max_digits=12, decimal_places=2)

    VAT_rate = models.DecimalField(max_digits=5, decimal_places=2, default=0)

    # ✅ use CharField with proper choices
    VAT_type = models.CharField(
        max_length=20,
        choices=VAT_CHOICES,
        default='exclusive',  # optional
        null=True,
        blank=True
    )
    AIT_type = models.CharField(
        max_length=20,
        choices=VAT_CHOICES,
        default='exclusive',  # optional
        null=True,
        blank=True
    )

    total_price = models.DecimalField(max_digits=15, decimal_places=2, blank=True)

    def save(self, *args, **kwargs):
        base_amount = self.quantity * self.unit_price
        vat_rate = Decimal(self.VAT_rate or 0) / 100
        if self.VAT_type == 'inclusive':
            vat_amt = (base_amount - (base_amount / (1 + vat_rate))).quantize(Decimal("0.01"))
            base_amount -= vat_amt
        else:
            vat_amt = (base_amount * vat_rate).quantize(Decimal("0.01"))
        self.vat_amount = vat_amt
        self.total_price = base_amount + vat_amt if self.VAT_type == 'exclusive' else base_amount
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.product} ({self.quantity})"


class PurchaseOrder(models.Model):
    order_id = models.CharField(max_length=20)
    purchase_request_order = models.ForeignKey(PurchaseRequestOrder, 
        on_delete=models.CASCADE, null=True, blank=True,related_name='purchase_order_request_order')

    supplier_quotation = models.ForeignKey(SupplierQuotation, 
        on_delete=models.CASCADE, null=True, blank=True,related_name='supplier_quotations')
    user = models.ForeignKey(CustomUser, on_delete=models.CASCADE, null=True, blank=True, related_name='purchase_order_user')
    supplier = models.ForeignKey(Supplier, on_delete=models.CASCADE, related_name='purchase_supplier')
    order_date = models.DateField(null=True, blank=True)
    ORDER_STATUS_CHOICES = [
        ('IN_PROCESS', 'In Process'),
        ('READY_FOR_QC', 'Ready for QC'),
        ('DISPATCHED', 'Dispatched'),
        ('ON_BOARD', 'On Board'),
        ('IN_TRANSIT', 'In Transit'),
        ('CUSTOM_CLEARANCE_IN_PROCESS', 'Custom Clearance In Process'),   
        ('REACHED', 'Reached'),         
        ('OBI','OBI done'),
        ('DELIVERED', 'Delivered'),     
        ('CANCELLED', 'Cancelled'),
        ]
    status = models.CharField(max_length=50, choices=ORDER_STATUS_CHOICES, default='IN_PROCESS',null=True,blank=True)   
    APPROVAL_STATUS_CHOICES = [
    ('SUBMITTED', 'Submitted'),
     ('REVIEWED', 'Reviewed'),
    ('APPROVED', 'Approved'),   
    ('CANCELLED','Cancelled'),
        ]

     # TAX SETTINGS
    AIT_rate = models.DecimalField(max_digits=5, decimal_places=2, blank=True, null=True)
    AIT_type = models.CharField(
        max_length=50,
        choices=[('inclusive', 'Inclusive'), ('exclusive', 'Exclusive')],
        null=True, blank=True, default='exclusive'
    )
    VAT_rate = models.DecimalField(max_digits=5, decimal_places=2, blank=True, null=True)
    VAT_type = models.CharField(
        max_length=50,
        choices=[('inclusive', 'Inclusive'), ('exclusive', 'Exclusive')],
        null=True, blank=True, default='exclusive'
    )

    vat_amount = models.DecimalField(max_digits=15, decimal_places=2, default=0)
    ait_amount = models.DecimalField(max_digits=15, decimal_places=2, default=0)
    approval_status = models.CharField(max_length=20, choices=APPROVAL_STATUS_CHOICES, default='SUBMITTED',null=True, blank=True) 
    total_amount = models.DecimalField(max_digits=15, decimal_places=2,null=True, blank=True)

    requester = models.ForeignKey(CustomUser, on_delete=models.SET_NULL, null=True, blank=True, related_name='order_requester')
    reviewer = models.ForeignKey(CustomUser, on_delete=models.SET_NULL, null=True, blank=True, related_name='order_reviewer')
    approver = models.ForeignKey(CustomUser, on_delete=models.SET_NULL, null=True, blank=True, related_name='order_approvar')
    
    created_at = models.DateField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    remarks=models.TextField(null=True,blank=True)

    approval_data = models.JSONField(default=dict,null=True,blank=True)
    requester_approval_status = models.CharField(max_length=20, null=True, blank=True)
    reviewer_approval_status = models.CharField(max_length=20, null=True, blank=True)
    approver_approval_status = models.CharField(max_length=20, null=True, blank=True)

    Requester_remarks=models.TextField(null=True,blank=True)
    Reviewer_remarks=models.TextField(null=True,blank=True)
    Approver_remarks=models.TextField(null=True,blank=True)
      
    class Meta:
        permissions = [
            ("can_request", "can request"),
            ("can_review", "Can review"),
            ("can_approve", "Can approve"),
        ]

    def save(self, *args, **kwargs):
        if not self.requester:
            self.requester = CustomUser.objects.filter(groups__name='Requester').first()
        if not self.reviewer:
            self.reviewer = CustomUser.objects.filter(groups__name='Reviewer').first()
        if not self.approver:
            self.approver = CustomUser.objects.filter(groups__name='Approver').first()

        if not self.order_id:
            self.order_id= f"PROID-{uuid.uuid4().hex[:8].upper()}"
        super().save(*args, **kwargs)

        
    def __str__(self):
        return self.order_id
    
    @property
    def is_fully_delivered(self):
        total_delivered_agg = self.purchase_shipment.all().aggregate(
            total_dispatched=Sum('shipment_dispatch_item__dispatch_quantity', filter=Q(shipment_dispatch_item__status='DELIVERED'))
        )
        total_delivered = total_delivered_agg['total_dispatched'] if total_delivered_agg and total_delivered_agg['total_dispatched'] is not None else 0
       
        total_ordered_agg = self.purchase_order_item.all().aggregate(
            total_ordered=Sum('quantity')
        )
        total_ordered = total_ordered_agg['total_ordered'] if total_ordered_agg and total_ordered_agg['total_ordered'] is not None else 0
       
        return total_delivered >= total_ordered

    def get_payment_status(self):
        shipments = self.purchase_shipment.all()
        if not shipments.exists():
            return "NO_SHIPMENT"

        invoices = PurchaseInvoice.objects.filter(purchase_shipment__in=shipments)
        if not invoices.exists():
            return "NO_INVOICE"

        fully_paid = True
        partially_paid = False
        no_payment = True

        for invoice in invoices:
            if invoice.is_fully_paid:
                no_payment = False
            elif invoice.total_paid_amount > 0:
                fully_paid = False
                partially_paid = True
                no_payment = False
            else:
                fully_paid = False

        if fully_paid:
            return "FULLY_PAID"
        elif partially_paid:
            return "PARTIALLY_PAID"
        elif no_payment:
            return "NO_PAYMENT"
        return "UNKNOWN"
    
    def get_payment_action(self):
        if self.approver_approval_status != "APPROVED":
            return {"status": "APPROVAL_PENDING"}

        shipments = self.purchase_shipment.all()
        if not shipments.exists():
            return {"status": "NO_SHIPMENT"}

        invoices = PurchaseInvoice.objects.filter(purchase_shipment__in=shipments)
        if not invoices.exists():
            return {"status": "NO_INVOICE"}

        payments = PurchasePayment.objects.filter(purchase_invoice__in=invoices)
        if not payments.exists():
            # pick the first invoice to attach payment action
            return {"status": "NO_PAYMENT", "invoice": invoices.first()}

        # Check if all invoices are fully paid
        if all(inv.is_fully_paid for inv in invoices):
            return {"status": "FULLY_PAID"}

        # Some invoices unpaid → allow payment on the first unpaid one
        unpaid_invoice = next((inv for inv in invoices if not inv.is_fully_paid), None)
        return {"status": "PARTIAL", "invoice": unpaid_invoice}
    
    def get_first_invoice(self):
        """Safely return the first invoice for the first shipment, or None."""
        shipment = self.purchase_shipment.first()
        if shipment:
            return shipment.shipment_invoices.first()
        return None

    def get_invoice_status(self):
        invoice = self.get_first_invoice()
        return invoice.status if invoice else None
    
    


class PurchaseOrderItem(models.Model):
    order_item_id = models.ForeignKey(PurchaseRequestItem,on_delete=models.CASCADE,related_name='order_request_item',null=True,blank=True)
    user = models.ForeignKey(CustomUser, on_delete=models.CASCADE, null=True, blank=True, related_name='purchase_order_item_user')
    purchase_order = models.ForeignKey(PurchaseOrder, related_name='purchase_order_item', on_delete=models.CASCADE)
    batch = models.ForeignKey(Batch,on_delete=models.CASCADE,related_name='batch_purchase_order_item',null=True, blank=True)
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name='purchases', null=True, blank=True)
    quantity = models.PositiveIntegerField(null=True, blank=True)  # Total quantity ordered
    total_price = models.DecimalField(max_digits=15, decimal_places=2, null=True, blank=True)
    supplier = models.ForeignKey(Supplier, on_delete=models.CASCADE, related_name='purchase_order_items_supplier',null=True,blank=True)
    prepared_by = models.ForeignKey(CustomUser, related_name='prepared_purchases', on_delete=models.CASCADE, null=True, blank=True)
    approved_by = models.ForeignKey(CustomUser, related_name='approved_purchases', on_delete=models.CASCADE, null=True, blank=True)
    status = models.CharField(
    max_length=50,
    choices=[
        ('IN_PROCESS', 'In Process'),
        ('READY_FOR_QC', 'Ready for QC'),
        ('DISPATCHED', 'Dispatched'),
        ('ON_BOARD', 'On Board'),
        ('IN_TRANSIT', 'In Transit'),
        ('CUSTOM_CLEARANCE_IN_PROCESS', 'Custom Clearance In Process'),   
        ('REACHED', 'Reached'),         
        ('OBI','OBI done'),
        ('DELIVERED', 'Delivered'),     
        ('CANCELLED', 'Cancelled'),
    ],
    null=True,
    blank=True,
    default='IN_PROCESS'
)
    created_at = models.DateField(auto_now_add=True)
    updated_at = models.DateField(auto_now=True)
    remarks = models.TextField(null=True, blank=True)


  

    @property
    def quantity_dispatch(self):
        related_items = self.related_item_dispatch.all()  # Get all related dispatch items
        logger.info(f"Related dispatch items: {related_items}")
        total_dispatch = self.related_item_dispatch.aggregate(total_dispatched=Sum('dispatch_quantity'))['total_dispatched'] or 0
        return total_dispatch

    @property
    def remaining_to_dispatch(self):
        return (self.quantity or 0) - self.quantity_dispatch

    def __str__(self):
        return f"{self.quantity} nos {self.product.name}"
    
    
    def save(self,*args,**kwargs):      
        if not self.total_price:
             self.total_price = self.quantity * self.batch.unit_price
        super().save(*args,**kwargs)
    

#


class QualityControl(models.Model):
    purchase_dispatch_item = models.ForeignKey('logistics.PurchaseDispatchItem', on_delete=models.CASCADE,
         related_name='quality_control',null=True,blank=True)
    user = models.ForeignKey(CustomUser, on_delete=models.CASCADE, null=True, blank=True, related_name='quality_control_user')
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name='qc_product', null=True, blank=True)
    total_quantity = models.PositiveIntegerField(null=True, blank=True)
    good_quantity = models.PositiveIntegerField(null=True, blank=True)
    bad_quantity = models.PositiveIntegerField(null=True, blank=True)
    inspection_date = models.DateField(null=True, blank=True)
    comments = models.TextField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

  

    def save(self):
        PurchaseDispatchItem = apps.get_model('logistics', 'PurchaseDispatchItem')
        return PurchaseDispatchItem.objects.get(id=self.purchase_dispatch_item.id) if self.purchase_dispatch_item else None
     

    def save(self,*args,**kwargs):
        self.total_quantity = self.purchase_dispatch_item.dispatch_quantity
        if not self.product:
             self.product = self.purchase_dispatch_item.dispatch_item.product

        super().save(*args,**kwargs)

    def __str__(self):
        return f" QC{self.product.name},total qty: {self.total_quantity} good qty={self.good_quantity}, bad qty={self.bad_quantity}"




class ReceiveGoods(models.Model):
    purchase_order = models.ForeignKey(PurchaseOrder, on_delete=models.CASCADE, related_name='received_goods')
    quality_control = models.ForeignKey(QualityControl, on_delete=models.CASCADE, related_name='qc_goods')
    product = models.ForeignKey(Product, on_delete=models.CASCADE)  
    warehouse = models.ForeignKey('inventory.warehouse', on_delete=models.CASCADE, related_name='received_goods_warehouse',null=True, blank=True)
    location = models.ForeignKey('inventory.location', on_delete=models.CASCADE, null=True, blank=True,related_name='received_goods_location')
    quantity_received = models.PositiveIntegerField(null=True, blank=True)
    user = models.ForeignKey(CustomUser, on_delete=models.CASCADE, null=True, blank=True, related_name='received_goods')

    RECEIVE_STATUS_CHOICES = [
        ('RECEIVED', 'RECEIVED'),
        ('PENDING', 'PENDING'),
    ]
    receive_status = models.CharField(max_length=20, null=True, blank=True, choices=RECEIVE_STATUS_CHOICES, default='PENDING')
    received_at = models.DateTimeField(default=timezone.now)
    created_at = models.DateField(auto_now_add=True)
    updated_at = models.DateField(auto_now=True)
    remarks = models.TextField(null=True, blank=True)


    def get_warehouse(self):
        Warehouse = apps.get_model('inventory', 'Warehouse')
        return Warehouse.objects.get(id=self.warehouse.id) if self.warehouse else None

    def get_location(self):
        Location = apps.get_model('inventory', 'Location')
        return Location.objects.get(id=self.location.id) if self.location else None

    def save(self,*args,**kwargs):
       self.product = self.quality_control.product.name
       self.quantity_received = self.quality_control.good_quantity
       super().save(*args,**kwargs)

    def __str__(self):
        return f"{self.quantity_received} of {self.product.name} received at {self.warehouse.name}"
