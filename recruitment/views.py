from django.shortcuts import render,redirect
from django.shortcuts import get_object_or_404
from django.utils import timezone
from django.contrib.auth.decorators import login_required,permission_required
from django.contrib import messages
from django.core.paginator import Paginator
from django.urls import reverse 
from django.forms import Form, ChoiceField, RadioSelect
from django.db.models import Sum, Avg, F,Count,Q
from django.utils.timezone import localtime
from django.http import JsonResponse

from.models import ScoreCard,Experience,Language,LanguageSkillLevel,Job,TakeExam,Candidate,Exam,Question
from .forms import QuestionForm,ExamForm,CandidateForm,LanguageSkillLevelForm,ProjectForm
from .forms import JobForm,ScoreCardForm,ExperienceForm,TakeExamForm,LanguageForm,SearchApplicationForm

from .models import  PanelMember, InterviewScore,CandidateScreeningHistory,InterviewScreeningHistory
from .forms import PanelScoreForm,PanelMemberForm,ShortlistThresholdForm
from.models import ExamScreeningHistory,Project
from django.db import transaction

from.forms import SelectedCandidateForm,AllJobForm,ProjectForm,ProjectReportForm 
from .models import Project, Job, Candidate

from reportlab.pdfgen import canvas
from datetime import datetime
from reportlab.lib.pagesizes import A4,letter
from django.core.mail import EmailMessage,send_mail
from django.template.loader import render_to_string
from io import BytesIO
from core.models import Employee
import base64
import json

from django.contrib.sites.models import Site
from collections import defaultdict
from core.forms import AddEmployeeForm
from django.contrib.auth.models import Group

from.models import CommonDocument,CandidateDocument
from.forms import CommonDocumentForm,CandidateDocumentForm

from .models import Job, Exam, Candidate, PanelMember, TakeExam,Interview,InterviewScore




@login_required
def recruitment_dashboard(request):
    menu_items = [
        {'title': 'Create Job Category', 'url': reverse('recruitment:create_job_category'), 'icon': 'fa-folder-plus'},
        {'title': 'Create Job', 'url': reverse('recruitment:create_job'), 'icon': 'fa-briefcase'},
        {'title': 'Job List', 'url': reverse('recruitment:job_list'), 'icon': 'fa-list'},
        {'title': 'CV Screening', 'url': reverse('recruitment:cv_screening'), 'icon': 'fa-file-alt'},
        {'title': 'Create Exam', 'url': reverse('recruitment:create_exam'), 'icon': 'fa-pencil-ruler'},
        {'title': 'Exam List', 'url': reverse('recruitment:exam_list'), 'icon': 'fa-file-signature'},
        {'title': 'Create Questions', 'url': reverse('recruitment:create_questions'), 'icon': 'fa-question-circle'},
        {'title': 'Exam Screening', 'url': reverse('recruitment:exam_screening'), 'icon': 'fa-clipboard-check'},
        {'title': 'Create Panel', 'url': reverse('recruitment:create_panel'), 'icon': 'fa-users'},
        {'title': 'Create Panel Member', 'url': reverse('recruitment:create_panel_member'), 'icon': 'fa-user-plus'},
        {'title': 'Interview Screening', 'url': reverse('recruitment:interview_screening'), 'icon': 'fa-comments'},
        {'title': 'Selected Candidate', 'url': reverse('recruitment:selected_candidate'), 'icon': 'fa-user-check'},
        {'title': 'Grand Summary', 'url': reverse('recruitment:grand_summary'), 'icon': 'fa-chart-line'},
        {'title': 'Create Common Documents', 'url': reverse('recruitment:create_common_documents'), 'icon': 'fa-file-upload'},
        {'title': 'Create Candidate Documents', 'url': reverse('recruitment:create_candidate_documents'), 'icon': 'fa-id-card'},
    ]

    return render(request, 'recruitment/recruitment_dashboard.html', {'menu_items': menu_items})


@login_required
def manage_common_documents(request, id=None):  
    instance = get_object_or_404(CommonDocument, id=id) if id else None
    message_text = "updated successfully!" if id else "added successfully!"  
    form = CommonDocumentForm(request.POST or None, request.FILES or None, instance=instance)

    if request.method == 'POST' and form.is_valid():
        form_intance=form.save(commit=False)
        form_intance.user = request.user
        form_intance.save()        
        messages.success(request, message_text)
        return redirect('recruitment:create_common_documents')  

    datas = CommonDocument.objects.all().order_by('-created_at')
    paginator = Paginator(datas, 5)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    form = CommonDocumentForm(instance=instance)
    return render(request, 'recruitment/manage_common_documents.html', {
        'form': form,
        'instance': instance,
        'datas': datas,
        'page_obj': page_obj
    })


@login_required
def delete_common_documents(request, id):
    instance = get_object_or_404(CommonDocument, id=id)
    if request.method == 'POST':
        instance.delete()
        messages.success(request, "Deleted successfully!")
        return redirect('recruitment:create_common_documents')    

    messages.warning(request, "Invalid delete request!")
    return redirect('recruitment:create_common_documents')    



@login_required
def manage_candidate_documents(request, id=None):  
    instance = get_object_or_404(CandidateDocument, id=id) if id else None
    message_text = "updated successfully!" if id else "added successfully!"  
    form = CandidateDocumentForm(request.POST or None, request.FILES or None, instance=instance)

    if request.method == 'POST' and form.is_valid():
        form_intance=form.save(commit=False)
        form_intance.user = request.user
        form_intance.save()        
        messages.success(request, message_text)
        return redirect('recruitment:create_candidate_documents')  

    datas = CandidateDocument.objects.all().order_by('-created_at')
    paginator = Paginator(datas, 5)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    form = CandidateDocumentForm(instance=instance)
    return render(request, 'recruitment/manage_candidate_documents.html', {
        'form': form,
        'instance': instance,
        'datas': datas,
        'page_obj': page_obj
    })


@login_required
def delete_candidate_documents(request, id):
    instance = get_object_or_404(CandidateDocument, id=id)
    if request.method == 'POST':
        instance.delete()
        messages.success(request, "Deleted successfully!")
        return redirect('recruitment:create_candidate_documents')      

    messages.warning(request, "Invalid delete request!")
    return redirect('recruitment:create_candidate_documents')    


from.forms import JobRequestForm
from.forms import JobRequestProcessForm

# requester will submit job request with below form
@login_required
def manage_job(request, id=None):  
    instance = get_object_or_404(Job, id=id) if id else None
    message_text = "updated successfully!" if id else "added successfully!"  
    form = JobRequestForm(request.POST or None, request.FILES or None, instance=instance)

    if request.method == 'POST' and form.is_valid():
        form_intance=form.save(commit=False)
        form_intance.requester = request.user
        form_intance.is_active = False
        form_intance.save()        
        messages.success(request, message_text)
        return redirect('recruitment:create_job')  
    else:
        print(form.errors)

    datas = Job.objects.all().order_by('-created_at')
    paginator = Paginator(datas, 5)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    form = JobRequestForm( instance=instance)
    return render(request, 'recruitment/manage_job.html', {
        'form': form,
        'instance': instance,
        'datas': datas,
        'page_obj': page_obj
    })



@login_required
def delete_job(request, id):
    instance = get_object_or_404(Job, id=id)
    if request.method == 'POST':
        instance.delete()
        messages.success(request, "Deleted successfully!")
        return redirect('recruitment:create_job')    

    messages.warning(request, "Invalid delete request!")
    return redirect('recruitment:create_job')  



def job_request_list(request):    
    datas = Job.objects.all().order_by('-created_at')
    paginator = Paginator(datas, 5)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    return render(request, 'recruitment/job_request_list.html', {
        'datas': datas,
        'page_obj': page_obj
    })



@login_required
def process_job_requirement(request, id):
    requirement = get_object_or_404(Job, id=id)

    role_status_map = {
        "Requester": ["SUBMITTED", "CANCELLED"],
        "Reviewer": ["REVIEWED", "CANCELLED"],
        "Approver": ["APPROVED", "CANCELLED"],
    }

    if request.method == 'POST':
        form = JobRequestProcessForm(request.POST)
        if form.is_valid():  
            if requirement.approval_data is None:
                requirement.approval_data = {}         

            status = form.cleaned_data['status']
            remarks = form.cleaned_data['remarks']
            role = None

            user_roles = []
            if request.user.groups.filter(name="Requester").exists():
                user_roles.append("Requester")
            if request.user.groups.filter(name="Reviewer").exists():
                user_roles.append("Reviewer")
            if request.user.groups.filter(name="Approver").exists():
                user_roles.append("Approver")

            for user_role in user_roles:
                if status in role_status_map[user_role]:
                    role = user_role
                    break

            if not role:
                messages.error(
                    request,
                    "You do not have permission to perform this action or invalid status."
                )
                return redirect('recruitment:job_request_list')

            if role == "Requester":
                requirement.requester_approval_status = status
                requirement.Requester_remarks = remarks
            elif role == "Reviewer":
                requirement.reviewer_approval_status = status
                requirement.Reviewer_remarks = remarks
            elif role == "Approver":
                requirement.approver_approval_status = status
                requirement.Approver_remarks = remarks

            requirement.approval_data[role] = {
                'status': status,
                'remarks': remarks,
                'date': timezone.now().isoformat(),
            }

            requirement.save()
            messages.success(request, f"Order {requirement.id} successfully updated.")
            return redirect('recruitment:job_request_list')
        else:
            messages.error(request, "Invalid form submission.")
    else:
        form = JobRequestProcessForm()
    return render(request, 'recruitment/job_request_process.html', {'form': form, 'requirement': requirement})


def launch_job_by_hiring_manager(request, id):
    job_instance = get_object_or_404(Job, id=id)    
    if request.method == 'POST':
        form = JobForm(request.POST, request.FILES or None, instance=job_instance)        
        if form.is_valid():
            form_instance = form.save(commit=False)
            form_instance.is_active = True
            form_instance.save()            
            return redirect('recruitment:job_request_list') 
        else:
            print(form.errors)  
    else:
        form = JobForm(instance=job_instance)    
    return render(request, 'recruitment/launch_job.html', {'form': form, 'job_instance': job_instance})




@login_required
def manage_project(request, id=None):  
    instance = get_object_or_404(Project, id=id) if id else None
    message_text = "updated successfully!" if id else "added successfully!"  
    form = ProjectForm(request.POST or None, request.FILES or None, instance=instance)

    if request.method == 'POST' and form.is_valid():
        form_intance=form.save(commit=False)
        form_intance.user = request.user
        form_intance.save()        
        messages.success(request, message_text)
        return redirect('recruitment:create_project')  

    datas = Project.objects.all().order_by('-created_at')
    paginator = Paginator(datas, 5)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    return render(request, 'recruitment/manage_project.html', {
        'form': form,
        'instance': instance,
        'datas': datas,
        'page_obj': page_obj
    })


@login_required
def delete_project(request, id):
    instance = get_object_or_404(Project, id=id)
    if request.method == 'POST':
        instance.delete()
        messages.success(request, "Deleted successfully!")
        return redirect('recruitment:create_project')     

    messages.warning(request, "Invalid delete request!")
    return redirect('recruitment:create_project')    


@login_required
def manage_score_card(request, id=None):  
    instance = get_object_or_404(ScoreCard, id=id) if id else None
    message_text = "updated successfully!" if id else "added successfully!"  
    form = ScoreCardForm(request.POST or None, request.FILES or None, instance=instance)

    if request.method == 'POST' and form.is_valid():
        form_intance=form.save(commit=False)
        form_intance.user = request.user
        form_intance.save()        
        messages.success(request, message_text)
        return redirect('recruitment:create_score_card')  

    datas = ScoreCard.objects.all().order_by('-created_at')
    paginator = Paginator(datas, 5)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    return render(request, 'recruitment/cv/manage_score_card.html', {
        'form': form,
        'instance': instance,
        'datas': datas,
        'page_obj': page_obj
    })


@login_required
def delete_score_card(request, id):
    instance = get_object_or_404(ScoreCard, id=id)
    if request.method == 'POST':
        instance.delete()
        messages.success(request, "Deleted successfully!")
        return redirect('recruitment:create_score_card')     

    messages.warning(request, "Invalid delete request!")
    return redirect('recruitment:create_score_card')    


def score_card_detail(request, id):
    score_card = ScoreCard.objects.prefetch_related(
        'score_experience',
        'score_education',
        'score_institution',
        'score_esubject',        
        'score_skills',
        'score_age',
        'score_certification',

        'score_language__skill_levels'

       
    ).get(id=id)
  
    experiences = score_card.score_experience.all()
    educations = score_card.score_education.all()
    institutions = score_card.score_institution.all()
    subjects = score_card.score_esubject.all()

    skills = score_card.score_skills.all()
    ages = score_card.score_age.all()
    certifications = score_card.score_certification.all()
    languages = score_card.score_language.all()
   
   
    language_skills = []
    for language in languages:
        skill_levels = language.skill_levels.all()
        language_skills.append({'language': language, 'skill_levels': skill_levels,})

    return render(request, 'recruitment/cv/score_card_detail.html', {
        'score_card': score_card,
        'experiences': experiences,
        'educations': educations,
        'institutions': institutions,
        'subjects': subjects,

        'score_skills': skills,
        'score_ages': ages,
        'certifications': certifications,     
        'languages': language_skills,
    })


@login_required
def manage_experience(request, id=None):  
    instance = get_object_or_404(Experience, id=id) if id else None
    message_text = "updated successfully!" if id else "added successfully!"  
    form = ExperienceForm(request.POST or None, request.FILES or None, instance=instance)

    if request.method == 'POST' and form.is_valid():
        form_intance=form.save(commit=False)
        form_intance.user = request.user
        form_intance.save()        
        messages.success(request, message_text)
        return redirect('recruitment:create_experience')  

    datas = Experience.objects.all().order_by('-created_at')
    paginator = Paginator(datas, 5)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    return render(request, 'recruitment/cv/manage_experience.html', {
        'form': form,
        'instance': instance,
        'datas': datas,
        'page_obj': page_obj
    })



@login_required
def delete_experience(request, id):
    instance = get_object_or_404(Experience, id=id)
    if request.method == 'POST':
        instance.delete()
        messages.success(request, "Deleted successfully!")
        return redirect('recruitment:create_experience')      

    messages.warning(request, "Invalid delete request!")
    return redirect('recruitment:create_experience') 



@login_required
def manage_language(request, id=None):  
    instance = get_object_or_404(Experience, id=id) if id else None
    message_text = "updated successfully!" if id else "added successfully!"  
    form = LanguageForm(request.POST or None, request.FILES or None, instance=instance)

    if request.method == 'POST' and form.is_valid():
        form_intance=form.save(commit=False)
        form_intance.user = request.user
        form_intance.save()        
        messages.success(request, message_text)
        return redirect('recruitment:create_language')  

    datas = Language.objects.all().order_by('-created_at')
    paginator = Paginator(datas, 5)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    return render(request, 'recruitment/cv/manage_language.html', {
        'form': form,
        'instance': instance,
        'datas': datas,
        'page_obj': page_obj
    })



@login_required
def delete_language(request, id):
    instance = get_object_or_404(Language, id=id)
    if request.method == 'POST':
        instance.delete()
        messages.success(request, "Deleted successfully!")
        return redirect('recruitment:create_language')      

    messages.warning(request, "Invalid delete request!")
    return redirect('recruitment:create_language') 



@login_required
def manage_language_skill(request, id=None):  
    instance = get_object_or_404(LanguageSkillLevel, id=id) if id else None
    message_text = "updated successfully!" if id else "added successfully!"  
    form = LanguageSkillLevelForm(request.POST or None, request.FILES or None, instance=instance)

    if request.method == 'POST' and form.is_valid():
        form_intance=form.save(commit=False)
        form_intance.user = request.user
        form_intance.save()        
        messages.success(request, message_text)
        return redirect('recruitment:create_language_skill')  

    datas = LanguageSkillLevel.objects.all().order_by('-created_at')
    paginator = Paginator(datas, 5)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    return render(request, 'recruitment/cv/manage_language_skill.html', {
        'form': form,
        'instance': instance,
        'datas': datas,
        'page_obj': page_obj
    })


@login_required
def delete_language_skill(request, id):
    instance = get_object_or_404(LanguageSkillLevel, id=id)
    if request.method == 'POST':
        instance.delete()
        messages.success(request, "Deleted successfully!")
        return redirect('recruitment:create_language_skill')        

    messages.warning(request, "Invalid delete request!")
    return redirect('recruitment:create_language_skill')  


from.models import Education,EducationalInstitution,EducationalSubject,Age,Certification
from.forms import EducationalInstitutionForm,EducationalSubjectForm,EducationForm,AgeForm,CertificationForm
@login_required
def manage_education(request, id=None):  
    instance = get_object_or_404(Education, id=id) if id else None
    message_text = "updated successfully!" if id else "added successfully!"  
    form = EducationForm(request.POST or None, request.FILES or None, instance=instance)

    if request.method == 'POST' and form.is_valid():
        form_intance=form.save(commit=False)
        form_intance.user = request.user
        form_intance.save()        
        messages.success(request, message_text)
        return redirect('recruitment:create_education')  

    datas = Education.objects.all().order_by('-created_at')
    paginator = Paginator(datas, 5)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    return render(request, 'recruitment/skills/manage_education.html', {
        'form': form,
        'instance': instance,
        'datas': datas,
        'page_obj': page_obj
    })



@login_required
def delete_education(request, id):
    instance = get_object_or_404(Education, id=id)
    if request.method == 'POST':
        instance.delete()
        messages.success(request, "Deleted successfully!")
        return redirect('recruitment:create_education')        

    messages.warning(request, "Invalid delete request!")
    return redirect('recruitment:create_education')  

@login_required
def manage_edu_institution(request, id=None):  
    instance = get_object_or_404(EducationalInstitution, id=id) if id else None
    message_text = "updated successfully!" if id else "added successfully!"  
    form = EducationalInstitutionForm(request.POST or None, request.FILES or None, instance=instance)

    if request.method == 'POST' and form.is_valid():
        form_intance=form.save(commit=False)
        form_intance.user = request.user
        form_intance.save()        
        messages.success(request, message_text)
        return redirect('recruitment:create_edu_institution')  

    datas = EducationalInstitution.objects.all().order_by('-created_at')
    paginator = Paginator(datas, 5)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    return render(request, 'recruitment/skills/manage_edu_institution.html', {
        'form': form,
        'instance': instance,
        'datas': datas,
        'page_obj': page_obj
    })



@login_required
def delete_edu_institution(request, id):
    instance = get_object_or_404(EducationalInstitution, id=id)
    if request.method == 'POST':
        instance.delete()
        messages.success(request, "Deleted successfully!")
        return redirect('recruitment:create_edu_institution')        

    messages.warning(request, "Invalid delete request!")
    return redirect('recruitment:create_edu_institution')  



@login_required
def manage_edu_subject(request, id=None):  
    instance = get_object_or_404(EducationalSubject, id=id) if id else None
    message_text = "updated successfully!" if id else "added successfully!"  
    form = EducationalSubjectForm(request.POST or None, request.FILES or None, instance=instance)

    if request.method == 'POST' and form.is_valid():
        form_intance=form.save(commit=False)
        form_intance.user = request.user
        form_intance.save()        
        messages.success(request, message_text)
        return redirect('recruitment:create_edu_subject')  

    datas = EducationalSubject.objects.all().order_by('-created_at')
    paginator = Paginator(datas, 5)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    return render(request, 'recruitment/skills/manage_edu_subject.html', {
        'form': form,
        'instance': instance,
        'datas': datas,
        'page_obj': page_obj
    })



@login_required
def delete_edu_subject(request, id):
    instance = get_object_or_404(EducationalSubject, id=id)
    if request.method == 'POST':
        instance.delete()
        messages.success(request, "Deleted successfully!")
        return redirect('recruitment:create_edu_subject')         

    messages.warning(request, "Invalid delete request!")
    return redirect('recruitment:create_edu_subject')  




@login_required
def manage_certification(request, id=None):  
    instance = get_object_or_404(Certification, id=id) if id else None
    message_text = "updated successfully!" if id else "added successfully!"  
    form = CertificationForm(request.POST or None, request.FILES or None, instance=instance)

    if request.method == 'POST' and form.is_valid():
        form_intance=form.save(commit=False)
        form_intance.user = request.user
        form_intance.save()        
        messages.success(request, message_text)
        return redirect('recruitment:create_certification')  

    datas = Certification.objects.all().order_by('-created_at')
    paginator = Paginator(datas, 5)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    return render(request, 'recruitment/skills/manage_certification.html', {
        'form': form,
        'instance': instance,
        'datas': datas,
        'page_obj': page_obj
    })



@login_required
def delete_certificationt(request, id):
    instance = get_object_or_404(Certification, id=id)
    if request.method == 'POST':
        instance.delete()
        messages.success(request, "Deleted successfully!")
        return redirect('recruitment:create_certification')         

    messages.warning(request, "Invalid delete request!")
    return redirect('recruitment:create_certification')  



@login_required
def manage_age(request, id=None):  
    instance = get_object_or_404(Age, id=id) if id else None
    message_text = "updated successfully!" if id else "added successfully!"  
    form = AgeForm(request.POST or None, request.FILES or None, instance=instance)

    if request.method == 'POST' and form.is_valid():
        form_intance=form.save(commit=False)
        form_intance.user = request.user
        form_intance.save()        
        messages.success(request, message_text)
        return redirect('recruitment:create_age')  

    datas = Age.objects.all().order_by('-created_at')
    paginator = Paginator(datas, 5)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    return render(request, 'recruitment/skills/manage_age.html', {
        'form': form,
        'instance': instance,
        'datas': datas,
        'page_obj': page_obj
    })



@login_required
def delete_age(request, id):
    instance = get_object_or_404(Age, id=id)
    if request.method == 'POST':
        instance.delete()
        messages.success(request, "Deleted successfully!")
        return redirect('recruitment:create_age')         

    messages.warning(request, "Invalid delete request!")
    return redirect('recruitment:create_age')  


from.forms import skillsForm
from.models import Skills
@login_required
def manage_skills(request, id=None):  
    instance = get_object_or_404(Skills, id=id) if id else None
    message_text = "updated successfully!" if id else "added successfully!"  
    form = skillsForm(request.POST or None, request.FILES or None, instance=instance)

    if request.method == 'POST' and form.is_valid():
        form_intance=form.save(commit=False)
        form_intance.user = request.user
        form_intance.save()        
        messages.success(request, message_text)
        return redirect('recruitment:create_skill')  

    datas = Skills.objects.all().order_by('-created_at')
    paginator = Paginator(datas, 5)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    return render(request, 'recruitment/skills/manage_skills.html', {
        'form': form,
        'instance': instance,
        'datas': datas,
        'page_obj': page_obj
    })



@login_required
def delete_skills(request, id):
    instance = get_object_or_404(Skills, id=id)
    if request.method == 'POST':
        instance.delete()
        messages.success(request, "Deleted successfully!")
        return redirect('recruitment:create_skill')         

    messages.warning(request, "Invalid delete request!")
    return redirect('recruitment:create_skill')  



from.models import JobCategory
from.forms import JobCategoryForm

@login_required
def manage_job_category(request, id=None):  
    instance = get_object_or_404(JobCategory, id=id) if id else None
    message_text = "updated successfully!" if id else "added successfully!"  
    form = JobCategoryForm(request.POST or None, request.FILES or None, instance=instance)

    if request.method == 'POST' and form.is_valid():
        form_intance=form.save(commit=False)
        form_intance.user = request.user
        form_intance.is_active = True
        form_intance.save()        
        messages.success(request, message_text)
        return redirect('recruitment:create_job_category')  
    else:
        print(form.errors)

    datas = JobCategory.objects.all().order_by('-created_at')
    paginator = Paginator(datas, 5)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    form = JobCategoryForm( instance=instance)
    return render(request, 'recruitment/manage_job_category.html', {
        'form': form,
        'instance': instance,
        'datas': datas,
        'page_obj': page_obj
    })



@login_required
def delete_job_category(request, id):
    instance = get_object_or_404(JobCategory, id=id)
    if request.method == 'POST':
        instance.delete()
        messages.success(request, "Deleted successfully!")
        return redirect('recruitment:create_job_category')     

    messages.warning(request, "Invalid delete request!")
    return redirect('recruitment:create_job_category')   




def job_list(request):  
    jobs = Job.objects.all().order_by('-created_at')
    for job in jobs:
        if job.deadline < timezone.now().date():
            job.is_active = False
            job.save()
    candidates = Candidate.objects.all().order_by('-created_at')
    candidate = Candidate.objects.filter(candidate=request.user).first()    
    form = SearchApplicationForm()
    
    paginator = Paginator(jobs, 5)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    return render (request,'recruitment/job_list.html',{
        'jobs':jobs,
        'page_obj':page_obj,
         'jobs': jobs,
        'candidates': candidates,
        'candidate': candidate,
        'form':form
      
        })
    


def job_list_candidate_view(request): 
    jobs = Job.objects.all().order_by('-created_at')
    candidates = Candidate.objects.all()
    candidate = Candidate.objects.filter(candidate=request.user).first()
    exam_start_time = None
    exam_end_time = None
    current_time = timezone.now()   

    candidate_jobs = Job.objects.filter(
        id__in=Candidate.objects.filter(candidate=request.user).values_list('applied_job_id', flat=True)
    ).order_by('-created_at')


    # if candidate.status != 'Shortlisted':
    #     messages.info(request, "You are not shortlisted for this exam.")
    

    for job in jobs:
        if job.deadline < timezone.now().date():
            job.is_active = False
            job.save()
        exams = job.job_exam.all()
        for exam in exams:
            exam_start_time = localtime(exam.start_time).isoformat()
            exam_end_time = localtime(exam.end_time).isoformat()   
            
    if not exam.is_exam_active:
        messages.warning(request, 'The exam time has expired.')
        
    if exam.start_time > current_time:
        messages.info(request, 'The exam has not started yet')              

   

    paginator = Paginator(candidate_jobs, 5)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    return render (request,'recruitment/job_list_candidate_view.html',{
        'jobs':jobs,
        'page_obj':page_obj,
         'jobs': jobs,
        'candidates': candidates,
        'candidate': candidate,     

        'exam_start_time':  exam_start_time,
        'exam_end_time':  exam_end_time,
        'current_time': localtime(current_time).isoformat(),
      
        })



def job_list_interview_panel_view(request):  
    jobs = Job.objects.all().order_by('-created_at')
    for job in jobs:
        if job.deadline < timezone.now().date():
            job.is_active = False   
            job.save()

    form = SearchApplicationForm()
    paginator = Paginator(jobs, 5)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    return render (request,'recruitment/job_list_interview_panel_view.html',{
        'jobs':jobs,
        'page_obj':page_obj,
         'jobs': jobs,       
        'form':form
      
        })


def job_application(request, id):
    today = now().date()
    job = get_object_or_404(Job, id=id)

    candidate = job.candidates.filter(candidate=request.user).first()

    if request.method == "POST":
        form = CandidateForm(request.POST, request.FILES, instance=candidate)

        if form.is_valid():
            candidate_instance = form.save(commit=False)  
            candidate_instance.candidate = request.user         
            candidate_instance.save()
            form.save_m2m()
 
            candidate_instance.cv_screening_score = Decimal(candidate_instance.calculate_cv_screening_score())
            candidate_instance.save(update_fields=['cv_screening_score'])
            pass_marks = candidate_instance.applied_job.score_card.pass_marks
            if candidate.cv_screening_score >= pass_marks:
                candidate.cv_screening_status = 'SHORT-LISTED'
                candidate.status = 'SHORT-LISTED'
            else:
                candidate.cv_screening_status = 'REJECTED'
                candidate.status = 'REJECTED'

            candidate.save()         
            
            messages.success(request, "Your job application has been submitted successfully.")
            return redirect('customerportal:job_list_candidate_view')
        else:
            print(form.errors)
            messages.error(request, "There was an error with your application.")

    else:
        initial_data = {'applied_job': job}
        form = CandidateForm(initial=initial_data)

    return render(request, 'customerportal/recruitment/job_application_form.html', {
        'job': job,
        'form': form,
        'today': today
    })


def candidate_details(request,id):
    candidate =get_object_or_404(Candidate,id=id)
    return render(request,'recruitment/candidate_details.html',{'candidate':candidate})




def applicant_list(request, job_id):   
    job_instance = get_object_or_404(Job, id=job_id)
    form = SearchApplicationForm(request.GET or None)     
    candidates = job_instance.candidates.all().order_by('-created_at')
    no_results_message = None  

    if form.is_valid():
        query = form.cleaned_data.get('query')   
        if query:   
            candidates = candidates.filter(
                full_name__icontains=query
            ) | candidates.filter(email__icontains=query)

        if not candidates.exists():
            no_results_message = "No candidates found for the given search query."
    else:
        print('Form is invalid')  

    form = SearchApplicationForm() 
    paginator = Paginator(candidates, 10)  
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    return render(request, 'recruitment/applicant_list.html', {
        'page_obj': page_obj,
        'form': form,
        'job': job_instance,  
        'no_results_message': no_results_message,
    })



def get_exams_for_job(request, job_id):
    try:
        job = Job.objects.get(id=job_id)
        exams = job.job_exam.all()  
        exam_data = [{'id': exam.id, 'name': exam.title} for exam in exams]
        return JsonResponse({'exams': exam_data})
    except Job.DoesNotExist:
        return JsonResponse({'error': 'Job not found'}, status=404)



@login_required
def manage_exam(request, id=None):  
    instance = get_object_or_404(Job, id=id) if id else None
    message_text = "updated successfully!" if id else "added successfully!"  
    form = ExamForm(request.POST or None, request.FILES or None, instance=instance)

    if request.method == 'POST' and form.is_valid():
        form_intance=form.save(commit=False)
        form_intance.user = request.user
        form_intance.is_active = True
        form_intance.save()        
        messages.success(request, message_text)
        return redirect('recruitment:create_exam')  
    else:
        print(form.errors)

    datas = Exam.objects.all().order_by('-created_at')
    paginator = Paginator(datas, 5)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    form = ExamForm( instance=instance)
    return render(request, 'recruitment/manage_exam.html', {
        'form': form,
        'instance': instance,
        'datas': datas,
        'page_obj': page_obj
    })



@login_required
def delete_exam(request, id):
    instance = get_object_or_404(Exam, id=id)
    if request.method == 'POST':
        instance.delete()
        messages.success(request, "Deleted successfully!")
        return redirect('recruitment:create_exam')    

    messages.warning(request, "Invalid delete request!")
    return redirect('recruitment:create_exam')  




def job_exam_list(request, job_id):
    job = get_object_or_404(Job, id=job_id)
    exams = Exam.objects.filter(job=job)
    
    panel_members = PanelMember.objects.filter(
        panel__job=job,
        panel_member__user_profile__user=request.user
    ).distinct()  # Avoid duplicates

   
    exam_candidates = []
    for exam in exams:
        take_exams = exam.exam_attempts.all()
        for take_exam in take_exams:
            candidate = take_exam.candidate
            if candidate not in exam_candidates:
                exam_candidates.append(candidate)

    return render(request, 'recruitment/job_exam_list.html', {
        'job': job,
        'exams': exams,
        'panel_members': panel_members,
        'exam_candidates': exam_candidates,
       
    })



def exam_list(request):   
    datas = Exam.objects.all().order_by('-created_at')
    paginator = Paginator(datas, 5)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    return render (request,'recruitment/exam_list.html',{'page_obj':page_obj})
    


def exam_details(request,exam_id):   
    exam_instance = get_object_or_404(Exam,id = exam_id)
    return render (request,'recruitment/exam_details.html',{'data':exam_instance})
    



@login_required
def manage_questions(request, id=None):  
    instance = get_object_or_404(Question, id=id) if id else None
    message_text = "updated successfully!" if id else "added successfully!"  
    form = QuestionForm(request.POST or None, request.FILES or None, instance=instance)

    if request.method == 'POST' and form.is_valid():
        form_intance=form.save(commit=False)
        form_intance.user = request.user
        form_intance.is_active = True
        form_intance.save()        
        messages.success(request, message_text)
        return redirect('recruitment:create_questions')  
    else:
        print(form.errors)

    datas = Question.objects.all().order_by('-created_at')
    paginator = Paginator(datas, 5)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    form = QuestionForm( instance=instance)
    return render(request, 'recruitment/manage_question.html', {
        'form': form,
        'instance': instance,
        'datas': datas,
        'page_obj': page_obj
    })

def question_paper(request,exam_id):
    exam_instance = get_object_or_404(Exam,id = exam_id)
    questions = exam_instance.questions.all()
    return render(request,'recruitment/exam_question_paper.html',{'questions':questions})




@login_required
def delete_question(request, id):
    instance = get_object_or_404(Question, id=id)
    if request.method == 'POST':
        instance.delete()
        messages.success(request, "Deleted successfully!")
        return redirect('recruitment:create_question')   

    messages.warning(request, "Invalid delete request!")
    return redirect('recruitment:create_question')  




from django.shortcuts import redirect, get_object_or_404
from django.utils.timezone import localtime

def pre_take_exam(request, exam_id, candidate_id):
    exam = get_object_or_404(Exam, id=exam_id)
    candidate = get_object_or_404(Candidate, id=candidate_id)
    current_time = timezone.now()
 
    if current_time <= exam.start_time:
        return redirect('recruitment:take_exam', exam_id=exam.id, candidate_id=candidate.id)
    
    return render(request, 'recruitment/pre_take_exam.html', {
        'exam': exam,
        'candidate': candidate,
        'exam_start_time': localtime(exam.start_time).isoformat(),
        'exam_end_time': localtime(exam.end_time).isoformat(),
        'current_time': localtime(current_time).isoformat(),
    })


from django.utils.timezone import now

def take_exam(request, exam_id, candidate_id):
    exam = get_object_or_404(Exam, id=exam_id)
    candidate = get_object_or_404(Candidate, id=candidate_id)

    # if candidate.status != 'Shortlisted':
    #     messages.info(request, "You are not shortlisted for this exam.")
    #     return redirect('recruitment:job_list')  

    current_time = timezone.now()
    # if exam.is_expired():
    #     messages.warning(request, 'The exam time has expired. You can no longer take this exam.')
    #     return redirect('recruitment:job_list')
    # if exam.start_time > current_time:
    #     messages.info(request, 'The exam has not started yet. Please wait.')
    #     return redirect('recruitment:job_list')

    # if TakeExam.objects.filter(candidate=candidate, exam=exam).exists():
    #     messages.warning(request, "You have already attempted this exam. Multiple attempts are not allowed.")
    #     return redirect('recruitment:result', exam_id=exam.id, candidate_id=candidate.id)  


    

    questions = exam.questions.all()

    if request.method == "POST":
        form = TakeExamForm(questions, request.POST)
        if form.is_valid():
            if exam.end_time <= current_time:
                messages.warning(request, 'The exam time has expired. You cannot submit the exam paper.')
                return redirect('recruitment:job_list')

            total_marks = 0
            for question in questions:
                selected_option = form.cleaned_data.get(f'question_{question.id}')
                is_correct = selected_option == question.correct_answer  
                question_marks = question.marks if is_correct else 0  
                total_marks += question_marks

                TakeExam.objects.create(
                    candidate=candidate,
                    exam=exam,
                    question=question,
                    selected_option=selected_option,
                    obtained_marks=question_marks
                )
            
            
            candidate.exam_status = 'EXAM-PASS' if total_marks >= exam.pass_marks else 'EXAM-FAIL'
            candidate.exam_score = Decimal(total_marks)
            candidate.mcq_bq_score = float(candidate.bq_exam_score) + float(total_marks)
            candidate.total_score =  float(candidate.bq_exam_score) + float(total_marks) + float(candidate.cv_screening_score) + float(candidate.interview_score)
            candidate.save()  
            exam.is_active = False
            exam.save() 
                   

            broad_question_paper = BQQuestionPaper.objects.filter(job=exam.job).first()

            if broad_question_paper:
                return redirect('recruitment:take_bq_exam', paper_id=broad_question_paper.id, candidate_id=candidate.id)
            else:
                messages.warning(request, "No Broad Question Paper found for this job.")
                return redirect('recruitment:result', exam_id=exam.id, candidate_id=candidate.id)

            #return redirect(reverse('recruitment:result', kwargs={'exam_id': exam.id, 'candidate_id': candidate.id}))
    else:
        form = TakeExamForm(questions)
    return render(request, 'customerportal/recruitment/take_exam.html', {
        'exam': exam,
        'candidate': candidate,
        'form': form,
        'exam_start_time': localtime(exam.start_time).isoformat(),
        'exam_end_time': localtime(exam.end_time).isoformat(),
        'current_time': localtime(now()).isoformat(),
    })



def result(request, exam_id, candidate_id):
    exam = get_object_or_404(Exam, id=exam_id)
    candidate = get_object_or_404(Candidate, id=candidate_id)    
    question_answers = TakeExam.objects.filter(exam=exam, candidate=candidate)     
    score = 0
    for answer in question_answers:
        question = answer.question      
        if answer.selected_option == question.correct_answer:
            answer.is_correct = True
            score += question.marks
        else:
            answer.is_correct = False
        answer.save() 
    
    candidate.exam_score = score
    candidate.save()

    return render(request, 'recruitment/result.html', {
        'exam': exam,
        'candidate': candidate,
        'candidate_answers': question_answers,
        'score': score,
        'total_questions': question_answers.count(),
    })




def search_applications(request):
    form = SearchApplicationForm(request.GET or None)  
    candidates = Candidate.objects.all()  

    if form.is_valid(): 
        query = form.cleaned_data.get('query')
        if query:   
            candidates = candidates.filter(
                full_name__icontains=query
            ) | candidates.filter(email__icontains=query)

    return render(request, 'recruitment/search_applications.html', {
        'form': form,
        'candidates': candidates,
    })





from.models import Panel
from.forms import PanelForm

@login_required
def manage_panel(request, id=None):  
    instance = get_object_or_404(Panel, id=id) if id else None
    message_text = "updated successfully!" if id else "added successfully!"  
    form = PanelForm(request.POST or None, request.FILES or None, instance=instance)

    if request.method == 'POST' and form.is_valid():
        form_intance=form.save(commit=False)
        form_intance.user = request.user
        form_intance.is_active = True
        form_intance.save()      
        form.save_m2m()  
        messages.success(request, message_text)
        return redirect('recruitment:create_panel')  
    else:
        print(form.errors)

    datas = Panel.objects.all().order_by('-created_at')
    paginator = Paginator(datas, 5)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    form = PanelForm( instance=instance)
    return render(request, 'recruitment/manage_panel.html', {
        'form': form,
        'instance': instance,
        'datas': datas,
        'page_obj': page_obj
    })



@login_required
def delete_panel(request, id):
    instance = get_object_or_404(Panel, id=id)
    if request.method == 'POST':
        instance.delete()
        messages.success(request, "Deleted successfully!")
        return redirect('recruitment:create_panel')     

    messages.warning(request, "Invalid delete request!")
    return redirect('recruitment:create_panel')  


def panel_details(request,id):
    panel =get_object_or_404(Panel,id=id)
    return render(request,'recruitment/panel_details.html',{'panel':panel})

from django.conf import settings
@login_required
def manage_panel_member(request, id=None):  
    instance = get_object_or_404(PanelMember, id=id) if id else None
    message_text = "updated successfully!" if id else "added successfully!"  
    form = PanelMemberForm(request.POST or None, request.FILES or None, instance=instance)

    if request.method == 'POST' and form.is_valid():
        panel_member = form.cleaned_data['panel_member']  # Get the selected Employee
        form_instance = form.save(commit=False)
        form_instance.user = request.user
        form_instance.is_active = True
        form_instance.save()     
        form.save_m2m()   
        messages.success(request, message_text)
     
        recipient_email = panel_member.email         

        if recipient_email:
            subject = "Interview Panel Assignment Notification"
            message = f"Dear {panel_member.name},\n\nYou have been added as a panel member for an interview. Please check the system for details.\n\nBest regards,\nRecruitment Team"
            
            send_mail(
                subject,
                message,
                settings.DEFAULT_FROM_EMAIL,
                [recipient_email],
                fail_silently=False,
            )

        return redirect('recruitment:create_panel_member')  

    datas = PanelMember.objects.all().order_by('-created_at')
    paginator = Paginator(datas, 5)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    form = PanelMemberForm(instance=instance)

    return render(request, 'recruitment/manage_panel_member.html', {
        'form': form,
        'instance': instance,
        'datas': datas,
        'page_obj': page_obj
    })


@login_required
def delete_panel_member(request, id):
    instance = get_object_or_404(Job, id=id)
    if request.method == 'POST':
        instance.delete()
        messages.success(request, "Deleted successfully!")
        return redirect('recruitment:create_panel_member')     

    messages.warning(request, "Invalid delete request!")
    return redirect('recruitment:create_panel_member')  



from.forms import ManageInterviewForm

@login_required
def manage_interview(request, id=None):  
    instance = get_object_or_404(Interview, id=id) if id else None
    message_text = "updated successfully!" if id else "added successfully!"  
    form = ManageInterviewForm(request.POST or None, request.FILES or None, instance=instance)

    if request.method == 'POST' and form.is_valid():
        form_intance=form.save(commit=False)
        form_intance.user = request.user
        form_intance.is_active = True
        form_intance.save()      
        form.save_m2m()  
        messages.success(request, message_text)
        return redirect('recruitment:create_interview')  
    else:
        print(form.errors)

    datas = Interview.objects.all().order_by('-created_at')
    paginator = Paginator(datas, 5)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    form = ManageInterviewForm( instance=instance)
    return render(request, 'recruitment/interview/manage_interview.html', {
        'form': form,
        'instance': instance,
        'datas': datas,
        'page_obj': page_obj
    })



@login_required
def delete_interview(request, id):
    instance = get_object_or_404(Interview, id=id)
    if request.method == 'POST':
        instance.delete()
        messages.success(request, "Deleted successfully!")
        return redirect('recruitment:create_interview')     

    messages.warning(request, "Invalid delete request!")
    return redirect('recruitment:create_interview')  





def panel_member_scoring(request, job_id, exam_id, candidate_id, panel_member_id):
    job = get_object_or_404(Job, id=job_id)
    exam = get_object_or_404(Exam, id=exam_id)
    candidate = get_object_or_404(Candidate, id=candidate_id, applied_job=job)
    panel_member = get_object_or_404(PanelMember, id=panel_member_id, panel__job=job, panel__exam=exam)

    total_score = 0
    average_score = 0  

    interview = Interview.objects.filter(job=job, exam=exam).first()
    if interview:
        if interview.candidate is None:
            interview.candidate = candidate
            interview.save()
    else:
        interview = Interview.objects.create(
            candidate=candidate,
            job=job,
            exam=exam,
            total_score=50,
            pass_score=30
        )


    score_instance, created = InterviewScore.objects.get_or_create(
        interview=interview,
        panel_member=panel_member
    )
    if  InterviewScore.objects.filter(
        interview__job=job,
        interview__exam=exam,
        interview__candidate=candidate,
        panel_member__panel_member__user_profile__user = request.user
    ).exists:
        messages.warning(request,'you have taken interview for this candidate alreay')
        return redirect('recruitment:job_list')


    # Only panel members in the same panel can interview this candidate
    panel_members = PanelMember.objects.filter(panel__job=job, panel__exam=exam)
    interviewed_panel_members = InterviewScore.objects.filter(
        interview__job=job, interview__exam=exam, interview__candidate=candidate
    ).values_list('panel_member_id', flat=True)

    if request.method == 'POST':
        form = PanelScoreForm(request.POST, instance=score_instance)
        if form.is_valid():
            form_instance = form.save(commit=False)

            x = form.cleaned_data['communication_skill_score']
            y = form.cleaned_data['technical_skill_score']
            z = form.cleaned_data['interpersonal_skill_score']
            m = form.cleaned_data['managerial_skill_score']
            n = form.cleaned_data['problem_solving_score']

            total_interview_score = x + y + z + m + n
            average_interview_score = float(total_interview_score) /float( 5.0)
            form_instance.total_score = total_interview_score
            form_instance.avg_score = average_interview_score
            form_instance.save()            
            
            scores = InterviewScore.objects.filter(interview__candidate=candidate)
            aggregate_scores = scores.aggregate(            
                total_score=Sum(
                    F('communication_skill_score') +
                    F('technical_skill_score') +
                    F('interpersonal_skill_score') +
                    F('managerial_skill_score') +
                    F('problem_solving_score')
                ),
            )

            candidate_total_score = aggregate_scores['total_score'] or 0
            num_panel_members = scores.count()
            candidate_interview_scores = candidate_total_score / (num_panel_members) if num_panel_members > 0 else 0
                
            candidate.interview_score = candidate_interview_scores
            pass_marks = interview.pass_score
            if float(candidate_interview_scores) >= pass_marks:
                candidate.interview_status = 'INTERVIEW-PASS'
                candidate.status = 'SELECTED'
            else:
                candidate.interview_status = 'INTERVIEW-FAIL'

            candidate.save()      


            messages.success(request, "Scoring has been successfully saved.")
            return redirect('recruitment:job_list')
        else:                   
            print(form.errors)   

    initial = {
        'interview': score_instance.interview,
        'panel_member': score_instance.panel_member
    }

    form = PanelScoreForm(initial=initial)    

    return render(request, 'recruitment/interview/panel_score.html', {
        'form': form,
        'candidate': candidate,
        'panel_member': panel_member,
        'job': job,
        'exam': exam,
        'score_instance': score_instance,
        'total_score': total_score,
        'average_score': average_score
    })


def candidate_interview_scores(request, candidate_id):
    candidate = get_object_or_404(Candidate, id=candidate_id)
    scores = InterviewScore.objects.filter(interview__candidate=candidate)
    cv_screening_score = candidate.cv_screening_score
    exam_score = candidate.exam_score
    mcq_bq_exam_score = candidate.mcq_bq_score
    bq_exam_score = candidate.bq_exam_score

    total_interview_score = sum(score.avg_score for score in scores if score.avg_score or 0)
    average_interview_score =  total_interview_score / scores.count() if scores.exists() else 0

    total_average_score= (float(cv_screening_score) + float(mcq_bq_exam_score) + float(average_interview_score)) / 3.0

    return render(request, 'recruitment/interview/candidate_interview_score.html', {
        'candidate': candidate,
        'scores': scores,
        'total_interview_score':  total_interview_score,
        'cv_screening_score': cv_screening_score,
        'exam_score': exam_score,
        'bq_exam_score':bq_exam_score,
        'mcq_bq_exam_score': mcq_bq_exam_score,
        'average_interview_score':average_interview_score,
        'total_average_score':total_average_score
    })





def cv_screening(request):
    jobs = Job.objects.all()
    exam_name = None
    job_title = None
    chart_data = {}
    total_candidates = 0
    No_of_candidate_fail = 0
    No_of_candidate_pass = 0
    threshold_score=0

    cv_history = CandidateScreeningHistory.objects.all()

    if request.method == 'POST':
        form = ShortlistThresholdForm(request.POST)
        if form.is_valid():
            threshold_score = form.cleaned_data['threshold_score']
            job_title = form.cleaned_data['job_title']
            exam_name = form.cleaned_data['exam']
            record_created = False

            if job_title:
                jobs = jobs.filter(title__icontains=job_title)

                for job in jobs:
                    if exam_name:
                        exams = job.job_exam.filter(title__icontains=exam_name)
                    else:
                        exams = job.job_exam.all()
                    
                    for exam in exams:
                        candidates = job.candidates.all()
                        for candidate in candidates:
                            if candidate.exam_score is not None:
                                if candidate.cv_screening_score >= threshold_score:
                                    candidate.cv_screening_status = 'SHORT-LISTED'
                                else:
                                    candidate.cv_screening_status = 'REJECTED'
                                candidate.save()                             

                                latest_screening = CandidateScreeningHistory.objects.filter(
                                    candidate=candidate, job=job
                                ).order_by('-screening_round').first()

                                if  latest_screening and  latest_screening.threshold_score == threshold_score:
                                    continue

                                screening_round = (latest_screening.screening_round or 0) + 1 if latest_screening else 1

                                # Create new screening record
                                CandidateScreeningHistory.objects.create(
                                    candidate=candidate,
                                    status=candidate.cv_screening_status,
                                    threshold_score=threshold_score,
                                    job=job,
                                    exam=exam,
                                    screening_round=screening_round
                                     )   
                                record_created = True

                if record_created:
                    messages.success(request, "The screening process was completed successfully.")
                else:
                    messages.warning(request, "No new record created. The last threshold score is the same as before.")                                               
        else:
            messages.success(request, "Form submission fail.")
            print(form.errors)
            form = ShortlistThresholdForm()

    if not chart_data:
        cv_screening_result = Candidate.objects.all()
        total = cv_screening_result.aggregate(
            candidate_pass=Count('id', filter=Q(cv_screening_status='SHORT-LISTED')),
            candidate_fail=Count('id', filter=Q(cv_screening_status='REJECTED'))
        )

        No_of_candidate_pass = total['candidate_pass']
        No_of_candidate_fail = total['candidate_fail']
        total_candidates = No_of_candidate_pass + No_of_candidate_fail

        chart_data = {
            'labels': ['Total Candidates', 'No of Candidate Pass', 'No of Candidate Fail'],
            'values': [total_candidates, No_of_candidate_pass, No_of_candidate_fail],
        }
   
    candidate_name = request.GET.get('candidate_name', '')
    number_of_top = request.GET.get('number_of_top', 5)
    try:
        number_of_top = int(number_of_top)
    except ValueError:
        number_of_top = 5

    cv_history = CandidateScreeningHistory.objects.all().order_by('-screening_round')
    if candidate_name:
        cv_history = cv_history.filter(candidate__full_name__icontains=candidate_name)

    paginator = Paginator(cv_history, 8)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    form = ShortlistThresholdForm()
    return render(request, 'recruitment/cv/cv_screening.html', {
        'form': form,
        'jobs': jobs,
        'page_obj': page_obj,
        'threshold_score': threshold_score,
        'total_candidates': total_candidates,
        'No_of_candidate_pass': No_of_candidate_pass,
        'No_of_candidate_fail': No_of_candidate_fail,
        'chart_data': json.dumps(chart_data),
    })




def exam_screening(request):
    jobs = Job.objects.all()
    exam_name = None
    job_title = None
    chart_data = {}
    total_candidates = 0
    No_of_candidate_fail = 0
    No_of_candidate_pass = 0
    threshold_score=0

    exam_history = ExamScreeningHistory.objects.all()

    if request.method == 'POST':
        form = ShortlistThresholdForm(request.POST)
        if form.is_valid():
            threshold_score = form.cleaned_data['threshold_score']
            job_title = form.cleaned_data['job_title']
            exam_name = form.cleaned_data['exam']
            record_created = True

            if job_title:
                jobs = jobs.filter(title__icontains=job_title)

                for job in jobs:
                    if exam_name:
                        exams = job.job_exam.filter(title__icontains=exam_name)
                    else:
                        exams = job.job_exam.all()
                    for exam in exams:
                        candidates = job.candidates.all()
                        for candidate in candidates:
                            if candidate.mcq_bq_score is not None:                                
                                if candidate.mcq_bq_score >= threshold_score:                                   
                                    candidate.mcq_bq_exam_status = 'EXAM-PASS'                                    
                                else:                                    
                                    candidate.mcq_bq_exam_status = 'EXAM-FAIL'                                 
                                candidate.save()
                                latest_screening = ExamScreeningHistory.objects.filter(candidate=candidate, job=job).order_by('-screening_round').first()
                                if latest_screening and latest_screening.threshold_score == threshold_score:
                                    continue  #                                
                                screening_round = (latest_screening.screening_round or 0) + 1 if latest_screening else 1

                                ExamScreeningHistory.objects.create(
                                    candidate=candidate,
                                    status=candidate.mcq_bq_exam_status,
                                    threshold_score=threshold_score,
                                    job=job,
                                    exam=exam,
                                    screening_round=screening_round
                                )
                                record_created = True
                
                if record_created:
                    messages.success(request, "The screening process was completed successfully.")
                else:
                    messages.warning(request, "No new record created. The last threshold score is the same as before.")
                          
       
            exam_screening_result = Candidate.objects.all()

            if job_title:
                exam_screening_result = exam_screening_result.filter(applied_job__title=job_title)

            total = exam_screening_result.aggregate(
                candidate_pass=Count('id', filter=Q(mcq_bq_exam_status='EXAM-PASS')),
                candidate_fail=Count('id', filter=Q(mcq_bq_exam_status='EXAM-FAIL'))
            )

            No_of_candidate_pass = total['candidate_pass']
            No_of_candidate_fail = total['candidate_fail']
            total_candidates = No_of_candidate_pass + No_of_candidate_fail

            chart_data = {
                'labels': ['Total Candidates', 'No of Candidate Pass', 'No of Candidate Fail'],
                'values': [total_candidates, No_of_candidate_pass, No_of_candidate_fail],
            }
        else: 
            print(form.errors)
            messages.success(request, "Form submissin fail.")
            form = ShortlistThresholdForm()

           

    if not chart_data:
        exam_screening_result = Candidate.objects.all()
        total = exam_screening_result.aggregate(
            candidate_pass=Count('id', filter=Q(mcq_bq_exam_status='EXAM-PASS')),
            candidate_fail=Count('id', filter=Q(mcq_bq_exam_status='EXAM-FAIL'))
        )

        No_of_candidate_pass = total['candidate_pass']
        No_of_candidate_fail = total['candidate_fail']
        total_candidates = No_of_candidate_pass + No_of_candidate_fail

        chart_data = {
            'labels': ['Total Candidates', 'No of Candidate Pass', 'No of Candidate Fail'],
            'values': [total_candidates, No_of_candidate_pass, No_of_candidate_fail],
        }
   
    candidate_name = request.GET.get('candidate_name', '')
    number_of_top = request.GET.get('number_of_top', 5)
    try:
        number_of_top = int(number_of_top)
    except ValueError:
        number_of_top = 5

    exam_history = ExamScreeningHistory.objects.all().order_by('-screening_round')
    if candidate_name:
        exam_history = exam_history.filter(candidate__full_name__icontains=candidate_name)

    paginator = Paginator(exam_history, 8)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    form = ShortlistThresholdForm()
    return render(request, 'recruitment/cv/exam_screening.html', {
        'form': form,
        'jobs': jobs,
        'page_obj': page_obj,
        'threshold_score': threshold_score,
        'total_candidates': total_candidates,
        'No_of_candidate_pass': No_of_candidate_pass,
        'No_of_candidate_fail': No_of_candidate_fail,
        'chart_data': json.dumps(chart_data),
    })





def interview_screening(request):
    jobs = Job.objects.all()
    exam_name = None
    job_title = None
    chart_data = {}
    total_candidates = 0
    No_of_candidate_fail = 0
    No_of_candidate_pass = 0
    threshold_score=0
    page_obj=None

    interview_history = InterviewScreeningHistory.objects.all()

    if request.method == 'POST':
        form = ShortlistThresholdForm(request.POST)
        if form.is_valid():
            threshold_score = form.cleaned_data['threshold_score']
            job_title = form.cleaned_data['job_title']
            exam_name = form.cleaned_data['exam']
            record_created = False
            if job_title:
                jobs = jobs.filter(title__icontains=job_title)
                for job in jobs:
                    if exam_name:
                        exams = job.job_exam.filter(title__icontains=exam_name)
                    else:
                        exams = job.job_exam.all()
                    for exam in exams:
                        candidates = job.candidates.all()
                        for candidate in candidates:
                            if candidate.interview_score is not None:                                
                                if candidate.interview_score >= threshold_score:                                   
                                    candidate.interview_status = 'INTERVIEW-PASS'                                    
                                else:                                    
                                    candidate.interview_status = 'INTERVIEW-FAIL'                                 
                                candidate.save()
                                latest_screening = InterviewScreeningHistory.objects.filter(candidate=candidate, job=job).order_by('-screening_round').first()
                                if latest_screening and latest_screening.threshold_score == threshold_score:
                                    continue  #                                
                                screening_round = (latest_screening.screening_round or 0) + 1 if latest_screening else 1
                                InterviewScreeningHistory.objects.create(
                                    candidate=candidate,
                                    status=candidate.interview_status,
                                    threshold_score=threshold_score,
                                    job=job,
                                    exam=exam,
                                    screening_round=screening_round
                                )
                                record_created = True
                if record_created:
                    messages.success(request, "The screening process was completed successfully.")
                else:
                    messages.warning(request, "No new record created. The last threshold score is the same as before.")
                                          
            interview_screening_result = Candidate.objects.all()
            if job_title:
                interview_screening_result = interview_screening_result.filter(applied_job__title=job_title)

            total = interview_screening_result.aggregate(
                candidate_pass=Count('id', filter=Q(interview_status='INTERVIEW-PASS')),
                candidate_fail=Count('id', filter=Q(interview_status='INTERVIEW-FAIL'))
            )

            No_of_candidate_pass = total['candidate_pass']
            No_of_candidate_fail = total['candidate_fail']
            total_candidates = No_of_candidate_pass + No_of_candidate_fail

            chart_data = {
                'labels': ['Total Candidates', 'No of Candidate Pass', 'No of Candidate Fail'],
                'values': [total_candidates, No_of_candidate_pass, No_of_candidate_fail],
            }           

            if not chart_data:
                interview_screening_result = Candidate.objects.all()
                total = interview_screening_result.aggregate(
                    candidate_pass=Count('id', filter=Q(interview_status='INTERVIEW-PASS')),
                    candidate_fail=Count('id', filter=Q(interview_status='INTERVIEW-FAIL'))
                )

                No_of_candidate_pass = total['candidate_pass']
                No_of_candidate_fail = total['candidate_fail']
                total_candidates = No_of_candidate_pass + No_of_candidate_fail

                chart_data = {
                    'labels': ['Total Candidates', 'No of Candidate Pass', 'No of Candidate Fail'],
                    'values': [total_candidates, No_of_candidate_pass, No_of_candidate_fail],
                }
        
            candidate_name = request.GET.get('candidate_name', '')
            number_of_top = request.GET.get('number_of_top', 5)
            try:
                number_of_top = int(number_of_top)
            except ValueError:
                number_of_top = 5

            interview_history = InterviewScreeningHistory.objects.all().order_by('-screening_round')
            if candidate_name:
                interview_history = interview_history.filter(candidate__full_name__icontains=candidate_name)
        
            paginator = Paginator(interview_history, 8)
            page_number = request.GET.get('page')
            page_obj = paginator.get_page(page_number)
        else:
            print(form.errors)
            messages.error(request, "Form submission failed. Please check your input.")
            form = ShortlistThresholdForm()    

    form = ShortlistThresholdForm()
    return render(request, 'recruitment/cv/interview_screening.html', {
        'form': form,
        'jobs': jobs,
        'page_obj': page_obj,
        'threshold_score': threshold_score,
        'total_candidates': total_candidates,
        'No_of_candidate_pass': No_of_candidate_pass,
        'No_of_candidate_fail': No_of_candidate_fail,
        'chart_data': json.dumps(chart_data),
    })




def selected_candidate(request):
    candidates = Candidate.objects.filter(status='SELECTED')
    all_candidates = Candidate.objects.all()
    job_title=None
    total_selected_candidates=None
    total_candidates=None
    percentage_selected=None
    total_offer_candidates=None
    total_waitlist_candidates=None
    total_confirmed_candidates=None
    total_onboard_candidates=None
    chart_data={}
    form_name = request.POST.get('form_name', '')

    form = SelectedCandidateForm(request.POST)
    if request.method == 'POST' and form_name == 'form-1':        
        form = SelectedCandidateForm(request.POST)
        if form.is_valid():
            job_title = form.cleaned_data['job_title']
            candidate_name = form.cleaned_data['candidate_name']
            if job_title:
                candidates = candidates.filter(applied_job__title=job_title)
            if candidate_name:
                candidates = candidates.filter(full_name__icontains=candidate_name)
            total_candidates =  all_candidates.count()
            total_selected_candidates = candidates.count()

            total_offer_candidates = candidates.filter(offer_status='offered').count()
            total_waitlist_candidates = candidates.filter(offer_status='waitlist').count()
            total_confirmed_candidates = candidates.filter(confirmation_status='accepted').count()
            total_onboard_candidates = candidates.filter(onboard_status='onboard').count()
                                        
            Selected = (total_selected_candidates / total_candidates * 100.0) if total_candidates > 0 else 0
            Offerred = (total_offer_candidates / total_candidates * 100.0) if total_candidates > 0 else 0
            Waitlist = (total_waitlist_candidates / total_candidates * 100.0) if total_candidates > 0 else 0
            Confirmed = (total_confirmed_candidates / total_candidates * 100.0) if total_candidates > 0 else 0
            Onboarded = (total_onboard_candidates / total_candidates * 100.0) if total_candidates > 0 else 0
            
            
            
            chart_data = {
                'labels': ['Selected', 'Offerred', 'Waitlist','Confirmed','Onboarded'],
                'values': [Selected, Offerred, Waitlist,Confirmed,Onboarded],
                    }                     
        
                         
        else:
            form = SelectedCandidateForm()
            print(form.errors)         
              
    paginator = Paginator(candidates, 8)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
 
    return render(request,'recruitment/selected_candidates.html',
        {
        'page_obj':page_obj,
        'form':form,
        'job_title':job_title,
        'total_candidates': total_candidates,
        'total_selected_candidates': total_selected_candidates,      
        'total_offer_candidates': total_offer_candidates,
        'total_waitlist_candidates':  total_waitlist_candidates,
        'total_confirmed_candidates':total_confirmed_candidates,
        'total_onboard_candidates': total_onboard_candidates,
        'chart_data':json.dumps(chart_data)
        })



def selected_candidates_with_id(request, job_id):
    job = get_object_or_404(Job, id=job_id)  # Get the Job instance
    candidates = Candidate.objects.filter(applied_job=job).order_by('-total_score')


    total_candidates = candidates.count()
    total_selected_candidates = candidates.filter(
        status='SELECTED',
        mcq_bq_exam_status='EXAM-PASS',
        interview_status = 'INTERVIEW-PASS',
        ).count()
    total_offer_candidates = candidates.filter(offer_status='offered').count()
    total_waitlist_candidates = candidates.filter(offer_status='waitlist').count()
    total_confirmed_candidates = candidates.filter(confirmation_status='accepted').count()
    total_onboard_candidates = candidates.filter(onboard_status='onboard').count()


    percentage_selected = (total_selected_candidates / total_candidates * 100.0) if total_candidates > 0 else 0
    percentage_offer = (total_offer_candidates / total_candidates * 100.0) if total_candidates > 0 else 0
    percentage_waitlist = (total_waitlist_candidates / total_candidates * 100.0) if total_candidates > 0 else 0
    percentage_confirmed = (total_confirmed_candidates / total_candidates * 100.0) if total_candidates > 0 else 0
    percentage_onboard = (total_onboard_candidates / total_candidates * 100.0) if total_candidates > 0 else 0

    chart_data = {
        'labels': ['% Selected', '% Offer', '% waitlist','% Confirmed','% Onboard'],
        'values': [percentage_selected, percentage_offer, percentage_waitlist,percentage_confirmed,percentage_onboard],
    }

    paginator = Paginator(candidates, 8)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    return render(request, 'recruitment/selected_candidates.html', {
        'page_obj': page_obj,
        'job': job,
        'total_candidates': total_candidates,
        'total_selected_candidates': total_selected_candidates,      
        'total_offer_candidates': total_offer_candidates,
        'total_waitlist_candidates':  total_waitlist_candidates,
        'total_confirmed_candidates':total_confirmed_candidates,
        'total_onboard_candidates': total_onboard_candidates,
        'chart_data': json.dumps(chart_data),
    })


def all_job_candidate_status(request):
    project_name = None
    jobs = Job.objects.all()
    job_candidate_status = {}
    total_candidates = 0
    project = None

    form = AllJobForm(request.GET)
    
    if request.method == 'GET':
        form = AllJobForm(request.GET)
        if form.is_valid():
            project_name = form.cleaned_data['project_name'] 
            if project_name:
                jobs = jobs.filter(project__name__icontains=project_name)              
           
            for job in jobs:
                project = job.project.name
                candidates = Candidate.objects.filter(applied_job=job)
                pass_count = candidates.filter(cv_screening_status='SHORT-LISTED').count()
                fail_count = candidates.filter(cv_screening_status='REJECTED').count()
                
                candidate_count = candidates.count()
                total_candidates += candidate_count

                job_candidate_status[job] = {
                    'pass_count': pass_count,
                    'fail_count': fail_count,
                    'candidates': candidates
                }

    return render(request, 'recruitment/all_job_candidate_status.html', {
        'job_candidate_status': job_candidate_status,
        'form': form,
        'total_candidates':total_candidates,
        'project':project
    })



def grand_summary(request):
    form = ProjectReportForm(request.GET or None)
    project = Project.objects.all()
    project_name = None
    project=None
    job_title = None
    job_instance=None
    total_candidates_project=0
    total_selected_project=0
    total_offer_letter_project=0
    total_waitlist_project =0
    total_confirmation_project=0
    total_onboard_project=0
    job_reports = []  
    candidates =None

    if form.is_valid():
        project_name = form.cleaned_data.get('project_name', None)
        job_title = form.cleaned_data.get('job_title', None)
        project_details = get_object_or_404(Project,name__icontains = project_name)
        if project_name:
           project = get_object_or_404(Project, name=project_name)          
        jobs = Job.objects.filter(project=project)
        if job_title:
            jobs = jobs.filter(title=job_title)          

        if not jobs.exists():
            messages.error(request, f"No jobs found for '{job_title}' in project '{project_name}'")
            return render(request, 'recruitment/grand_summary.html', {'form': form})
    
        total_candidates_project = Candidate.objects.filter(applied_job__in=jobs).count()
        total_selected_project = Candidate.objects.filter(applied_job__in=jobs, 
                status='SELECTED',               
                ).count()
        total_offer_letter_project = Candidate.objects.filter(applied_job__in=jobs, offer_status='offered').count()
        total_waitlist_project = Candidate.objects.filter(applied_job__in=jobs, offer_status='waitlist').count()
        total_confirmation_project = Candidate.objects.filter(applied_job__in=jobs, confirmation_status='accepted').count()
        total_onboard_project = Candidate.objects.filter(applied_job__in=jobs, onboard_status='onboard').count()

            
        for job in jobs:
            candidates =job.candidates.all()
            job_reports.append({
                'job_title': job.title,
                'job_id':job.id,
                'total_candidates': Candidate.objects.filter(applied_job=job).count(),
                'total_selected': Candidate.objects.filter(applied_job=job, status='SELECTED').count(),
                'total_offer_letter': Candidate.objects.filter(applied_job=job, offer_status='offered').count(),
                'total_waitlist': Candidate.objects.filter(applied_job=job, offer_status='waitlist').count(),
                'total_confirmation': Candidate.objects.filter(applied_job=job, confirmation_status='accepted').count(),
                'total_onboard': Candidate.objects.filter(applied_job=job, onboard_status='onboard').count(),
            })

        pie_labels = ["Selected", "Offer Letters", "Waitlisted", "Confirmed", "Onboarded"]
        pie_data = [
            total_selected_project,
            total_offer_letter_project,
            total_waitlist_project,
            total_confirmation_project,
            total_onboard_project
        ]

        pie_chart_data = {
            'labels': pie_labels,
            'data': pie_data
        }

        return render(request, 'recruitment/grand_summary.html',  {
            'form': form,
            'project_name': project_name,
            'total_candidates_project': total_candidates_project,
            'total_selected_project': total_selected_project,
            'total_offer_letter_project': total_offer_letter_project,
            'total_waitlist_project': total_waitlist_project,
            'total_confirmation_project': total_confirmation_project,
            'total_onboard_project': total_onboard_project,
            'job_reports': job_reports,
            'pie_chart_data': json.dumps(pie_chart_data), 
            'project_name':project_name,
            'job_title':job_title,
            'job_instance':job_instance,
            'project':project,
            'candidates':candidates,
            'project_details':project_details
        })
    else:
        form = ProjectReportForm()
        print(form.errors)
    form = ProjectReportForm()
    return render(request, 'recruitment/grand_summary.html', {'form': form})





def generate_offer_letter_pdf(candidate, employee):
    buffer = BytesIO()
    pdf_canvas = canvas.Canvas(buffer, pagesize=A4)

    margin = 50
    line_height = 15
    y_position = 700  
    pdf_canvas.setFont("Helvetica", 12)
    current_date = datetime.now().strftime("%Y-%m-%d")

    if employee:
        logo_path = employee.company.logo.path if employee.company and employee.company.logo else None

        if logo_path:
            logo_width = 80 
            logo_height = 80  #
            pdf_canvas.drawImage(logo_path, margin, y_position + 30, width=logo_width, height=logo_height)  # Adjust position
        
        pdf_canvas.setFont("Helvetica-Bold", 14)  
        y_position -= line_height
        pdf_canvas.drawString(margin, y_position, employee.company.name) if employee.company else None
        y_position -= line_height
        pdf_canvas.setFont("Helvetica", 10)
        if employee.company and employee.company.company_locations.exists():
            company_location = employee.company.company_locations.first()
            pdf_canvas.drawString(margin, y_position, company_location.address)
            y_position -= line_height
            pdf_canvas.drawString(margin, y_position, f"{company_location.phone} | {company_location.email}")

        y_position -= 60  # Extra spacing

        # Offer Letter Title
        pdf_canvas.setFont("Helvetica-Bold", 12)
        pdf_canvas.drawString(margin, y_position, f"Offer Letter for {candidate.full_name}")
        y_position -= 40
        pdf_canvas.drawString(margin, y_position, f"For the Position: {candidate.applied_job}")
        y_position -= 40
        pdf_canvas.drawString(margin, y_position, f"Date: {datetime.now().strftime('%Y-%m-%d')}")
        y_position -=40

        # Body
        pdf_canvas.setFont("Helvetica", 11)
        company_name = employee.company.name if employee.company else "Company Name Not Available"
        job_title = candidate.applied_job.title if candidate.applied_job else "Job Title Not Available"

        body_text = f"""
    Dear {candidate.full_name},    

    We are pleased to offer you the position of { job_title} at {company_name}.
    We are impressed with your qualifications and believe you will be a valuable addition to our team.

    We are offering you a competitive salary, and we look forward to your joining us on {candidate.joining_deadline}.

    Your key remuneration is as follows:
    - Basic Salary: {(candidate.applied_job.salary_structure.basic_salary):.2f}
    - House Allowance: {(candidate.applied_job.salary_structure.hra):.2f}
    - Medical Allowance: {(candidate.applied_job.salary_structure.medical_allowance):.2f}
    - Conveyance Allowance: {(candidate.applied_job.salary_structure.conveyance_allowance):.2f}
    - Festival Bonus: {(candidate.applied_job.salary_structure.festival_allowance):.2f}
    - Performance Bonus: {(candidate.applied_job.salary_structure.performance_bonus):.2f}
    - Provident Fund: {(candidate.applied_job.salary_structure.provident_fund):.2f}
    - Professional Tax: {(candidate.applied_job.salary_structure.professional_tax):.2f}
    - Income Tax: {(candidate.applied_job.salary_structure.income_tax):.2f}

    Please review the terms and conditions of your employment and feel free to reach out if you have any questions.

    Best regards,
    {employee.name}
    {employee.position}
    {company_name }
    """
        for line in body_text.strip().split("\n"):
            pdf_canvas.drawString(margin, y_position, line.strip())
            y_position -= line_height

            if y_position < 100:  # New page if necessary
                pdf_canvas.showPage()
                pdf_canvas.setFont("Helvetica", 11)
                y_position = 780

        pdf_canvas.showPage()
        pdf_canvas.save()
        buffer.seek(0)
        return buffer




@login_required
def preview_offer_letter(request, candidate_id): 
    selected_candidates = Candidate.objects.filter(
        status='SELECTED',
        mcq_bq_exam_status='EXAM-PASS',
        interview_status = 'INTERVIEW-PASS',
        )
    candidate = get_object_or_404(Candidate, id=candidate_id)
    employee = Employee.objects.filter(user_profile__user=request.user).first()
    
    if not employee:
        messages.error(request, 'Employee profile not found.')
        return redirect('recruitment:selected_candidate') 
    
    pdf_buffer = generate_offer_letter_pdf(candidate, employee)
    pdf_base64 = base64.b64encode(pdf_buffer.getvalue()).decode('utf-8')

    return render(request, "recruitment/offer_letter_preview.html", {
        "candidate": candidate,
        "pdf_preview": pdf_base64,
        "selected_candidates": selected_candidates
    })




def send_offer_letter(candidate, employee):      
    if not candidate.email:
        return f"Candidate email not found for {candidate.full_name}."

    pdf_buffer = generate_offer_letter_pdf(candidate, employee)

    current_site = Site.objects.get_current().domain
    confirmation_link = f"http://{current_site}{reverse('recruitment:candidate_confirmation', args=[candidate.id])}"
    onboarding_link = f"http://{current_site}{reverse('recruitment:candidate_joining', args=[candidate.id])}"

    message = render_to_string('recruitment/offer_letter_email.html', {
        'candidate': candidate,
        'confirmation_link': confirmation_link,
        'onboarding_link': onboarding_link
    })

    try:
        email = EmailMessage(
            subject="Offer Letter from Our Company",
            body=message,
            from_email="yourcompany@example.com",
            to=[candidate.email]
        )

        email.attach(f"offer_letter_{candidate.id}.pdf", pdf_buffer.getvalue(), 'application/pdf')
        email.content_subtype = "html"
        email.send()
        
        candidate.offer_status = "offered"
        candidate.confirmation_deadline = timezone.now() + timezone.timedelta(hours=24)
        candidate.joining_deadline = timezone.now() + timezone.timedelta(hours=72)
        candidate.save()

        return f"Offer letter sent to {candidate.full_name} successfully!"
    except Exception as e:
        return f"Error sending offer letter to {candidate.full_name}: {str(e)}"




@login_required
def generate_and_send_offer_letter(request, candidate_id):
    candidate = get_object_or_404(Candidate, id=candidate_id)
    employee = Employee.objects.filter(user_profile__user=request.user).first()
    message = send_offer_letter(candidate, employee)
    if "Error" in message:
        messages.error(request, message)
    else:
        messages.success(request, message)
    return redirect('recruitment:selected_candidate')




@login_required
def send_offer_letters_to_top_scorers(request):
    employee = Employee.objects.filter(user_profile__user=request.user).first()
    selected_candidates = Candidate.objects.filter(
        status='SELECTED',         
        ).order_by('-total_score')

    job_candidates = defaultdict(list)
    for candidate in selected_candidates:
        job_candidates[candidate.applied_job].append(candidate)

    for job, candidates in job_candidates.items():
        no_of_vacancies = job.no_of_vacancies  
        top_candidates = candidates[:no_of_vacancies]
        waitlist_candidates = candidates[no_of_vacancies:]

        for candidate in top_candidates:
            message = send_offer_letter(candidate, employee)
            if "Error" in message:
                messages.error(request, message)
            else:
                messages.success(request, message)

        Candidate.objects.filter(id__in=[c.id for c in waitlist_candidates]).update(offer_status='waitlist')

    messages.info(request, 'Offer letters sent as per job vacancies. Others are on the waitlist.')
    return redirect('recruitment:selected_candidate')




def candidate_confirmation(request, candidate_id):
    candidate = get_object_or_404(Candidate, id=candidate_id)

    if candidate.confirmation_deadline and candidate.confirmation_deadline < timezone.now().date():
        messages.info(request, 'Your timing of confirmation has expired')
        return redirect("recruitment:job_list_candidate_view")

    if request.method == "POST":
        decision = request.POST.get("decision")
        joining_date = request.POST.get("joining_date")
        if decision == "accept":           
            candidate.confirmation_status = "accepted"
            if joining_date: 
                candidate.expected_joining_date = joining_date                
            messages.success(request, f"Congratulation Dear Mr.{candidate.full_name}.Please meet with our hiring manager at your conveinent time within office hour")
            return redirect(reverse("recruitment:congratulations", args=[candidate.id]))
        else:           
            candidate.confirmation_status = "declined"
            messages.warning(request, f"{candidate.full_name} has declined the offer.")
        
        candidate.save()
        return redirect("recruitment:job_list_candidate_view")
    return render(request, "recruitment/candidate_confirmation.html", {"candidate": candidate})


def congratulations(request, candidate_id):
    #candidate = get_object_or_404(Candidate, id=candidate_id, confirmation_status="accepted")
    candidate = get_object_or_404(Candidate, id=candidate_id)

    guidelines = [
        "Meet the hiring manager on your joining date.",
        "Bring original copies of your documents (ID proof, academic certificates, etc.).",
        "Sign the employment contract upon arrival.",
        "Complete your HR formalities and onboarding process.",
    ]
    return render(request, "recruitment/congratulations.html", {"candidate": candidate, "guidelines": guidelines})



@login_required
def hiring_manager_confirm_onboarding(request, candidate_id):
    candidate = get_object_or_404(Candidate, id=candidate_id)
    if request.method == "POST":
        candidate.manager_confirmation_of_joining = True
        candidate.save()
        messages.success(request, f"Candidate {candidate.full_name} is approved for onboarding.")
        return redirect("recruitment:onboarding_dashboard")

    return render(request, "recruitment/hiring_manager_confirm_onboarding.html", {"candidate": candidate})




def candidate_joining(request, candidate_id):
    candidate = get_object_or_404(Candidate, id=candidate_id)  
    if not candidate.manager_confirmation_of_joining:
        messages.warning(request, "Hiring Manager has not approved the onboarding yet.")
        return redirect("recruitment:selected_candidate")

    if candidate.joining_deadline and candidate.joining_deadline < timezone.now().date():
        messages.warning(request, 'Your timing of joining has expired')
        return redirect("recruitment:selected_candidate")

    if request.method == "POST":
        form = AddEmployeeForm(request.POST)
        if form.is_valid():
            employee = form.save(commit=False)          
            employee.save()

            subject = f"Welcome to {candidate.applied_job.company} - Your Employment Details"
            message = render_to_string("recruitment/onboard_welcome_template.html", {"employee": employee})
            email = EmailMessage(
                subject,
                message,
                "hr@yourcompany.com",  
                [employee.email],  
            )
           
            common_documents = CommonDocument.objects.all()
            for doc in common_documents:
                email.attach(doc.name, doc.file.read(), doc.file.content_type)

            candidate_documents = CandidateDocument.objects.filter(candidate=candidate)
            for doc in candidate_documents:
                email.attach(doc.name, doc.file.read(), doc.file.content_type)

            email.send(fail_silently=False)         
                                
            candidate.hiring_status = True
            candidate.onboard_status = "onboard"
            candidate.save()
     
            if candidate.candidate:
                user = candidate.candidate
                job_seekers = Group.objects.get(name="Job_seekes")
                staff_group, _ = Group.objects.get_or_create(name="Staff")

                user.groups.remove(job_seekers)
                user.groups.add(staff_group)

            messages.success(request, f"{candidate.full_name} has officially joined the company.")
            return redirect("account:login")
    else:
       form = AddEmployeeForm(initial={
            "name": candidate.full_name,
            "email": candidate.email,  
            "salary_structure": candidate.applied_job.salary_structure,          
            "department": candidate.applied_job.department,
            "position": candidate.applied_job.position,  
            "location": candidate.applied_job.location,
            "joining_date": candidate.expected_joining_date,
            "company": candidate.applied_job.company,
            "gender": candidate.gender,
            'user_profile':candidate.candidate.user_profile,
           
        })
    return render(request, "recruitment/candidate_joining.html", {"form": form, "candidate": candidate})
   


@login_required
def handle_declines_and_offer_next_candidates(request):
    expired_candidates = Candidate.objects.filter(
        offer_status='offered', confirmation_deadline__lt=timezone.now()
    )
    expired_candidates_count = expired_candidates.count() 
    expired_candidates.update(offer_status='declined')
    declined_by_user_count = Candidate.objects.filter(confirmation_status='declined').count() 
    total_declined_count = expired_candidates_count + declined_by_user_count 
    waitlist_candidates = Candidate.objects.filter(offer_status='waitlist').order_by('-total_score')
    available_replacements = waitlist_candidates.count()
    if total_declined_count > 0 and available_replacements > 0:
        if available_replacements >= total_declined_count:
            top_waitlist_candidates = waitlist_candidates[:total_declined_count]
        else:
            messages.warning(
                request,
                f'Not enough candidates in waitlist. Needed {total_declined_count}, but only {available_replacements} available.'
            )
            top_waitlist_candidates = waitlist_candidates
    else:
        messages.info(request, 'No declined candidates to replace or no waitlisted candidates available.')
        return redirect('recruitment:selected_candidate')

    for candidate in top_waitlist_candidates:
        message = send_offer_letter(candidate, None)  
        if "Error" in message:
            messages.error(request, message)
        else:
            messages.success(request, message)

    return redirect('recruitment:selected_candidate')



@login_required
def handle_onboard_declines_and_offer_next_candidates(request): 
    expired_candidates = Candidate.objects.filter(
        ~Q(onboard_status='onboard'), 
        offer_status='accepted', 
        joining_deadline__lt=timezone.now()
    )
    expired_candidates_count = expired_candidates.count()

    if expired_candidates_count == 0:
        messages.info(request, 'No candidates failed to onboard within the deadline.')
        return redirect('recruitment:selected_candidate')

    expired_candidates.update(
        offer_status='declined', 
        confirmation_status='declined', 
        onboard_status='declined'
    )

    waitlist_candidates = Candidate.objects.filter(offer_status='waitlist').order_by('-total_score')
    available_replacements = waitlist_candidates.count()

    if available_replacements == 0:
        messages.warning(request, 'No waitlisted candidates available for replacement.')
        return redirect('recruitment:selected_candidate')

    top_waitlist_candidates = waitlist_candidates[:min(expired_candidates_count, available_replacements)]

    for candidate in top_waitlist_candidates:
        message = send_offer_letter(candidate, None)  
        if "Error" in message:
            messages.error(request, message)
        else:
            messages.success(request, message)

    return redirect('recruitment:selected_candidate')





######################################## Broad question #################################
# import spacy
# from sklearn.feature_extraction.text import TfidfVectorizer
# from sklearn.metrics.pairwise import cosine_similarity
# from transformers import pipeline
from django.utils.timezone import localtime
from decimal import Decimal

from .models import BQQuestionPaper, BQQuestion, BQCandidateAnswer
from .forms import BQExamForm,BQQuestionForm,BQQuestionrPaperForm
# pip uninstall spacy scikit-learn transformers



@login_required
def manage_bq_question_paper(request, id=None):  
    instance = get_object_or_404(BQQuestionPaper, id=id) if id else None
    message_text = "updated successfully!" if id else "added successfully!"  
    form = BQQuestionrPaperForm(request.POST or None, request.FILES or None, instance=instance)

    if request.method == 'POST' and form.is_valid():
        form_instance = form.save(commit=False)
        form_instance.user = request.user
        form_instance.save()        
        messages.success(request, message_text)
        return redirect('recruitment:create_question_paper')  

    datas = BQQuestionPaper.objects.all().order_by('-created_at')
    paginator = Paginator(datas, 5)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)  

    return render(request, 'recruitment/BQ_exam/manage_bq_question_paper.html', {
        'form': form,  # No need to reinitialize
        'instance': instance,
        'datas': datas,
        'page_obj': page_obj
    })




@login_required
def delete_bq_question_paper(request, id):
    instance = get_object_or_404(BQQuestionPaper, id=id)
    if request.method == 'POST':
        instance.delete()
        messages.success(request, "Deleted successfully!")
        return redirect('recruitment:create_question_paper')      

    messages.warning(request, "Invalid delete request!")
    return redirect('recruitment:create_question_paper')   



def bq_question_paper_list(request):   
    datas = BQQuestionPaper.objects.all().order_by('-created_at')
    
    paginator = Paginator(datas, 5)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    return render(request,'recruitment/BQ_exam/bq_question_paper_list.html',{'page_obj':page_obj})




@login_required
def manage_bq_question(request, id=None):  
    instance = get_object_or_404( BQQuestion, id=id) if id else None
    message_text = "updated successfully!" if id else "added successfully!"  
    form = BQQuestionForm(request.POST or None, request.FILES or None, instance=instance)

    if request.method == 'POST' and form.is_valid():
        form_intance=form.save(commit=False)
        form_intance.user = request.user
        form_intance.save()        
        messages.success(request, message_text)
        return redirect('recruitment:create_bq_question')  

    datas = BQQuestion.objects.all().order_by('-created_at')
    paginator = Paginator(datas, 5)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    form =  BQQuestionForm(instance=instance)
    return render(request, 'recruitment/BQ_exam/manage_bq_question.html', {
        'form': form,
        'instance': instance,
        'datas': datas,
        'page_obj': page_obj
    })


@login_required
def delete_bq_question(request, id):
    instance = get_object_or_404(BQQuestion, id=id)
    if request.method == 'POST':
        instance.delete()
        messages.success(request, "Deleted successfully!")
        return redirect('recruitment:create_bq_question')      

    messages.warning(request, "Invalid delete request!")
    return redirect('recruitment:create_bq_question')   



'''

nlp = spacy.load("en_core_web_sm")
def calculate_similarity(candidate_answer, correct_answer):
    vectorizer = TfidfVectorizer().fit_transform([candidate_answer, correct_answer])
    similarity_matrix = cosine_similarity(vectorizer)
    return similarity_matrix[0, 1]


def evaluate_answer_using_bert(candidate_answer, correct_answer):
    nlp_model = pipeline('zero-shot-classification', model='facebook/bart-large-mnli')
    result = nlp_model(candidate_answer, candidate_labels=[correct_answer])
    return result['scores'][0]  


def score_answer(candidate_answer, question):  
    correct_answer = question.correct_answer  
    similarity_score = calculate_similarity(candidate_answer, correct_answer)
   
    if similarity_score > 0.75:
        return float(question.score)  # Full score if the answer is very similar
    elif similarity_score > 0.5:
        return float(question.score) * 0.5  # Partial score
    else:
        return 0  




@login_required
def take_bq_exam(request, paper_id, candidate_id):
    exam = get_object_or_404(BQQuestionPaper, id=paper_id)
    candidate = get_object_or_404(Candidate, id=candidate_id)
    questions = exam.bq_questions.all()
    current_time = localtime()

    # if BQCandidateAnswer.objects.filter(candidate=candidate,question_paper=exam).exists():
    #     messages.warning(request, "You have already attempted this exam. Multiple attempts are not allowed.")
    #     return redirect('recruitment:bq_question_paper_list')  


    if request.method == "POST":
        form = BQExamForm(questions, request.POST)
        if form.is_valid():
            if exam.end_time <= current_time:
                messages.warning(request, "The exam time has expired. You cannot submit the exam paper.")
                return redirect("customerportal:job_list_candidate_view")

            total_marks = Decimal(0)

            for question in questions:
                field_name = f'question_{question.id}'
                answer = form.cleaned_data[field_name]
               
                obtained_marks = Decimal(score_answer(answer, question))  
                total_marks += obtained_marks

                BQCandidateAnswer.objects.create(
                    candidate=candidate,
                    question_paper=exam,
                    question=question,
                    answer=answer,
                    score=obtained_marks
                )

            candidate.bq_exam_status = "EXAM-PASS" if total_marks >= exam.pass_marks else "EXAM-FAIL"
            candidate.bq_exam_score = total_marks  # Ensure BQ score is updated first
            candidate.mcq_bq_score = float(candidate.exam_score) + float(candidate.bq_exam_score)
            candidate.total_score = float(candidate.cv_screening_score) + float(candidate.exam_score) + float(candidate.bq_exam_score) + float(candidate.interview_score)

            # Fix exam status assignment
            if candidate.exam_status == 'EXAM-PASS' and candidate.bq_exam_status == 'EXAM-PASS':
                candidate.mcq_bq_exam_status = 'EXAM-PASS'
            else:
                candidate.mcq_bq_exam_status = 'EXAM-FAIL'
            candidate.save()          

            exam.is_active = False
            exam.save()
            return redirect("customerportal:job_list_candidate_view")
        else:
            print(form.errors)

   
    form = BQExamForm(questions)

    return render(request, 'recruitment/BQ_exam/take_bq_exam.html', {
        "exam": exam,
        "candidate": candidate,
        "form": form,
        'questions':questions,
        "exam_start_time": localtime(exam.start_time).isoformat(),
        "exam_end_time": localtime(exam.end_time).isoformat(),
        'current_time': localtime(now()).isoformat()
    })




@login_required
def bq_exam_results(request, paper_id, total_score):
    question_paper = get_object_or_404(BQQuestionPaper, id=paper_id)
    return render(request, 'nlp_app/exam_results.html', {
        'question_paper': question_paper,
        'total_score': total_score
    })
'''