from django import forms
from .models import Job,Experience,Exam,Candidate,Project
from .models import Question,ScoreCard,Language,LanguageSkillLevel,InterviewScore,PanelMember
from.models import Education,EducationalInstitution,EducationalSubject,Age,Certification,Skills
from.models import CommonDocument,CandidateDocument
from .models import BQCandidateAnswer,BQQuestionPaper,BQQuestion,JobCategory,Interview,Panel





class JobRequestForm(forms.ModelForm):
    class Meta:
        model = Job
        fields = ['company', 'department','job_category','title','position','reporting_manager','location','no_of_vacancies','deadline']
        widgets = {
            'title': forms.TextInput(attrs={'class': 'form-control'}),
            'description': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            'requirements': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
           
            'deadline': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'salary': forms.NumberInput(attrs={'class': 'form-control'}),
        }

class JobRequestProcessForm(forms.Form):
    STATUS_CHOICES = [
        ('SUBMITTED', 'Submitted'),
        ('REVIEWED', 'Reviewed'),
        ('APPROVED', 'Approved'),
        ('CANCELLED', 'Cancelled'),
    ]
    status = forms.ChoiceField(choices=STATUS_CHOICES, widget=forms.Select)

    remarks = forms.CharField(
        widget=forms.Textarea(
            attrs={
                'class': 'form-control custom-textarea',
                'rows': 3, 
                'style': 'height: 60px;',  
            }
        ),
        required=False
    )


# HR/hiring manager use below form to launch recruitment process and update rest of the fields
class JobForm(forms.ModelForm):
    class Meta:
        model = Job
        exclude = [
            'is_active','job_code','requester','status','approval_data',
            'requester_approval_status','reviewer_approval_status','approver_approval_status',
            'Requester_remarks','Approver_remarks','Reviewer_remarks'

            ]
       


class CommonDocumentForm(forms.ModelForm):
    class Meta:
        model = CommonDocument
        exclude=['user']
      


class CandidateDocumentForm(forms.ModelForm):
    class Meta:
        model = CandidateDocument
        exclude=['user']

       

class ProjectForm(forms.ModelForm):
    class Meta:
        model = Project
        exclude=['user']

        widgets={
            'description':forms.TextInput(attrs={
                'row':'2',
                'class':'form-control',
                'style':'height:100px'
            }),
            'deadline':forms.DateInput(attrs={'type':'date'})
        }



class ProjectReportForm(forms.Form):    
    project_name = forms.ModelChoiceField(
        queryset=Project.objects.all(),
        required=False,
        empty_label="Select a Project"
    )
  


class ScoreCardForm(forms.ModelForm):
    class Meta:
        model = ScoreCard
        exclude=['user']



class ExperienceForm(forms.ModelForm):
    class Meta:
        model = Experience
        exclude=['user']

class LanguageForm(forms.ModelForm):
    class Meta:
        model = Language
        exclude=['user']

class LanguageSkillLevelForm(forms.ModelForm):
    class Meta:
        model = LanguageSkillLevel
        exclude=['user']


class EducationForm(forms.ModelForm):
    class Meta:
        model = Education
        exclude=['user']

class EducationalSubjectForm(forms.ModelForm):
    class Meta:
        model = EducationalSubject
        exclude=['user']

class EducationalInstitutionForm(forms.ModelForm):
    class Meta:
        model = EducationalInstitution
        exclude=['user']

class AgeForm(forms.ModelForm):
    class Meta:
        model = Age
        exclude=['user']

class CertificationForm(forms.ModelForm):
    class Meta:
        model = Certification
        exclude=['user']

class skillsForm(forms.ModelForm):
    class Meta:
        model = Skills
        exclude=['user']

        


class JobCategoryForm(forms.ModelForm):
    class Meta:
        model = JobCategory
        exclude = ['user']
        widgets = {
           
            'description': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
           
        }



class CandidateForm(forms.ModelForm):   
    class Meta:
        model = Candidate
        exclude = ['candidate','bq_exam_score','bq_exam_status','cv_screening_score','exam_score','interview_score','status','cv_screening_status','exam_status','interview_status','hiring_status']
        widgets = {                  
           
            'language_skill_level': forms.CheckboxSelectMultiple,            
            'experience': forms.CheckboxSelectMultiple,
            'certification': forms.CheckboxSelectMultiple,
            'skills': forms.CheckboxSelectMultiple,
            'education': forms.CheckboxSelectMultiple,
            'subject': forms.CheckboxSelectMultiple,
            'subject_of_education': forms.CheckboxSelectMultiple,
            'institution_of_education': forms.CheckboxSelectMultiple,
            
            
        }
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs) 
        self.fields['age'].required = False
        self.fields['education'].required = False
        self.fields['subject_of_education'].required = False
        self.fields['institution_of_education'].required = False
        self.fields['experience'].required = False
        self.fields['certification'].required = False
        self.fields['skills'].required = False
        self.fields['language_skill_level'].required = False




class ShortlistThresholdForm(forms.Form):
    threshold_score = forms.DecimalField(
        max_digits=5, decimal_places=2, 
        label="Desired Threshold Score", 
        min_value=0.0,
        required=False
    )
    job_title = forms.ModelChoiceField(
        queryset=Job.objects.all(),
        required=False,
        empty_label="Select a Job"
    )
    exam = forms.ModelChoiceField(
        queryset=Exam.objects.all(), 
        required=False,
        empty_label="Select an Exam"
    )



class SearchCandidateForm(forms.Form):
    threshold_score = forms.DecimalField(
        max_digits=5, decimal_places=2, 
        label="Desired Threshold Score", 
        min_value=0.0,
        required=False
    )
    job_title = forms.ModelChoiceField(
        queryset=Job.objects.all(),
        required=False,
        empty_label="Select a Job"
    )
    exam = forms.ModelChoiceField(
        queryset=Exam.objects.all(), 
        required=False,
        empty_label="Select an Exam"
    )


class ExamForm(forms.ModelForm):
    class Meta:
        model = Exam
        fields = ['job','title', 'start_time','end_time','total_marks','pass_marks']
        widgets = {
            'title': forms.TextInput(attrs={'class': 'form-control'}),
            'duration': forms.NumberInput(attrs={'class': 'form-control', 'placeholder': 'Duration in minutes'}),
            'total_marks': forms.NumberInput(attrs={'class': 'form-control'}),
            'pass_marks': forms.NumberInput(attrs={'class': 'form-control'}),
            'start_time': forms.DateInput(attrs={'class': 'form-control','type':'datetime-local'}),
            'end_time': forms.DateInput(attrs={'class': 'form-control','type':'datetime-local'}),
        }



class QuestionForm(forms.ModelForm):
    class Meta:
        model = Question
        exclude=['user']
        widgets = {
            'exam': forms.Select(),
            'text': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            'option_a': forms.TextInput(),
            'option_b': forms.TextInput(),
            'option_c': forms.TextInput(),
            'option_d': forms.TextInput(),
            'correct_answer': forms.Select(choices=[
                ('option_a', 'Option a'),
                ('option_b', 'Option b'),
                ('option_c', 'Option c'),
                ('option_d', 'Option d'),
            ],),
        }



class TakeExamForm(forms.Form):
    def __init__(self, questions, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.question_marks = {}  

        for question in questions:
            field_name = f'question_{question.id}'  
            label_with_marks = f"{question.text} (Marks: {question.marks})"  
            choices = [
                ('A', f"A: {question.option_a}"),
                ('B', f"B: {question.option_b}"),
                ('C', f"C: {question.option_c}"),
                ('D', f"D: {question.option_d}"),
            ]
  
            self.fields[field_name] = forms.ChoiceField(
                choices=choices,
                widget=forms.RadioSelect,
                label=label_with_marks, 
                required=True,
            )

            self.question_marks[field_name] = question.marks



class CandidateStatusForm(forms.ModelForm):
    class Meta:
        model = Candidate
        fields = ['status']
        widgets = {
            'status': forms.Select(choices=[
                ('Applied', 'Applied'),
                ('Shortlisted', 'Shortlisted'),
                ('Rejected', 'Rejected'),
            ], attrs={'class': 'form-control'}),
        }




class ApplicationFilterForm(forms.Form):
    job = forms.ModelChoiceField(
        queryset=Job.objects.all(),
        widget=forms.Select(attrs={'class': 'form-control'}),
        required=False
    )
    status = forms.ChoiceField(
        choices=[
            ('', 'All'),
            ('Applied', 'Applied'),
            ('Shortlisted', 'Shortlisted'),
            ('Rejected', 'Rejected'),
        ],
        widget=forms.Select(attrs={'class': 'form-control'}),
        required=False
    )


class SearchApplicationForm(forms.Form):
    query = forms.CharField(
        max_length=100,
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Search by job name, candidate email/name'}),
        required=False
    )



class PanelForm(forms.ModelForm):
    class Meta:
        model = Panel
        exclude=['user','is_active']
       

class PanelMemberForm(forms.ModelForm):
    class Meta:
        model = PanelMember
        exclude=['user','is_active']
       

class PanelScoreForm(forms.ModelForm):
    class Meta:
        model = InterviewScore
        fields = '__all__'
        widgets={
            'remarks':forms.TextInput(attrs={
                'row':'2',
                'class':'form-control',
                'style':'height:100px;width:500px'
            })
        }



class ManageInterviewForm(forms.ModelForm):
    class Meta:
        model = Interview
        exclude=['candidate']
        widgets = {
            'interview_date': forms.DateTimeInput(attrs={'class': 'form-control', 'type': 'datetime-local'}),
           
        }


class SelectedCandidateForm(forms.Form):   
    job_title = forms.ModelChoiceField(
        queryset=Job.objects.all(),
        required=False,
        empty_label="Select a Job"
    )

    candidate_name = forms.CharField(
        max_length=100,
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Search by name or email(optional)'}),
        required=False
    )
 

class AllJobForm(forms.Form):      
   project_name = forms.CharField(
        max_length=100,
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Search project'}),
        required=False
    )


############################# Broad question ######################

class BQQuestionrPaperForm(forms.ModelForm):
    class Meta:
        model = BQQuestionPaper
        exclude = ['user', 'duration']
        widgets = {
            'start_time': forms.DateTimeInput(attrs={'class': 'form-control', 'type': 'datetime-local'}),
            'end_time': forms.DateTimeInput(attrs={'class': 'form-control', 'type': 'datetime-local'}),
        }


class BQQuestionForm(forms.ModelForm):
    class Meta:
        model = BQQuestion
        exclude=['user']
        widgets = {
            'answer': forms.Textarea(attrs={'rows': 4, 'cols': 50}),
        }


class BQCandidateAnswerForm(forms.ModelForm):
    class Meta:
        model = BQCandidateAnswer
        exclude=['user']
        widgets = {
            'answer': forms.Textarea(attrs={'rows': 4, 'cols': 50}),           
        }


class BQExamForm(forms.Form):
    def __init__(self, questions, *args, **kwargs):
        super().__init__(*args, **kwargs)

        for question in questions:
            field_name = f'question_{question.id}'  
            label_with_marks = f"{question.text} (Marks: {question.score})"

            self.fields[field_name] = forms.CharField(
                widget=forms.Textarea(attrs={'class':'form-control','rows': 3,'column':100, 'placeholder': 'Write your answer here...'}),
                label=label_with_marks,
                required=True,
            )
