
from tasks.models import TaskMessage

from reporting.models import Notification

def notifications_context(request):
    notifications = []
    unread_notifications = []
    if request.user.is_authenticated: 
        notifications = Notification.objects.filter(user=request.user).order_by('-created_at')
        unread_notifications = Notification.objects.filter(user=request.user, is_read=False).order_by('-created_at')
    else:
        notifications = []
    return {'notifications': notifications,'unread_notifications':unread_notifications}



def tenant_schema(request):
    schema_name = getattr(request.tenant, 'schema_name', 'public')
    return {'schema_name': schema_name}



# def unread_messages(request):
#     unread_msgs_by_task = {}
#     if request.user.is_authenticated:
#         unread_msgs = TaskMessage.objects.filter(sender=request.user, read=False)
#         for message in unread_msgs:
#             unread_msgs_by_task[message.task_id] = True

#     return {'unread_messages': unread_msgs_by_task}



from django_tenants.utils import get_public_schema_name
from django.db import connection

def unread_messages(request):
    unread_msgs_by_task = {}
    unread_msgs={}

    if request.user.is_authenticated:
        if connection.schema_name == get_public_schema_name():
            unread_msgs_by_task = {}
        else:
             unread_msgs = TaskMessage.objects.filter(sender=request.user, read=False)

        for message in unread_msgs:
            if message.task_id not in unread_msgs_by_task:
                unread_msgs_by_task[message.task_id] = True

    return {'unread_messages': unread_msgs_by_task}
