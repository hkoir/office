from django.contrib import admin
from .models import Job, Candidate,Question,TakeExam,Exam,Experience,CandidateScreeningHistory

from.models import PanelMember,Interview,InterviewScore,ExamScreeningHistory,InterviewScreeningHistory

from.models import CandidateDocument,Panel,PanelMember,BQQuestionPaper,BQQuestion,BQCandidateAnswer


@admin.register(Job)
class JobAdmin(admin.ModelAdmin):
    list_display = ['title', 'location', 'deadline']

@admin.register(Candidate)
class CandidateAdmin(admin.ModelAdmin):
    list_display = ['full_name', 'applied_job', 'email', 'status', 'applied_at']
    list_filter = ['applied_job', 'status']

admin.site.register(Question)
admin.site.register(TakeExam)
admin.site.register(Exam)
admin.site.register(CandidateScreeningHistory)
admin.site.register(ExamScreeningHistory)
admin.site.register(InterviewScreeningHistory)

admin.site.register(InterviewScore)
admin.site.register(Interview)
admin.site.register(Panel)
admin.site.register(PanelMember)

admin.site.register(BQQuestionPaper)
admin.site.register(BQQuestion)
admin.site.register(BQCandidateAnswer)


admin.site.register(CandidateDocument)

class ExperienceAdmin(admin.ModelAdmin):
    list_display = ['user', 'score_card', 'year_of_experience', 'score']
    search_fields = ['user__username', 'area_of_experience']

admin.site.register(Experience, ExperienceAdmin)

