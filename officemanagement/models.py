from django.db import models
import uuid
from django.utils.timezone import now
from inventory.models import Warehouse,Location
from accounts.models import CustomUser
from supplier.models import Supplier
from django.utils import timezone
from core.models import Department,Company,Employee



class StationaryCategory(models.Model):
    user = models.ForeignKey(CustomUser, on_delete=models.CASCADE, null=True, blank=True, related_name='stationary_category_user')
    name = models.CharField(max_length=100)
    category_id = models.CharField(max_length=150, unique=True, null=True, blank=True)
    description = models.TextField(blank=True, null=True)
    created_at = models.DateField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)


    class Meta:
            ordering = ['created_at']

    def save(self, *args, **kwargs):
        if not self.category_id:
            self.category_id = f"CAT-{uuid.uuid4().hex[:8].upper()}"
        super().save(*args, **kwargs)

    def __str__(self):
        return self.name
    

class StationaryProduct(models.Model):
    user = models.ForeignKey(CustomUser, on_delete=models.CASCADE, null=True, blank=True)    
    product_id = models.CharField(max_length=150, unique=True, null=True, blank=True)
    stationary_category = models.ForeignKey(StationaryCategory, on_delete=models.CASCADE)
    name = models.CharField(max_length=255, unique=True)
    description = models.TextField(blank=True, null=True)
    unit_price = models.DecimalField(max_digits=10, decimal_places=2)
    reorder_level = models.PositiveIntegerField(default=10)
    created_at = models.DateField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
   

    def save(self, *args, **kwargs): 
        if not self.product_id:
            timestamp = timezone.now().strftime('%Y%m%d%H%M%S')
            unique_id = str(uuid.uuid4().hex)[:6]  
            self.product_id = f"PID-{timestamp}-{unique_id}"
        super().save(*args, **kwargs)
    
    def __str__(self):
        return self.name



class StationaryBatch(models.Model):
    user = models.ForeignKey(CustomUser, on_delete=models.CASCADE, null=True, blank=True)
    batch_number = models.CharField(max_length=50, unique=True, editable=False)
    stationary_product = models.ForeignKey(StationaryProduct, on_delete=models.CASCADE)    
    quantity = models.PositiveIntegerField()
    remaining_quantity = models.PositiveIntegerField(null=True, blank=True)
    unit_price = models.DecimalField(max_digits=10, decimal_places=2)
   
    created_at = models.DateField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
 

    def save(self, *args, **kwargs): 
        if not self.batch_number:
            timestamp = timezone.now().strftime('%Y%m%d%H%M%S')
            unique_id = str(uuid.uuid4().hex)[:6]  
            self.batch_number = f"BATCH-{timestamp}-{unique_id}"

        if not self.id:
            self.remaining_quantity = self.quantity

        super().save(*args, **kwargs)

    def __str__(self):
        return f'BATCH:{self.stationary_product}:unit price:{self.unit_price}:available{self.quantity}'


class StationaryPurchaseOrder(models.Model):
    user = models.ForeignKey(CustomUser,on_delete=models.CASCADE,null=True,blank=True)
    order_id = models.CharField(max_length=50)     
    total_amount = models.DecimalField(max_digits=15, decimal_places=2,null=True, blank=True) 
    supplier = models.ForeignKey(Supplier,on_delete=models.CASCADE)
    invoice_number = models.CharField(max_length=50,null=True,blank=True)   
    invoice_file = models.FileField(upload_to='stationary_invoices',null=True, blank=True)
    APPROVAL_STATUS_CHOICES = [
    ('SUBMITTED', 'Submitted'),
     ('REVIEWED', 'Reviewed'),
    ('APPROVED', 'Approved'),   
    ('CANCELLED','Cancelled'),
        ]
    approval_status = models.CharField(max_length=20, choices=APPROVAL_STATUS_CHOICES, default='SUBMITTED',null=True, blank=True) 
    PURCHASE_STATUS_CHOICES = [
    ('COMPLETED', 'Completed'),
    ('IN-PROCESS', 'In Process'),
    ('CANCELLED','Cancelled'),
        ]
    status = models.CharField(max_length=20, choices= PURCHASE_STATUS_CHOICES, default='IN-PROCESS',null=True, blank=True) 
    approved_by = models.ForeignKey(Employee,on_delete=models.CASCADE,null=True,blank=True,related_name='stationary_purchase_order_user')
    request_submission_date = models.DateField(default=timezone.now)
    approved_on = models.DateField(default=timezone.now)
    order_date = models.DateField(default=timezone.now)

    approval_data = models.JSONField(default=dict,null=True,blank=True)
    requester_approval_status = models.CharField(max_length=20, null=True, blank=True)
    reviewer_approval_status = models.CharField(max_length=20, null=True, blank=True)
    approver_approval_status = models.CharField(max_length=20, null=True, blank=True)

    Requester_remarks=models.TextField(null=True,blank=True)
    Reviewer_remarks=models.TextField(null=True,blank=True)
    Approver_remarks=models.TextField(null=True,blank=True)
    created_at = models.DateField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        permissions = [
            ("can_request", "can request"),
            ("can_review", "Can review"),
            ("can_approve", "Can approve"),
        ]


    def save(self, *args, **kwargs): 
        if not self.order_id:
            timestamp = timezone.now().strftime('%Y%m%d%H%M%S')
            unique_id = str(uuid.uuid4().hex)[:6]  
            self.order_id = f"PID-{timestamp}-{unique_id}"
        super().save(*args, **kwargs)

    def __str__(self):
        return f'{self.order_id}-amount{self.total_amount}'
   

class StationaryPurchaseItem(models.Model):
    stationary_purchase_order = models.ForeignKey(StationaryPurchaseOrder,on_delete=models.CASCADE,null=True,blank=True,related_name='stationary_request_order')
    user = models.ForeignKey(CustomUser,on_delete=models.CASCADE,null=True,blank=True)
    stationary_category = models.ForeignKey(StationaryCategory, on_delete=models.CASCADE,null=True,blank=True)
    stationary_product = models.ForeignKey(StationaryProduct, on_delete=models.CASCADE)
    batch = models.ForeignKey(StationaryBatch, on_delete=models.CASCADE,null=True,blank=True)
    quantity = models.PositiveIntegerField() 
    purchase_date = models.DateField(auto_now_add=True)    
    created_at = models.DateField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
  

    def __str__(self):
        return f"Purchased {self.quantity} of {self.stationary_product.name} on {self.purchase_date}"



class StationaryUsageRequestOrder(models.Model):
    user = models.ForeignKey(CustomUser,on_delete=models.CASCADE,null=True,blank=True)
    request_id = models.CharField(max_length=50)       
    department = models.ForeignKey(Department,on_delete=models.CASCADE)
    STATUS_CHOICES = [
        ('Pending', 'Pending'),
        ('Approved', 'Approved'),
        ('Rejected', 'Rejected'),
    ]
    total_amount = models.DecimalField(max_digits=10,decimal_places=2,null=True,blank=True)
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default='Pending')
    approved_by = models.CharField(max_length=255, blank=True, null=True) 
    approved_on = models.DateField(default=now)
    
    approval_data = models.JSONField(default=dict,null=True,blank=True)
    requester_approval_status = models.CharField(max_length=20, null=True, blank=True)
    reviewer_approval_status = models.CharField(max_length=20, null=True, blank=True)
    approver_approval_status = models.CharField(max_length=20, null=True, blank=True)

    Requester_remarks=models.TextField(null=True,blank=True)
    Reviewer_remarks=models.TextField(null=True,blank=True)
    Approver_remarks=models.TextField(null=True,blank=True)
    created_at = models.DateField(auto_now_add=True)
    updated_at = models.DateField(auto_now=True)

    class Meta:
        permissions = [
            ("can_request", "can request"),
            ("can_review", "Can review"),
            ("can_approve", "Can approve"),
        ]
 

    def save(self, *args, **kwargs): 
        if not self.request_id:
            timestamp = timezone.now().strftime('%Y%m%d%H%M%S')
            unique_id = str(uuid.uuid4().hex)[:6]  
            self.request_id = f"PID-{timestamp}-{unique_id}"
        super().save(*args, **kwargs)


class StationaryUsageRequestItem(models.Model):
    user = models.ForeignKey(CustomUser,on_delete=models.CASCADE,null=True,blank=True)
    stationary_usage_request_order=models.ForeignKey(StationaryUsageRequestOrder,on_delete=models.CASCADE,related_name='usage_order')
    stationary_category = models.ForeignKey(StationaryCategory, on_delete=models.CASCADE,null=True,blank=True) 
    stationary_product = models.ForeignKey(StationaryProduct, on_delete=models.CASCADE) 
    batch= models.ForeignKey(StationaryBatch,on_delete=models.CASCADE,null=True,blank=True,related_name='batch_usage')
    quantity = models.PositiveIntegerField() 
    created_at = models.DateField(auto_now_add=True)
    updated_at = models.DateField(auto_now=True)
   

    def __str__(self):
        return f"{self.quantity}nos of {self.stationary_product.name}"




class StationaryInventory(models.Model):
    user = models.ForeignKey(CustomUser, on_delete=models.CASCADE, null=True, blank=True)
    stationary_product = models.ForeignKey(StationaryProduct, on_delete=models.CASCADE)
    warehouse = models.ForeignKey(Warehouse, on_delete=models.CASCADE)
    location = models.ForeignKey(Location, on_delete=models.CASCADE)
    quantity = models.PositiveIntegerField(default=0)
    batch = models.ForeignKey(StationaryBatch,on_delete=models.CASCADE,null=True,blank=True,related_name='batch_inventory')
    reorder_level = models.PositiveIntegerField(default=10,null=True,blank=True)
    remarks = models.TextField(null=True,blank=True)
    created_at = models.DateField(auto_now_add=True)
    updated_at = models.DateField(auto_now=True)
  
        
    def __str__(self):
        return f"{self.stationary_product.name} - {self.quantity}-{self.warehouse}"



class StationaryInventoryTransaction(models.Model):
    user = models.ForeignKey(CustomUser, on_delete=models.CASCADE, null=True, blank=True)
    stationary_inventory = models.ForeignKey(StationaryInventory,on_delete=models.CASCADE)
    stationary_product = models.ForeignKey(StationaryProduct, on_delete=models.CASCADE)
    batch = models.ForeignKey(StationaryBatch,on_delete=models.CASCADE,null=True,blank=True,related_name='batch_inventory_transaction')
    warehouse = models.ForeignKey(Warehouse, on_delete=models.CASCADE)
    location = models.ForeignKey(Location, on_delete=models.CASCADE)
    quantity = models.PositiveIntegerField(default=0)
    stationary_purchase_order = models.ForeignKey(StationaryPurchaseOrder, related_name='stationary_purchase_transactions', null=True, blank=True, on_delete=models.CASCADE)
    stationary_usage_request_order = models.ForeignKey(StationaryUsageRequestOrder, related_name='stationary_usage_transactions', null=True, blank=True, on_delete=models.CASCADE)
    transaction_type = models.CharField(max_length=50, choices=[('inbound','Inbound'),('outbound','Outbound')])
    created_at = models.DateField(auto_now_add=True)
    updated_at = models.DateField(auto_now=True)
  

    def __str__(self):
        return f"{self.transaction_type}-{self.stationary_product.name} - {self.quantity}-{self.warehouse}"



#############################################################################################

class OfficeAdvance(models.Model):
    advance_id = models.CharField(max_length=50,null=True, blank=True)
    user = models.ForeignKey(CustomUser, on_delete=models.CASCADE, null=True, blank=True)
    PURPOSE_TYPE = [
        ('Office Supplies', 'Office Supplies'),
        ('Travel', 'Travel'),
        ('Utilities', 'Utilities'),
        ('Other', 'Other')
    ]
    purpose=models.CharField(max_length=150,choices=PURPOSE_TYPE)
    amount = models.DecimalField(max_digits=15,decimal_places=2)
    estimated_reimbursement_date = models.DateField()
    STATUS_CHOICES = [
        ('Pending', 'Pending'),
        ('Approved', 'Approved'),
        ('Rejected', 'Rejected'),
    ]
   
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default='Pending',null=True,blank=True)
    approved_by = models.ForeignKey(CustomUser, on_delete=models.SET_NULL, related_name='approved_advances', null=True, blank=True)
    approved_on = models.DateField(default=timezone.now)
    created_at = models.DateField(auto_now_add=True)
    updated_at = models.DateField(auto_now=True)

    def save(self, *args, **kwargs):
        if not self.advance_id:
            timestamp = timezone.now().strftime('%Y%m%d%H%M%S')
            unique_id = str(uuid.uuid4().hex)[:6]
            self.advance_id = f"PID-{timestamp}-{unique_id}"
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.advance_id}-{self.user.username} - ${self.amount}"
    

from django.db.models import Sum

class ExpenseSubmissionOrder(models.Model):
    user = models.ForeignKey(CustomUser, on_delete=models.CASCADE, null=True, blank=True)
    submission_id = models.CharField(max_length=50)
    total_amount = models.DecimalField(max_digits=10, decimal_places=2,null=True, blank=True)
    has_advance = models.BooleanField(default=False)
    advance_ref = models.ForeignKey(OfficeAdvance,on_delete=models.CASCADE,null=True,blank=True)
    submitted_by = models.ForeignKey(Employee, on_delete=models.CASCADE,related_name='expense_submission_user',null=True,blank=True)
    submission_date = models.DateField()
    approved_by = models.ForeignKey(CustomUser, on_delete=models.SET_NULL, related_name='user_approved_advances', null=True, blank=True)
    approved_on = models.DateField(null=True,blank=True)
    status =models.CharField(max_length=30,choices=[('submitted','Submitted'),('approved','Approved')],default='submitted')
    created_at = models.DateField(auto_now_add=True)
    updated_at = models.DateField(auto_now=True)

    class Meta:
        unique_together = ('advance_ref',)
   
    def update_total_amount(self):       
        total = self.items_submitted.aggregate(Sum("amount"))["amount__sum"] or 0
        self.total_amount = total
        self.save(update_fields=["total_amount"])  

    def save(self, *args, **kwargs):
        if not self.submission_id:
            timestamp = timezone.now().strftime('%Y%m%d%H%M%S')
            unique_id = str(uuid.uuid4().hex)[:6]
            self.submission_id = f"PID-{timestamp}-{unique_id}"
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.submission_id} - ${self.total_amount}"


class ExpenseSubmissionItem(models.Model):
    user = models.ForeignKey(CustomUser,on_delete=models.CASCADE)   
    CATEGORY_CHOICES = [
        ('Office Supplies', 'Office Supplies'),
        ('Travel', 'Travel'),
        ('Utilities', 'Utilities'),
        ('Other', 'Other')
    ]
    submission_order = models.ForeignKey(ExpenseSubmissionOrder,on_delete=models.CASCADE,related_name='items_submitted')
    category = models.CharField(max_length=50, choices=CATEGORY_CHOICES)   
    amount = models.DecimalField(max_digits=10, decimal_places=2)    
    description = models.TextField(null=True,blank=True)      
    created_at = models.DateField(auto_now_add=True)
    updated_at = models.DateField(auto_now=True)

    def save(self, *args, **kwargs):     
        super().save(*args, **kwargs)
        self.submission_order.update_total_amount()

    def delete(self, *args, **kwargs):
        submission_order = self.submission_order
        super().delete(*args, **kwargs)
        submission_order.update_total_amount()

    def __str__(self):
        return f"{self.category} - ${self.amount}"

#################################################################################


class MeetingOrder(models.Model):
    user = models.ForeignKey(CustomUser, on_delete=models.CASCADE, null=True, blank=True)
    order_id=models.CharField(max_length=50)
    title = models.CharField(max_length=255)
    order_by = models.ForeignKey(Employee,on_delete=models.CASCADE,null=True,blank=True,related_name='meeting_order_user')   
    meeting_type=models.CharField(max_length=50,choices=[('internal','Internal'),('external','External')]) 
    organization = models.CharField(max_length=100,null=True,blank=True)
    meeting_place = models.CharField(max_length=255,null=True,blank=True)
    description = models.TextField(null=True,blank=True)
    meeting_date = models.DateField()
    meeting_start_time = models.TimeField(null=True,blank=True)
    meeting_end_time = models.TimeField(null=True,blank=True)
    created_at = models.DateField(auto_now_add=True)
    updated_at = models.DateField(auto_now=True)  

    def save(self, *args, **kwargs): 
        if not self.order_id:
            timestamp = timezone.now().strftime('%Y%m%d%H%M%S')
            unique_id = str(uuid.uuid4().hex)[:6]  
            self.order_id = f"PID-{timestamp}-{unique_id}"
        super().save(*args, **kwargs)  
    
    def __str__(self):
        return f"{self.title} - date:{self.meeting_date} at {self.meeting_start_time}"
    

class Attendees(models.Model):
    meeting_order = models.ForeignKey(MeetingOrder,on_delete=models.CASCADE)
    user = models.ForeignKey(CustomUser, on_delete=models.CASCADE, null=True, blank=True)
    name = models.ForeignKey(Employee,on_delete=models.CASCADE,related_name='meeting_attendees')  
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateField(auto_now=True) 

    def __str__(self):
        return self.name



class MeetingRoom(models.Model):
    user = models.ForeignKey(CustomUser, on_delete=models.CASCADE, null=True, blank=True)
    name = models.CharField(max_length=255, unique=True)
    capacity = models.PositiveIntegerField()
    location = models.CharField(max_length=255, blank=True, null=True)
    is_available = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateField(auto_now=True) 
    
    def __str__(self):
        return f"{self.name} ({self.capacity} people)"




class MeetingRoomBooking(models.Model):
    user = models.ForeignKey(CustomUser, on_delete=models.CASCADE, null=True, blank=True)
    STATUS_CHOICES = [('Pending', 'Pending'), ('Confirmed', 'Confirmed'), ('Cancelled', 'Cancelled')]

    room = models.ForeignKey(MeetingRoom, on_delete=models.CASCADE,related_name='meeting_room_bookings')
    meeting_ref= models.ForeignKey(MeetingOrder,on_delete=models.CASCADE,null=True,blank=True,help_text='Optional')
    booked_by = models.ForeignKey(Employee, on_delete=models.CASCADE,related_name='meeting_room_booking_user')
    purpose = models.TextField()
    date = models.DateField()
    start_time = models.TimeField()
    end_time = models.TimeField()
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default='Pending')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateField(auto_now=True) 

    class Meta:
        unique_together = ('room', 'date', 'start_time', 'end_time')  # Prevents double booking

    def __str__(self):
        return f"{self.room} - {self.date} ({self.start_time} to {self.end_time}) by {self.booked_by}"




class ITSupportTicket(models.Model):
    STATUS_CHOICES = [('Open', 'Open'), ('In Progress', 'In Progress'), ('Closed', 'Closed')]

    ticket_id = models.CharField(max_length=30)
    user= models.ForeignKey(CustomUser, on_delete=models.CASCADE)
    issue = models.TextField()
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='Open')  
    solution_description = models.TextField(null=True, blank=True)
    resolved_by = models.ForeignKey(CustomUser, on_delete=models.SET_NULL, null=True, blank=True, related_name='resolved_tickets')
    resolved_date = models.DateField(default=timezone.now)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
   
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateField(auto_now=True) 
   
    def save(self, *args, **kwargs): 
        if not self.ticket_id:
            timestamp = timezone.now().strftime('%Y%m%d%H%M%S')
            unique_id = str(uuid.uuid4().hex)[:6]  
            self.ticket_id = f"TICKET-{timestamp}-{unique_id}"
        super().save(*args, **kwargs)  
  
    def __str__(self):
        return f"{self.ticket_id} - {self.status}"


import qrcode
from io import BytesIO
from django.core.files import File
from django.utils import timezone
from django.core.files.base import ContentFile


class VisitorIDCard(models.Model):
    card_number = models.CharField(max_length=50, unique=True)
    issue_date = models.DateTimeField(default=timezone.now)
    expiry_date = models.DateTimeField(null=True, blank=True)

    STATUS_CHOICES = [
        ('active', 'Active'),
        ('inactive', 'Inactive'),
        ('lost', 'Lost'),
        ('expired', 'Expired'),
        ('idle', 'Idle'),
        ('in_use', 'In Use'),
    ]
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='active')
    printed = models.BooleanField(default=False)
    qr_code = models.ImageField(upload_to='visitor_qrcodes/', null=True, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"ID Card {self.card_number}"

    def save(self, *args, **kwargs):
        if not self.card_number:
            # Automatically generate unique card number
            last_card = VisitorIDCard.objects.order_by('-id').first()
            next_number = 1 if not last_card else last_card.id + 1
            self.card_number = f"VC-{next_number:05d}"

        # Generate QR code
        qr_data = f"Visitor Card: {self.card_number}"
        qr_img = qrcode.make(qr_data)
        buffer = BytesIO()
        qr_img.save(buffer, format='PNG')
        file_name = f"qr_{self.card_number}.png"
        self.qr_code.save(file_name, ContentFile(buffer.getvalue()), save=False)

        super().save(*args, **kwargs)



class VisitorGroup(models.Model):
    user = models.ForeignKey(CustomUser, on_delete=models.CASCADE, null=True, blank=True)
    company = models.CharField(max_length=255)
    address=models.CharField(max_length=255,null=True,blank=True)
    purpose = models.TextField(null=True, blank=True)
    expected_check_in_time = models.DateTimeField(null=True, blank=True,help_text='Optional')
    check_in = models.DateTimeField(null=True, blank=True)
    check_out = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    
    class Meta:
            ordering = ['-created_at']

    def __str__(self):
        return f"Visitors from {self.company} - {self.purpose}"
    


class VisitorLog(models.Model):
    user = models.ForeignKey(CustomUser, on_delete=models.CASCADE, null=True, blank=True)  
    company = models.ForeignKey(VisitorGroup, on_delete=models.CASCADE, related_name="visitors", null=True, blank=True,
        help_text='Please choose company to add member if any')
    visitor_type = models.CharField(max_length=100, choices=[('local', 'Local'), ('foreigner', 'Foreigner')], null=True, blank=True)
    name = models.CharField(max_length=255)

    designation = models.CharField(max_length=255, null=True, blank=True)
    id_card = models.ForeignKey(VisitorIDCard,on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='assigned_visitors',
        help_text='Select the ID card issued to this visitor'
    )
    phone = models.IntegerField(null=True, blank=True)
    address =models.CharField(max_length=255,null=True,blank=True)
    photo = models.ImageField(upload_to="visitor_photo", null=True, blank=True)   
    check_in = models.DateTimeField(null=True, blank=True)
    check_out = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.name} ({self.company.company if self.company else 'Individual'})"


class OfficeDocument(models.Model): 
    user = models.ForeignKey(CustomUser, on_delete=models.CASCADE, null=True, blank=True)
    document_type = models.CharField(max_length=150,
        choices=[
        ('agreement', 'Agreement Paper'),       
        ('licencing', 'Licence Paper'),     
        ('Meeting', 'Meeting Papers'),
        ('govt-circular', 'Govt. Circlular'),       
        ('employee-documents', 'Employee Related Docs'),     
        ('general', 'General'),
    ],
    null=True,
    blank=True,
    default='General'
)
    title = models.CharField(max_length=255,null=True, blank=True)
    company = models.ForeignKey(Company,on_delete=models.CASCADE,related_name='company_doc',null=True, blank=True)
    department = models.ForeignKey(Department,on_delete=models.CASCADE,related_name='department_doc')
    file = models.FileField(upload_to='Scan_documents/')
    uploaded_by = models.ForeignKey(Employee, on_delete=models.CASCADE,related_name='office_doc_upload_user',null=True, blank=True)
    upload_date = models.DateTimeField(auto_now_add=True)
    created_at = models.DateField(auto_now_add=True)
    updated_at = models.DateField(auto_now=True)
    
    def __str__(self):
        return self.title

