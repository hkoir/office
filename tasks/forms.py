from django import forms
from .models import Task, Team, Employee,Ticket,TeamMember
from django import forms

from .models import QualitativeEvaluation
from core.models import Employee,Department,Position
from.models import TimeExtensionRequest,TaskMessage
from django.utils.timezone import make_aware
from core.models import SalaryIncrementAndPromotion




class ChatForm(forms.ModelForm):
    class Meta:
        model = TaskMessage
        fields = ['message']
        widgets = {
            'message': forms.Textarea(attrs=
            {'placeholder': 'Enter your message here...',           
            
             
             })
        }


class TaskAssignmentForm(forms.ModelForm):  
     due_dattime = forms.DateTimeField(label='Due datetime', required=False, widget=forms.DateTimeInput(attrs={'type': 'datetime-local'}))   
     team_name = forms.CharField(label='Team name',required=False)
     member = forms.CharField(required=False)
     class Meta:
        model = Task
        fields = ['department','title', 'priority', 'assigned_to', 'due_datetime']  

     assigned_to = forms.ModelChoiceField(
        queryset=Employee.objects.all(),
        label="assigned to",
        widget=forms.Select(attrs={'class': 'form-control'})
    )
     


class TeamForm(forms.ModelForm):
    description = forms.CharField(required=False,
    widget=forms.Textarea(
        attrs={
            'class': 'form-control custom-textarea',
            'rows': 2,           
            }
        )
    )
    class Meta:
        model = Team
        fields = ['department','name','manager']
        widgets = {
            'department': forms.Select(attrs={'class': 'form-control'}),  # keep dropdown
            'name': forms.TextInput(attrs={'class': 'form-control'}),    # text input
            'manager': forms.Select(attrs={'class': 'form-control'}),    # dropdown if ForeignKey
        }
        

class AddMemberForm(forms.ModelForm):
    team = forms.ModelChoiceField(
        queryset=Team.objects.all(),
        required=True,
        label='Team',
        widget=forms.Select(attrs={'class': 'form-control'})  # styled dropdown
        )
    member = forms.ModelChoiceField(
        queryset=Employee.objects.all(),
        required=True,
        label='Member',
        widget=forms.Select(attrs={'class': 'form-control'})  # styled dropdown
       )
    class Meta:
        model = TeamMember
        exclude=['user']
       



class TaskForm(forms.ModelForm):    
    class Meta:
        model = Task
        fields = ['department','task_type','title','ticket','assigned_to', 'assigned_to_employee', 'assigned_to_team','task_manager','assigned_number','assigned_datetime', 'due_datetime','priority','remarks']

        widgets={
            'due_datetime':forms.DateTimeInput(attrs={'type':'datetime-local'}),
             'assigned_datetime':forms.DateTimeInput(attrs={'type':'datetime-local'}),
            'remarks':forms.Textarea(attrs={
                'rows':2,
                'class':'form-control custom-textarea',
                
                }),           
        }
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)       
        self.fields['ticket'].queryset = Ticket.objects.all()

    
class AssignTaskForm(forms.ModelForm):    
    class Meta:
        model = Task
        fields = ['department','assigned_to', 'assigned_to_employee', 'assigned_to_team','task_manager','assigned_number','assigned_datetime', 'due_datetime','priority','remarks']

        widgets={
            'due_datetime':forms.DateTimeInput(attrs={'type':'datetime-local'}),
             'assigned_datetime':forms.DateTimeInput(attrs={'type':'datetime-local'}),
            'remarks':forms.Textarea(attrs={
                'rows':2,
                'class':'form-control custom-textarea',
                
                }),           
        }
   


class TicketForm(forms.ModelForm):    
    class Meta:
        model = Ticket

        fields = ['ticket_type','sales','operations', 'production','repair_return', 'subject', 'priority','description','status']
        widgets={
            'description':forms.Textarea(attrs={
                'row':3,
                'style':'height:100px;width:15opx'
            })
        }

    
class CustomerUpdateTicketForm(forms.ModelForm):    
    class Meta:
        model = Ticket
        fields = ['status','customer_feedback','ticket_resolution_date','customer_comments']
        widgets = {
            'customer_comments': forms.Textarea(attrs={
                'class': 'form-control',  
                'placeholder': 'Provide your comments here...', 
                'rows': 4, 
                'style': 'resize: vertical;', 
            }),
            'ticket_resolution_date':forms.DateTimeInput(attrs={'type':'datetime-local'}),
        }
        


class TaskProgressForm(forms.ModelForm):
    class Meta:
        model = Task
        fields = ['progress']
        widgets = {
            'progress': forms.NumberInput(attrs={
                'min': 0,
                'max': 100,
                'class': 'form-control',
                'placeholder': 'Enter progress percentage (0-100)',
            })
        }

    def clean_progress(self):
        progress = self.cleaned_data['progress']
        if progress < 0 or progress > 100:
            raise forms.ValidationError("Progress must be between 0 and 100.")
        return progress




class RequestExtensionForm(forms.ModelForm):
    class Meta:
        model = TimeExtensionRequest
        fields = ['task', 'requested_extension_datetime', 'time_extension_reason']
        widgets = {
            'requested_extension_datetime': forms.DateTimeInput(attrs={'type': 'datetime-local'})
        }

    def clean_requested_extension_datetime(self):
        requested_extension_datetime = self.cleaned_data.get('requested_extension_datetime')
        if requested_extension_datetime and requested_extension_datetime.tzinfo is None:
            requested_extension_datetime = make_aware(requested_extension_datetime)
        
        return requested_extension_datetime



class ApproveExtensionForm(forms.ModelForm):    
    class Meta:
        model = TimeExtensionRequest
        fields = ['is_approved', 'approved_extension_datetime', 'manager_comments']
        
        APPROVE_CHOICES = [
        (True, 'Yes'),
        (False, 'No')]
        
        widgets = {
            'is_approved': forms.RadioSelect(choices=APPROVE_CHOICES),
            'approved_extension_datetime': forms.DateTimeInput(attrs={'type': 'datetime-local'}),
            'manager_comments': forms.Textarea(attrs={'rows': 4, 'cols': 50}),
        }
        labels = {
            'is_approved': "Approve Extension?",
            'approved_extension_datetime': "Extended Datetime",
            'manager_comments': "Manager Comments",
        }

    def clean_approved_extension_datetime(self):
        approved_extension_datetime = self.cleaned_data.get('approved_extension_datetime')
        if approved_extension_datetime and approved_extension_datetime.tzinfo is None:
            approved_extension_datetime = make_aware(approved_extension_datetime)        
        return approved_extension_datetime



class QualitativeEvaluationForm(forms.ModelForm):
    class Meta:
        model = QualitativeEvaluation
        fields = [
            'performance_evaluation', 
            'employee', 
            'task', 
            'evaluator',
            'manager_given_quantitative_number',
            'work_quality_score',
            'communication_quality_score',
            'teamwork_score',
            'initiative_score',
            'punctuality_score',
            'feedback'
        ]
        widgets = {
            'feedback': forms.Textarea(attrs={'rows': 5, 'placeholder': 'Add feedback here'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)     
        self.fields['task'].label = "Task Title"
        if 'initial' in kwargs and isinstance(kwargs['initial'].get('task'), Task):
            self.fields['task'].initial = kwargs['initial']['task'].title

    def clean(self):
        cleaned_data = super().clean()
        score_fields = [
            'work_quality_score',
            'communication_quality_score',
            'teamwork_score',
            'initiative_score',
            'punctuality_score'
        ]
        for field in score_fields:
            score = cleaned_data.get(field)
            if score < 0 or score > 5:
                self.add_error(field, f"{field.replace('_', ' ').capitalize()} must be between 0 and 5.")
        return cleaned_data




class YearlyTrendForm(forms.Form):  
    start_year = forms.IntegerField(label='Start Year',required=True)
    end_year = forms.IntegerField(label='End Year',required=True)           

    employee_name = forms.ModelChoiceField(
        queryset=Employee.objects.all(),
        required=False,
        widget=forms.Select(attrs={'id': 'id_employee_name'}),
    )
    
    department = forms.ModelChoiceField(
        queryset=Department.objects.all(),  # Fetch all departments
        label='Department',
        required=False,
        widget=forms.Select(
            attrs={
                'style': 'width: 200px;',  # Inline style for width
                'class': 'custom-select',  # Optional styling
            }
        ),
    )

    position = forms.ModelChoiceField(
        queryset=Position.objects.all(),  # Fetch all departments
        label=Position,
        required=False,
        widget=forms.Select(
            attrs={
                'style': 'width: 200px;',  # Inline style for width
                'class': 'custom-select',  # Optional styling
            }
        ),
    )




class MonthlyQuarterlyTrendForm(forms.Form):  
    year = forms.IntegerField(required=True, label="Year") 

    employee = forms.ModelChoiceField(
        queryset=Employee.objects.all(),
        required=True,
        widget=forms.Select(attrs={'id': 'id_employee_name'}),
    )
    
    department = forms.ModelChoiceField(
        queryset=Department.objects.all(),  # Fetch all departments
        label='Department',
        required=False,
        widget=forms.Select(
            attrs={
                'style': 'width: 200px;',  # Inline style for width
                'class': 'custom-select',  # Optional styling
            }
        ),
    )

    position = forms.ModelChoiceField(
        queryset=Position.objects.all(),  # Fetch all departments
        label=Position,
        required=False,
        widget=forms.Select(
            attrs={
                'style': 'width: 200px;',  # Inline style for width
                'class': 'custom-select',  # Optional styling
            }
        ),
    )


class GroupTrendForm(forms.Form):  

    start_date = forms.DateField(
        label='Start Date',
        widget=forms.DateInput(attrs={'type': 'date'}),
        required=False
    )
    end_date = forms.DateField(
        label='End Date',
        widget=forms.DateInput(attrs={'type': 'date'}),
        required=False
    )
    days = forms.IntegerField(
        label='Number of Days',
        min_value=1,
        required=False
    )
   
    
    department = forms.ModelChoiceField(
        queryset=Department.objects.all(),  # Fetch all departments
        label='Department',
        required=False,
        widget=forms.Select(
            attrs={
                'style': 'width: 200px;',  # Inline style for width
                'class': 'custom-select',  # Optional styling
            }
        ),
    )

    position = forms.ModelChoiceField(
        queryset=Position.objects.all(),  # Fetch all departments
        label='Position',
        required=False,
        widget=forms.Select(
            attrs={
                'style': 'width: 200px;',  # Inline style for width
                'class': 'custom-select',  # Optional styling
            }
        ),
    )



class IncrementPromotionCheckForm(forms.Form):
    INCREMENT_TYPE_CHOICES = [
        ('MONTHLY', 'Monthly'),
        ('QUARTERLY', 'Quarterly'),
        ('HALF-YEARLY', 'Half Yearly'),
        ('YEARLY', 'Yearly'),
    ]

    INCREMENT_CATEGORY_CHOICES=[
        ('BY_EMPLOYEE','By Employee'),
        ('BY_DEPARTMENT','By department'),
        ('BY_POSITION','By Position'),
        ('BY_COMPANY','By Company')]

    MONTH_CHOICES = [
        ('JANUARY', 'January'),
        ('FEBRUARY', 'February'),
        ('MARCH', 'March'),
        ('APRIL', 'April'),
        ('MAY', 'May'),
        ('JUNE', 'June'),
        ('JULY', 'July'),
        ('AUGUST', 'August'),
        ('SEPTEMBER', 'September'),
        ('OCTOBER', 'October'),
        ('NOVEMBER', 'November'),
        ('DECEMBER', 'December'),
    ]

    QUARTER_CHOICES = [
        ('1ST-QUARTER', '1st Quarter'),
        ('2ND-QUARTER', '2nd Quarter'),
        ('3RD-QUARTER', '3rd Quarter'),
        ('4TH-QUARTER', '4th Quarter'),
    ]

    HALF_YEAR_CHOICES = [
        ('1ST-HALF-YEAR', 'First Half Year'),
        ('2ND-HALF-YEAR', 'Second Half Year'),
    ]
    appraisal_year= forms.IntegerField(required=False)
    appraisal_type = forms.ChoiceField(required=False,choices=INCREMENT_TYPE_CHOICES) 

    year= forms.IntegerField(required=False)     
    month=forms.ChoiceField(required=False,choices=MONTH_CHOICES)
    quarter=forms.ChoiceField(required=False,choices=QUARTER_CHOICES)
    half_year=forms.ChoiceField(required=False,choices=HALF_YEAR_CHOICES)

    eligible_score_for_promotion= forms.FloatField(required=False) 
    eligible_score_for_promotion= forms.FloatField(required=False)
    max_promotion_limit = forms.FloatField(required=False)
    salary_increment_percentage = forms.FloatField(required=False)
    promotional_increment_percentage = forms.FloatField(required=False)


class IncrementPromotionForm(forms.ModelForm):  
    effective_date = forms.DateField(
        label='Effective Date',
        widget=forms.DateInput(attrs={'type': 'date'}),
        required=False
    )
    eligible_score_for_promotion= forms.FloatField(required=False)
    max_promotion_limit = forms.FloatField(required=False)
 
            
    class Meta:
        model=SalaryIncrementAndPromotion
        exclude=[
            'new_basic_salary',
            'increment_amount',
            'obtained_promotion_recommendation',
            'promotion_recommendation',
            'task_count',
            'task_count_employee',
            'avg_task_count',
            'final_score',
            'weighted_final_score',
            'max_weighted_score',
            'normalized_weighted_final_score',
            'max_task_count',
            'task_factor',   
            'obtained_salary_increment_percentage',
            'obtained_promotional_increment_percentage',
            'salary_increment_amount',
            'promotional_increment_amount'


            ]
        


class IncrementPromotionFinalDataForm(forms.ModelForm):                  
    class Meta:
        model=SalaryIncrementAndPromotion
        fields=['appraisal_year','appraisal_category','appraisal_type','year','month','quarter','half_year']
       


class DownloadIncrementPromotionForm(forms.Form):
    INCREMENT_TYPE_CHOICES = [
        ('MONTHLY', 'Monthly'),
        ('QUARTERLY', 'Quarterly'),
        ('HALF-YEARLY', 'Half Yearly'),
        ('YEARLY', 'Yearly'),
    ]

    INCREMENT_CATEGORY_CHOICES=[
        ('BY_EMPLOYEE','By Employee'),
        ('BY_DEPARTMENT','By department'),
        ('BY_POSITION','By Position'),
        ('BY_COMPANY','By Company')]

    MONTH_CHOICES = [
        ('JANUARY', 'January'),
        ('FEBRUARY', 'February'),
        ('MARCH', 'March'),
        ('APRIL', 'April'),
        ('MAY', 'May'),
        ('JUNE', 'June'),
        ('JULY', 'July'),
        ('AUGUST', 'August'),
        ('SEPTEMBER', 'September'),
        ('OCTOBER', 'October'),
        ('NOVEMBER', 'November'),
        ('DECEMBER', 'December'),
    ]

    QUARTER_CHOICES = [
        ('1ST-QUARTER', '1st Quarter'),
        ('2ND-QUARTER', '2nd Quarter'),
        ('3RD-QUARTER', '3rd Quarter'),
        ('4TH-QUARTER', '4th Quarter'),
    ]

    HALF_YEAR_CHOICES = [
        ('1ST-HALF-YEAR', 'First Half Year'),
        ('2ND-HALF-YEAR', 'Second Half Year'),
    ]


    appraisal_year= forms.IntegerField(required=False)
    appraisal_type = forms.ChoiceField(required=False,choices=INCREMENT_TYPE_CHOICES)
    month=forms.ChoiceField(required=False,choices=MONTH_CHOICES)
    quarter=forms.ChoiceField(required=False,choices=QUARTER_CHOICES)
    half_year=forms.ChoiceField(required=False,choices=HALF_YEAR_CHOICES)
    appraisal_category = forms.ChoiceField(required=False,choices=INCREMENT_CATEGORY_CHOICES)
   

   
class GenerateIncrementPromotionPdfForm(forms.Form):
    INCREMENT_TYPE_CHOICES = [
        ('MONTHLY', 'Monthly'),
        ('QUARTERLY', 'Quarterly'),
        ('HALF-YEARLY', 'Half Yearly'),
        ('YEARLY', 'Yearly'),
    ]

    INCREMENT_CATEGORY_CHOICES=[
        ('BY_EMPLOYEE','By Employee'),
        ('BY_DEPARTMENT','By department'),
        ('BY_POSITION','By Position'),
        ('BY_COMPANY','By Company')]

    MONTH_CHOICES = [
        ('JANUARY', 'January'),
        ('FEBRUARY', 'February'),
        ('MARCH', 'March'),
        ('APRIL', 'April'),
        ('MAY', 'May'),
        ('JUNE', 'June'),
        ('JULY', 'July'),
        ('AUGUST', 'August'),
        ('SEPTEMBER', 'September'),
        ('OCTOBER', 'October'),
        ('NOVEMBER', 'November'),
        ('DECEMBER', 'December'),
    ]

    QUARTER_CHOICES = [
        ('1ST-QUARTER', '1st Quarter'),
        ('2ND-QUARTER', '2nd Quarter'),
        ('3RD-QUARTER', '3rd Quarter'),
        ('4TH-QUARTER', '4th Quarter'),
    ]

    HALF_YEAR_CHOICES = [
        ('1ST-HALF-YEAR', 'First Half Year'),
        ('2ND-HALF-YEAR', 'Second Half Year'),
    ]

 
    appraisal_year= forms.IntegerField(required=False)
    appraisal_type = forms.ChoiceField(required=False,choices=INCREMENT_TYPE_CHOICES)
    month=forms.ChoiceField(required=False,choices=MONTH_CHOICES)
    quarter=forms.ChoiceField(required=False,choices=QUARTER_CHOICES)
    half_year=forms.ChoiceField(required=False,choices=HALF_YEAR_CHOICES)
    appraisal_category = forms.ChoiceField(required=False,choices=INCREMENT_CATEGORY_CHOICES)
   

class GenerateIncrementPromotionGeneralPdfForm(forms.Form):
    INCREMENT_TYPE_CHOICES = [
        ('MONTHLY', 'Monthly'),
        ('QUARTERLY', 'Quarterly'),
        ('HALF-YEARLY', 'Half Yearly'),
        ('YEARLY', 'Yearly'),
    ]

    INCREMENT_CATEGORY_CHOICES=[
        ('BY_EMPLOYEE','By Employee'),
        ('BY_DEPARTMENT','By department'),
        ('BY_POSITION','By Position'),
        ('BY_COMPANY','By Company')]

    MONTH_CHOICES = [
        ('JANUARY', 'January'),
        ('FEBRUARY', 'February'),
        ('MARCH', 'March'),
        ('APRIL', 'April'),
        ('MAY', 'May'),
        ('JUNE', 'June'),
        ('JULY', 'July'),
        ('AUGUST', 'August'),
        ('SEPTEMBER', 'September'),
        ('OCTOBER', 'October'),
        ('NOVEMBER', 'November'),
        ('DECEMBER', 'December'),
    ]

    QUARTER_CHOICES = [
        ('1ST-QUARTER', '1st Quarter'),
        ('2ND-QUARTER', '2nd Quarter'),
        ('3RD-QUARTER', '3rd Quarter'),
        ('4TH-QUARTER', '4th Quarter'),
    ]

    HALF_YEAR_CHOICES = [
        ('1ST-HALF-YEAR', 'First Half Year'),
        ('2ND-HALF-YEAR', 'Second Half Year'),
    ]

    employee_name = forms.CharField(        
        label='Employee_name',
        required=False,        
    )
    appraisal_year= forms.IntegerField(required=False)
    appraisal_type = forms.ChoiceField(required=False,choices=INCREMENT_TYPE_CHOICES)
    month=forms.ChoiceField(required=False,choices=MONTH_CHOICES)
    quarter=forms.ChoiceField(required=False,choices=QUARTER_CHOICES)
    half_year=forms.ChoiceField(required=False,choices=HALF_YEAR_CHOICES)
    appraisal_category = forms.ChoiceField(required=False,choices=INCREMENT_CATEGORY_CHOICES)
   


       
