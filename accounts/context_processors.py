
from .models import UserProfile
from tasks.models import TaskMessage


def user_info(request):

    profile_picture_url = None
    
    if request.user.is_authenticated:
        user_profile = UserProfile.objects.filter(user=request.user).first()  # Get the UserProfile for the logged-in user
        if user_profile and user_profile.profile_picture:  
            profile_picture_url = user_profile.profile_picture.url
            
    return {
        'user_info': request.user.username if request.user.is_authenticated else None,  # Adjust to show username or desired field
        'profile_picture_url': profile_picture_url
    }



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
