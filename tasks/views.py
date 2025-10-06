
from django.core.paginator import Paginator
from django.utils import timezone
from datetime import datetime,timedelta
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.contrib.auth.decorators import login_required
import uuid,json,csv
from myproject.utils import create_notification,calculate_task_score,distribute_team_score,calculate_total_performance

from datetime import date
import openpyxl
from django.http import HttpResponse, HttpResponseRedirect
from decimal import Decimal
from django.db import transaction
from core.models import SalaryIncrementAndPromotion
from reportlab.lib.pagesizes import A4,letter
from reportlab.pdfgen import canvas

from .models import PerformanceEvaluation, Employee,QualitativeEvaluation,Task,TeamMember,Team,TaskMessage

from.forms import IncrementPromotionCheckForm,IncrementPromotionForm,IncrementPromotionFinalDataForm
from.forms import GenerateIncrementPromotionPdfForm,DownloadIncrementPromotionForm
from.forms import MonthlyQuarterlyTrendForm,YearlyTrendForm,ChatForm
from .forms import QualitativeEvaluationForm,TaskForm,TeamForm,AddMemberForm
from .forms import TaskProgressForm,TaskAssignmentForm,RequestExtensionForm,ApproveExtensionForm
from core.forms import CommonFilterForm
from django.db.models import Sum, ExpressionWrapper, F, FloatField,Count,Q,Avg
from django.urls import reverse
from statistics import mean
from decimal import Decimal, ROUND_HALF_UP
from django.utils.timezone import now
from.models import TaskMessageReadStatus
from django.contrib.auth.models import User

from django.http import JsonResponse
from django.db.models import Max, Avg
import calendar
from collections import defaultdict

from django.template.loader import render_to_string
from django.core.mail import EmailMessage,send_mail

import base64
from io import BytesIO




def tasks_dashboard(request):
    return render(request, 'tasks/task_dashboard.html')



def chat(request, task_id):
    task = get_object_or_404(Task, id=task_id)
    taskmessages = TaskMessage.objects.filter(task=task).order_by('timestamp')

    for message in taskmessages:
        TaskMessageReadStatus.objects.update_or_create(
            task_message=message,
            user=request.user,
            defaults={'read': True, 'read_at': now()}
        )

    if request.method == 'POST':
        form = ChatForm(request.POST)
        if form.is_valid():
            message = form.save(commit=False)
            message.task = task
            message.sender = request.user
            message.timestamp = now()
            message.save()

            for user in User.objects.all():  
                TaskMessageReadStatus.objects.create(
                    task_message=message,
                    user=user,
                    read=False
                )
            return redirect('tasks:chat', task_id=task_id)
    else:
        form = ChatForm()
    return render(request, 'tasks/tchat.html', {'task': task, 'taskmessages': taskmessages, 'form': form})



def create_team(request):
    teams = Team.objects.all().order_by('-created_at')   
    start_date = request.GET.get('start_date')
    end_date = request.GET.get('end_date')

    if start_date and end_date:
        teams = teams.filter(created_at__range=[start_date, end_date])
    else:            
        seven_days_ago = timezone.now() - timedelta(days=7)
        teams = teams.filter(created_at__gte=seven_days_ago)  
    
    if request.method == 'POST':
        form = TeamForm(request.POST)
        if form.is_valid():
            team= form.save(commit=False)
            team.save()
            messages.success(request, 'Team created successfully!')
            create_notification(request.user,message=f"A team named '{team.name}' has been created with manager: {team.manager} for {team.description}",notification_type='TASK-NOTIFICATION')
            return redirect('tasks:create_team')
        else:
            for field, errors in form.errors.items():
                for error in errors:
                    messages.error(request, f"Error in {field}: {error}")
   
    paginator = Paginator(teams, 10)  
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    form = TeamForm()
    return render(request, 'tasks/create_team.html', {'form': form,'page_obj':page_obj,'teams':teams})


def delete_team(request, team_id):  
    team = get_object_or_404(Team, id=team_id)
    if request.method == 'POST':
        team.delete()
        messages.success(request, "Team has been successfully deleted.")
        create_notification(request.user,message=f'team-{team.name} has been deleted by {request.user} on {timezone.now()}',notification_type='TASKS-NOTIFICATION')
        return redirect('tasks:create_team') 
    return render(request, 'tasks/delete_record.html', {'team': team})



def add_member(request):
    members = TeamMember.objects.all().order_by('-created_at')
    start_date = request.GET.get('start_date')
    end_date = request.GET.get('end_date')
    if start_date and end_date:
        members = members.filter(created_at__range=[start_date, end_date])
    else:
        seven_days_ago = timezone.now() - timedelta(days=7)
        members = members.filter(created_at__gte=seven_days_ago)

    if request.method == 'POST':
        form = AddMemberForm(request.POST)
        if form.is_valid():
            form_data = form.save(commit=False)
            form_data.save()
 
            member = form_data.member if hasattr(form_data, 'member') else None
            team = form_data.team if hasattr(form_data, 'team') else None

            if member and team:
                create_notification(
                    request.user,message=
                    f'Member {member.name} has been added to the team {team.name}',notification_type='TASKS-NOTIFICATION'
                )
                messages.success(request, 'Member added to the team successfully!')
            else:
                messages.warning(request, 'Member added, but notification creation failed due to missing data.')

            return redirect('tasks:add_member')
        else:
            for field, errors in form.errors.items():
                for error in errors:
                    messages.error(request, f"Error in {field}: {error}")
    else:
        pass
    paginator = Paginator(members, 10)  
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    form = AddMemberForm()
    return render(request, 'tasks/add_member.html', {'form': form,'members':members,'page_obj':page_obj})



def add_member_with_id(request,team_id):
    team = get_object_or_404(Team, id=team_id)
    members = TeamMember.objects.all().order_by('-created_at')

    if request.method == 'POST':
        form = AddMemberForm(request.POST)
        if form.is_valid():
            form_data = form.save(commit=False)
            form_data.save()
            messages.success(request, 'Member added to the team successfully!')
            create_notification(request.user,message=f'member {team.members.first.member.name} has been added to the team {team.name}',notification_type='TASK-NOTIFICATION')
            return redirect('tasks:create_team')
        else:
            for field, errors in form.errors.items():
                for error in errors:
                    messages.error(request, f"Error in {field}: {error}")
    else:
        form = AddMemberForm()
    return render(request, 'tasks/add_member.html', {'form': form,'members':members,'team':team})


def delete_member(request, team_id):  
    team = get_object_or_404(TeamMember, id=team_id)
    if request.method == 'POST':
        team.delete()
        messages.success(request, "member has been successfully deleted.")
        create_notification(request.user,message=f'member {team.member.name} has been deleted frrom team {team.team.name}, deleted by {request.user} dated {timezone.now()}'
            ,notification_type='TASK-NOTIFICATION')
        return redirect('tasks:add_member') 
    return render(request, 'tasks/delete_record.html', {'team': team})



@login_required
def create_task(request):
    tasks = Task.objects.all().order_by('-created_at')

    if not request.user.groups.filter(name='Approver').exists():
        messages.success(request, 'You are not authorized to create a task.')
        return redirect('tasks:tasks_dashboard')
    

    start_date = request.GET.get('start_date')
    end_date = request.GET.get('end_date')
    if start_date and end_date:
        tasks = tasks.filter(created_at__range=[start_date, end_date])
    else:
        seven_days_ago = timezone.now() - timedelta(days=7)
        tasks = tasks.filter(created_at__gte=seven_days_ago)

    if request.method == 'POST':
        form = TaskForm(request.POST)
        if form.is_valid():
            task = form.save(commit=False) 
            assigned_to = form.cleaned_data['assigned_to']

            if assigned_to == 'team':
                task.assigned_to_team = form.cleaned_data['assigned_to_team']
                team = get_object_or_404(Team,name=task.assigned_to_team)
                members = team.members.all()
                if not members:
                    messages.warning(request,'No member(s) in this team, Plese add member before assignin task to this team') 
                    return redirect('tasks:create_task')                 
                task.assigned_to_employee = None
            elif assigned_to == 'member':
                task.assigned_to_employee = form.cleaned_data['assigned_to_employee']
                task.assigned_to_team = None

            task.save()
            create_notification(
                request.user,message=
                f'Task: {task.title} has been created and assigned to {task.assigned_to_team or task.assigned_to_employee}, manager: {task.task_manager} created by {request.user} dated {timezone.now()}',notification_type='TASK-NOTIFICATION'

            )
            messages.success(request, 'Task created successfully!')
            return redirect('tasks:create_task')
        else:
            for field, errors in form.errors.items():
                for error in errors:
                    messages.error(request, f"Error in {field}: {error}")

    paginator = Paginator(tasks, 10)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    form = TaskForm()
    return render(request, 'tasks/create_tasks.html', {'form': form, 'tasks': tasks, 'page_obj': page_obj})




@login_required
def assigned_task(request, task_id):
    task = get_object_or_404(Task, id=task_id)

    if not request.user.groups.filter(name='managers').exists():
        messages.error(request, 'You are not authorized to assign a task.')
        return redirect('tasks:tasks_dashboard')

    if request.method == 'POST':
        form = TaskForm(request.POST, instance=task)
        if form.is_valid():
            assigned_to = form.cleaned_data['assigned_to']

            task = form.save(commit=False)

            if not task.ticket:
                task.ticket = task.ticket  
            if not task.task_type:
                task.task_type = 'TICKET'  

            if assigned_to == 'team':
                task.assigned_to_team = form.cleaned_data['assigned_to_team']
                task.assigned_to_employee = None
            elif assigned_to == 'member':
                task.assigned_to_employee = form.cleaned_data['assigned_to_employee']
                task.assigned_to_team = None

            task.save()
            create_notification(
                request.user,message=
                f'Task: {task.title} has been assigned to \
                {task.assigned_to_team or task.assigned_to_employee}, \
                manager: {task.task_manager} created by {request.user} \
                dated {timezone.now()}',notification_type='TASK-NOTIFICATION'
            )
            messages.success(request, 'Task assigned successfully!')
            return redirect('tasks:tasks_list')
        else:  
            for field, errors in form.errors.items():
                for error in errors:
                    messages.error(request, f"Error in {field}: {error}")

    form = TaskForm(instance=task)
    return render(request, 'tasks/create_tasks.html', {'form': form})



def delete_task(request, task_id):  
    task = get_object_or_404(Task, id=task_id)
    if request.method == 'POST':
        task.delete()
        messages.success(request, f"{task} has been successfully deleted.")
        return redirect('tasks:add_member') 
    return render(request, 'tasks/delete_record.html', {'task': task})



def tasks_list(request):
    form = CommonFilterForm(request.GET)
    tasks = Task.objects.all().order_by('-created_at')  
 
    unread_messages = defaultdict(list) 
    unread_statuses = TaskMessageReadStatus.objects.filter(user=request.user, read=False)
    for status in unread_statuses:
        unread_messages[status.task_message.task.id].append(status.task_message)
      
    if form.is_valid():
        start_date = form.cleaned_data['start_date']
        end_date = form.cleaned_data['end_date']
        department = form.cleaned_data['department']

        if start_date and end_date:
           tasks = tasks.filter(created_at__range=(start_date, end_date))  
        else:            
            x_days_ago = timezone.now() - timedelta(days=30)
            tasks = tasks.filter(created_at__gte=x_days_ago)   
        if department:
            tasks = tasks.filter(department__name=department)

    
    paginator = Paginator(tasks, 8)  
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    form = CommonFilterForm()
    return render(request,'tasks/tasks_list.html',{'tasks':tasks,'page_obj':page_obj,'form':form,'unread_messages': unread_messages})




# for ajax

def task_details(request, task_id):
    try:
        task = Task.objects.get(id=task_id)       
        data = {
            "task_id": task.task_id,           
            "description": task.description,
            "status": task.status,
            "assigned_to": task.assigned_to,
            "due_datetime": task.due_datetime.strftime("%Y-%m-%d") if task.due_datetime else None,
            'ticket_subject':task.ticket.subject,
            'ticket_description':task.ticket.description,
            'ticket_raised_by':task.ticket.user.username,
            'ticket_origin_date':task.ticket.ticket_origin_date,
            'ticket_resolution_date':task.ticket.ticket_resolution_date
        }
 
        return JsonResponse(data)
    except Task.DoesNotExist:
        return JsonResponse({"error": "Task not found"}, status=404)

   

def view_team_members(request, task_id):
    task=get_object_or_404(Task,id=task_id)
    team_members = task.assigned_to_team.members.all()
    return render(request,'tasks/view_team_members.html',{'team_members':team_members,'task':task})
    
from repairreturn.models import RepairReturnCustomerFeedback

def update_task_progress(request, task_id):
    task = get_object_or_404(Task, id=task_id)

    if not task.assigned_to:
        messages.info(request, "Task can not update as nobody has assigned yet")
        return redirect('tasks:tasks_list')


    latest_extension_request = task.time_extension_requests.filter(is_approved=True).order_by('-updated_at').first()

    if latest_extension_request and latest_extension_request.approved_extension_datetime < timezone.now():
        messages.error(request, "You cannot update the task as the approved extension time has expired.")
        return redirect('tasks:tasks_list')
    
    elif not latest_extension_request and task.due_datetime < timezone.now():  
        messages.error(request, "You cannot update the task as the due date has passed.")
        return redirect('tasks:tasks_list')

    if request.method == 'POST':
        form = TaskProgressForm(request.POST, instance=task)
        if form.is_valid():
            given_progress = form.cleaned_data['progress']
            form.save()            
     
    # Update ticket progress #########################################
            if task.ticket:
                task.ticket.progress_by_user = given_progress
                task.ticket.save()

    # Update repair return progress####################################
            try:           
                sale_order = task.ticket.sales           
                if not sale_order:
                    raise AttributeError("No Sale Order found for the task ticket.")

                sale_order_item = sale_order.sale_order.first()            
                if not sale_order_item :
                    raise AttributeError("No Sale Returns found for the Sale Order.") 
                sale_return = sale_order_item.sale_returns.first()              
               
                sale_return.progress_by_user = given_progress
                sale_return.save()              

            except AttributeError as e:
                print(f"Error: {str(e)}") 

    # Calculate performance ####################################    
           
            new_obtained_number = task.calculate_obtained_number()    
            print(f'new obtained number= {new_obtained_number}')
            if new_obtained_number > 100:
                messages.error(request, "Cumulative progress cannot exceed 100%.")
                return redirect('tasks:tasks_list')

            task.obtained_number = new_obtained_number
            if task.assigned_number > 0:
                task.obtained_score = (new_obtained_number / task.assigned_number) * 100 

            if task.progress >= 100:
                task.status = 'COMPLETED'
            elif task.progress > 0:
                task.status = 'IN_PROGRESS'
            else:
                task.status = 'PENDING'

            task.save()

            if task.assigned_to_team:
                team_members = TeamMember.objects.filter(team=task.assigned_to_team)
                for member in team_members:
                    evaluation, created = PerformanceEvaluation.objects.get_or_create(
                        employee=member.member,
                        task=task,
                        team=task.assigned_to_team,
                        defaults={
                            'assigned_quantitative_number': 0,
                            'remarks': 'Progressive evaluation in progress.',
                        }
                    )
                    evaluation.obtained_quantitative_score = (task.obtained_number / task.assigned_number) * 100 if task.assigned_number else 0
                    evaluation.obtained_quantitative_number = task.obtained_number
                    evaluation.assigned_quantitative_number = task.assigned_number
                    evaluation.remarks = f"Progress: {task.progress}%. Updated incremental score."
                    evaluation.save()
                    create_notification(
                        request.user,
                        message=f'Task:{task.title}, progress {task.progress}% updated by {request.user} dated {timezone.now()}',
                        notification_type='TASK-NOTIFICATION'
                    )

            elif task.assigned_to_employee:
                evaluation, created = PerformanceEvaluation.objects.get_or_create(
                    employee=task.assigned_to_employee,
                    task=task,
                    defaults={
                        'assigned_quantitative_number': 0,
                        'remarks': 'Progressive evaluation in progress.',
                    }
                )
                evaluation.obtained_quantitative_score = task.obtained_score
                evaluation.obtained_quantitative_number = task.obtained_number
                evaluation.assigned_quantitative_number = task.assigned_number
                evaluation.remarks = f"Progress: {task.progress}%. Updated incremental score."
                evaluation.save()

            # Success message and redirect
            messages.success(request, "Task progress updated successfully.")
            create_notification(
                request.user,
                message=f'Task:{task.title}, progress {task.progress}% updated by {request.user} dated {timezone.now()}',
                notification_type='TASK-NOTIFICATION'
            )
            return redirect('tasks:tasks_list')
        else:
            # Display specific form errors
            for field, errors in form.errors.items():
                for error in errors:
                    messages.error(request, f"Error in {field}: {error}")

    else:
        form = TaskProgressForm(instance=task)
    return render(request, 'tasks/update_progress.html', {'form': form, 'task': task})



def request_extension(request, task_id):
    task = get_object_or_404(Task, id=task_id)

    if task.assigned_to_employee:
        if task.assigned_to_employee.user_profile.user.id != request.user.id:
            messages.info(request, "You are not allowed to apply time extension")
            return redirect('tasks:tasks_list')

    if task.assigned_to_team:
        team_members = task.assigned_to_team.members.all()
        is_allowed = False

        for member in team_members:
            if member.member.user_profile.user.id == request.user.id and member.is_team_leader:
                is_allowed = True
                break

        if not is_allowed:
            messages.info(request, "Only the team leader can request a time extension.")
            return redirect('tasks:tasks_list')

    if request.method == 'POST':
        form = RequestExtensionForm(request.POST)
        if form.is_valid():
            task_form = form.save(commit=False)
            task_form.task = task  
            task.status = 'TIME_EXTENSION'  
            task.save() 
            task_form.save()            
                   
            messages.success(request, 'Time extension request submitted successfully.')
            return redirect('tasks:tasks_list')
        else:
            for field, errors in form.errors.items():
                for error in errors:
                    messages.error(request, f"Error in {field}: {error}")
    else:
        form = RequestExtensionForm(initial={'task':task})
    return render(request, 'tasks/request_extension.html', {'form': form, 'task': task})



def approve_extension(request, task_id):
    task = get_object_or_404(Task, id=task_id)

    if task.task_manager and task.task_manager.user_profile.id != request.user.id:
        messages.error(request, "Only the task manager can approve extensions.")
        return redirect('tasks:tasks_list')

    latest_request = task.time_extension_requests.filter(is_approved=False).last()

    if not latest_request:
        messages.info(request, "No pending time extension requests.")
        return redirect('tasks:tasks_list')

    if request.method == 'POST':
        form = ApproveExtensionForm(request.POST)
        if form.is_valid():
            is_approved = form.cleaned_data['is_approved']
            approved_extension_datetime = form.cleaned_data['approved_extension_datetime']
            extension_request = form.save(commit=False)

            extension_request.requested_by = latest_request.requested_by  
            extension_request.task = task 
            extension_request.is_approved = is_approved

            extension_request.save()

            if is_approved:
                task.extended_due_datetime = approved_extension_datetime
                task.status = 'IN_PROGRESS'
                task.save()

            if is_approved:
                messages.success(request, 'Extension request approved successfully.')
            else:
                messages.warning(request, 'Extension request rejected.')

            return redirect('tasks:tasks_list')
    else:
        form = ApproveExtensionForm()
    return render(request, 'tasks/approve_extension.html', {'form': form, 'task': task, 'request': latest_request})


def performance_evaluation_view(request):
    form = CommonFilterForm(request.GET)
    evaluations = PerformanceEvaluation.objects.none()  
    if form.is_valid():
        start_date = form.cleaned_data.get('start_date')
        end_date = form.cleaned_data.get('end_date')
        employee = form.cleaned_data.get('employee')

        department = form.cleaned_data.get('department')
        position = form.cleaned_data.get('position')

        evaluations = PerformanceEvaluation.objects.all().order_by('-evaluation_date')

        if start_date and end_date:
            evaluations = evaluations.filter(created_at__range=(start_date, end_date))
        if employee:
            evaluations = evaluations.filter(employee__name__icontains=employee)
        if department:
            evaluations = evaluations.filter(department__name__icontains=department)
        if position:
            evaluations = evaluations.filter(position__name__icontains=position)
    else:
        for field, errors in form.errors.items():
            for error in errors:
                messages.error(request, f"Error in {field}: {error}")

    paginator = Paginator(evaluations, 10)  
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    form = CommonFilterForm()
    return render(request, 'tasks/performance_evaluation_view.html', {
        'evaluations': evaluations,
        'form': form,
        'page_obj':page_obj
    })



@login_required
def create_qualitative_evaluation(request, task_id):
    task = get_object_or_404(Task, id=task_id)

    # if task.task_manager.user_profile.user == request.user:
    #     pass
    # else:
    #     messages.info(request, "This is a performance evaluation process of task. Only Task manager can evaluate performance.")
    #     return redirect('tasks:tasks_list')

    def calculate_performance_quality_score(evaluations):      
        
        total_score = 0
        total_items = 0
        max_score_per_item = 5.0 
        total_max_score = max_score_per_item * 5 

        for evaluation in evaluations:
            total_score += (
                evaluation.work_quality_score +
                evaluation.communication_quality_score +
                evaluation.teamwork_score +
                evaluation.initiative_score +
                evaluation.punctuality_score
            )
            total_items += 5 
        
        if total_items > 0:
            average_score = total_score / total_items
            percentage_score = (average_score / max_score_per_item) * 100        

            return total_max_score, total_score, percentage_score
        return 0, 0, 0
    
        
    if request.method == 'POST':
        form = QualitativeEvaluationForm(request.POST)
        if form.is_valid():
            qualitative_evaluation = form.save(commit=False)
            qualitative_evaluation.evaluator = request.user
            if qualitative_evaluation.manager_given_quantitative_number >task.assigned_number:
                messages.info(request, f'Quantitative score can not be more than assigned score-{task.assigned_score}')
                return redirect('tasks:tasks_list')
            
            if task.assigned_to_team:
                team_members = TeamMember.objects.filter(team=task.assigned_to_team)
                if team_members.exists():
                    total_team_members = team_members.count() # all members will get equal number/total given by manager will get everyone  so this count does not need anymore
                    manager_given_number = qualitative_evaluation.manager_given_quantitative_number
                    manager_given_score =(manager_given_number / task.assigned_number) * 100  
                    task.manager_given_number=manager_given_number
                    task.manager_given_score = manager_given_score
                    task.save()
                 

                    for member in team_members:                       
                        performance_evaluation, _ = PerformanceEvaluation.objects.get_or_create(
                            task=task,
                            employee=member.member,
                            team=task.assigned_to_team,
                            defaults={'obtained_quantitative_score': 0.0, 'obtained_qualitative_score': 0.0},
                        )                        
                        
                        QualitativeEvaluation.objects.create(
                            performance_evaluation=performance_evaluation,
                            employee=member.member,
                            task=task,
                            team = task.assigned_to_team,
                            evaluator=request.user,
                            manager_given_quantitative_number=qualitative_evaluation.manager_given_quantitative_number,
                            manager_given_quantitative_score=manager_given_score,
                           
                            work_quality_score=qualitative_evaluation.work_quality_score,
                            communication_quality_score=qualitative_evaluation.communication_quality_score,
                            teamwork_score=qualitative_evaluation.teamwork_score,
                            initiative_score=qualitative_evaluation.initiative_score,
                            punctuality_score=qualitative_evaluation.punctuality_score,
                            feedback=qualitative_evaluation.feedback,
                        )                        
                       
                        evaluations = QualitativeEvaluation.objects.filter(performance_evaluation=performance_evaluation)
                                              
                        total_max_score, total_score, percentage_score = calculate_performance_quality_score(evaluations)                                       
                                              
                        performance_evaluation.obtained_qualitative_number = total_score
                        performance_evaluation.assigned_qualitative_number = total_max_score
                        performance_evaluation.obtained_qualitative_score = percentage_score 

                        performance_evaluation.given_quantitative_number = manager_given_number    
                        performance_evaluation.given_quantitative_score = manager_given_score
                      
                        performance_evaluation.save()                   
                        
                    messages.success(request, f"Qualitative evaluation for the team '{task.assigned_to_team.name}' was successfully saved.")
                    create_notification(request.user,message=f'Task:{task.title}, manager evaluation completed by Mr {request.user} dated {timezone.now()}',notification_type='TASK-NOTIFICATION')
                else:
                    messages.error(request, "No members found in the assigned team.")
            
            elif task.assigned_to_employee:               
                performance_evaluation, _ = PerformanceEvaluation.objects.get_or_create(
                    task=task,
                    employee=task.assigned_to_employee,
                    defaults={'obtained_quantitative_score': 0.0, 'obtained_qualitative_score': 0.0},
                )                

                qualitative_evaluation.employee = task.assigned_to_employee
                qualitative_evaluation.performance_evaluation = performance_evaluation
                qualitative_evaluation.save()                
               
                evaluations = QualitativeEvaluation.objects.filter(performance_evaluation=performance_evaluation)
                total_max_score, total_score, percentage_score = calculate_performance_quality_score(evaluations)                                       
                                              
                performance_evaluation.obtained_qualitative_number = total_score
                performance_evaluation.assigned_qualitative_number = total_max_score
                performance_evaluation.obtained_qualitative_score = percentage_score 

                manager_given_number = qualitative_evaluation.manager_given_quantitative_number
                manager_given_score =(manager_given_number / task.assigned_number) * 100  
                task.manager_given_number=manager_given_number
                task.manager_given_score = manager_given_score
                task.save()
                            
                performance_evaluation.given_quantitative_number = manager_given_number
                performance_evaluation.given_quantitative_score = manager_given_score               

                performance_evaluation.save()                

                create_notification(request.user,message = f'Task:{task.title}, manager evaluation completed by Mr {request.user} dated {timezone.now()}',notification_type = 'TICKET-NOTIFICATION')             
                messages.success(request, f"Qualitative evaluation for {task.assigned_to_employee.name} was successfully saved.")
            else:
                messages.error(request, "No employee or team assigned to this task.")            
            return redirect('tasks:tasks_list')
        else:
            for field, errors in form.errors.items():
                for error in errors:
                    messages.error(request, f"Error in {field}: {error}")
    else:
        form = QualitativeEvaluationForm(initial={'task': task})
    return render(request, 'tasks/qualitative_evaluation_form.html', {'form': form, 'task': task})



from django.db.models import Case, When, Value, FloatField

taskaggregated_report = []
def aggregated_report_sheet(request):
    global taskaggregated_report
    evaluations = PerformanceEvaluation.objects.all().order_by('evaluation_date')
    
    form = CommonFilterForm(request.GET)
    employee=None
    position=None
    department=None 
    year=None
    aggregation_type=None

    form_data=None

    if form.is_valid():
        year = form.cleaned_data.get('year')
        employee = form.cleaned_data.get('employee')
        department = form.cleaned_data.get('department')
        position = form.cleaned_data.get('position')
        aggregation_type = form.cleaned_data.get('aggregation_type')

        form_data=form.cleaned_data

        if year:
            evaluations = evaluations.filter(year=year)
        if employee:
            evaluations = evaluations.filter(employee__name__icontains=employee)
        if department:
            evaluations = evaluations.filter(department__name=department)
        if position:
            evaluations = evaluations.filter(position__name=position)

        if aggregation_type == 'month_wise':
            taskaggregated_report = evaluations.values(
                'month', 'year', 'employee__id', 'employee__name', 'department__name', 'position__name'
            ).annotate(
                total_assigned_quantitative=Sum('assigned_quantitative_number'),
                total_obtained_quantitative=Sum('obtained_quantitative_number'),
                total_given_quantitative=Sum('given_quantitative_number'),
                total_assigned_qualitative=Sum('assigned_qualitative_number'),
                total_obtained_qualitative=Sum('obtained_qualitative_number'),
                
                avg_quantitative_score=Case(
                    When(total_assigned_quantitative=0, then=Value(0.0)),
                    default=ExpressionWrapper(
                        F('total_obtained_quantitative') * 100.0 / F('total_assigned_quantitative'),
                        output_field=FloatField()
                    )
                ),
                
                avg_manager_given_quantitative_score=Case(
                    When(total_assigned_quantitative=0, then=Value(0.0)),
                    default=ExpressionWrapper(
                        F('total_given_quantitative') * 100.0 / F('total_assigned_quantitative'),
                        output_field=FloatField()
                    )
                ),

                avg_qualitative_score=Case(
                    When(total_assigned_qualitative=0, then=Value(0.0)),
                    default=ExpressionWrapper(
                        F('total_obtained_qualitative') * 100.0 / F('total_assigned_qualitative'),
                        output_field=FloatField()
                    )
                ),

                total_assigned_number=F('total_assigned_quantitative') + F('total_assigned_qualitative'),
                total_obtained_number=F('total_obtained_quantitative') + F('total_obtained_qualitative'),
                total_given_number=F('total_given_quantitative') + F('total_obtained_qualitative'),

                over_all_obtained_score=Case(
                    When(total_assigned_number=0, then=Value(0.0)),
                    default=ExpressionWrapper(
                        F('total_obtained_number') * 100.0 / F('total_assigned_number'),
                        output_field=FloatField()
                    )
                ),

                over_all_given_score=Case(
                    When(total_assigned_number=0, then=Value(0.0)),
                    default=ExpressionWrapper(
                        F('total_given_number') * 100.0 / F('total_assigned_number'),
                        output_field=FloatField()
                    )
                ),
            ).order_by('year', 'month')
           
        elif aggregation_type == 'quarter_wise':
            taskaggregated_report = evaluations.values(
                'quarter', 'year', 'employee__id', 'employee__name', 'department__name', 'position__name'
            ).annotate(
                total_assigned_quantitative=Sum('assigned_quantitative_number'),
                total_obtained_quantitative=Sum('obtained_quantitative_number'),
                total_given_quantitative=Sum('given_quantitative_number'),
                total_assigned_qualitative=Sum('assigned_qualitative_number'),
                total_obtained_qualitative=Sum('obtained_qualitative_number'),
                
                avg_quantitative_score=Case(
                    When(total_assigned_quantitative=0, then=Value(0.0)),
                    default=ExpressionWrapper(
                        F('total_obtained_quantitative') * 100.0 / F('total_assigned_quantitative'),
                        output_field=FloatField()
                    )
                ),
                
                avg_manager_given_quantitative_score=Case(
                    When(total_assigned_quantitative=0, then=Value(0.0)),
                    default=ExpressionWrapper(
                        F('total_given_quantitative') * 100.0 / F('total_assigned_quantitative'),
                        output_field=FloatField()
                    )
                ),

                avg_qualitative_score=Case(
                    When(total_assigned_qualitative=0, then=Value(0.0)),
                    default=ExpressionWrapper(
                        F('total_obtained_qualitative') * 100.0 / F('total_assigned_qualitative'),
                        output_field=FloatField()
                    )
                ),

                total_assigned_number=F('total_assigned_quantitative') + F('total_assigned_qualitative'),
                total_obtained_number=F('total_obtained_quantitative') + F('total_obtained_qualitative'),
                total_given_number=F('total_given_quantitative') + F('total_obtained_qualitative'),

                over_all_obtained_score=Case(
                    When(total_assigned_number=0, then=Value(0.0)),
                    default=ExpressionWrapper(
                        F('total_obtained_number') * 100.0 / F('total_assigned_number'),
                        output_field=FloatField()
                    )
                ),

                over_all_given_score=Case(
                    When(total_assigned_number=0, then=Value(0.0)),
                    default=ExpressionWrapper(
                        F('total_given_number') * 100.0 / F('total_assigned_number'),
                        output_field=FloatField()
                    )
                ),
            ).order_by('year', 'quarter')

        elif aggregation_type == 'year_wise':
            taskaggregated_report = evaluations.values(
                'year', 'employee__id', 'employee__name', 'department__name', 'position__name'
            ).annotate(
                total_assigned_quantitative=Sum('assigned_quantitative_number'),
                total_obtained_quantitative=Sum('obtained_quantitative_number'),
                total_given_quantitative=Sum('given_quantitative_number'),
                total_assigned_qualitative=Sum('assigned_qualitative_number'),
                total_obtained_qualitative=Sum('obtained_qualitative_number'),
                
                avg_quantitative_score=Case(
                    When(total_assigned_quantitative=0, then=Value(0.0)),
                    default=ExpressionWrapper(
                        F('total_obtained_quantitative') * 100.0 / F('total_assigned_quantitative'),
                        output_field=FloatField()
                    )
                ),
                
                avg_manager_given_quantitative_score=Case(
                    When(total_assigned_quantitative=0, then=Value(0.0)),
                    default=ExpressionWrapper(
                        F('total_given_quantitative') * 100.0 / F('total_assigned_quantitative'),
                        output_field=FloatField()
                    )
                ),

                avg_qualitative_score=Case(
                    When(total_assigned_qualitative=0, then=Value(0.0)),
                    default=ExpressionWrapper(
                        F('total_obtained_qualitative') * 100.0 / F('total_assigned_qualitative'),
                        output_field=FloatField()
                    )
                ),

                total_assigned_number=F('total_assigned_quantitative') + F('total_assigned_qualitative'),
                total_obtained_number=F('total_obtained_quantitative') + F('total_obtained_qualitative'),
                total_given_number=F('total_given_quantitative') + F('total_obtained_qualitative'),

                over_all_obtained_score=Case(
                    When(total_assigned_number=0, then=Value(0.0)),
                    default=ExpressionWrapper(
                        F('total_obtained_number') * 100.0 / F('total_assigned_number'),
                        output_field=FloatField()
                    )
                ),

                over_all_given_score=Case(
                    When(total_assigned_number=0, then=Value(0.0)),
                    default=ExpressionWrapper(
                        F('total_given_number') * 100.0 / F('total_assigned_number'),
                        output_field=FloatField()
                    )
                ),
            ).order_by('year')
    
    form=CommonFilterForm()
    if request.GET.get('export') == 'true':
        return export_to_excel(taskaggregated_report)
    
    
    form=CommonFilterForm()
    return render(request, 'tasks/aggregated_report_sheet.html', {
        'aggregated_report': taskaggregated_report,
        'form': form,
        'year':year,
        'aggregation_type':aggregation_type,
        'department':department,
        'employee':employee,
        'form_data':form_data
            })




def export_to_excel(taskaggregated_report):
   
    if not taskaggregated_report:
        return HttpResponse("No data available for export.", content_type="text/plain")

    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "Aggregated Report"
    headers = [
        "Employee", "Year", "Avg Quantitative Score (%)", "Avg Manager Given Quantitative Score (%)",
        "Avg Qualitative Score (%)", "Total Assigned Quantitative Number", "Total Assigned Qualitative Number",
        "Total Assigned Number", "Total Obtained Number", "Total Given Number",
        "Overall Obtained Score (%)", "Overall Given Score (%)"
    ]
    ws.append(headers)

    # Populate rows
    for report in taskaggregated_report:
        row = [
            report.get('employee__name'),
            report.get('year'),
            report.get('avg_quantitative_score', 0),
            report.get('avg_manager_given_quantitative_score', 0),
            report.get('avg_qualitative_score', 0),
            report.get('total_assigned_quantitative_number', 0),
            report.get('total_assigned_qualitative_number', 0),
            report.get('total_assigned_number', 0),
            report.get('total_obtained_number', 0),
            report.get('total_given_number', 0),
            report.get('over_all_obtained_score', 0),
            report.get('over_all_given_score', 0),
        ]
        ws.append(row)
    response = HttpResponse(content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
    response['Content-Disposition'] = 'attachment; filename=aggregated_report.xlsx'
    wb.save(response)
    return response




  
def employee_performance_chart(request):  
    tasks = Task.objects.filter(assigned_to='employee').order_by('-created_at')
    employee_scores = []
    employee=None
    department=None
    has_data=False
    evaluations_by_date = PerformanceEvaluation.objects.all().order_by('-evaluation_date')
   

    form = CommonFilterForm(request.GET or None)

    if request.method == 'GET':
        form = CommonFilterForm(request.GET or None)
        if form.is_valid():
            employee = form.cleaned_data.get('employee_name')
            department = form.cleaned_data.get('department') 
            start_date = form.cleaned_data.get('start_date')
            end_date = form.cleaned_data.get('end_date')
           
           
            if start_date and end_date:
                evaluations_by_date = evaluations_by_date.filter(evaluation_date__range=(start_date, end_date)).distinct()
               
            if department:
                evaluations_by_date = evaluations_by_date.filter(department__name__icontains=department)
               
            if employee:
                evaluations_by_date = evaluations_by_date.filter(employee=employee)                                   
        else:
            print(form.errors)  

                      
        evaluations_by_date = evaluations_by_date.values('evaluation_date').annotate(
        assigned_quantitative_number=Sum('assigned_quantitative_number'),
        assigned_qulaitative_number=Sum('assigned_qualitative_number'),

        obtained_qualitative_number=Sum('obtained_qualitative_number'),
        given_quantitative_number=Sum('given_quantitative_number'),
        ).order_by('evaluation_date')

        for eval_date in evaluations_by_date:
            assigned_quantitative_number2 = eval_date['assigned_quantitative_number']  
            assigned_qulaitative_number2 = eval_date['assigned_qulaitative_number']  
            obtained_qualitative_number2 = eval_date['obtained_qualitative_number']  
            manager_given_quantitative_number2 = eval_date['given_quantitative_number']
            total_score = ((obtained_qualitative_number2+ manager_given_quantitative_number2) / (assigned_quantitative_number2 + assigned_qulaitative_number2)) * 100
            total_score = min(total_score, 100)  # Cap the score at 100
            
            employee_scores.append({
                'created_at': eval_date['evaluation_date'].strftime('%Y-%m-%d'),
                'total_score': total_score,
                'employee_name': employee.name if employee else 'Unknown'
            })
            has_data=bool(employee_scores)

    else:
        for field, errors in form.errors.items():
            for error in errors:
                messages.error(request, f"Error in {field}: {error}")

    chart_data = json.dumps( employee_scores)
    
    form = CommonFilterForm()
    paginator = Paginator(employee_scores, 6)  
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number) 


  
    return render(request, 'tasks/employee_performance_chart.html', {
        'chart_data': chart_data,
        'employee_scores': employee_scores,
        'form': form,
        'page_obj':page_obj,
        'employee':employee,
        'department':department,
        'has_data':has_data
    })





def team_performance_chart(request):  
    tasks = Task.objects.filter(assigned_to='team').order_by('created_at')
    team_scores_over_time = []
    has_data=False

    form = CommonFilterForm(request.GET)
    if form.is_valid():
        team_name = form.cleaned_data.get('team_name')
        department = form.cleaned_data.get('department')
        start_date = form.cleaned_data.get('start_date')
        end_date = form.cleaned_data.get('end_date')

        teams = Team.objects.all().order_by('created_at')
        if start_date and end_date:            
            teams= teams.filter(team_ev__evaluation_date__range=(start_date,end_date)).distinct()
        if team_name:
            teams = teams.filter(name__icontains=team_name)
        if department:
            teams = teams.filter(department__name=department)
        
        # teams = Team.objects.all() if not team_name else Team.objects.filter(name__icontains=team_name)

        for team in teams:
            for task in tasks.filter(assigned_to_team=team).order_by('created_at'):
                evaluations_by_date = PerformanceEvaluation.objects.filter(
                    team=team, task=task                        
                ).values('created_at__date').annotate(
                    assigned_quantitative_number=Sum('assigned_quantitative_number'),
                    assigned_qulaitative_number=Sum('assigned_qualitative_number'),
                    obtained_qualitative_number=Sum('obtained_qualitative_number'),
                    given_quantitative_number=Sum('given_quantitative_number'),
                ).order_by('evaluation_date')

                for eval_date in evaluations_by_date:
                    assigned_quantitative_number2 = eval_date['assigned_quantitative_number']
                    assigned_qulaitative_number2 = eval_date['assigned_qulaitative_number']
                    obtained_qualitative_number2 = eval_date['obtained_qualitative_number']
                    manager_given_quantitative_number2 = eval_date['given_quantitative_number']
                    total_score = ((obtained_qualitative_number2 + manager_given_quantitative_number2) /
                                   (assigned_quantitative_number2 + assigned_qulaitative_number2)) * 100
                    total_score = min(total_score, 100)

                    team_scores_over_time.append({
                        'team': team.name,
                        'created_at': eval_date['created_at__date'].strftime('%Y-%m-%d'),
                        'score': total_score
                    })
                    has_data = bool(team_scores_over_time)

    else:
        print(f"Form errors: {form.errors}")

    paginator = Paginator(team_scores_over_time, 6)  
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)   

    form = CommonFilterForm() 
    return render(request, 'tasks/team_performance_chart.html', {
        'chart_data': json.dumps(team_scores_over_time),
        'team_scores': team_scores_over_time,
        'form': form,
        'page_obj':page_obj,
        'team_name':team_name,
        'department':department,
        'has_data':has_data
    })



def year_month_performance_chart(request):
    year = None   
    employee = None
    form = MonthlyQuarterlyTrendForm(request.GET)
    report_data = []
    has_data=None
    department=None

    if form.is_valid():       
        department = form.cleaned_data.get('department')
        employee = form.cleaned_data.get('employee')
        year = form.cleaned_data.get('year')
       
        employees = Employee.objects.all()

        if employee and department:
            employees = employees.filter(
               name=employee.name,            
                department=department
            ).first()

        if employee:
            employees = employees.filter(
               name=employee.name               
            ).first()
      
       
        if employee:
            evaluations = PerformanceEvaluation.objects.filter(
                evaluation_date__year=year,
                employee=employee
            ).values('evaluation_date__month', 'evaluation_date__year').annotate(
                    assigned_quantitative_number=Sum('assigned_quantitative_number'),
                    assigned_qulaitative_number=Sum('assigned_qualitative_number'),
                    obtained_qualitative_number=Sum('obtained_qualitative_number'),
                    given_quantitative_number=Sum('given_quantitative_number'),
                    
            ).order_by('evaluation_date__month')
            for eval_date in evaluations:
                assigned_quantitative_number2 = eval_date['assigned_quantitative_number']  # * QUANTITATIVE_WEIGHT
                assigned_qulaitative_number2 = eval_date['assigned_qulaitative_number']  # * QUALITATIVE_WEIGHT
                obtained_qualitative_number2 = eval_date['obtained_qualitative_number']  # * QUANTITATIVE_WEIGHT
                manager_given_quantitative_number2 = eval_date['given_quantitative_number']
                total_score = ((obtained_qualitative_number2+ manager_given_quantitative_number2) / (assigned_quantitative_number2 + assigned_qulaitative_number2)) * 100
                total_score = min(total_score, 100)  # Cap the score at 100

            def get_month_name(month_number):
                month_names = [
                    'January', 'February', 'March', 'April', 'May', 'June',
                    'July', 'August', 'September', 'October', 'November', 'December'
                ]
                return month_names[month_number - 1]  

            for entry in evaluations:
                month_number = entry['evaluation_date__month']
                year_number = entry['evaluation_date__year']
                month_name = get_month_name(month_number)  

                report_data.append({
                    'created_at': month_name,  
                    'total_score': total_score,
                })
    else:
        print(form.errors)
        form = MonthlyQuarterlyTrendForm()

    chart_labels = [data['created_at'] for data in report_data]  
    total_scores = [data['total_score'] for data in report_data]
    has_data=bool(report_data)

    chart_data = {
        "labels": chart_labels,
        "total_scores": total_scores,
    }

    chart_data_json = json.dumps(chart_data)

  
    paginator = Paginator(report_data, 6)  
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)   

    form = MonthlyQuarterlyTrendForm()
    return render(request, 'tasks/year_month_performance_chart.html', {
        'form': form,
        'year': year,
        'employee_name': employee.name if employee else '',
        'report_data': report_data,
        'chart_data_json': chart_data_json,
        'page_obj':page_obj,
        'has_data':has_data,
        'department':department
    })




def year_quarter_performance_chart(request):
    year=None
    employee_name = None   
    employee = None
    form = MonthlyQuarterlyTrendForm(request.GET)
    report_data = {}  
    has_data=None
    department=None
    employees = Employee.objects.all()

    if form.is_valid():       
        department = form.cleaned_data.get('department')
        employee = form.cleaned_data.get('employee')
        year = form.cleaned_data.get('year')  

        if department:
            employee = employees.filter(name=employee.name, department=department).first()                  
       
        evaluations = PerformanceEvaluation.objects.filter(
            evaluation_date__year=year,
            employee=employee
        ).values('quarter').annotate(
            assigned_quantitative_number=Sum('assigned_quantitative_number'),
            assigned_qulaitative_number=Sum('assigned_qualitative_number'),
            obtained_qualitative_number=Sum('obtained_qualitative_number'),
            given_quantitative_number=Sum('given_quantitative_number'),
        ).order_by('evaluation_date')

        for eval_date in evaluations:
                assigned_quantitative_number2 = eval_date['assigned_quantitative_number']  # * QUANTITATIVE_WEIGHT
                assigned_qulaitative_number2 = eval_date['assigned_qulaitative_number']  # * QUALITATIVE_WEIGHT
                obtained_qualitative_number2 = eval_date['obtained_qualitative_number']  # * QUANTITATIVE_WEIGHT
                manager_given_quantitative_number2 = eval_date['given_quantitative_number']
                total_score = ((obtained_qualitative_number2+ manager_given_quantitative_number2) / (assigned_quantitative_number2 + assigned_qulaitative_number2)) * 100
                total_score = min(total_score, 100)  # Cap the score at 100

        report_data = {}
        for entry in evaluations:
            quarter = entry['quarter']
            quarter_name = f"{quarter}"
            report_data[quarter_name] = {               
                'total_score': total_score,
            }
    else:
        print("Form errors:", form.errors)

    chart_labels = list(report_data.keys())   
    total_scores = [data['total_score'] for data in report_data.values()]
    has_data = bool(report_data)

    chart_data = {
        "labels": chart_labels,       
        "total_scores": total_scores,
    }

    chart_data_json = json.dumps(chart_data)  

    report_data_items = list(report_data.items())  
    paginator = Paginator(report_data_items, 6)  
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)   

    form=MonthlyQuarterlyTrendForm()
    return render(request, 'tasks/year_quarter_performance_chart.html', {
        'form': form,
        'year': year,
        'employee_name': employee_name if 'employee_name' in locals() else '',
        'report_data': report_data,
        'chart_data_json': chart_data_json,  
        'page_obj':page_obj,
        'has_data':has_data,
        'department':department,
        'employee':employee
    })




def yearly_performance_trend(request):
    employee_scores = {}
    chart_data = {}   
    employee = None
    department = None
    has_data=None

    form = YearlyTrendForm(request.GET)

    if form.is_valid():
        employee= form.cleaned_data.get('employee_name')
        start_year = form.cleaned_data.get('start_year')
        end_year = form.cleaned_data.get('end_year')
        department = form.cleaned_data.get('department')

       
        if start_year and not end_year:
            end_year = start_year
        elif not start_year and end_year:
            start_year = end_year
        if not start_year and not end_year:
            start_year = 2000
            end_year = date.today().year

        employees = Employee.objects.all()
        if department:
            employees = employees.filter(department=department)
        if employee:
            employee = employees.filter(name=employee.name).first() if employee else None

        if employee:
            evaluations = PerformanceEvaluation.objects.filter(
                employee=employee,
                evaluation_date__year__gte=start_year,
                evaluation_date__year__lte=end_year,
            ).values(
                'evaluation_date__year'
            ).annotate(
                assigned_quantitative_number=Sum('assigned_quantitative_number'),
                assigned_qulaitative_number=Sum('assigned_qualitative_number'),
                obtained_qualitative_number=Sum('obtained_qualitative_number'),
                given_quantitative_number=Sum('given_quantitative_number'),
            ).order_by('evaluation_date__year')

            for evaluation in evaluations:
                year = evaluation['evaluation_date__year']               

                assigned_quantitative_number2 = evaluation.get('assigned_quantitative_number', 0) or 0
                assigned_qulaitative_number2 = evaluation.get('assigned_qulaitative_number', 0) or 0
                obtained_qualitative_number2 = evaluation.get('obtained_qualitative_number', 0) or 0
                manager_given_quantitative_number2 = evaluation.get('given_quantitative_number', 0) or 0

                denominator = assigned_quantitative_number2 + assigned_qulaitative_number2
                if denominator > 0:
                    total_score = (
                        (obtained_qualitative_number2 + manager_given_quantitative_number2) / denominator
                    ) * 100
                    total_score = min(total_score, 100)
                    employee_scores[year] = {'total_score': round(total_score, 2)}
                    print(f"Year: {year}, Total Score: {total_score}")
                else:
                    print(f"Year: {year}, Skipped due to zero denominator")

            chart_data = json.dumps(employee_scores)
   
        has_data = bool(employee_scores)

    employee_scores_items = list(employee_scores.items())
    paginator = Paginator(employee_scores_items, 6)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    form = YearlyTrendForm()
    return render(request, 'tasks/yearly_performance_trend.html', {
        'form': form,
        'chart_data': chart_data,
        'employee_scores': employee_scores,
        'employee_name':employee,
        'department': department,
        'page_obj': page_obj,
        'has_data':has_data
    })




def group_performance_chart(request):
    employee_data = {}
    chart_data={}

    form = CommonFilterForm(request.GET)
    if form.is_valid():
        position = form.cleaned_data.get('position')
        department = form.cleaned_data.get('department')
        start_date = form.cleaned_data.get('start_date')
        end_date = form.cleaned_data.get('end_date')

        evaluations = PerformanceEvaluation.objects.none().order_by('evaluation_date')

        if position:
            evaluations = PerformanceEvaluation.objects.filter(position__name=position).order_by('evaluation_date')
        if department:
            evaluations = evaluations.filter(department__name=department)
        if start_date and end_date:
            evaluations = evaluations.filter(evaluation_date__range=(start_date, end_date))

        evaluations = (
            evaluations.values("employee__name", "evaluation_date")
            .annotate(average_score=Avg("total_obtained_score"))
            .order_by("evaluation_date")
        )

        for evaluation in evaluations:
            employee_name = evaluation["employee__name"]
            date = evaluation["evaluation_date"].strftime('%Y-%m-%d')
            average_score = round(evaluation["average_score"], 2)

            if employee_name not in employee_data:
                employee_data[employee_name] = {
                    "dates": [],
                    "scores": [],
                }

            employee_data[employee_name]["dates"].append(date)
            employee_data[employee_name]["scores"].append(average_score)

        all_dates = sorted({date for data in employee_data.values() for date in data["dates"]})

        colors = [
            "rgba(255, 99, 132, 1)",  # Red
            "rgba(54, 162, 235, 1)",  # Blue
            "rgba(255, 206, 86, 1)",  # Yellow
            "rgba(75, 192, 192, 1)",  # Teal
            "rgba(153, 102, 255, 1)",  # Purple
            "rgba(255, 159, 64, 1)",  # Orange
        ]
        
        if position:
           chart_data = {
                "labels": all_dates,
                "datasets": [
                    {
                        "label": f'{employee_name} - {position}' if position else employee_name,
                        "data": [
                            employee_data[employee_name]["scores"][employee_data[employee_name]["dates"].index(date)]
                            if date in employee_data[employee_name]["dates"]
                            else 30  # Fill missing dates with None
                            for date in all_dates
                        ],
                        "borderColor": colors[i % len(colors)],
                        "backgroundColor": colors[i % len(colors)].replace("1)", "0.6)"),
                        "borderWidth": 2,
                        "fill": False,
                        "tension": 0.4,
                    }
                    for i, employee_name in enumerate(employee_data.keys())
                ],
            }


        else:
            chart_data = {}
        has_data = bool(chart_data.get("datasets"))



    flattened_data = []
    for employee_name, data in employee_data.items():
        for date, score in zip(data["dates"], data["scores"]):
            flattened_data.append({
                "employee": employee_name,
                "date": date,
                "score": score,
            })

    paginator = Paginator(flattened_data, 8)  
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    form = CommonFilterForm()
    context = {
        "chart_data": json.dumps(chart_data),
        "evaluations": evaluations,
        "form": form,
        "page_obj": page_obj,
        'has_data':has_data
    }
    return render(request, "tasks/group_performance_chart.html", context)




def increment_promotion_check(request):
    task_counts=[]
    weighted_scores=[] 
    max_task_count=0 
    task_factor=0
    weighted_final_score=0


    total_eligible = 0
    percentage_of_eligibility = 0
    report_data = []
    eligible_employee_list = []
    eligible_employees = []
    total_employee = 0
    promotional_increment_total = 0
    salary_increment_total = 0
    total_increment_total = 0
    
    appraisal_year = 0
    appraisal_type = 'Unknown'
    salary_increment_for_all=0
    salary_increment_for_all_total=0
    all_eligible_count=0
    total_eligible_employee_list=[]
    percentage_of_all_eligibility=0.0
    salary_increment_percentage=0
    promotional_increment_percentage=0
    max_promotion_limit=0
    eligible_score_for_promotion=0
    percentage_of_all_eligibility=0
    task_count_for_employee = 0      
    task_counts=[]
    max_task_count= 0
    average_task_count= 0
    final_score =0
    total_eligible_count =0 
    month_name=None
    quarter_name = None
    chart_data=[]
    chart_data2=[]

    form = IncrementPromotionCheckForm(request.POST or None)
    month_name_to_num = {month.upper(): num for num, month in enumerate(calendar.month_name[1:], 1)}

    if request.method == 'POST' and form.is_valid():  
        appraisal_year = form.cleaned_data['appraisal_year']
        appraisal_type = form.cleaned_data['appraisal_type']
        quarter_name = form.cleaned_data['quarter']
        half_year = form.cleaned_data['half_year']
        month_name = form.cleaned_data['month']
        year = form.cleaned_data['year']
        salary_increment_percentage = form.cleaned_data['salary_increment_percentage']
        eligible_score_for_promotion = form.cleaned_data['eligible_score_for_promotion']
        max_promotion_limit = form.cleaned_data['max_promotion_limit']
        promotional_increment_percentage = form.cleaned_data['promotional_increment_percentage']
       
        base_evaluations = PerformanceEvaluation.objects.all()
        if appraisal_year:
            base_evaluations = base_evaluations.filter(year=appraisal_year)
            performance_evaluations = None 

            employes=Employee.objects.all()
            for employee in employes:
                salary_increment_for_all= float(employee.salary_structure.basic_salary)* (salary_increment_percentage / 100)
                salary_increment_for_all_total += salary_increment_for_all
        else:
            messages.info(request,'Please select appraisal year')
        
        if appraisal_type == 'QUARTERLY': 
            if quarter_name:
                performance_evaluations = base_evaluations.filter(quarter=quarter_name)          

        elif appraisal_type == 'HALF-YEARLY':         
            if half_year:
                performance_evaluations = base_evaluations.filter(half_year=half_year) 

        elif appraisal_type == 'YEARLY':         
            if year:
                performance_evaluations = base_evaluations.filter(year=year)               

        elif appraisal_type == 'MONTHLY':    
            if month_name:
                month_num = month_name_to_num.get(month_name.upper())
                if month_num:
                    performance_evaluations = base_evaluations.filter(evaluation_date__month=month_num)                  
        else:
            print("No specific filter selected")       
        if performance_evaluations and performance_evaluations.exists(): 
            distinct_employees = performance_evaluations.values('employee').distinct() 
            for employee in distinct_employees:
                employee_id = employee['employee'] 
                employee=get_object_or_404(Employee,id=employee_id)                            
                                                       
                employee_evaluations = performance_evaluations.filter(employee=employee)                
                task_count_for_employee = employee_evaluations.count()
                task_counts.append(task_count_for_employee)          
                            
                total_obtained = sum(evaluation.total_obtained_number for evaluation in employee_evaluations)
                total_assigned = sum(evaluation.total_assigned_number for evaluation in employee_evaluations)

                max_task_count = max(task_counts) if task_counts else 1
                if total_assigned > 0:
                        final_score = (total_obtained / total_assigned) * 100
                        task_factor = task_count_for_employee / max_task_count
                        weighted_final_score = final_score * task_factor
                else:
                    weighted_final_score = 0

                weighted_scores.append(
                    {
                        "employee": employee,
                        "weighted_final_score": weighted_final_score,
                        "task_count_employee": task_count_for_employee,
                        "final_score": final_score,
                        }
                    )                 

            eligible_employees = [
                score for score in weighted_scores if score["weighted_final_score"] >= eligible_score_for_promotion
            ]
            total_eligible_count = len(eligible_employees)

            if eligible_employees:
                obtained_promotion_recommendation = 'Yes'
            else:
                obtained_promotion_recommendation = 'No'

            eligible_employees.sort(key=lambda x: x["weighted_final_score"], reverse=True)

            top_20_percent_count = int(len(eligible_employees) * max_promotion_limit / 100)
            top_20_percent_employees = eligible_employees[:top_20_percent_count]

            total_employee=Employee.objects.all().count

            eligible_employee_list = Employee.objects.filter(
                id__in=[e['employee'].id for e in top_20_percent_employees]
            ).values('id', 'name', 'salary_structure__basic_salary', 'department__name', 'position__name').order_by('name')

            for employee in eligible_employee_list:
                if any(employee['id'] == e['employee'].id for e in top_20_percent_employees):
                    promotional_increment = promotional_increment_percentage / 100.0 * float(employee['salary_structure__basic_salary'])
                else:
                    promotional_increment = 0
                promotional_increment_total += promotional_increment
            total_increment_total = promotional_increment_total + salary_increment_for_all_total

            eligible_report = (
                Employee.objects.filter(id__in=[e['employee'].id for e in top_20_percent_employees])
                .values('department__name', 'position__name')
                .annotate(eligible_count=Count('id'))
                .order_by('department__name', 'position__name')
            )

            total_report = (
                Employee.objects.all()
                .values('department__name', 'position__name')
                .annotate(total_count=Count('id'))
                .order_by('department__name', 'position__name')
            )

            total_eligible = len(top_20_percent_employees)
            total_employee = Employee.objects.all().count()

            if total_employee > 0:
                percentage_of_eligibility = total_eligible / total_employee * 100
                percentage_of_all_eligibility = total_eligible_count / total_employee * 100

            report_data = []
            total_report_dict = {f"{row['department__name']}|{row['position__name']}": row['total_count'] for row in total_report}
            for row in eligible_report:
                department_position_key = f"{row['department__name']}|{row['position__name']}"
                total_count = total_report_dict.get(department_position_key, 0)
                report_data.append({
                    'department_name': row['department__name'],
                    'position_name': row['position__name'],
                    'eligible_count': row['eligible_count'],
                    'total_count': total_count,
                })

            total_eligible_employee_list = Employee.objects.filter(
                id__in=[e['employee'].id for e in eligible_employees]
            ).values('id', 'name', 'salary_structure__basic_salary', 'department__name', 'position__name').order_by('name')

            chart_data = {
                'labels': ['Promotional Increment', 'Salary Increment', 'Total Increment'],
                'values': [promotional_increment_total, salary_increment_for_all_total, total_increment_total],
            }

            chart_data2 = {
                'labels': ['Total Employee', 'Eligible Employee', 'Top Eligible'],
                'values': [total_employee, total_eligible_count, total_eligible],
            }                       

    else:
       print(form.errors)        
       print("The form submission is invalid. Please correct the errors.")

    form = IncrementPromotionCheckForm()   
    paginator = Paginator( eligible_employee_list, 10)  
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    paginator = Paginator(total_eligible_employee_list, 10)  
    page_number = request.GET.get('page')
    page_obj2 = paginator.get_page(page_number)
   
    return render(request, 'tasks/increment_promotion_check.html', {
         'form': form,
        'report_data': report_data,
        'total_eligible': total_eligible,
        'all_eligible_count': total_eligible_count,
        'total_employee': total_employee,
        'percentage_of_eligibility': percentage_of_eligibility,
        'eligible_employee_list': eligible_employee_list,
        'toal_eligible_employee_list':total_eligible_employee_list,
        'promotional_increment': promotional_increment_total,
        'salary_increment': salary_increment_for_all_total,
        'total_increment': total_increment_total,
        'chart_data': json.dumps(chart_data),
        'chart_data2': json.dumps(chart_data2),
        'appraisal_year': appraisal_year,
        'appraisal_type': appraisal_type,
        'salary_increment_percentage': salary_increment_percentage,
        'promotional_increment_percentage': promotional_increment_percentage,
        'max_promotion_limit':max_promotion_limit,
        'eligible_score_for_promotion': eligible_score_for_promotion,
        'percentage_of_all_eligibility':percentage_of_all_eligibility,
        'page_obj':page_obj,
        'page_obj2':page_obj2

        
    })



def calculate_task_count(year=None, quarter=None, half_year=None, month=None):
    task_queryset = PerformanceEvaluation.objects.filter(year=year)
    if month:
        task_queryset = task_queryset.filter(month=month)
    elif quarter:
        task_queryset = task_queryset.filter(quarter=quarter)
    elif half_year:
        task_queryset = task_queryset.filter(half_year=half_year)
    elif year:
        task_queryset = task_queryset.filter(year=year)
   
    max_task_count = (
        task_queryset.values('employee')
        .annotate(task_count=Count('id'))
        .aggregate(max_task_count=Max('task_count'))['max_task_count']
    )
    
    avg_task_count = (
        task_queryset.values('employee')
        .annotate(task_count=Count('id'))
        .aggregate(avg_task_count=Avg('task_count'))['avg_task_count']    )

    return max_task_count or 0, avg_task_count or 0 


def get_employees(appraisal_category, employee_id=None, department_name=None, position_name=None):
    if appraisal_category == 'BY_EMPLOYEE' and employee_id:
        return Employee.objects.filter(id=employee_id)
    elif appraisal_category == 'BY_DEPARTMENT' and department_name:
        return Employee.objects.filter(department__name=department_name)
    elif appraisal_category == 'BY_POSITION' and position_name:
        return Employee.objects.filter(position__name=position_name)
    elif appraisal_category == 'BY_COMPANY':
        return Employee.objects.all()
    return Employee.objects.none()



# below view is for final appraisal submission
def increment_promotion(request):
    data=SalaryIncrementAndPromotion.objects.all().order_by('-created_at')
    paginator = Paginator(data, 10)  
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    employee_totals = {}
    task_count =0
    max_task_count = 0 
    avg_task_count=0
    weighted_scores=[]
    appraisal_year=None
    appraisal_type=None
    appraisal_category=None
    quarter=None
    half_year=None
    month=None
    year=None
    department_name=None
    position_name=None
    eligible_score_for_promotion=None
    max_promotion_limit=None
    promotional_increment_percentage=None
    salary_increment_percentage=None
    effective_date=None
    obtained_promotion_recommendation=None
 
    
    month_name_to_num = {month.upper(): num for num, month in enumerate(calendar.month_name[1:], 1)}
    
    form = IncrementPromotionForm(request.POST or None)
    if request.method == 'POST' and form.is_valid():

        appraisal_year = form.cleaned_data.get('appraisal_year')
        appraisal_type = form.cleaned_data.get('appraisal_type')
        quarter = form.cleaned_data.get('quarter')
        half_year = form.cleaned_data.get('half_year')
        month = form.cleaned_data.get('month')
        year = form.cleaned_data.get('year')
        appraisal_category = form.cleaned_data.get('appraisal_category')
        department_name = form.cleaned_data.get('department')
        position_name = form.cleaned_data.get('position')
        employee_name = form.cleaned_data.get('employee')

        eligible_score_for_promotion = form.cleaned_data.get('eligible_score_for_promotion')
        max_promotion_limit = form.cleaned_data.get('max_promotion_limit')
        promotional_increment_percentage =form.cleaned_data.get('promotional_increment_percentage')
        salary_increment_percentage =form.cleaned_data.get('salary_increment_percentage')
        effective_date =form.cleaned_data.get('effective_date')

        max_task_count, avg_task_count = calculate_task_count(        
        quarter=quarter,
        half_year=half_year,
        month=month,
        year=year
    )     

        if appraisal_year is None:
            messages.info(request,'Please select appraisal year and other parameters')
        else:
            pass
       
        performance_evaluations = PerformanceEvaluation.objects.all()

        if appraisal_category == 'BY_EMPLOYEE' and employee_name:
            employee= get_object_or_404(Employee,name = employee_name)
            employees = get_employees(appraisal_category, employee_id=employee.id)
        else:
            employees = get_employees(appraisal_category, department_name=department_name, position_name=position_name)

       
        employee_performance = []
        precision = Decimal('0.01')

        if employees.exists():
            for employee in employees:
                employee_evaluations = performance_evaluations.filter(employee=employee)
                if not employee_evaluations.exists():    
                    salary_increment_amount_for_non_evaluated_employee = (
                        employee.salary_structure.basic_salary * Decimal(salary_increment_percentage) / Decimal(100.0) * Decimal(0.5)
                    )                                   
                    new_basic_salary = employee.salary_structure.basic_salary + salary_increment_amount_for_non_evaluated_employee                
                    with transaction.atomic():
                        SalaryIncrementAndPromotion.objects.update_or_create(
                            employee=employee,
                            appraisal_type=appraisal_type,
                            appraisal_year=appraisal_year,
                            defaults={
                                "month": month,
                                "quarter": quarter,
                                "half_year": half_year,    
                                "year": year,  
                                'salary_increment_amount': Decimal(salary_increment_amount_for_non_evaluated_employee).quantize(precision, rounding=ROUND_HALF_UP),  
                                "new_basic_salary": Decimal(new_basic_salary).quantize(precision, rounding=ROUND_HALF_UP),                     
                            }
                        )  
                    employee.salary_structure.basic_salary = new_basic_salary
                    employee.save()
                    messages.info(request, f'Employee {employee.name} is not under performance evaluation; applying 50% salary increment.')
                    return render(request, 'tasks/increment_promotion.html', {'form': IncrementPromotionForm(), 'page_obj': page_obj})

                else:

                    if appraisal_type == 'QUARTERLY' and quarter and appraisal_year:  
                        employee_evaluations = employee_evaluations.filter(
                           year=appraisal_year,
                            quarter=quarter
                        )
                
                    elif appraisal_type == 'HALF-YEARLY' and half_year and appraisal_year:
                        employee_evaluations = employee_evaluations.filter(
                            year=appraisal_year,
                            half_year=half_year
                        )
                    
                    elif appraisal_type == 'YEARLY' and appraisal_year:
                        employee_evaluations = employee_evaluations.filter(
                            year=year,
                            
                        )
    
                    elif appraisal_type == 'MONTHLY' and month and appraisal_year:
                        month_num = month_name_to_num.get(month.upper())
                        if month_num:
                            employee_evaluations = employee_evaluations.filter(
                                appraisal_year=appraisal_year,
                                evaluation_date__month=month_num
                            )
                    else:
                        print("No specific filter selected or missing required data for appraisal type.")

                    if employee_evaluations.exists():
                        employee_performance.append(employee_evaluations)
                    else:
                        print(f"No matching performance evaluations found for {employee.name} based on selected criteria.")
      

            for evaluations in employee_performance:
                for evaluation in evaluations:
                    if evaluation.total_assigned_number > 0:
                        employee_name = evaluation.employee.name
        
                        if employee_name not in employee_totals:
                            employee_totals[employee_name] = {'total_assigned': 0, 'total_obtained': 0,'task_count':0}

                        employee_totals[employee_name]['total_assigned'] += evaluation.total_assigned_number
                        employee_totals[employee_name]['total_obtained'] += evaluation.total_obtained_number
                        employee_totals[employee_name]['task_count'] += 1
                               
        
            if employee_totals:            
                for employee_name, totals in employee_totals.items():
                    total_assigned = totals.get('total_assigned', 0)
                    total_obtained = totals.get('total_obtained', 0)
                    task_count_for_employee = totals.get('task_count', 0)
            
                    final_score = (total_obtained / total_assigned) * 100 if total_assigned > 0 else 0
                    task_factor = task_count_for_employee / max_task_count if max_task_count > 0 else 1
                    weighted_final_score = final_score * task_factor
                    obtained_salary_increment_percentage_for_all = salary_increment_percentage * weighted_final_score / 100

                    weighted_scores.append(
                        {
                            "employee": employee_name,
                            "weighted_final_score": weighted_final_score,
                            "task_count_employee": task_count_for_employee,
                            "final_score": final_score,
                            "task_factor": task_factor,
                            'avg_task_count':avg_task_count,
                            "obtained_salary_increment_percentage_for_all": obtained_salary_increment_percentage_for_all,
                        }
                    )
    
            total_promotion_eligible_employees = [
                score for score in weighted_scores if score["weighted_final_score"] >= eligible_score_for_promotion
            ]
            total_promotion_eligible_count = len(total_promotion_eligible_employees)

            total_promotion_eligible_employee_list = Employee.objects.filter(
                name__in=[e['employee'] for e in total_promotion_eligible_employees]
            ).values('id', 'name', 'salary_structure__basic_salary', 'department__name', 'position__name').order_by('name')
    
            for employee in total_promotion_eligible_employee_list:
                obtained_promotion_recommendation = "Yes"
                for score in weighted_scores:
                    if score['employee'] == employee['name']:
                        score['obtained_promotion_recommendation'] = obtained_promotion_recommendation
    
            total_promotion_eligible_employees.sort(key=lambda x: x["weighted_final_score"], reverse=True)
            top_20_percent_count = int(len(total_promotion_eligible_employees) * max_promotion_limit / 100)
            top_20_percent_employees = total_promotion_eligible_employees[:top_20_percent_count]

            top_20_eligible_employee_list = Employee.objects.filter(
                name__in=[e['employee'] for e in top_20_percent_employees]
            ).values('id', 'name', 'salary_structure__basic_salary', 'department__name', 'position__name').order_by('name')

            for employee in top_20_eligible_employee_list:  
                employee_score = next(
                    (score for score in weighted_scores if score['employee'] == employee['name']), None
                )
                if employee_score:
                    weighted_final_score = employee_score['weighted_final_score']
                    employee_in_top_20 = any(
                        top_employee['employee'] == employee['name'] for top_employee in top_20_percent_employees
                    )

                    if employee_in_top_20:
                        obtained_promotional_increment_percentage = (
                            promotional_increment_percentage * weighted_final_score / 100
                        )
                        promotion_recommendation = "Yes"
                    else:
                        obtained_promotional_increment_percentage = 0
                        promotion_recommendation = "No"

                    employee_score['promotion_recommendation'] = promotion_recommendation
                    employee_score['obtained_promotional_increment_percentage'] = obtained_promotional_increment_percentage

            for score in weighted_scores:
                employee_name = score.get('employee', 'Unknown')
                obtained_promotional_increment_percentage = score.get('obtained_promotional_increment_percentage', 0)
                promotion_recommendation = score.get('promotion_recommendation', 'No')
                obtained_salary_increment_percentage_for_all = score.get('obtained_salary_increment_percentage_for_all', 0)
                weighted_final_score = score.get('weighted_final_score', 0)
                task_count_employee = score.get('task_count_employee', 0)
                final_score = score.get('final_score', 0)
                task_factor = score.get('task_factor', 1)

                employee = Employee.objects.get(name=employee_name)

                salary_increment_amount = Decimal(obtained_salary_increment_percentage_for_all / 100) * employee.salary_structure.basic_salary 
                promotional_increment_amount = Decimal(obtained_promotional_increment_percentage / 100) * employee.salary_structure.basic_salary
                new_basic_salary = employee.salary_structure.basic_salary + salary_increment_amount + promotional_increment_amount

                with transaction.atomic():
                    SalaryIncrementAndPromotion.objects.update_or_create(
                        employee_id=employee.id,
                        appraisal_type=appraisal_type,
                        appraisal_year=appraisal_year,
                        defaults={
                            "month": month,
                            "quarter": quarter,
                            "half_year": half_year,
                            "year":year,
                            'department':department_name,
                            'position':position_name,
                            "appraisal_year": appraisal_year,                
                            "appraisal_category": appraisal_category,
                        
                            "final_score": final_score,
                            "weighted_final_score": weighted_final_score,
                            "obtained_promotion_recommendation": obtained_promotion_recommendation, 
                            "promotion_recommendation": promotion_recommendation,                  
                            "new_basic_salary": new_basic_salary,                  
                        
                            "max_task_count": max_task_count,
                            'task_count_employee':task_count_employee,
                            'task_factor':task_factor,
                            'avg_task_count': avg_task_count,
                            'salary_increment_percentage':salary_increment_percentage,
                            'promotional_increment_percentage':promotional_increment_percentage,
                            'obtained_salary_increment_percentage':obtained_salary_increment_percentage_for_all,
                            'obtained_promotional_increment_percentage':obtained_promotional_increment_percentage,
                            'promotional_increment_amount':promotional_increment_amount,
                            'salary_increment_amount':salary_increment_amount,
                            'effective_date':effective_date


                        }
                    )   

                    employee.salary_structure.basic_salary = new_basic_salary
                    employee.save()                 
                     
    else:
        print('form is invalid')       
    form = IncrementPromotionForm() 
    return render(request, 'tasks/increment_promotion.html', {
        'form': form,
        'page_obj':page_obj
    })



# Below view is for data fetching after final appraisal submission
def increment_promotion_final_data(request):    
    form = IncrementPromotionFinalDataForm(request.GET) 
    data = SalaryIncrementAndPromotion.objects.all().order_by('-created_at')  

    appraisal_year=None
    appraisal_type=None
    month=None
    quarter=None
    half_year=None


    if form.is_valid():
        appraisal_year = form.cleaned_data.get('appraisal_year')
        appraisal_category = form.cleaned_data.get('appraisal_category')
        appraisal_type = form.cleaned_data.get('appraisal_type')
        quarter = form.cleaned_data.get('quarter')
        half_year = form.cleaned_data.get('half_year')
        month = form.cleaned_data.get('month')
        year=form.cleaned_data.get('year')

        if appraisal_category:
            data = data.filter(appraisal_category=appraisal_category)

        if appraisal_year:
            data = data.filter(appraisal_year=appraisal_year)
        if year:
            data = data.filter(year=year)

        if quarter:
            data = data.filter(quarter=quarter)

        if half_year:
            data = data.filter(half_year=half_year)

        if month:
            data = data.filter(month=month)

    
        total_employee = Employee.objects.all().count()
        total_employee_evaluated = data.count()
        total_promoted_employee = data.filter(promotion_recommendation='Yes').count()
     
        total_salary_increment = data.aggregate(total_salary_increment=Sum('salary_increment_amount'))
        total_promotional_increment = data.aggregate(total_promotional_increment=Sum('promotional_increment_amount'))
   
        total_salary_increment_value = total_salary_increment['total_salary_increment'] or 0
        total_promotional_increment_value = total_promotional_increment['total_promotional_increment'] or 0
        total_increment_value = total_salary_increment_value + total_promotional_increment_value
  
        chart_data = {
            'labels': [ 'Total Increment','Promotional Increment', 'Salary Increment'],
            'values': [total_increment_value,total_promotional_increment_value, total_salary_increment_value]
        }

        chart_data2 = {
            'labels': ['Total employee', 'Total evaluated employee', 'Total promoted employee'],
            'values': [ total_employee,total_employee_evaluated,total_promoted_employee]
        }
    
    else:
        print("Form is not valid")
    
    paginator = Paginator(data, 10)  
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    if not page_obj:
        messages.info(request,'No data found within selected criteria')

    form = IncrementPromotionFinalDataForm() 
    return render(request, 'tasks/increment_promotion_final_data.html', {
        'page_obj': page_obj,       
        'form': form  ,
        'chart_data': json.dumps(chart_data),
        'chart_data2': json.dumps(chart_data2),
        'appraisal_year':appraisal_year,
        'appraisal_type':appraisal_type,
        'month':month,
        'quarter':quarter,
        'half_year':half_year,
        'total_employee': total_employee,
        'total_employee_evaluated': total_employee_evaluated,
        'total_promoted_employee':total_promoted_employee,
        'total_salary_increment_value':total_salary_increment_value,
        'total_promotional_increment_value': total_promotional_increment_value,
        'total_increment_value': total_increment_value
    })





def draw_text(pdf_canvas, x, y, text, font='Helvetica', size=10, color='black', line_spacing=15):
    pdf_canvas.setFont(font, size)
    pdf_canvas.setFillColor(color)
    pdf_canvas.drawString(x, y, text)
    return y - line_spacing 

def generate_increment_promotion_letter_pdf(employee):
    buffer = BytesIO()
    a4_size = A4
    pdf_canvas = canvas.Canvas(buffer, pagesize=a4_size)
    
    # Define gender-specific prefixes
    prefix = '' 
    prefix2 = ''
    if employee.gender == 'Male':
        prefix = 'Mr.'
        prefix2 = 'his'
    elif employee.gender == 'Female':
        prefix = 'Mrs.'
        prefix2 = 'her'
    
    # Logo and company information
    logo_path = 'D:/SCM/dscm/media/logo.png'
    pdf_canvas.drawImage(logo_path, 50, 750, width=60, height=60)  
    
    # Spacing and positioning
    y_space = 720
    spacing1 = 15
    
    # Draw company info
    company_info = [
        "mymeplus Technology Limited", 
        "House#39, Road#15, Block#F, Bashundhara R/A, Dhaka-1229", 
        "Phone:01842800705", 
        "email: hkobir@mymeplus.com", 
        "website: www.mymeplus.com"
    ]
    
    for info in company_info:
        y_space = draw_text(pdf_canvas, 50, y_space, info)
    
    # Current Date
    current_date = datetime.now().strftime("%Y-%m-%d")
    y_space = draw_text(pdf_canvas, 50, y_space-20, f"Date: {current_date}")
    
    # Appraisal letter
    y_space = draw_text(pdf_canvas, 50, y_space-20, f"Appraisal letter for {prefix} {employee.first_name} {employee.last_name}", size=12)
    y_space = draw_text(pdf_canvas, 50, y_space-20, f"Dear {prefix} {employee.last_name}", font="Helvetica-Bold", size=12)
    
    # Check promotion recommendation
    increment_data = employee.increment_employee.first()
    if increment_data and increment_data.promotion_recommendation == 'Yes':
        y_space = draw_text(pdf_canvas, 50, y_space-20, "Congratulations. You have been promoted", font="Helvetica-Bold", size=12, color='blue')
    
    y_space = draw_text(pdf_canvas, 50, y_space-10, f"", font="Helvetica-Bold", size=12)
    # Appraisal message
    appraisal_message = [
        "Management is pleased to inform you of your appraisal as a token of recognition for your outstanding performance,",
        "dedication, and the significant contributions you have made to the company.",
        "Your commitment to excellence, ability to overcome challenges, and consistent display of teamwork and innovation",
        "have made a lasting impact on our organization. We deeply value the energy and expertise you bring to your role,",
        "and we are excited to acknowledge your hard work through this appraisal."
    ]
    
    for msg in appraisal_message:
        y_space = draw_text(pdf_canvas, 50, y_space, msg)

    y_space = draw_text(pdf_canvas, 50, y_space-10, f"",  size=12)
    # Remuneration details
    y_space = draw_text(pdf_canvas, 50, y_space, "Your enhanced remuneration is as follows:", size=12)
    y_space = draw_text(pdf_canvas, 150, y_space, f"Basic Salary: {employee.salary_structure.basic_salary:,.2f}")
    y_space = draw_text(pdf_canvas, 150, y_space, f"House Allowance: {employee.salary_structure.hra:,.2f}")
    y_space = draw_text(pdf_canvas, 150, y_space, f"Medical Allowance: {employee.salary_structure.medical_allowance:,.2f}")
    y_space = draw_text(pdf_canvas, 150, y_space, f"Transportation Allowance: {employee.salary_structure.conveyance_allowance:,.2f}")
    y_space = draw_text(pdf_canvas, 150, y_space, f"Festival Bonus: {employee.salary_structure.performance_bonus:,.2f}")
    
    if increment_data:
        y_space = draw_text(pdf_canvas, 50, y_space-10, f"Your gross monthly remuneration amounts to {employee.salary_structure.gross_salary():,.2f} effective from {increment_data.effective_date}")
    
    y_space = draw_text(pdf_canvas, 50, y_space-10, "Wish you the best of luck.")
    
    # CFO signature details
    cfo_employee = Employee.objects.filter(position__name='CFO').first()
    if cfo_employee:
        pdf_canvas.drawString(50, 150, f"Authorized Signature________________")
        pdf_canvas.drawString(50, 135, f"Name:{cfo_employee.name}")
        pdf_canvas.drawString(50, 120, f"Designation:{cfo_employee.position}")
    else:
        pdf_canvas.drawString(50, 150, f"Authorized Signature________________")
        pdf_canvas.drawString(50, 135, f"Name:........")
        pdf_canvas.drawString(50, 120, f"Designation:.....")
    
    # Signature note
    pdf_canvas.setFont("Helvetica-Bold", 10)
    pdf_canvas.setFillColor('green')
    pdf_canvas.drawString(50, 80, "Signature is not mandatory due to computerized authorization")
    
    pdf_canvas.showPage()
    pdf_canvas.save()

    buffer.seek(0)
    return buffer


       

@login_required
def preview_increment_promotion(request, employee_id): 
    employee_instance = Employee.objects.filter(id=employee_id).first()
    if not employee_instance:
        messages.info(request, "No employee found. Please try again.")
        return HttpResponseRedirect(reverse('tasks:generate_increment_promotion_letter'))  # Redirect to form  

    form = GenerateIncrementPromotionPdfForm(request.POST or None)
    pdf_base64 = None  # Ensure no PDF is loaded on initial page load

    if request.method == "POST":
        if form.is_valid():
            appraisal_category = form.cleaned_data.get('appraisal_category')
            appraisal_type = form.cleaned_data.get('appraisal_type')
            appraisal_year = form.cleaned_data.get('appraisal_year')
            employee_name = form.cleaned_data.get('employee_name')
            month = form.cleaned_data.get('month')
            quarter = form.cleaned_data.get('quarter')
            half_year = form.cleaned_data.get('half_year')

            filter_criteria = {
                'appraisal_category': appraisal_category,
                'appraisal_type': appraisal_type,
                'appraisal_year': appraisal_year,
                'appraisal_year': appraisal_year,
            }

            if appraisal_type == 'MONTHLY' and month:
                filter_criteria['month'] = month
            elif appraisal_type == 'QUARTERLY' and quarter:
                filter_criteria['quarter'] = quarter
            elif appraisal_type == 'HALF-YEARLY' and half_year:
                filter_criteria['half_year'] = half_year
                
            filtered_data = SalaryIncrementAndPromotion.objects.filter(**filter_criteria)
            
            if filtered_data.exists():            
                pdf_buffer = generate_increment_promotion_letter_pdf(employee_instance)
                pdf_base64 = base64.b64encode(pdf_buffer.getvalue()).decode('utf-8')
            else:
                messages.info(request, "No matching data found. Please adjust the filters.")

    return render(request, "core/preview_increment_promotion.html", {
        "employee": employee_instance,
        "pdf_preview": pdf_base64,  
        "form": form
    })

from.forms import GenerateIncrementPromotionGeneralPdfForm

@login_required
def preview_increment_promotion_general(request): 
    employee_instance = None
    form = GenerateIncrementPromotionGeneralPdfForm(request.POST or None)
    pdf_base64 = None  

    if request.method == "POST":
        if form.is_valid():
            appraisal_category = form.cleaned_data.get('appraisal_category')
            appraisal_type = form.cleaned_data.get('appraisal_type')
            appraisal_year = form.cleaned_data.get('appraisal_year')
            employee_name = form.cleaned_data.get('employee_name')
            month = form.cleaned_data.get('month')
            quarter = form.cleaned_data.get('quarter')
            half_year = form.cleaned_data.get('half_year')

            employee_instance = Employee.objects.filter(name__icontains=employee_name).first()
            if not employee_instance:
                messages.info(request, "No employee found. Please try again.")
                return HttpResponseRedirect(reverse('tasks:generate_increment_promotion_letter'))  # Redirect to form  


            filter_criteria = {
                'appraisal_category': appraisal_category,
                'appraisal_type': appraisal_type,
                'appraisal_year': appraisal_year,
                'appraisal_year': appraisal_year,
            }

            if appraisal_type == 'MONTHLY' and month:
                filter_criteria['month'] = month
            elif appraisal_type == 'QUARTERLY' and quarter:
                filter_criteria['quarter'] = quarter
            elif appraisal_type == 'HALF-YEARLY' and half_year:
                filter_criteria['half_year'] = half_year
                
            filtered_data = SalaryIncrementAndPromotion.objects.filter(**filter_criteria)
            
            if filtered_data.exists():            
                pdf_buffer = generate_increment_promotion_letter_pdf(employee_instance)
                pdf_base64 = base64.b64encode(pdf_buffer.getvalue()).decode('utf-8')
            else:
                messages.info(request, "No matching data found. Please adjust the filters.")

    return render(request, "core/preview_increment_promotion.html", {
        "employee": employee_instance,
        "pdf_preview": pdf_base64,  
        "form": form
    })




def send_increment_promotion(employee):      
    if not employee.email:
        return f"Employee email not found for {employee.name}."

    pdf_buffer = generate_increment_promotion_letter_pdf(employee)   
    message = f'Dear {employee.name}, your requested salary certificate is attached herewith.'
    
    try:
        email = EmailMessage(
            subject="Offer Letter from Our Company",
            body=message,
            from_email="yourcompany@example.com",
            to=[employee.email]
        )
        email.attach(f"Pay slip_{employee.id}.pdf", pdf_buffer.getvalue(), 'application/pdf')
        email.content_subtype = "html"
        email.send()        
      
        return f"Offer letter sent to {employee.name} successfully!"
    except Exception as e:
        return f"Error sending offer letter to {employee.name}: {str(e)}"


@login_required
def generate_and_send_increment_promotion_single(request, employee_id): 
    employee = get_object_or_404(Employee,id=employee_id)
    message = send_increment_promotion(employee)
    if "Error" in message:
        messages.error(request, message)
    else:
        messages.success(request, message)

    return redirect('core:employee_list')




@login_required
def generate_and_send_appraisal_letter_to_all_eligible(request):
    form = GenerateIncrementPromotionPdfForm(request.POST or None)
    if request.method == "POST":
        if form.is_valid():
            appraisal_category = form.cleaned_data.get('appraisal_category')
            appraisal_type = form.cleaned_data.get('appraisal_type')
            appraisal_year = form.cleaned_data.get('appraisal_year')
            month = form.cleaned_data.get('month')
            quarter = form.cleaned_data.get('quarter')
            half_year = form.cleaned_data.get('half_year')

            filter_criteria = {
                'appraisal_category': appraisal_category,
                'appraisal_type': appraisal_type,
                'appraisal_year': appraisal_year,
            }

            if appraisal_type == 'MONTHLY' and month:
                filter_criteria['month'] = month
            elif appraisal_type == 'QUARTERLY' and quarter:
                filter_criteria['quarter'] = quarter
            elif appraisal_type == 'HALF-YEARLY' and half_year:
                filter_criteria['half_year'] = half_year
                
            employees = Employee.objects.filter(
                id__in=SalaryIncrementAndPromotion.objects.filter(**filter_criteria)
                .values_list('employee_id', flat=True)
            ).distinct()

            if not employees.exists():
                messages.info(request, "No eligible employees found.")
                return redirect('core:employee_list')  
         
            for employee in employees:
                message = send_increment_promotion(employee)
                if "Error" in message:
                    messages.error(request, message)
                else:
                    messages.success(request, message)
            messages.info(request, 'Offer letters sent successfully.')
            return redirect('core:employee_list')  

    return render(request, "core/preview_increment_promotion_all.html", {
        "form": form
    })
