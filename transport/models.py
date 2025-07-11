from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone
from inventory.models import InventoryTransaction 
from decimal import Decimal
from accounts.models import CustomUser
from datetime import datetime


class Transport(models.Model):
    vehicle_ownership = models.CharField(max_length=150,choices=[('OWN_TRANSPORT','Own Transport'),('OUT-SOURCE','OutSource')],null=True, blank=True)
    vehicle_owner_name= models.CharField(max_length=50, default='None')
    vehilce_owner_mobile_number = models.CharField(max_length=50, default='None')
    vehicle_owner_address = models.TextField(default='None')
    vehicle_owner_company_name = models.CharField(max_length=50, default='None')
    vehicle_kilometer_commit_per_liter = models.DecimalField(max_digits=10, decimal_places=2,null=True, blank=True) 
    vehicle_money_commit_per_kilometer_gasoline = models.DecimalField(max_digits=10, decimal_places=2,null=True, blank=True)
    vehicle_money_commit_per_kilometer_CNG = models.DecimalField(max_digits=10, decimal_places=2,null=True, blank=True)
    vehicle_max_kilometer_CNG = models.DecimalField(max_digits=10, decimal_places=2,null=True, blank=True)

    vehicle_registration_date=models.DateField(null=True,blank=True)  
    vehicle_code = models.CharField(max_length=50,unique=True, null=True, blank=True)
    vehicle_registration_number = models.CharField(max_length=50,unique=True,null=True,blank=True)
    vehicle_initial_mileage = models.CharField(max_length=50, null=True,blank=True)
    vehicle_mileage = models.CharField(max_length=50, null=True,blank=True)
    vehicle_description=models.TextField(null=True,blank=True)
    vehicle_image=models.ImageField(upload_to='vehicle',null=True,blank=True)  
    vehicle_supporting_documents = models.FileField(upload_to='vehicle_supporting_documents/', null=True, blank=True)
    capacity = models.PositiveIntegerField()  
    location = models.CharField(max_length=255,null=True,blank=True)     
    joining_date = models.DateField(null=True, blank=True)
    
    vehicle_body_overtime_rate = models.DecimalField(max_digits=10, decimal_places=2,null=True, blank=True)
    vehicle_driver_overtime_rate = models.DecimalField(max_digits=10, decimal_places=2,null=True, blank=True)
    
   
    
    vehicle_fuel_type_choices=[
        ('diesel','diesel'),
        ('octane', 'octane'),
        ('cng','cng'),
        ('taka','taka'),
    ]
    vehicle_fuel_type = models.CharField(max_length=50, choices=vehicle_fuel_type_choices, default='None')    
    vehicle_fuel_unit_price = models.DecimalField(max_digits=15,decimal_places=2,null=True,blank=True)

    vehicle_brand_choices=[
        ('toyota_pickup_single','toyota_pickup_single'),
        ('nissan_pickup_single', 'nissan_pickup_single'),
        ('tata_pickup_single','tata_pickup_single'),
        ('toyota_pickup_double','toyota_pickup_double'),
        ('nissan_pickup_double', 'nissan_pickup_double'),
        ('tata_pickup_double','tata_pickup_double'),
        ('toyota_private_car','toyota_private_car'),
        ('toyota_microbus','toyota_microbus'),
        ('PRIVAT-CAR','Private Car'),
        ('MICROBUS','Microbus'),
        ('BUS','Bus'),
        ('MINITRUCK','Mini Truck'),
        ('TRUCK','Truck')
    ]
    vehicle_brand_name = models.CharField(max_length=50, choices= vehicle_brand_choices,default='None')
    vehicle_rent = models.DecimalField(max_digits=10, decimal_places=2,null=True, blank=True)
            
    driver_name = models.CharField(max_length=150,null=True, blank=True)
    driver_phone = models.IntegerField(null=True, blank=True)
    supervisor_phone = models.IntegerField(null=True, blank=True)
    supervisor_name = models.CharField(null=True, blank=True)   
    last_maintenance_date = models.DateField(null=True, blank=True)
    status = models.CharField(max_length=50,
    choices=[
        ('AVAILABLE','Available'),
        ('IN-USE','In use'),
        ('PENALIZED','Penalized'),
        ('BOOKED','Booked'),
        ('FAULTY','Faulty'),
        ('COMPLETED', 'Completed'),      
        ],null=True,blank=True)  
    created_at = models.DateField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def save(self, *args, **kwargs):
        if not self.vehicle_code: 
            last_vehicle = Transport.objects.order_by('-id').first()  
            if last_vehicle and last_vehicle.vehicle_code:
                try:
                    last_code = int(last_vehicle.vehicle_code)
                    new_code = f"{last_code + 1:04d}" 
                except ValueError:  
                    new_code = "0001"
            else:
                new_code = "0001"

            self.vehicle_code = new_code
        super().save(*args, **kwargs) 
   


    def __str__(self):
        return f"{self.vehicle_code}-{self.vehicle_registration_number}"


import uuid

class TransportRequest(models.Model):
    request_code = models.CharField(max_length=50, null=True,blank=True)
    STATUS_CHOICES = [
        ('PENDING', 'Pending'),
        ('APPROVED', 'Approved'),
        ('BOOKED', 'Booked'),
        ('COMPLETED', 'Completed'),
        ('IN-USE', 'In use'),
        ('PENALIZED', 'Penalized'),
        ('REJECTED', 'Rejected'),
    ]
    TRANSPORT_TYPE_CHOICES = [
        ('Goods', 'Goods'),
        ('Staff', 'Staff'),
    ]

    staff = models.ForeignKey(CustomUser, on_delete=models.CASCADE,null=True,blank=True) 
    vehicle = models.ForeignKey(Transport, on_delete=models.CASCADE,related_name='transport_request')  
    transport_type = models.CharField(max_length=10, choices=TRANSPORT_TYPE_CHOICES,default='Staff')
    item_description = models.TextField(null=True, blank=True) 
    request_datetime = models.DateTimeField(null=True,blank=True)  
    return_datetime = models.DateTimeField(null=True,blank=True)   
    purpose = models.CharField(max_length=255,null=True,blank=True)  
    status = models.CharField(choices=STATUS_CHOICES, max_length=50, default='PENDING')
    actual_return = models.DateTimeField(default=timezone.now)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def save(self, *args, **kwargs):       
        if not self.request_code:
            self.request_code= f"RC-{uuid.uuid4().hex[:8].upper()}"
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.vehicle.vehicle_registration_number} on {self.request_datetime}"

    def approve(self):
        self.status = 'APPROVED'
        self.save()

    def reject(self):
        self.status = 'REJECTED'
        self.save()





class ManagerApproval(models.Model):
    approval_code = models.CharField(max_length=50,null=True,blank=True)
    request = models.ForeignKey(TransportRequest, on_delete=models.CASCADE,related_name='request_approval')
    manager = models.ForeignKey(CustomUser, on_delete=models.CASCADE) 
    approved_at = models.DateTimeField(default=timezone.now)
    status=models.CharField(max_length=50,choices=[('APPROVED','Approved'),('REJECTED','Rejected')],null=True,blank=True)
    rejection_reason = models.TextField(null=True, blank=True)
    created_at = models.DateField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def save(self, *args, **kwargs):       
        if not self.approval_code:
            self.approval_code= f"RC-{uuid.uuid4().hex[:8].upper()}"
        super().save(*args, **kwargs)

    def approve_request(self):
        self.request.approve()
        self.approved_at = timezone.now()
        self.save()

    def reject_request(self, reason):
        self.request.reject()
        self.rejection_reason = reason
        self.save()



class TransportExtension(models.Model):
    booking = models.ForeignKey(TransportRequest, on_delete=models.CASCADE,related_name='time_extension')
    requested_until = models.DateTimeField(null=True, blank=True)
    extended_until = models.DateTimeField(null=True, blank=True)
    reason = models.CharField(max_length=255,blank=True, null=True)
    requested_at = models.DateTimeField(default=timezone.now)
    approved_by = models.ForeignKey(CustomUser,on_delete=models.CASCADE,null=True,blank=True)
    approval_status=models.CharField(max_length=50,choices=[('APPROVED','Approved'),('CANCELLED','Cancelled'),('PENDING','Pending')],default='PENDING')
    cancellation_reason=models.CharField(max_length=255,null=True,blank=True)
    created_at = models.DateField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

        
    def save(self,*args,**kwargs):
        if self.extended_until:
            self.booking.return_datetime = self.extended_until
            self.booking.save()
   
        super().save(*args,*kwargs)

    def __str__(self):
        return f"Extension for {self.booking} until {self.extended_until}"


class TransportUsage(models.Model):
    transport_usage_code = models.CharField(max_length=50,null=True,blank=True)
    booking = models.ForeignKey(TransportRequest, on_delete=models.CASCADE, related_name='booking_usage')
    status = models.CharField(max_length=50, choices=[
        ('IN-USE','In use'),
        ('COMPLETED', 'Completed'),
        ('OVERDUE', 'Overdue'),
    ], default='IN-USE')

 
    travel_date = models.DateField(null=True, blank=True)
    start_time=models.TimeField(null=True, blank=True)
    end_time = models.TimeField(null=True, blank=True)
    start_location = models.CharField(max_length=255, null=True, blank=True)
    end_location = models.CharField(max_length=255, null=True, blank=True)   
    start_reading=models.FloatField(null=True, blank=True)
    end_reading=models.FloatField(null=True, blank=True)

    running_hours = models.FloatField(default=None, null=True, blank=True)
    overtime_hours = models.FloatField(default=None, null=True, blank=True)

    kilometer_cost = models.DecimalField(max_digits=20, decimal_places=2, null=True, blank=True)
    fuel_consumed = models.DecimalField(max_digits=20, decimal_places=2, null=True, blank=True)
    fuel_balance = models.DecimalField(max_digits=20, decimal_places=2, null=True, blank=True)
    fuel_cost = models.DecimalField(max_digits=20, decimal_places=2, null=True, blank=True)
    vehicle_rent_per_day = models.DecimalField(max_digits=20, decimal_places=2, null=True, blank=True)
    weekend_status = models.CharField(max_length=50,null=True,blank=True) 
   
    kilometer_cost_CNG = models.DecimalField(max_digits=20, decimal_places=2, null=True, blank=True)
    kilometer_cost_gasoline = models.DecimalField(max_digits=20, decimal_places=2, null=True, blank=True) 

    kilometer_run = models.DecimalField(max_digits=20, decimal_places=2, null=True, blank=True)
    fuel_consumed = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    toll = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    other_cost = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    total_cost_incurred = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)   
    weekend_status = models.CharField(max_length=50,null=True,blank=True) 
    created_at = models.DateField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
   
    def save(self, *args, **kwargs):
        if not self.transport_usage_code:
            self.transport_usage_code= f"TUC-{uuid.uuid4().hex[:8].upper()}"

        if self.end_reading is not None and self.start_reading is not None:
            try:
                self.kilometer_run = Decimal(self.end_reading) - Decimal(self.start_reading)                
                if self.booking.vehicle.vehicle_kilometer_commit_per_liter:
                    self.fuel_consumed = self.kilometer_run / Decimal(self.booking.vehicle.vehicle_kilometer_commit_per_liter)
                
             
                if self.booking.vehicle.vehicle_fuel_unit_price is not None:
                    self.fuel_cost = self.fuel_consumed * Decimal(self.booking.vehicle.vehicle_fuel_unit_price)
                else:
                    self.fuel_cost = None
                
                if self.kilometer_run is not None:
                    if self.kilometer_run <= Decimal(self.booking.vehicle.vehicle_max_kilometer_CNG):
                        self.kilometer_cost_CNG = Decimal(self.kilometer_run) * Decimal(self.booking.vehicle.vehicle_money_commit_per_kilometer_CNG)
                        self.kilometer_cost_gasoline = Decimal(0.0)
                        self.kilometer_cost= self.kilometer_cost_CNG + self.kilometer_cost_gasoline
                    else:
                        self.kilometer_cost_CNG = Decimal(self.booking.vehicle.vehicle_max_kilometer_CNG) * Decimal(self.booking.vehicle.vehicle_money_commit_per_kilometer_CNG)
                        self.kilometer_cost_gasoline = Decimal(self.kilometer_run - self.booking.vehicle.vehicle_max_kilometer_CNG) * Decimal(self.booking.vehicle.vehicle_money_commit_per_kilometer_gasoline)
                        self.kilometer_cost = self.kilometer_cost_CNG + self.kilometer_cost_gasoline
                        self.kilometer_cost= self.kilometer_cost_CNG + self.kilometer_cost_gasoline
            except:
                pass
        
     
        start_datetime = datetime.combine(self.travel_date, self.start_time)
        end_datetime = datetime.combine(self.travel_date, self.end_time)

        running_hours_timedelta = end_datetime - start_datetime
        self.running_hours = running_hours_timedelta.total_seconds() / 3600
            
        if self.travel_date:
            if self.travel_date.weekday() in [4, 5]:
                self.weekend_status = 'weekend'
            else:
                self.weekend_status = 'weekday'       
                       
        self.vehicle_rent_per_day = self.booking.vehicle.vehicle_rent / 30

        if self.toll and self.other_cost is None:            
            self.total_cost_incurred = self.toll + self.fuel_cost +self.kilometer_cost
        elif self.other_cost and self.toll is None:
            self.total_cost_incurred = self.fuel_cost + self.other_cost + self.kilometer_cost
        elif self.other_cost and self.toll:
            self.total_cost_incurred = self.fuel_cost + self.other_cost + self.toll + self.kilometer_cost
        else:
            self.total_cost_incurred = self.kilometer_cost        

        super(TransportUsage, self).save(*args, **kwargs)

    def __str__(self):
        return self.booking.vehicle.vehicle_registration_number




class BookingHistory(models.Model):    
    booking = models.OneToOneField(TransportRequest,on_delete=models.CASCADE,related_name='history_request',null=True, blank=True)
    transport_used = models.ForeignKey(Transport, on_delete=models.CASCADE,null=True, blank=True)
    staff = models.ForeignKey(CustomUser, on_delete=models.CASCADE,null=True, blank=True)
    booked_at = models.DateTimeField(default=timezone.now,null=True, blank=True)
    created_at = models.DateField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    def save(self, *args, **kwargs):   
        if self.booking.status == 'COMPLETED':
            self.booked_at = self.booking.request_datetime           
        super(BookingHistory, self).save(*args, **kwargs)
    
    def __str__(self):
        return f"Booking by {self.staff.username} using {self.transport_used.vehicle_code} on {self.booked_at}"


class Penalty(models.Model):
    staff = models.ForeignKey(CustomUser, on_delete=models.CASCADE,null=True, blank=True)
    transport_request = models.ForeignKey(TransportRequest, on_delete=models.CASCADE,related_name='penalty')
    penalty_amount = models.DecimalField(max_digits=10, decimal_places=2,blank=True, null=True)
    issued_at = models.DateTimeField(auto_now_add=True)
    reason = models.TextField(blank=True, null=True)   
    payment_status = models.BooleanField(default=False)   
    created_at = models.DateField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.transport_request} of amount {self.penalty_amount}"


class PenaltyPayment(models.Model):
    staff = models.ForeignKey(CustomUser, on_delete=models.CASCADE,null=True, blank=True)
    penalty = models.ForeignKey(Penalty, on_delete=models.CASCADE,related_name='penalty_payment')
    paid_amount = models.DecimalField(max_digits=10, decimal_places=2,blank=True, null=True)
    payment_doc =models.ImageField(upload_to='Penalty_payment',null=True,blank=True)
    paid_at = models.DateTimeField(default=timezone.now)
    created_at = models.DateField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Paid amount {self.paid_amount}"



class FuelPumpDatabase(models.Model):  
    pump_code = models.CharField(max_length=50,null=True,blank=True) 
    fuel_pump_name = models.CharField(max_length=100,null=True,blank=True)
    fuel_pump_id = models.CharField(max_length=50, default='None',null=True,blank=True)  
    fuel_pump_company_name = models.CharField(max_length=100,null=True,blank=True)
    fuel_pump_phone = models.CharField(max_length=100,null=True,blank=True)
    fuel_pump_email = models.EmailField(null=True,blank=True)
    fuel_pump_address = models.TextField(null=True,blank=True)     
    pump_type_choices=[
        ('prepaid','prepaid'),
        ('postpaid','postpaid')
    ]
              
   
    fuel_pump_type = models.CharField(max_length=100,choices=pump_type_choices,null=True,blank=True)
    diesel_rate = models.DecimalField(max_digits=10,decimal_places=2,null=True,blank=True)
    petrol_rate = models.DecimalField(max_digits=10,decimal_places=2,null=True,blank=True)
    octane_rate = models.DecimalField(max_digits=10,decimal_places=2,null=True,blank=True)
    CNG_rate = models.DecimalField(max_digits=10,decimal_places=2,null=True,blank=True)
    LPG_rate = models.DecimalField(max_digits=10,decimal_places=2,null=True,blank=True)
    
    fuel_pump_supporting_documents = models.FileField(upload_to='fuel_pump_supporting_documents/', null=True, blank=True)
    advance_amount_given = models.DecimalField(max_digits=20,decimal_places=2,null=True,blank=True)
    contact_date = models.DateField(null=True,blank=True)    
    contact_period = models.DecimalField(max_digits=10, decimal_places=1,null=True,blank=True)
    created_at = models.DateField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def save(self, *args, **kwargs):
        if not self.pump_code:
            self.pump_code= f"PC-{uuid.uuid4().hex[:8].upper()}"
           
        super().save(*args, **kwargs) 
    
   
    def __str__(self):
        return self.fuel_pump_name
    

class FuelPumpPayment(models.Model):
    pump = models.ForeignKey(FuelPumpDatabase,related_name='fuel_pump_pay_data',on_delete=models.CASCADE)
    payment_amount =models.DecimalField(max_digits=15,decimal_places=2,null=True,blank=True)   
    payment_id = models.CharField(max_length=100, default='None',null=True,blank=True)
    payment_document = models.ImageField(upload_to="fuel_pump_payment", null=True,blank=True)
    paid_at=models.DateTimeField(default=timezone.now)
    created_at = models.DateField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    def save(self, *args, **kwargs):
        if not self.payment_id:
            self.payment_id= f"PAY-{uuid.uuid4().hex[:8].upper()}"
           
        super().save(*args, **kwargs) 
    
 


class FuelRefill(models.Model):   
    refil_code = models.CharField(max_length=50,null=True,blank=True)
    vehicle = models.ForeignKey(Transport, related_name='refills_info', on_delete=models.CASCADE)
    REFILL_CHOICES = [
        ('pump', 'pump'),
        ('local_purchase', 'Local Purchase')
    ]
    
    refill_type = models.CharField(max_length=20, choices=REFILL_CHOICES, default='pump')
   
    pump = models.ForeignKey(FuelPumpDatabase,related_name='vehicle_fuel_pump',on_delete=models.CASCADE,default=None,null=True,blank=True)
    user = models.ForeignKey(CustomUser, related_name='refill_requester_name', on_delete=models.CASCADE, null=True, blank=True)
    fuel_refill_code = models.CharField(max_length=50, default='None')
    refill_date = models.DateField(default=timezone.now)

    fuel_type_choices=[
        ('diesel','diesel'),
        ('octane','octane'),
        ('petrol','petrol'),
        ('CNG','CNG'),
        ('LPG','LPG')
    ]         
    fuel_type =models.CharField(max_length=100, choices=fuel_type_choices,null=True, blank=True, default='None')        
    fuel_rate = models.DecimalField(max_digits=10,decimal_places=2,null=True,blank=True)
    refill_amount = models.DecimalField(max_digits=10, decimal_places=2, default=0.0)
   
    fuel_cost = models.DecimalField(max_digits=15,decimal_places=2,null=True,blank=True)
   
    vehicle_kilometer_reading = models.DecimalField(max_digits=50, decimal_places=2, default=0.0)
    vehicle_kilometer_run = models.DecimalField(max_digits=20, decimal_places=2, default=0.0) 
    vehicle_fuel_consumed = models.DecimalField(max_digits=30, decimal_places=2, default=0.0)
    vehicle_fuel_balance = models.DecimalField(max_digits=30, decimal_places=2, default=0.0)
    vehicle_total_fuel_reserve = models.DecimalField(max_digits=30, decimal_places=2, default=0.0)
   
    refill_supporting_documents = models.FileField(upload_to='refill_supporting_documents/', null=True, blank=True)
    fuel_supplier_name = models.CharField(max_length=150,null=True,blank=True)                  
    fuel_supplier_phone = models.CharField(max_length=50, default='None')   
    fuel_supplier_address = models.TextField(default='None',null=True, blank=True)      
   
    created_at = models.DateField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    class Meta:
        unique_together = ('vehicle', 'refil_code')
   
    def save(self, *args, **kwargs):
        if not self.pk and not self.refil_code: 
            self.refil_code = f"RC-{uuid.uuid4().hex[:8].upper()}"
        super().save(*args, **kwargs)


        if self.refill_amount is not None and self.pump is not None:
            rate_mapping = {
                'diesel': self.pump.diesel_rate,
                'petrol': self.pump.petrol_rate,
                'octane': self.pump.octane_rate,
                'CNG': self.pump.CNG_rate,
                'LPG': self.pump.LPG_rate,
            }
            self.fuel_cost = self.refill_amount * rate_mapping.get(self.fuel_type, Decimal('0.0'))
        else:
            self.fuel_cost = self.refill_amount * self.fuel_rate

        last_refill = (
        FuelRefill.objects.filter(vehicle=self.vehicle)
        .exclude(id=self.id)  # Exclude current record
        .order_by('-refill_date')
        .first()
    )

        last_kilometer_reading = Decimal('0.0') if not last_refill else last_refill.vehicle_kilometer_reading or Decimal('0.0')
        print(last_refill,last_kilometer_reading)
               
        if last_refill:
            self.vehicle_kilometer_run = max(Decimal('0.0'), self.vehicle_kilometer_reading - last_kilometer_reading)               
        else:
            self.vehicle_kilometer_run = Decimal('0.0')   

        if self.vehicle.vehicle_kilometer_commit_per_liter and self.vehicle.vehicle_kilometer_commit_per_liter>0:
            self.vehicle_fuel_consumed = self.vehicle_kilometer_run / self.vehicle.vehicle_kilometer_commit_per_liter
                    
        if last_refill:
            self.vehicle_fuel_balance = last_refill.refill_amount - self.vehicle_fuel_consumed
            self.vehicle_total_fuel_reserve = self.refill_amount + self.vehicle_fuel_balance
        else:  
            self.vehicle_fuel_balance = self.refill_amount
            self.vehicle_total_fuel_reserve = self.refill_amount
        
       

        super().save(*args, **kwargs)


    def __str__(self):
            return self.vehicle.vehicle_registration_number





class Vehiclefault(models.Model):  
    vehicle_fault_id = models.CharField(max_length=50, default='None')    
    vehicle = models.ForeignKey(Transport, related_name='vehiclefault_info', on_delete=models.CASCADE,null=True, blank=True)
    vehicle_runnin_data = models.ForeignKey(TransportUsage, related_name='VehicleRuniningDataInfo', on_delete=models.CASCADE ,null=True, blank=True) 
    user = models.ForeignKey(CustomUser, related_name='vehicle_fault_user', on_delete=models.CASCADE, null=True, blank=True)
    fault_start_time = models.DateTimeField(default=timezone.now)    
    fault_stop_time = models.DateTimeField(default=timezone.now)  
    fault_duration_hours = models.FloatField(default=None, null=True, blank=True)
    fault_location = models.CharField(max_length=255, default='None',null=True, blank=True)
    fault_type_choices=[
        ('accident','accident'),
        ('engine_stop','engine_stop'),
        ('tyre_punchure','tyre_punchure'),
        ('others','others')
    ]
    fault_type = models.CharField(max_length=255,choices=fault_type_choices,default='None',null=True, blank=True)
    created_at = models.DateField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)


    def save(self, *args, **kwargs):     
        fault_hours = self.fault_stop_time - self.fault_start_time
        self.fault_duration_hours = fault_hours.total_seconds() / 3600      
        super(Vehiclefault, self).save(*args, **kwargs)

    def __str__(self):
        return self.vehicle.vehicle_registration_number


class VehicleRentalCost(models.Model):   
    vehicle = models.ForeignKey(Transport, related_name='vehiclerent_info', on_delete=models.CASCADE) 
    vehicle_rent_paid_id = models.CharField(max_length=50, default='None')   
    vehicle_rent_paid = models.FloatField(default=0.0, null=True, blank=True)
    vehicle_body_overtime_paid = models.FloatField(default=0.0, null=True, blank=True)
    vehicle_driver_overtime_paid =models.FloatField(default=0.0, null=True, blank=True)
    
    vehicle_kilometer_paid =models.FloatField(default=0.0, null=True, blank=True)
    vehicle_total_paid = models.FloatField(default=0.0, null=True, blank=True)   
   
    comments = models.TextField(max_length=50, default='None',null=True,blank=True)   
    paid_at=models.DateField(default=timezone.now)
    payment_document= models.ImageField(upload_to='Vehicle_payment',null=True,blank=True)
    created_at = models.DateField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
   
    def save(self, *args, **kwargs):
        if self.vehicle_rent_paid is not None and self.vehicle_kilometer_paid is not None  and self.vehicle_body_overtime_paid is not None and self.vehicle_driver_overtime_paid is not None:
            self.vehicle_total_paid = self.vehicle_rent_paid + self.vehicle_body_overtime_paid + self.vehicle_driver_overtime_paid + self.vehicle_kilometer_paid
                
        super().save(*args, **kwargs)      
    def __str__(self):
        return self.vehicle.vehicle_registration_number
  

class InsuranceDetails(models.Model):
    transport_request = models.OneToOneField(TransportRequest, on_delete=models.CASCADE,null=True, blank=True)
    insurance_provider = models.CharField(max_length=255,null=True, blank=True)
    policy_number = models.CharField(max_length=100,null=True, blank=True)  
    coverage_amount = models.DecimalField(max_digits=10, decimal_places=2) 
    insurance_status = models.BooleanField(default=False)  
    insurance_start_date = models.DateTimeField(null=True, blank=True) 
    insurance_end_date = models.DateTimeField(null=True, blank=True) 
    status = models.CharField(max_length=100,choices=[('CONFIRMED','Confirmed'),('CANCELLED','Cancelled')])
    insurance_document= models.ImageField(upload_to='insurance_paper',null=True,blank=True)
    created_at = models.DateField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Insurance for {self.transport_request} by {self.insurance_provider}"
