from django.db import models
from django.contrib.auth.models import User
from core.models import Employee
from django.utils import timezone
import uuid
import calendar
from core.models import Position,Department
from core.utils import DEPARTMENT_CHOICES


from sales.models import SaleOrder
from manufacture.models import MaterialsRequestOrder
from operations.models import OperationsDeliveryItem
from datetime import datetime
from accounts.models import CustomUser



class Team(models.Model):   
    department = models.ForeignKey(Department, on_delete=models.SET_NULL, null=True, blank=True,related_name='team_department')
    user=models.ForeignKey(CustomUser,on_delete=models.CASCADE,null=True,blank=True)   
    team_id = models.CharField(max_length=20, unique=True, editable=False)
    manager = models.ForeignKey(Employee,on_delete=models.CASCADE,related_name='team_manager',null=True,blank=True)
    name = models.CharField(max_length=100)
    description = models.TextField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def save(self, *args, **kwargs):
        if not self.team_id:
            self.team_id = f"TEAM-{uuid.uuid4().hex[:8].upper()}"
        super().save(*args, **kwargs)

    def __str__(self):
        return self.name

    def current_tasks(self):
        return Task.objects.filter(team=self, status='IN_PROGRESS')





PRIORITY_CHOICES = [
    ('LOW', 'Low'),
    ('MEDIUM', 'Medium'),
    ('HIGH', 'High'),
    ('CRITICAL', 'Critical'),
]

class Ticket(models.Model):
    user=models.ForeignKey(CustomUser,on_delete=models.CASCADE,null=True,blank=True)
    ticket_code = models.CharField(max_length=150, unique=True, editable=False)
    organization = models.CharField(max_length=100,null=True,blank=True,
    choices=[
        ('ROBI','Robi'),
        ('GP','Gp'),
        ('BANGLALINK','Banglalink'),
        ('TELETALK','Teletalk'),
        ('INTERNAL','Internal'),
    ])
    ticket_type=models.CharField(max_length=150,choices=[
        ('SALES','Sales'),
        ('OPERATIONS','Operation'), 
        ('PRODUCTION','Production'),        
        ('FINANCE','Finance'),
        ('BILLING','Billing'),
        ('TECHNICAL','Technical'),
        ('IT','IT'),
        ('GENERAL','General'),
        ('REPAIR-RETRUN','Repair return'),
        ],null=True,blank=True
        )
    
    sales=models.ForeignKey(SaleOrder,on_delete=models.CASCADE,null=True,blank=True,related_name='sales_ticket')
    repair_return=models.ForeignKey(SaleOrder,on_delete=models.CASCADE,null=True,blank=True,related_name='repair_return_ticket')            
    operations = models.ForeignKey( OperationsDeliveryItem,on_delete=models.CASCADE,null=True,blank=True)
    production = models.ForeignKey(MaterialsRequestOrder,on_delete=models.CASCADE,null=True,blank=True)
    subject = models.CharField(max_length=200,null=True,blank=True)
    description = models.TextField(blank=True, null=True)
    created_by = models.ForeignKey(CustomUser, on_delete=models.CASCADE, related_name="created_tickets",null=True,blank=True)    
    priority = models.CharField(max_length=20,choices=PRIORITY_CHOICES,default='LOW')

    sla=models.FloatField(null=True,blank=True)

    status = models.CharField(
        max_length=50,
        choices=[
            ('OPEN', 'Open'),
            ('IN_PROGRESS', 'In Progress'),
            ('RESOLVED', 'Resolved'),
            ('CLOSED', 'Closed')
        ],
        default='OPEN',
    )

    ticket_origin_date = models.DateTimeField(auto_now_add=True)
    ticket_resolution_date=models.DateTimeField(null=True,blank=True)
    progress_by_customer = models.FloatField(default=0,null=True, blank=True) 
    progress_by_user = models.FloatField(default=0,null=True, blank=True)  
    customer_feedback=models.CharField(max_length=100,choices=
            [                        
                ('PROGRESS-20%','Progress 20%'),
                ('PROGRESS-30%','Progress 30%'),
                ('PROGRESS-40%','Progress 40%'),
                ('PROGRESS-50%','Progress 50%'),
                ('PROGRESS-60%','Progress 60%'),
                ('PROGRESS-70%','Progress 70%'),
                ('PROGRESS-80%','Progress 80%'),
                ('PROGRESS-90%','Progress 90%'),
                ('PROGRESS-100%','Progress 100%'),                             
               
            ], null=True, blank=True
            )
    customer_comments = models.TextField(null=True,blank=True)
    user_comments = models.TextField(null=True,blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)


    def save(self, *args, **kwargs):
        if not self.ticket_id:
            current_date = datetime.now().strftime("%Y%m%d") 
            unique_id = uuid.uuid4().hex[:8].upper() 
            self.ticket_id = f"{current_date}-{unique_id}"
           
            # if self.customer_feedback == 'PROGRESS-20%':
            #     self.progress_by_customer = 20.0
            # elif self.customer_feedback == 'PROGRESS-30%':
            #     self.progress_by_customer = 30.0
            # elif self.customer_feedback == 'PROGRESS-40%':
            #     self.progress_by_customer = 40.0
            # elif self.customer_feedback == 'PROGRESS-40%':
            #     self.progress_by_customer = 40.0
            # elif self.customer_feedback == 'PROGRESS-50%':
            #     self.progress_by_customer = 50.0
            # elif self.customer_feedback == 'PROGRESS-60%':
            #     self.progress_by_customer = 60.0
            # elif self.customer_feedback == 'PROGRESS-70%':
            #     self.progress_by_customer = 70.0
            # elif self.customer_feedback == 'PROGRESS-80%':
            #     self.progress_by_customer = 80.0
            # elif self.customer_feedback == 'PROGRESS-90%':
            #     self.progress_by_customer = 90.0
            # elif self.customer_feedback == 'PROGRESS-100%':
            #     self.progress_by_customer = 100.0
            # else:
            #     self.progress_by_customer = 0.0
                
                 
        super().save(*args, **kwargs)

    def __str__(self):
        return f"Ticket #{self.ticket_code}"




class TeamMember(models.Model):
    user=models.ForeignKey(CustomUser,on_delete=models.CASCADE,null=True,blank=True)
    team = models.ForeignKey(Team, on_delete=models.CASCADE, related_name="members",blank=True,null=True)  
    member = models.ForeignKey(
        Employee, 
        on_delete=models.CASCADE, 
        related_name="team_memberships",blank=True,null=True
    ) 
    is_team_leader = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.member.name} - {self.team.name}"


from repairreturn.models import ReturnOrRefund
from officemanagement.models import ITSupportTicket

class Task(models.Model):
    user=models.ForeignKey(CustomUser,on_delete=models.CASCADE,null=True,blank=True)
    department=models.ForeignKey(Department,on_delete=models.CASCADE,null=True,blank=True)
    task_id = models.CharField(max_length=20,null=True, blank=True)
    task_manager = models.ForeignKey(Employee,on_delete=models.CASCADE,related_name='task_manager',null=True,blank=True)
    task_type = models.CharField(max_length=200,choices=[('TICKET','Ticket'),('TASK','Task'),('IT-TICKET','IT Ticket')],null=True, blank=True)
    title = models.CharField(max_length=200,null=True, blank=True)   
    ticket = models.ForeignKey(Ticket, on_delete=models.CASCADE, related_name="task", null=True, blank=True)
    it_support_ticket = models.ForeignKey(ITSupportTicket, on_delete=models.CASCADE, related_name="it_task_ticket", null=True, blank=True)
    priority = models.CharField(max_length=20,choices=PRIORITY_CHOICES,default='LOW')
    description = models.TextField(null=True, blank=True)
    
    assigned_datetime = models.DateTimeField(null=True, blank=True)
    due_datetime = models.DateTimeField(null=True, blank=True)    
    extended_due_datetime = models.DateTimeField(blank=True, null=True)  # For manager-approved extensions
    
    time_extension_approval_status= models.CharField(max_length=30,choices=[('APPROVED','Approved'),('REJECTED','Rejected')],null=True,blank=True)  
   
    assigned_number = models.FloatField(default=0,null=True, blank=True) 
    obtained_number = models.FloatField(default=0,null=True, blank=True) 
    obtained_score = models.FloatField(default=0,null=True, blank=True) 

    manager_given_number = models.FloatField(null=True, blank=True)
    manager_given_score = models.FloatField(null=True, blank=True)
    

    status = models.CharField(max_length=50, choices=[
        ('PENDING', 'Pending'),
        ('IN_PROGRESS', 'In Progress'),
        ('COMPLETED', 'Completed'),
        ('OVERDUE', 'Overdue'),
        ('TIME_EXTENSION', 'Time extension'),
    ], default='PENDING',null=True, blank=True)

    assigned_to = models.CharField(max_length=20,choices=[('member','member'),('team','team')],null=True,blank=True)
    assigned_to_employee = models.ForeignKey(
        Employee, on_delete=models.SET_NULL, null=True, blank=True, related_name='tasks_employee')
    assigned_to_team = models.ForeignKey(
        Team, on_delete=models.SET_NULL, null=True, blank=True, related_name='tasks_team')
    progress = models.FloatField(default=0,null=True, blank=True)  # Completion progress in %
    remarks = models.TextField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        permissions = [
            ("can_create_task", "Can create a task"),
        ]

   
    def calculate_obtained_number(self):
        if self.pk is None: 
            return 0  

        if self.progress > 0:
            progress_factor = self.progress / 100

            if self.due_datetime and self.assigned_number is not None:
                task_duration = (self.due_datetime - self.assigned_datetime).total_seconds() / 3600

                latest_extension_request = self.time_extension_requests.filter(is_approved=True).order_by('-updated_at').first()
                if latest_extension_request and latest_extension_request.approved_extension_datetime:
                    extension_duration = (latest_extension_request.approved_extension_datetime - self.due_datetime).total_seconds() / 3600
                else:
                    extension_duration = 0

                if task_duration > 0:   
                    reduction_factor = extension_duration / task_duration
                    reduction_number = self.assigned_number * reduction_factor
                    remaining_number = self.assigned_number - reduction_number

                    if remaining_number <= 0.0:   
                        remaining_number = self.assigned_number * 0.25
                        
                    return max(0, remaining_number * progress_factor)
                else:     
                    return 0
            else:  
                return (self.assigned_number or 0) * progress_factor
        else: 
            return 0


    def save(self, *args, **kwargs):
        if not self.task_id:
            current_date = datetime.now().strftime("%Y%m%d") 
            unique_id = uuid.uuid4().hex[:8].upper() 
            self.task_id = f"{current_date}-{unique_id}"

        is_new = self.pk is None
        super().save(*args, **kwargs)

        if is_new:
            latest_request = self.time_extension_requests.filter(is_approved=True).order_by('-created_at').first()
            if latest_request:
                self.extended_due_datetime = latest_request.approved_extension_datetime
                super().save(update_fields=['extended_due_datetime'])



    def __str__(self):
        if self.assigned_to == 'team':
            display_name = self.assigned_to_team
        else:
            display_name = self.assigned_to_employee

        return f' {self.task_id}-{display_name}'
    


class TaskMessage(models.Model):
    task = models.ForeignKey(Task, on_delete=models.CASCADE, related_name="task_messages",null=True,blank=True)
    sender = models.ForeignKey(CustomUser, on_delete=models.CASCADE)
    message = models.TextField()
    timestamp = models.DateTimeField(auto_now_add=True)
    read = models.BooleanField(default=False)  
    created_at=models.DateTimeField(auto_now_add=True,null=True,blank=True)

    def __str__(self):
        return f"{self.message} - {self.timestamp}"




class TaskMessageReadStatus(models.Model):
    task_message = models.ForeignKey(TaskMessage, on_delete=models.CASCADE, related_name="read_statuses")
    user = models.ForeignKey(CustomUser, on_delete=models.CASCADE)
    read = models.BooleanField(default=False)
    read_at = models.DateTimeField(null=True, blank=True)

    def __str__(self):
        return f"Message: {self.task_message.id} | User: {self.user.username} | Read: {self.read}"



class TimeExtensionRequest(models.Model):
    task = models.ForeignKey(Task, on_delete=models.CASCADE, related_name="time_extension_requests",null=True,blank=True)
    requested_by = models.ForeignKey(CustomUser, on_delete=models.CASCADE,null=True,blank=True)
    requested_extension_datetime = models.DateTimeField(null=True,blank=True)  
    time_extension_reason=models.CharField(max_length=50,null=True,blank=True,
    choices=[
        ('INTERNAL_AFFAIR','Internal Affair'),
        ('EXTERNAL_AFFAIR','External affair'),
        ('LOGISTICS_AFFAIR','Logistics affair'),
        ('FINANCIAL_AFFAIR','Financial affair'),
        ('LABOR_CRISIS','Labor crisis'),
        ('BAD_WEATHER','Bad weather'),
        ('OTHER_DEPARTMENT_DEPENDENCY','Other department dependency')
        ])
    
    is_approved = models.BooleanField(default=False)
    approved_extension_datetime = models.DateTimeField(null=True, blank=True)
    manager_comments = models.TextField(null=True, blank=True)
    created_at=models.DateTimeField(auto_now_add=True)
    updated_at =models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Request for Task {self.task.id} - Approved: {self.is_approved}"




class PerformanceEvaluation(models.Model):
    user=models.ForeignKey(CustomUser,on_delete=models.CASCADE,null=True,blank=True)
    ev_id = models.CharField(max_length=20, null=True, blank=True)
    employee = models.ForeignKey(Employee, on_delete=models.CASCADE, related_name='employee_evaluation', blank=True, null=True)
    department =models.ForeignKey(Department,on_delete=models.CASCADE,null=True,blank=True)
    position =models.ForeignKey(Position,on_delete=models.CASCADE,null=True,blank=True)
    task = models.ForeignKey(Task, on_delete=models.CASCADE, null=True, blank=True, related_name='task_ev') 
    team = models.ForeignKey(Team, on_delete=models.CASCADE, null=True, blank=True, related_name='team_ev') 
    evaluation_date = models.DateField(auto_now_add=True)

    assigned_quantitative_number = models.FloatField(default=0.0, null=True, blank=True) 
    assigned_qualitative_number = models.FloatField(default=0.0, null=True, blank=True)    

    obtained_quantitative_number = models.FloatField(default=0.0, null=True, blank=True)   
    given_quantitative_number = models.FloatField(default=0.0, null=True, blank=True) 
    obtained_qualitative_number = models.FloatField(default=0.0, null=True, blank=True)  
    
    obtained_quantitative_score = models.FloatField(default=0.0, null=True, blank=True) 
    given_quantitative_score = models.FloatField(default=0.0, null=True, blank=True)      
    obtained_qualitative_score = models.FloatField(default=0.0, null=True, blank=True)

    
   
  
    total_assigned_number = models.FloatField(default=0.0, null=True, blank=True)
    total_obtained_number = models.FloatField(default=0.0, null=True, blank=True)
    total_given_number = models.FloatField(default=0.0, null=True, blank=True)
    total_given_score = models.FloatField(default=0.0, null=True, blank=True)
    total_obtained_score = models.FloatField(default=0.0, null=True, blank=True) 

    evaluator = models.ForeignKey(CustomUser, on_delete=models.SET_NULL, null=True, blank=True,related_name='evaluation_evaluator')  
   
    half_year = models.CharField(max_length=20, null=True, blank=True)
    quarter = models.CharField(max_length=20, null=True, blank=True)
    month = models.CharField(max_length=20, null=True, blank=True)
    year = models.IntegerField(null=True, blank=True) 
    remarks = models.TextField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def save(self, *args, **kwargs):         
        if not self.ev_id:
            self.ev_id = f"EV-{uuid.uuid4().hex[:8].upper()}"   

        if self.employee:
            self.department = self.employee.department  
            self.position = self.employee.position  

        if self.evaluation_date:
            self.year = self.evaluation_date.year
            self.month = self.evaluation_date.strftime("%B")
            self.quarter = self.get_quarter(self.evaluation_date)
            self.half_year = self.get_half_year(self.evaluation_date)

        self.total_assigned_number = (self.assigned_quantitative_number or 0) + (self.assigned_qualitative_number or 0)
        self.total_obtained_number = (self.obtained_quantitative_number or 0) + (self.obtained_qualitative_number or 0)
        self.total_given_number = (self.given_quantitative_number or 0) + (self.obtained_qualitative_number or 0)

        if self.total_assigned_number > 0:
            self.total_obtained_score = (self.total_obtained_number / self.total_assigned_number) * 100
            self.total_given_score = (self.total_given_number / self.total_assigned_number) * 100
        else:
            self.total_obtained_score = 0
            self.total_given_score = 0
        super().save(*args, **kwargs)

    def get_quarter(self, evaluation_date):
        month = evaluation_date.month
        if month in [1, 2, 3]:
            return '1ST-QUARTER'
        elif month in [4, 5, 6]:
            return '2ND-QUARTER'
        elif month in [7, 8, 9]:
            return '3RD-QUARTER'
        elif month in [10, 11, 12]:
            return '4TH-QUARTER'
        return ''
    
    def get_half_year(self, evaluation_date):
        month = evaluation_date.month
        if month in [1, 2, 3, 4, 5, 6]:
            return '1ST-HALF-YEAR'
        elif month in [7, 8, 9, 10, 11, 12]:
            return '2ND-HALF-YEAR'
        return ''




    def __str__(self):
        return f"{self.employee.name}"





class QualitativeEvaluation(models.Model):
    user=models.ForeignKey(CustomUser,on_delete=models.CASCADE,null=True,blank=True)
    ev_id = models.CharField(max_length=20, null=True, blank=True)
    performance_evaluation = models.ForeignKey(PerformanceEvaluation, on_delete=models.CASCADE, related_name='qualitative_evaluations',blank=True, null=True)
    employee = models.ForeignKey(Employee, on_delete=models.CASCADE, related_name='employee_qualitative_evaluations',blank=True, null=True)
    team = models.ForeignKey(Team, on_delete=models.CASCADE, related_name='team_qualitative_evaluations',blank=True, null=True)
    task = models.ForeignKey(Task, on_delete=models.CASCADE, related_name='task_qualitative_evaluations', null=True, blank=True)
    evaluator = models.ForeignKey(CustomUser, on_delete=models.SET_NULL, null=True, blank=True,related_name='evaluator')  

    manager_given_quantitative_number = models.FloatField(null=True,blank=True)
    manager_given_quantitative_score = models.FloatField(null=True,blank=True)
    
    work_quality_score = models.FloatField(default=0.0,blank=True, null=True)  
    communication_quality_score = models.FloatField(default=0.0,blank=True, null=True) 
    teamwork_score = models.FloatField(default=0.0,blank=True, null=True)  
    initiative_score = models.FloatField(default=0.0,blank=True, null=True)  
    punctuality_score = models.FloatField(default=0.0,blank=True, null=True)  
       
    number_per_kpi = models.FloatField(default=0.0,blank=True, null=True)    

    feedback = models.TextField(blank=True, null=True)  
    evaluation_date = models.DateField(auto_now_add=True)  
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    def save(self, *args, **kwargs):       
        if not self.ev_id:
            self.ev_id = f"evq{uuid.uuid4().hex[:8].upper()}"  
        if not self.performance_evaluation.evaluator:
            self.performance_evaluation.evaluator = self.evaluator    
            self.performance_evaluation.save()
        
        super().save(*args, **kwargs)

    def __str__(self):
        return f"Qualitative Evaluation for {self.employee} on {self.task.title if self.task else 'N/A'}"



