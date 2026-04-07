
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






from product.models import Product
from purchase.models import Batch
import json
from django.core.serializers.json import DjangoJSONEncoder

def dropdown_mappings(request):
    products = Product.objects.select_related('category').all()
    category_product_map = {}
    for p in products:
        category_product_map.setdefault(p.category_id, []).append({
            'id': p.id,
            'name': p.name
        })

    # Product -> Batches
    batches = Batch.objects.select_related('product').all()
    product_batch_map = {}
    for b in batches:
        product_batch_map.setdefault(b.product_id, []).append({
            'id': b.id,
            'batch_number': b.batch_number,
            'remaining_quantity': b.remaining_quantity or 0
        })

    return {
        'category_product_map_json': json.dumps(category_product_map, cls=DjangoJSONEncoder),
        'product_batch_map_json': json.dumps(product_batch_map, cls=DjangoJSONEncoder)
    }





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
