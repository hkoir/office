from django.contrib import admin

from.models import Task,TeamMember, Team,PerformanceEvaluation,QualitativeEvaluation,TimeExtensionRequest,Ticket
from.models import TaskMessage
admin.site.register(Task)
admin.site.register(Team)
admin.site.register(TeamMember)
admin.site.register(PerformanceEvaluation)
admin.site.register(QualitativeEvaluation)
admin.site.register(TimeExtensionRequest)
admin.site.register(TaskMessage)
admin.site.register(Ticket)

