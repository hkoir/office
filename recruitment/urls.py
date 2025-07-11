
from django.urls import path
from .import views


app_name = 'recruitment'





urlpatterns = [

    path('recruitment_dashboard/', views.recruitment_dashboard, name='recruitment_dashboard'),
    
    path('create_job/', views.manage_job, name='create_job'),
    path('update_job/<int:id>/', views.manage_job, name='update_job'),
    path('delete_job/<int:id>/', views.delete_job, name='delete_job'),
   
    path('job_request_list/', views.job_request_list, name='job_request_list'),   
    path('process_job_requirement/<int:id>/', views.process_job_requirement, name='process_job_requirement'),
    path('launch_job_by_hiring_manager/<int:id>/', views.launch_job_by_hiring_manager, name='launch_job_by_hiring_manager'),

    path('create_project/', views.manage_project, name='create_project'),
    path('update_project/<int:id>/', views.manage_project, name='update_project'),
    path('delete_project/<int:id>/', views.delete_project, name='delete_project'),


    path('create_score_card/', views.manage_score_card, name='create_score_card'),
    path('update_score_card/<int:id>/', views.manage_score_card, name='update_score_card'),
    path('delete_score_card/<int:id>/', views.delete_score_card, name='delete_score_card'),
    path('score_card_detail/<int:id>/', views.score_card_detail, name='score_card_detail'),

    path('create_experience/', views.manage_experience, name='create_experience'),
    path('update_experience/<int:id>/', views.manage_experience, name='update_experience'),
    path('delete_experience/<int:id>/', views.delete_experience, name='delete_experience'),

    path('create_language/', views.manage_language, name='create_language'),
    path('update_language/<int:id>/', views.manage_language, name='update_language'),
    path('delete_language/<int:id>/', views.delete_language, name='delete_language'),

    path('create_language_skill/', views.manage_language_skill, name='create_language_skill'),
    path('update_language_skill/<int:id>/', views.manage_language_skill, name='update_language_skill'),
    path('delete_language_skill/<int:id>/', views.delete_language_skill, name='delete_language_skill'),

    path('create_education/', views.manage_education, name='create_education'),
    path('update_education/<int:id>/', views.manage_education, name='update_education'),
    path('delete_education/<int:id>/', views.delete_education, name='delete_education'),
    
    path('create_edu_institution/', views.manage_edu_institution, name='create_edu_institution'),
    path('update_edu_institution/<int:id>/', views.manage_edu_institution, name='update_edu_institution'),
    path('delete_edu_institution/<int:id>/', views.delete_edu_institution, name='delete_edu_institution'),

    path('create_edu_subject/', views.manage_edu_subject, name='create_edu_subject'),
    path('update_edu_subject/<int:id>/', views.manage_edu_subject, name='update_edu_subject'),
    path('delete_edu_subject/<int:id>/', views.delete_edu_subject, name='delete_edu_subject'),

    path('create_certification/', views.manage_certification, name='create_certification'),
    path('update_certification/<int:id>/', views.manage_certification, name='update_certification'),
    path('delete_certification/<int:id>/', views.delete_certificationt, name='delete_certification'),

    path('create_age/', views.manage_age, name='create_age'),
    path('update_age/<int:id>/', views.manage_age, name='update_age'),
    path('delete_age/<int:id>/', views.delete_age, name='delete_age'),

    path('create_skill/', views.manage_skills, name='create_skill'),
    path('updateskille/<int:id>/', views.manage_skills, name='update_skill'),
    path('delete_skill/<int:id>/', views.delete_skills, name='delete_skill'),

    path('create_job_category/', views.manage_job_category, name='create_job_category'),
    path('update_job_category/<int:id>/', views.manage_job_category, name='update_job_category'),
    path('delete_job_category/<int:id>/', views.delete_job_category, name='delete_job_category'),

  
    path('job_list/', views.job_list, name='job_list'),
    path('job_list_candidate_view/', views.job_list_candidate_view, name='job_list_candidate_view'),
    path('job_list_interview_panel_view/', views.job_list_interview_panel_view, name='job_list_interview_panel_view'),

    path('cv_screening/', views.cv_screening, name='cv_screening'),
    path('get_exams/<int:job_id>/', views.get_exams_for_job, name='get_exams_for_job'),
   
    path('job_application/<int:id>/', views.job_application, name='job_application'),
    path('applicant_list/<int:job_id>/', views.applicant_list, name='applicant_list'),
    
    path('create_exam', views.manage_exam, name='create_exam'),
    path('update_exam/<int:id>/', views.manage_exam, name='update_exam'),
    path('delete_exam/<int:id>/', views.delete_exam, name='delete_exam'),
    path('exam_details/<int:exam_id>/', views.exam_details, name='exam_details'),
    path('job_exam_list/<int:job_id>/', views.job_exam_list, name='job_exam_list'),
    path('exam_list/', views.exam_list, name='exam_list'),

    path('create_questions/', views.manage_questions, name='create_questions'),
    path('update_question/<int:id>/', views.manage_questions, name='update_question'),
    path('delete_question/<int:id>/', views.delete_question, name='delete_question'),
    path('question_paper/<int:exam_id>/', views.question_paper, name='question_paper'),

    path('pre_exams/<int:exam_id>/take/<int:candidate_id>/', views.pre_take_exam, name='pre_take_exam'),
    path('exams/<int:exam_id>/take/<int:candidate_id>/', views.take_exam, name='take_exam'),
    path('result/<int:exam_id>/<int:candidate_id>/', views.result, name='result'),
    path('exam_screening/', views.exam_screening, name='exam_screening'),

    path('search_applications/', views.search_applications, name='search_applications'),

     path('create_panel/', views.manage_panel, name='create_panel'),
     path('update_panel/<int:id>/', views.manage_panel, name='update_panel'),
     path('delete_panel/<int:id>/', views.delete_panel, name='delete_panel'),

     path('create_panel_member/', views.manage_panel_member, name='create_panel_member'),
     path('update_panel_member/<int:id>/', views.manage_panel_member, name='update_panel_member'),
     path('delete_panel_member/<int:id>/', views.delete_panel_member, name='delete_panel_member'),
     
     path('create_interview/', views.manage_interview, name='create_interview'),
     path('update_interview/<int:id>/', views.manage_interview, name='update_interview'),
     path('delete_interview/<int:id>/', views.delete_interview, name='delete_interview'),
     

     path('panel_details/<int:id>/', views.panel_details, name='panel_details'),  
    path('job/<int:job_id>/exam/<int:exam_id>/candidate/<int:candidate_id>/panel_member/<int:panel_member_id>/score/',views.panel_member_scoring, name='panel_member_scoring'),
    path('interview_scores/<int:candidate_id>/', views.candidate_interview_scores, name='candidate_interview_scores'),
    
    path('interview_screening/', views.interview_screening, name='interview_screening'),
    path('selected_candidate/', views.selected_candidate, name='selected_candidate'),
    path('selected_candidate_with_id/<int:job_id>/', views.selected_candidates_with_id, name='selected_candidate_with_id'),
    path('all_job_candidate_status/', views.all_job_candidate_status, name='all_job_candidate_status'),
    path('grand_summary/', views.grand_summary, name='grand_summary'),
     
    path('candidate/<int:id>/', views.candidate_details, name='candidate_details'),
    path('preview-offer-letter/<int:candidate_id>/', views.preview_offer_letter, name='preview_offer_letter'),
    path('send-offer-letter/<int:candidate_id>/', views.generate_and_send_offer_letter, name='send_offer_letter'),
    path('send-offer-letter-to-all-selected-candidates/', views.send_offer_letters_to_top_scorers, name='send_offer_letters_to_selected_candidates'),
    path('handle_declines_and_offer_next_candidates/', views.handle_declines_and_offer_next_candidates, name='handle_declines_and_offer_next_candidates'),
    path('handle_onboard_declines_and_offer_next_candidates/', views.handle_onboard_declines_and_offer_next_candidates, name='handle_onboard_declines_and_offer_next_candidates'),

    path('candidate_confirmation/<int:candidate_id>/', views.candidate_confirmation, name='candidate_confirmation'),
    path("congratulations/<int:candidate_id>/", views.congratulations, name="congratulations"),
   
    path('hiring_manager_onboarding_approval/<int:candidate_id>/', views.hiring_manager_confirm_onboarding, name='hiring_manager_onboarding_approval'),
    path('candidate_joining/<int:candidate_id>/', views.candidate_joining, name='candidate_joining'),


    path('create_common_documents/', views.manage_common_documents, name='create_common_documents'),
    path('update_common_documents/<int:id>/', views.manage_common_documents, name='update_common_documents'),
    path('delete_common_documents/<int:id>/', views.delete_common_documents, name='delete_common_document'),

    path('create_candidate_documents/', views.manage_candidate_documents, name='create_candidate_documents'),
    path('update_candidate_documents/<int:id>/', views.manage_candidate_documents, name='update_candidate_documents'),
    path('delete_candidate_documents/<int:id>/', views.delete_candidate_documents, name='delete_candidate_document'),


    
     path('create_question_paper/', views.manage_bq_question_paper, name='create_question_paper'),
     path('update_question_paper/<int:id>/', views.manage_bq_question_paper, name='update_question_paper'),
     path('delete_question_paper/<int:id>/', views.delete_bq_question_paper, name='delete_question_paper'),
     
     
     path('create_bq_question/', views.manage_bq_question, name='create_bq_question'),
     path('update_bq_question/<int:id>/', views.manage_bq_question, name='update_bq_question'),
     path('delete_bq_question/<int:id>/', views.delete_bq_question, name='delete_bq_question'),

      path('bq_question_paper_list/', views.bq_question_paper_list, name='bq_question_paper_list'),

    #  path('take_bq_exam/<int:paper_id>/<int:candidate_id>/', views.take_bq_exam, name='take_bq_exam'),

     

]


  
