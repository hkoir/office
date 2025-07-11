
from django.urls import path
from .import views


app_name = 'tasks'



urlpatterns = [
    
  path('', views.tasks_dashboard, name='tasks_dashboard'),
  path('chat/<str:task_id>/', views.chat, name='chat'), 
  
  path('update-task-progress/<int:task_id>/update/', views.update_task_progress, name='update_task_progress'),
  path('request-extension/<int:task_id>/', views.request_extension, name='request_extension'),
  path('approve-extension/<int:task_id>/', views.approve_extension, name='approve_extension'),
  path('tasks_list/', views.tasks_list, name='tasks_list'),
  path('performance_evaluation_view/', views.performance_evaluation_view, name='performance_evaluation_view'),

  path('create-team/', views.create_team, name='create_team'),  # URL to create a team
  path('delete-team/<int:team_id>/', views.delete_team, name='delete_team'),
  path('add-member/', views.add_member, name='add_member'),  # URL to add a member to a team
  path('add-member-with-id/<int:team_id>/', views.add_member_with_id, name='add_member_with_id'),  # URL to add a member to a team
  path('view-member-with-id/<int:task_id>/', views.view_team_members, name='view_team_members'),  # URL to add a member to a team
  path('delete-member/<int:team_id>/', views.delete_member, name='delete_member'),
  path('create-task/', views.create_task, name='create_task'), 
  path('assigned_task/<int:task_id>/', views.assigned_task, name='assigned_task'), 
  path('delete-task/', views.delete_task, name='delete_task'),  
  path('task_details/<int:task_id>/', views.task_details, name='task_details'),

  path('qualitative-evaluation/<int:task_id>/', views.create_qualitative_evaluation, name='qualitative_evaluation'),

 path('team_performance_chart/', views.team_performance_chart, name='team_performance_chart'), 
 path('employee_performance_chart/', views.employee_performance_chart, name='employee_performance_chart'),
 path('aggregated_report_sheet/', views.aggregated_report_sheet, name='aggregated_report_sheet'),
 path('year_month_performance_chart/', views.year_month_performance_chart, name='year_month_performance_chart'),
 path('year_quarter_performance_chart/', views.year_quarter_performance_chart, name='year_quarter_performance_chart'),
 path('yearly_performance_trend/', views.yearly_performance_trend, name='yearly_performance_trend'),
 path('group_performance_chart/', views.group_performance_chart, name='group_performance_chart'),


 path('increment_promotion_check/', views.increment_promotion_check, name='increment_promotion_check'),
 path('increment_promotion/', views.increment_promotion, name='increment_promotion'),
 path('increment_promotion_final_data/', views.increment_promotion_final_data, name='increment_promotion_final_data'),


 path('preview_increment_promotion/<int:employee_id>/', views.preview_increment_promotion, name='preview_increment_promotion'),
 path('preview_increment_promotion_general/', views.preview_increment_promotion_general, name='preview_increment_promotion_general'),
  path('generate_and_send_increment_promotion_single/<int:employee_id>/', views.generate_and_send_increment_promotion_single, name='generate_and_send_increment_promotion_single'),
 path('generate_and_send_appraisal_letter_to_all_eligible/', views.generate_and_send_appraisal_letter_to_all_eligible, name='generate_and_send_appraisal_letter_to_all_eligible'),




]
