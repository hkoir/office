from django.shortcuts import render,redirect,get_object_or_404
from django.contrib import messages
from django.utils import timezone
from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.db import transaction
import json
from datetime import timedelta,datetime
from django.utils.timezone import now
from django.db.models.functions import ExtractHour
from django.db.models import Sum, DecimalField, F,Count

from core.models import Department,Employee
from purchase.forms import PurchaseStatusForm
from inventory.models import Warehouse,Location
from supplier.models import Supplier

from.models import StationaryPurchaseOrder,StationaryPurchaseItem,StationaryInventory,StationaryInventoryTransaction
from.models import StationaryBatch,StationaryCategory,StationaryProduct, StationaryUsageRequestOrder,StationaryUsageRequestItem
from.models import OfficeAdvance,ExpenseSubmissionItem,ExpenseSubmissionOrder
from.models import MeetingOrder,MeetingRoom,MeetingRoomBooking,Attendees,ITSupportTicket
from.models import VisitorGroup,VisitorLog,OfficeDocument


from.forms import ExpenseSubmissionOrderForm,ExpenseSubmissionItemForm,ExpenseAdvanceForm,ExpenseAdvanceApprovalForm
from.forms import AddCategoryForm,AddProductForm,BatchForm,ExpenseSubmissionOrderUpdateForm
from.forms import StationaryPurchaseOrderForm,StationaryUsageOrderForm,OfficeDocumentForm
from.forms import PurchaseRequestInvoiceAddForm,WarehouseSelectionForm,MeetingOrderForm,MeetingRoomBookingForm,MeetingRoomForm
from.forms import AddAttendeeForm,ITSupportForm,ITSupportUpdateForm,VisitorGroupForm,VisitorLogForm



def office_supplies_stationary(request):
    return render(request,'officemanagement/dashboard/office_supplies_stationary.html')
def office_expense_advance(request):
    return render(request,'officemanagement/dashboard/office_expense_advance.html')
def office_meeting_room_booking(request):
    return render(request,'officemanagement/dashboard/office_meeting_room_booking.html')
def office_it_support_ticket(request):
    return render(request,'officemanagement/dashboard/office_it_support.html')
def office_visitor_management(request):
    return render(request,'officemanagement/dashboard/office_visitor_management.html')
def office_documentations(request):
    return render(request,'officemanagement/dashboard/office_documentations.html')



@login_required
def manage_category(request, id=None):  
    instance = get_object_or_404(StationaryCategory, id=id) if id else None
    message_text = "updated successfully!" if id else "added successfully!"  
    form = AddCategoryForm(request.POST or None, request.FILES or None, instance=instance)

    if request.method == 'POST' and form.is_valid():
        form_intance=form.save(commit=False)
        form_intance.user = request.user
        form_intance.save()        
        messages.success(request, message_text)
        return redirect('officemanagement:create_category')

    datas = StationaryCategory.objects.all().order_by('-created_at')
    paginator = Paginator(datas, 5)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    return render(request, 'officemanagement/purchase/manage_category.html', {
        'form': form,
        'instance': instance,
        'datas': datas,
        'page_obj': page_obj
    })



@login_required
def delete_category(request, id):
    instance = get_object_or_404(StationaryCategory, id=id)
    if request.method == 'POST':
        instance.delete()
        messages.success(request, "Deleted successfully!")
        return redirect('officemanagement:create_category')

    messages.warning(request, "Invalid delete request!")
    return redirect('officemanagement:create_category')


@login_required
def manage_product(request, id=None):  
    instance = get_object_or_404(StationaryProduct, id=id) if id else None
    message_text = "updated successfully!" if id else "added successfully!"  
    form = AddProductForm(request.POST or None, request.FILES or None, instance=instance)

    if request.method == 'POST' and form.is_valid():
        form_intance=form.save(commit=False)
        form_intance.user = request.user
        form_intance.save()        
        messages.success(request, message_text)
        return redirect('officemanagement:create_product') 

    datas =StationaryProduct.objects.all().order_by('-created_at')
    paginator = Paginator(datas, 5)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    return render(request, 'officemanagement/purchase/manage_product.html', {
        'form': form,
        'instance': instance,
        'datas': datas,
        'page_obj': page_obj
    })



@login_required
def delete_product(request, id):
    instance = get_object_or_404(StationaryProduct, id=id)
    if request.method == 'POST':
        instance.delete()
        messages.success(request, "Deleted successfully!")
        return redirect('officemanagement:create_product')

    messages.warning(request, "Invalid delete request!")
    return redirect('officemanagement:create_product')



@login_required
def manage_batch(request, id=None):  
    instance = get_object_or_404(StationaryBatch, id=id) if id else None
    message_text = "updated successfully!" if id else "added successfully!"  
    form = BatchForm(request.POST or None, request.FILES or None, instance=instance)

    if request.method == 'POST' and form.is_valid():
        form_intance=form.save(commit=False)
        form_intance.user = request.user
        form_intance.save()        
        messages.success(request, message_text)
        return redirect('officemanagement:create_batch')  

    datas = StationaryBatch.objects.all().order_by('-created_at')
    paginator = Paginator(datas, 5)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    return render(request, 'officemanagement/purchase/manage_batch.html', {
        'form': form,
        'instance': instance,
        'datas': datas,
        'page_obj': page_obj
    })



@login_required
def delete_batch(request, id):
    instance = get_object_or_404(StationaryBatch, id=id)
    if request.method == 'POST':
        instance.delete()
        messages.success(request, "Deleted successfully!")
        return redirect('officemanagement:create_batch')      

    messages.warning(request, "Invalid delete request!")
    return redirect('officemanagement:create_batch') 



@login_required
def create_purchase_request(request):
    if 'basket' not in request.session:
        request.session['basket'] = []
    form = StationaryPurchaseOrderForm(request.POST or None,request.FILES or None)
   
    if request.method == 'POST':
        if 'add_to_basket' in request.POST:
            if form.is_valid():

                category = form.cleaned_data['stationary_category']
                product_obj = form.cleaned_data['stationary_product']
                quantity = form.cleaned_data['quantity']
                batch = form.cleaned_data['batch']
                supplier = form.cleaned_data['supplier']
             
                basket = request.session.get('basket', [])
                product_in_basket = next((item for item in basket if item['id'] == product_obj.id), None)
                

                if product_in_basket:
                    product_in_basket['quantity'] += quantity
                else:
                    basket.append({
                        'id': product_obj.id,
                        'name': product_obj.name,   
                        'category_id': category.id,                   
                        'category': category.name,                      
                        'batch_id':batch.id,
                        'batch':batch.batch_number,
                        'quantity': quantity,                    
                        'supplier_id':supplier.id,
                        'supplier':supplier.name,
                        'unit_price':float(batch.unit_price),
                       
                    })

                request.session['basket'] = basket
                request.session.modified = True
                messages.success(request, f"Added '{product_obj.name}' to the purchase basket")
                return redirect('officemanagement:create_purchase_request')
            else:
                messages.error(request, "Form is invalid. Please check the details and try again.")

        elif 'action' in request.POST:
            action = request.POST['action']
            product_id = int(request.POST.get('product_id', 0))

            if action == 'update':
                new_quantity = int(request.POST.get('quantity', 1))
                for item in request.session['basket']:
                    if item['id'] == product_id:
                        item['quantity'] = new_quantity  

            elif action == 'delete':
                request.session['basket'] = [
                    item for item in request.session['basket'] if item['id'] != product_id
                ]  

            request.session.modified = True
            messages.success(request, "Purchase basket updated successfully.")
            return redirect('officemanagement:create_purchase_request')

        elif 'confirm_purchase' in request.POST:
            basket = request.session.get('basket', [])
            if not basket:
                messages.error(request, "Purchase basket is empty. Add products before confirming the purchase.")
                return redirect('officemanagement:create_purchase_request')
            return redirect('officemanagement:confirm_purchase_request')  

    basket = request.session.get('basket', [])
    return render(request, 'officemanagement/purchase/create_purchase_request.html', {'form': form, 'basket': basket})



@login_required
def confirm_purchase_request(request):
    basket = request.session.get('basket', [])
    if not basket:
        messages.error(request, "Purchase basket is empty. Cannot confirm purchase.")
        return redirect('officemanagement:create_purchase_request')

    if request.method == 'POST':
        try:
            with transaction.atomic(): 
                total_amount = sum(item['quantity'] * item['unit_price'] for item in basket)
                supplier_id = basket[0]['supplier_id'] if basket else None                 

                supplier = get_object_or_404(Supplier, id=supplier_id)
                stationary_purchase_order = StationaryPurchaseOrder(
                    total_amount=total_amount,
                    supplier=supplier,                   
                    approval_status='SUBMITTED',  
                    user=request.user  
                )
                stationary_purchase_order.save()  
               
                for item in basket:
                    product = get_object_or_404(StationaryProduct, id=item['id'])
                    quantity = item['quantity']
                    category = get_object_or_404(StationaryCategory, id=item['category_id'])
                    batch = get_object_or_404(StationaryBatch, id=item['batch_id'])                   
                    batch.remaining_quantity += quantity  
                    batch.save()  #

                    purchase_request_item = StationaryPurchaseItem(
                        stationary_purchase_order=stationary_purchase_order,
                        stationary_product=product,
                        quantity=quantity,
                        stationary_category = category,
                        batch = batch,
                        user=request.user  
                    )
                    purchase_request_item.save()

                request.session['basket'] = []
                request.session.modified = True
                messages.success(request, "Purchase order created successfully!")
                return redirect('officemanagement:create_purchase_request')

        except Exception as e:            
            messages.error(request, f"An error occurred while creating the purchase order: {str(e)}")
            return redirect('officemanagement:create_purchase_request')
    return render(request, 'officemanagement/purchase/confirm_purchase_request.html', {'basket': basket})






@login_required
def purchase_request_list(request):    
  
    if request.method == 'GET':
        end_date = request.GET.get('end_date')
        start_date = request.GET.get('start_date')
        order_id = request.GET.get('order_id')

        purchase_request_orders = StationaryPurchaseOrder.objects.all().order_by('-created_at')
        
        if not start_date or not end_date: 
            end_date = datetime.today().date()
            start_date = end_date - timedelta(days=7)
            purchase_request_orders = purchase_request_orders.filter(created_at__range=[start_date,end_date])
        else:             
            start_date = datetime.strptime(start_date, "%Y-%m-%d").date()
            end_date = datetime.strptime(end_date, "%Y-%m-%d").date()
            purchase_request_orders.filter(created_at__range=[start_date,end_date])

        if order_id:
            purchase_request_orders =purchase_request_orders.filter(order_id = order_id)            
             
    paginator = Paginator(purchase_request_orders, 10)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    return render(request, 'officemanagement/purchase/purchase_request_list.html', {
        'purchase_request_orders': purchase_request_orders,           
        'user': request.user, 
        'page_obj': page_obj,
        'request_order': purchase_request_orders,
      
    })



@login_required
def process_purchase_request(request, order_id):
    order = get_object_or_404(StationaryPurchaseOrder, id=order_id)

    role_status_map = {
        "Requester": ["SUBMITTED", "CANCELLED"],
        "Reviewer": ["REVIEWED", "CANCELLED"],
        "Approver": ["APPROVED", "CANCELLED"],
    }

    if request.method == 'POST':
        form = PurchaseStatusForm(request.POST)
        if form.is_valid():
            if order.approval_data is None:
                order.approval_data = {}

            approval_status = form.cleaned_data['approval_status']
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
                if approval_status in role_status_map[user_role]:
                    role = user_role
                    break

            if not role:
                messages.error(
                    request,
                    "You do not have permission to perform this action or invalid status."
                )
                return redirect('officemanagement:purchase_request_list')

            if role == "Requester":
                order.requester_approval_status = approval_status
                order.Requester_remarks = remarks
            elif role == "Reviewer":
                order.reviewer_approval_status = approval_status
                order.Reviewer_remarks = remarks
            elif role == "Approver":
                order.approver_approval_status = approval_status
                order.Approver_remarks = remarks

            order.approval_data[role] = {
                'status': approval_status,
                'remarks': remarks,
                'date': timezone.now().isoformat(),
            }

            order.save()
            messages.success(request, f"Order {order.id} successfully updated.")
            return redirect('officemanagement:purchase_request_list')
        else:
            messages.error(request, "Invalid form submission.")
    else:
        form = PurchaseStatusForm()
    return render(request, 'officemanagement/purchase/purchase_request_approval_form.html', {'form': form, 'order': order})



def purchase_confirmation_and_warehouse_entry(request, order_id):
    purchase_request_order = get_object_or_404(StationaryPurchaseOrder, id=order_id)   
    purchase_request_items = purchase_request_order.stationary_request_order.all()
  
    warehouses = Warehouse.objects.all()
    locations = Location.objects.all()

    if request.method == "POST":
        try:
            with transaction.atomic():
                for index, item in enumerate(purchase_request_items, start=1):                   
                    warehouse_id = request.POST.get(f"warehouse_{index}")
                    location_id = request.POST.get(f"location_{index}")
                 
                    batch = item.batch
                    product = item.batch.stationary_product
                    purchase_quantity = int(item.quantity)
               
                    warehouse = Warehouse.objects.get(id=warehouse_id)
                    location = Location.objects.get(id=location_id)

                    inventory, created = StationaryInventory.objects.get_or_create(
                        stationary_product=product,
                        warehouse=warehouse,
                        location=location,
                        batch=batch,
                        defaults={"quantity": 0, "batch": batch}
                    )
                 
                    inventory.quantity += purchase_quantity
                    inventory.save()
             
                    StationaryInventoryTransaction.objects.create(
                        stationary_product=product,
                        warehouse=warehouse,
                        location=location,
                        transaction_type="inbound",  
                        quantity=purchase_quantity,
                        stationary_inventory=inventory,
                        stationary_purchase_order=purchase_request_order,                      
                        batch=batch ,
                       
                    )

            messages.success(request, "Inventory updated successfully!")
            return redirect("officemanagement:purchase_request_list")

        except Exception as e:
            messages.error(request, f"Error updating inventory: {str(e)}")
            return redirect("officemanagement:purchase_request_list")

    else: 
        purchase_request_data = []
        for item in purchase_request_items:
            batches = StationaryBatch.objects.filter(
                stationary_product=item.stationary_product
            ).order_by("created_at")  # FIFO

            purchase_request_data.append({
                "product_id": item.stationary_product.id,
                "product_name": item.stationary_product.name,
                "quantity": item.quantity,
                "batches": batches,
                'requester': item.user.username,
            })

        return render(
            request,
            "officemanagement/purchase/inventory_entry.html",
            {
                "purchase_request_order": purchase_request_order,
                "purchase_request_items": purchase_request_data,
                "warehouses": warehouses,
                "locations": locations,
            },
        )




@login_required
def items_requested(request,request_id):
    order_instance = get_object_or_404(StationaryPurchaseOrder,id=request_id)    
    return render(request,'officemanagement/purchase/purchase_request_items.html',{'order_instance':order_instance})






def add_invoice(request,request_id):   
    request_instance = get_object_or_404(StationaryPurchaseOrder,id = request_id)
    form = PurchaseRequestInvoiceAddForm(request.POST or None,request.FILES or None,instance=request_instance)
    
    if request.method == 'POST':
        form = PurchaseRequestInvoiceAddForm(request.POST or None,request.FILES or None,instance=request_instance)
        if form.is_valid():
            form = form.save(commit=False)
            form.user = request.user
            form.save()
            messages.success(request,'Updated successfully')
            return redirect('officemanagement:purchase_request_list')
        else:
            print(form.errors)
            form = PurchaseRequestInvoiceAddForm(request.POST or None,request.FILES or None,instance=request_instance)

    return render(request,'officemanagement/purchase/add_purchase_invoice.html',{'form':form})



####### stationary usage/demand request ###################################################################


@login_required
def create_usage_request(request):
    if 'basket' not in request.session:
        request.session['basket'] = []
    form = StationaryUsageOrderForm(request.POST or None,request.FILES or None)
   
    if request.method == 'POST':
        form = StationaryUsageOrderForm(request.POST or None,request.FILES or None)
        if 'add_to_basket' in request.POST:
            if form.is_valid():

                category = form.cleaned_data['stationary_category']
                product_obj = form.cleaned_data['stationary_product']
                quantity = form.cleaned_data['quantity']
                batch = form.cleaned_data['batch']     
                department = form.cleaned_data['department']                                       

                basket = request.session.get('basket', [])
                product_in_basket = next((item for item in basket if item['id'] == product_obj.id), None)
                

                if product_in_basket:
                    product_in_basket['quantity'] += quantity
                else:
                    basket.append({
                        'id': product_obj.id,
                        'name': product_obj.name,   
                        'category_id': category.id,                   
                        'category': category.name,                      
                        'batch_id':batch.id,
                        'batch':batch.batch_number,
                        'department_id':department.id,
                        'department':department.name,
                        'quantity': quantity,                   
                        'unit_price':float(batch.unit_price),
                       
                    })

                request.session['basket'] = basket
                request.session.modified = True
                messages.success(request, f"Added '{product_obj.name}' to the purchase basket")
                return redirect('officemanagement:create_usage_request')
            else:
                messages.error(request, "Form is invalid. Please check the details and try again.")

        elif 'action' in request.POST:
            action = request.POST['action']
            product_id = int(request.POST.get('product_id', 0))

            if action == 'update':
                new_quantity = int(request.POST.get('quantity', 1))
                for item in request.session['basket']:
                    if item['id'] == product_id:
                        item['quantity'] = new_quantity  

            elif action == 'delete':
                request.session['basket'] = [
                    item for item in request.session['basket'] if item['id'] != product_id
                ]  

            request.session.modified = True
            messages.success(request, "Purchase basket updated successfully.")
            return redirect('officemanagement:create_usage_request')

        elif 'confirm_purchase' in request.POST:
            basket = request.session.get('basket', [])
            if not basket:
                messages.error(request, "Purchase basket is empty. Add products before confirming the purchase.")
                return redirect('officemanagement:create_usage_request')
            return redirect('officemanagement:confirm_usage_request')  

    basket = request.session.get('basket', [])
    form =  StationaryUsageOrderForm()
    return render(request, 'officemanagement/usage_request/create_usage_request.html', {'form': form, 'basket': basket})



@login_required
def confirm_usage_request(request):
    basket = request.session.get('basket', [])
    if not basket:
        messages.error(request, "Purchase basket is empty. Cannot confirm purchase.")
        return redirect('officemanagement:create_usage_request')

    if request.method == 'POST':
        try:
            with transaction.atomic(): 
                total_amount = sum(item['quantity'] * item['unit_price'] for item in basket)
                department_id = basket[0]['department_id'] if basket else None  
                department = get_object_or_404(Department,id=department_id)
                
                stationary_usage_order = StationaryUsageRequestOrder(
                    total_amount=total_amount,                                  
                    department = department,
                    user=request.user  
                )
                stationary_usage_order.save()  
               
                for item in basket:
                    product = get_object_or_404(StationaryProduct, id=item['id'])
                    quantity = item['quantity']
                    category = get_object_or_404(StationaryCategory, id=item['category_id'])
                    batch = get_object_or_404(StationaryBatch, id=item['batch_id'])   
                                 

                    usage_request_item = StationaryUsageRequestItem(
                        stationary_usage_request_order=stationary_usage_order,
                        stationary_product=product,
                        quantity=quantity,
                        stationary_category = category,
                        batch = batch,
                        user=request.user  
                    )
                    usage_request_item.save()

                request.session['basket'] = []
                request.session.modified = True
                messages.success(request, "Purchase order created successfully!")
                return redirect('officemanagement:create_usage_request')

        except Exception as e:            
            messages.error(request, f"An error occurred while creating the purchase order: {str(e)}")
            return redirect('officemanagement:create_usage_request')
    return render(request, 'officemanagement/usage_request/confirm_usage_request.html', {'basket': basket})




@login_required
def usage_request_list(request):    
  
    if request.method == 'GET':
        end_date = request.GET.get('end_date')
        start_date = request.GET.get('start_date')
        order_id = request.GET.get('order_id')

        usage_request_orders = StationaryUsageRequestOrder.objects.all().order_by('-created_at')
        
        if not start_date or not end_date: 
            end_date = datetime.today().date()
            start_date = end_date - timedelta(days=7)
            usage_request_orders = usage_request_orders.filter(created_at__range=[start_date,end_date])
        else:             
            start_date = datetime.strptime(start_date, "%Y-%m-%d").date()
            end_date = datetime.strptime(end_date, "%Y-%m-%d").date()
            usage_request_orders=usage_request_orders.filter(created_at__range=[start_date,end_date])

        if order_id:
            usage_request_orders =usage_request_orders.filter(request_id = order_id)            
             
    paginator = Paginator(usage_request_orders, 10)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    return render(request, 'officemanagement/usage_request/usage_request_list.html', {                
     'page_obj': page_obj,
       
      
    })




@login_required
def process_usage_request(request, request_id):
    order = get_object_or_404(StationaryUsageRequestOrder, id=request_id)

    role_status_map = {
        "Requester": ["SUBMITTED", "CANCELLED"],
        "Reviewer": ["REVIEWED", "CANCELLED"],
        "Approver": ["APPROVED", "CANCELLED"],
    }

    if request.method == 'POST':
        form = PurchaseStatusForm(request.POST)
        if form.is_valid():
            if order.approval_data is None:
                order.approval_data = {}

            approval_status = form.cleaned_data['approval_status']
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
                if approval_status in role_status_map[user_role]:
                    role = user_role
                    break

            if not role:
                messages.error(
                    request,
                    "You do not have permission to perform this action or invalid status."
                )
                return redirect('officemanagement:purchase_request_list')

            if role == "Requester":
                order.requester_approval_status = approval_status
                order.Requester_remarks = remarks
            elif role == "Reviewer":
                order.reviewer_approval_status = approval_status
                order.Reviewer_remarks = remarks
            elif role == "Approver":
                order.approver_approval_status = approval_status
                order.Approver_remarks = remarks

            order.approval_data[role] = {
                'status': approval_status,
                'remarks': remarks,
                'date': timezone.now().isoformat(),
            }          
            
            order.save()

            if order.approver_approval_status == 'APPROVED':
                order.status = 'Aproved'
            elif order.approver_approval_status == 'REJECTED':
                order.status = 'Rejected'
            else:
                order.status = 'Pending'
            order.save()

            messages.success(request, f"Order {order.id} successfully updated.")
            return redirect('officemanagement:usage_request_list')
        else:
            messages.error(request, "Invalid form submission.")
    else:
        form = PurchaseStatusForm()
    return render(request, 'officemanagement/usage_request/usage_request_approval_form.html', {'form': form, 'order': order})




@login_required
def usage_items_requested(request,request_id):
    order_instance = get_object_or_404(StationaryUsageRequestOrder,id=request_id)    
    return render(request,'officemanagement/usage_request/usage_request_items.html',{'order_instance':order_instance})




def confirm_usage_dispatch(request, request_id):
    usage_request_order = get_object_or_404(StationaryUsageRequestOrder, id=request_id)   
    usage_request_items = usage_request_order.usage_order.all()

    valuation_method = request.GET.get("valuation_method", "FIFO")  # FIFO or LIFO
    order_by = "created_at" if valuation_method == "FIFO" else "-created_at"

    warehouses = Warehouse.objects.all()
    locations = Location.objects.all()

    if request.method == "POST":
        try:
            with transaction.atomic():
                for index, item in enumerate(usage_request_items, start=1):
                    product_id = request.POST.get(f"product_id_{index}")
                    warehouse_id = request.POST.get(f"warehouse_{index}")
                    location_id = request.POST.get(f"location_{index}")
                    requested_quantity = int(item.quantity)
                    batch = item.batch

                    product = StationaryProduct.objects.get(id=product_id)
                    warehouse = Warehouse.objects.get(id=warehouse_id)
                    location = Location.objects.get(id=location_id)

                    inventories = StationaryInventory.objects.filter(
                        stationary_product=product,
                        warehouse=warehouse,
                        location=location,
                        batch = batch,
                        quantity__gt=0
                    ).order_by(order_by) 

                    if not inventories.exists():
                        messages.error(request, f"No stock available for {product.name} in the selected warehouse and location.")
                        return redirect("officemanagement:usage_request_list")

                    remaining_quantity = requested_quantity

                    for inventory in inventories:
                        if remaining_quantity <= 0:
                            break
                        
                        batch_deduct = min(inventory.quantity, remaining_quantity)                      
                        inventory.quantity -= batch_deduct
                        inventory.save()

                        if batch:
                            if batch.quantity >= batch_deduct:
                                batch.quantity -= batch_deduct
                                batch.remaining_quantity -= batch_deduct
                                batch.save(update_fields=["quantity", "remaining_quantity"])
                               
                            else:
                                messages.error(request, f"Batch {batch.batch_number} has insufficient stock for {product.name}.")
                                return redirect("officemanagement:usage_request_list")
                        else:
                            messages.error(request, f"No batch found for {product.name}.")
                            return redirect("officemanagement:usage_request_list")                       

                        remaining_quantity -= batch_deduct

                        StationaryInventoryTransaction.objects.create(
                            stationary_product=product,
                            warehouse=warehouse,
                            location=location,
                            transaction_type="outbound",
                            quantity=batch_deduct,
                            stationary_inventory=inventory,
                            stationary_usage_request_order=usage_request_order,
                            batch=batch  
                        )

                    if remaining_quantity > 0:
                        messages.error(
                            request,
                            f"Not enough stock available for {product.name}. {remaining_quantity} units short."
                        )
                        return redirect("officemanagement:usage_request_list")

            messages.success(request, "Inventory and batch updated successfully with FIFO/LIFO!")
            return redirect("officemanagement:usage_request_list")

        except Exception as e:
            messages.error(request, f"Error updating inventory: {str(e)}")
            return redirect("officemanagement:usage_request_list")

    else:
        # Fetch batches sorted for FIFO/LIFO display
        usage_request_data = []
        for item in usage_request_items:
            batches = StationaryBatch.objects.filter(
                stationary_product=item.stationary_product
            ).order_by("created_at")  # FIFO

            usage_request_data.append({
                "product_id": item.stationary_product.id,
                "product_name": item.stationary_product.name,
                "quantity": item.quantity,
                "batches": batches,
                "requester": item.user.username,
                "department": item.stationary_usage_request_order.department
            })

    return render(
        request,
        "officemanagement/usage_request/inventory_entry.html",
        {
            "usage_request_order": usage_request_order,
            "usage_request_items": usage_request_data,
            "warehouses": warehouses,
            "locations": locations,
            
        },
    )



def inventory_report(request):
    warehouses = Warehouse.objects.all()
    inventory_data = []
    total_stock_value =0

    for warehouse in warehouses:
        products = StationaryInventory.objects.filter(warehouse=warehouse)
        warehouse_data = {
            "warehouse_name": warehouse.name,
            "inbound_stock": 0,
            "outbound_stock": 0,
            "available_stock": 0,
            "total_stock_value": 0,  
            "products": []
        }

        for product in products:
            inbound = StationaryInventoryTransaction.objects.filter(
                warehouse=warehouse, stationary_product=product.stationary_product, transaction_type='inbound'
            ).aggregate(total=Sum('quantity'))['total'] or 0

            outbound = StationaryInventoryTransaction.objects.filter(
                warehouse=warehouse, stationary_product=product.stationary_product, transaction_type='outbound'
            ).aggregate(total=Sum('quantity'))['total'] or 0

            available_quantity = product.quantity  
            stock_value = float(available_quantity * product.batch.unit_price)  
            total_stock_value += stock_value


            warehouse_data["products"].append({
                "product": product.stationary_product.name,
                "available_quantity": available_quantity,
                "stock_value": stock_value,  
                "inbound": inbound,
                "outbound": outbound
            })

            warehouse_data["inbound_stock"] += inbound
            warehouse_data["outbound_stock"] += outbound
            warehouse_data["available_stock"] += available_quantity
            warehouse_data["total_stock_value"] += stock_value  

        inventory_data.append(warehouse_data)

    context = {
        "warehouse_json": json.dumps(inventory_data),'total_stock_value':total_stock_value 
    }
    return render(request, "officemanagement/report/inventory_report.html", context)




################## Meeting room ##########################################

@login_required
def manage_meeting_room(request, id=None):  
    end_date = datetime.today().date()
    start_date = end_date - timedelta(days=14)

    instance = get_object_or_404(MeetingRoom, id=id) if id else None
    message_text = "updated successfully!" if id else "added successfully!"  
    form = MeetingRoomForm(request.POST or None, request.FILES or None, instance=instance)

    if request.method == 'POST' and form.is_valid():
        form_intance=form.save(commit=False)
        form_intance.user = request.user
        form_intance.save()        
        messages.success(request, message_text)
        return redirect('officemanagement:create_meeting_room')  

    datas = MeetingRoom.objects.all().order_by('-created_at')
    paginator = Paginator(datas, 5)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    print(datas)

    return render(request, 'officemanagement/meeting_room/manage_meeting_room.html', {
        'form': form,
        'instance': instance,
        'datas': datas,
        'page_obj': page_obj
    })




@login_required
def delete_meeting_room(request, id):
    instance = get_object_or_404(MeetingRoom, id=id)
    if request.method == 'POST':
        instance.delete()
        messages.success(request, "Deleted successfully!")
        return redirect('officemanagement:create_meeting_room')        

    messages.warning(request, "Invalid delete request!")
    return redirect('officemanagement:create_meeting_room')  



@login_required
def manage_meeting_order(request, id=None):  
    end_date = datetime.today().date()
    start_date = end_date - timedelta(days=14)

    instance = get_object_or_404(MeetingOrder, id=id) if id else None
    message_text = "updated successfully!" if id else "added successfully!"  
    form = MeetingOrderForm(request.POST or None, request.FILES or None, instance=instance)

    if request.method == 'POST' and form.is_valid():
        form_intance=form.save(commit=False)
        form_intance.user = request.user
        form_intance.save()        
        messages.success(request, message_text)
        return redirect('officemanagement:create_meeting_order')  

    datas = MeetingOrder.objects.filter(created_at__range = [start_date,end_date]).order_by('-created_at')
    paginator = Paginator(datas, 5)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    return render(request, 'officemanagement/meeting_room/manage_meeting_order.html', {
        'form': form,
        'instance': instance,
        'datas': datas,
        'page_obj': page_obj
    })




@login_required
def delete_meeting_order(request, id):
    instance = get_object_or_404(MeetingOrder, id=id)
    if request.method == 'POST':
        instance.delete()
        messages.success(request, "Deleted successfully!")
        return redirect('officemanagement:create_meeting_order')         

    messages.warning(request, "Invalid delete request!")
    return redirect('officemanagement:create_meeting_order')  




@login_required
def manage_attendee(request, id=None):  
    instance = get_object_or_404(Attendees, id=id) if id else None
    message_text = "updated successfully!" if id else "added successfully!"  
    form = AddAttendeeForm(request.POST or None, request.FILES or None, instance=instance)

    if request.method == 'POST' and form.is_valid():
        form_intance=form.save(commit=False)
        form_intance.user = request.user
        form_intance.save()        
        messages.success(request, message_text)
        return redirect('officemanagement:create_attendee')  

    datas = Attendees.objects.all().order_by('-created_at')
    paginator = Paginator(datas, 5)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    return render(request, 'officemanagement/meeting_room/manage_attendee.html', {
        'form': form,
        'instance': instance,
        'datas': datas,
        'page_obj': page_obj
    })




@login_required
def delete_attendee(request, id):
    instance = get_object_or_404(Attendees, id=id)
    if request.method == 'POST':
        instance.delete()
        messages.success(request, "Deleted successfully!")
        return redirect('officemanagement:create_attendee')         

    messages.warning(request, "Invalid delete request!")
    return redirect('officemanagement:create_attendee')  



def meeting_room_list(request): 
    if request.method == 'GET':
        end_date = request.GET.get('end_date')
        start_date = request.GET.get('start_date')
        name= request.GET.get('name')
        rooms = MeetingRoom.objects.all().order_by('-created_at')        
        if not start_date or not end_date: 
            end_date = datetime.today().date() + timedelta(days=1)
            start_date = end_date - timedelta(days=7)
            rooms = rooms.filter(created_at__range=[start_date,end_date])
        else:             
            start_date = datetime.strptime(start_date, "%Y-%m-%d").date()
            end_date = datetime.strptime(end_date, "%Y-%m-%d").date()
            rooms=rooms.filter(created_at__range=[start_date,end_date])
        if name:
            rooms =rooms.filter(name = name)              
    paginator = Paginator(rooms, 10)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)                 
    return render(request, "officemanagement/meeting_room/meeting_room_list.html", {"page_obj": page_obj})


def meeting_room_calendar(request, room_id):
    room = get_object_or_404(MeetingRoom, id=room_id)
    bookings = MeetingRoomBooking.objects.filter(room=room)
    

    events = [
        {
            "title": f"{booking.booked_by.name} ({booking.purpose})",
            "start": f"{booking.date}T{booking.start_time}",
            "end": f"{booking.date}T{booking.end_time}",
            # 'status':f'{booking.room}{booking.status}',
            "color": "#007bff",
           
        }
        for booking in bookings
    ]

    return render(request, "officemanagement/meeting_room/meeting_room_calender.html", {
        "room": room,
        "bookings_json": json.dumps(events), 
    })



def book_meeting_room(request, room_id):
    room = MeetingRoom.objects.get(id=room_id)

    if request.method == "POST":
        form = MeetingRoomBookingForm(request.POST)
        if form.is_valid():
            date = form.cleaned_data["date"]
            start_time = form.cleaned_data["start_time"]
            end_time = form.cleaned_data["end_time"]

            # Check if the room is available in the selected time slot
            overlapping_bookings = MeetingRoomBooking.objects.filter(
                room=room,
                date=date,
                start_time__lt=end_time,
                end_time__gt=start_time
            )

            if overlapping_bookings.exists():
                messages.error(request, "This time slot is already booked. Please choose a different time.")
            else:
                booking = form.save(commit=False)
                booking.room = room
                if hasattr(request.user, "user_profile") and request.user.user_profile.employee_user_profile.exists():
                    booking.booked_by = request.user.user_profile.employee_user_profile.first()
                else:
                    messages.error(request, "Your profile is not linked to an employee record.")
                    return redirect("officemanagement:meeting_room_calendar", room_id=room.id)


                booking.status = "Pending" 
                booking.save()
                messages.success(request, "Meeting room booked successfully!")
                return redirect("officemanagement:meeting_room_calendar", room_id=room.id)
    
    else:
        form = MeetingRoomBookingForm()
    return render(request, "officemanagement/meeting_room/book_meeting_room.html", {"form": form, "room": room})



def meeting_room_report(request):
    current_time = now().time()
    thirty_minutes_later = (now() + timedelta(minutes=30)).time()

    total_Number_of_meeting_rooms = MeetingRoom.objects.all().count()

    # Rooms currently in use
    in_use_rooms = MeetingRoom.objects.filter(
        meeting_room_bookings__date=now().date(),
        meeting_room_bookings__start_time__lte=current_time,
        meeting_room_bookings__end_time__gt=current_time,
        meeting_room_bookings__status='Confirmed'
    ).distinct()

    # Rooms that will be free in 30 minutes (OR have no bookings at all)
    free_soon_rooms = MeetingRoom.objects.exclude(
        meeting_room_bookings__date=now().date(),
        meeting_room_bookings__start_time__lte=thirty_minutes_later,
        meeting_room_bookings__end_time__gt=current_time,
        meeting_room_bookings__status='Confirmed'
    ).distinct()

    context = {
        "in_use_rooms": in_use_rooms,
        "free_soon_rooms": free_soon_rooms,
        'total_Number_of_meeting_rooms':total_Number_of_meeting_rooms
    }
    
    return render(request, "officemanagement/report/meeting_room_report.html", context)




from tasks.models import Task
from myproject.utils import create_notification

@login_required
def manage_IT_support(request, id=None):  
    instance = get_object_or_404(ITSupportTicket, id=id) if id else None
    message_text = "updated successfully!" if id else "added successfully!"  
    form = ITSupportForm(request.POST or None, request.FILES or None, instance=instance)

    if request.method == 'POST' and form.is_valid():
        form_intance=form.save(commit=False)
        form_intance.user = request.user
        form_intance.save()     

        task = Task.objects.create(
                it_support_ticket=form_intance,  
                progress=0.0,
                user=request.user,
                task_type='IT-TICKET',
                title='IT Support',
                priority = 'MEDIUM'
            )
        
        messages.success(request, message_text)
        create_notification(request.user,message=f"A IT Support ticket with issue:{form_intance.issue} has been created",notification_type='TICKET-NOTIFICATION')
        return redirect('officemanagement:create_IT_support')  

    datas = ITSupportTicket.objects.all().order_by('-created_at')
    paginator = Paginator(datas, 5)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    return render(request, 'officemanagement/manage_IT_support.html', {
        'form': form,
        'instance': instance,
        'datas': datas,
        'page_obj': page_obj
    })



@login_required
def delete_IT_support(request, id):
    instance = get_object_or_404(ITSupportTicket, id=id)
    if request.method == 'POST':
        instance.delete()
        messages.success(request, "Deleted successfully!")
        return redirect('officemanagement:create_IT_support')        

    messages.warning(request, "Invalid delete request!")
    return redirect('officemanagement:create_IT_support') 


from datetime import datetime, timedelta
from django.core.paginator import Paginator
from django.shortcuts import render
from .models import ITSupportTicket

def IT_support_list(request):
    end_date = request.GET.get('end_date')
    start_date = request.GET.get('start_date')
    ticket_id = request.GET.get('ID')

    objects = ITSupportTicket.objects.all().order_by('-created_at')    

    if start_date and end_date:
        start_date = datetime.strptime(start_date, "%Y-%m-%d").date()
        end_date = datetime.strptime(end_date, "%Y-%m-%d").date() + timedelta(days=1)  # Include full end date
        objects = objects.filter(created_at__gte=start_date, created_at__lt=end_date)

    if ticket_id:
        objects = objects.filter(ticket_id=ticket_id)   
  
    paginator = Paginator(objects, 10)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)                 

    return render(request, 'officemanagement/IT_support_list.html', {
        'page_obj': page_obj,
        'start_date': request.GET.get('start_date', ''),
        'end_date': request.GET.get('end_date', ''),
        'ID': request.GET.get('ID', ''),
        'name': request.GET.get('name', ''),
    })

from tasks.models import TeamMember,PerformanceEvaluation

def update_it_feedback(request,support_id):   
    TT_instance = get_object_or_404(ITSupportTicket,id=support_id) 
    form = ITSupportUpdateForm(request.POST,instance = TT_instance)
    task = TT_instance.it_task_ticket.first() 

    if task:   
        if task.assigned_to is None:
            messages.info(request,'You have not assigned to update this ticket yet, Please ask your manager to assign this ticket as task in task list dashboard')
            return redirect('officemanagement:IT_support_list')
        if task.assigned_to_employee.user_profile != request.user.user_profile:
            messages.info(request, "Your manager has assigned this task to another person.")
            return redirect('officemanagement:IT_support_list')

       
    if request.method == 'POST':
        form = ITSupportUpdateForm(request.POST,instance = TT_instance)
        if form.is_valid():
            status = form.cleaned_data['status']
            form.save(commit=False)
            form.user = request.user
            form.save()
            if status == 'Closed':
                task.status = 'COMPLETED'
                task.progress = 100.0
                task.save() 

                new_obtained_number = task.calculate_obtained_number()           

                task.obtained_number = new_obtained_number
                if task.assigned_number > 0:
                    task.obtained_score = (new_obtained_number / task.assigned_number) * 100 
                    task.obtained_number = new_obtained_number
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

            create_notification(request.user, message= f'Task:{task.title}, progress {task.progress}% updated by {request.user} dated {timezone.now()}',notification_type='TASK-NOTIFICATION')
            messages.success(request, f'Ticket updated successfully with feedback:')
            return redirect('officemanagement:IT_support_list')
    form = ITSupportUpdateForm(instance = TT_instance)
    return render(request,'officemanagement/update_IT_support.html',{'form':form})




@login_required
def manage_visitor_group(request, id=None):  
    end_date = datetime.today().date()
    start_date = end_date - timedelta(days=14)

    instance = get_object_or_404(VisitorGroup, id=id) if id else None
    message_text = "updated successfully!" if id else "added successfully!"  
    form = VisitorGroupForm(request.POST or None, request.FILES or None, instance=instance)

    if request.method == 'POST' and form.is_valid():
        form_intance=form.save(commit=False)
        form_intance.user = request.user
        form_intance.save()        
        messages.success(request, message_text)
        return redirect('officemanagement:create_visitor_group')  

    datas = VisitorGroup.objects.all().order_by('-check_in')
    paginator = Paginator(datas, 5)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    return render(request, 'officemanagement/manage_visitor_group.html', {
        'form': form,
        'instance': instance,
        'datas': datas,
        'page_obj': page_obj
    })




@login_required
def delete_visitor_group(request, id):
    instance = get_object_or_404(VisitorGroup, id=id)
    if request.method == 'POST':
        instance.delete()
        messages.success(request, "Deleted successfully!")
        return redirect('officemanagement:create_visitor_group')        

    messages.warning(request, "Invalid delete request!")
    return redirect('officemanagement:create_visitor_group')  





@login_required
def add_member_visitor_group(request, id=None):  
    instance = get_object_or_404(VisitorLog, id=id) if id else None
    message_text = "updated successfully!" if id else "added successfully!"  
    form = VisitorLogForm(request.POST or None, request.FILES or None, instance=instance)

    if request.method == 'POST' and form.is_valid():
        form_intance=form.save(commit=False)
        form_intance.user = request.user
        form_intance.save()        
        messages.success(request, message_text)
        return redirect('officemanagement:create_visitor_member')  

    datas = VisitorLog.objects.all().order_by('-created_at')
    paginator = Paginator(datas, 5)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    return render(request, 'officemanagement/manage_visitor_member.html', {
        'form': form,
        'instance': instance,
        'datas': datas,
        'page_obj': page_obj
    })




@login_required
def delete_member_visitor_group(request, id):
    instance = get_object_or_404(VisitorLog, id=id)
    if request.method == 'POST':
        instance.delete()
        messages.success(request, "Deleted successfully!")
        return redirect('officemanagement:create_visitor_member')         

    messages.warning(request, "Invalid delete request!")
    return redirect('officemanagement:create_visitor_memeber_log')  



from .forms import VisitorSearchForm
from django.db import models


def search_visitor(request):
    form = VisitorSearchForm(request.GET or None)
    visitors = VisitorLog.objects.all().order_by('-created_at')

    if form.is_valid():
        query = form.cleaned_data.get("query")
        if query:
            visitors = visitors.filter(
                models.Q(name__icontains=query) | models.Q(phone__icontains=query)
            )

    

    paginator = Paginator(visitors, 5)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    return render(request, "officemanagement/visitor_search.html", {"form": form, "visitors": visitors,'page_obj':page_obj})



def visitor_reports(request):
    today = now().date()
 
    daily_visitors = VisitorLog.objects.filter(created_at__date=today).count()
    monthly_visitors = VisitorLog.objects.filter(created_at__month=today.month).count()

    # 2️⃣ Breakdown by Visitor Type (Local vs. Foreigner)
    visitor_summary = list(VisitorLog.objects.values('visitor_type').annotate(count=Count('id')))
 
    current_visitors = VisitorGroup.objects.filter(check_in__isnull=False, check_out__isnull=True).count()

    overdue_visitors = list(
    VisitorLog.objects.filter(
        company__check_in__isnull=False, 
        company__check_out__isnull=True, 
        company__check_in__lt=now() - timedelta(hours=8)
    ).values('name', 'phone', 'company__check_in')
        )

    company_visits = list(VisitorGroup.objects.values('company').annotate(total_visits=Count('id')))

    peak_hours = list(
        VisitorGroup.objects.annotate(hour=ExtractHour('check_in'))
        .values('hour')
        .annotate(count=Count('id'))
        .order_by('-count')
    )

    frequent_visitors = list(
        VisitorLog.objects.values('name', 'phone').annotate(visit_count=Count('id')).filter(visit_count__gt=1)
    )

    context = {
    "daily_visitors": daily_visitors,
    "monthly_visitors": monthly_visitors,
    "current_visitors": current_visitors,
    "overdue_visitors": overdue_visitors,  
    "frequent_visitors": frequent_visitors,  
    "visitor_summary_json": json.dumps(visitor_summary),  
    "company_visits_json": json.dumps(company_visits),  
    "peak_hours_json": json.dumps(peak_hours),  
}
    return render(request, "officemanagement/report/visitor_reports.html", context)



################ expense and advance record ####################################

@login_required
def manage_expense_advance(request, id=None):  
    end_date = datetime.today().date()
    start_date = end_date - timedelta(days=30)

    instance = get_object_or_404(OfficeAdvance, id=id) if id else None
    message_text = "updated successfully!" if id else "added successfully!"  
    form = ExpenseAdvanceForm(request.POST or None, request.FILES or None, instance=instance)

    if request.method == 'POST' and form.is_valid():
        form_intance=form.save(commit=False)
        form_intance.user = request.user
        form_intance.save()        
        messages.success(request, message_text)
        return redirect('officemanagement:create_expense_advance')  

    datas = OfficeAdvance.objects.filter(created_at__range = [start_date,end_date]).order_by('-created_at')
    paginator = Paginator(datas, 5)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    return render(request, 'officemanagement/expenses/manage_expense_advance.html', {
        'form': form,
        'instance': instance,
        'datas': datas,
        'page_obj': page_obj
    })



@login_required
def delete_expense_advance(request, id):
    instance = get_object_or_404(OfficeAdvance, id=id)
    if request.method == 'POST':
        instance.delete()
        messages.success(request, "Deleted successfully!")
        return redirect('officemanagement:create_expense_advance')        

    messages.warning(request, "Invalid delete request!")
    return redirect('officemanagement:create_expense_advance')    


@login_required
def expense_advance_list(request):
    if request.method == 'GET':
        end_date = request.GET.get('end_date')
        start_date = request.GET.get('start_date')      

        objects =  OfficeAdvance.objects.all().order_by('-created_at')    

        if not start_date or not end_date: 
            end_date = datetime.today().date()
            start_date = end_date - timedelta(days=7)
            objects = objects.filter(created_at__range=[start_date,end_date])
        else:             
            start_date = datetime.strptime(start_date, "%Y-%m-%d").date()
            end_date = datetime.strptime(end_date, "%Y-%m-%d").date()
            objects=objects.filter(created_at__range=[start_date,end_date])
             
   
    paginator = Paginator(objects , 10)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    return render(request, 'officemanagement/expenses/expense_advance_list.html', {               
        'user': request.user, 
        'page_obj': page_obj,
       
      
    })


def expense_advance_approval(request,submission_id):
    order_instance = get_object_or_404(OfficeAdvance,id = submission_id)
    form = ExpenseAdvanceApprovalForm(request.POST,instance = order_instance)

    if request.method == 'POST':
        form = ExpenseAdvanceApprovalForm(request.POST,instance = order_instance)
        if form.is_valid():
            form = form.save(commit=False)
            form.approved_by = request.user.user_profile.employee_user_profile.first()
            form.save()
            return redirect('officemanagement:expense_advance_list')
        
    form = ExpenseAdvanceApprovalForm(instance = order_instance)
    return render(request,'officemanagement/expenses/expense_advance_approval.html',{'form':form})




@login_required
def manage_expense_order(request, id=None):  
    end_date = datetime.today().date()
    start_date = end_date - timedelta(days=30)
  
    instance = get_object_or_404(ExpenseSubmissionOrder, id=id) if id else None
    message_text = "updated successfully!" if id else "added successfully!"  
    form = ExpenseSubmissionOrderForm(request.POST or None, request.FILES or None, instance=instance)

    if request.method == 'POST':
        form = ExpenseSubmissionOrderForm(request.POST or None, request.FILES or None, instance=instance)
        if form.is_valid():
            form_instance=form.save(commit=False)
            if form_instance.advance_ref and ExpenseSubmissionOrder.objects.filter(advance_ref=form_instance.advance_ref).exists():
                messages.error(request, "An ExpenseSubmissionOrder already exists for this advance reference.")
                return redirect('officemanagement:create_expense_order') 
            form_instance.user = request.user
            if hasattr(request.user, "user_profile") and hasattr(request.user.user_profile, "employee_user_profile"):
                form_instance.submitted_by = request.user.user_profile.employee_user_profile.first()
            form_instance.user = request.user
            form_instance.save()     
        
            messages.success(request, message_text)
            return redirect('officemanagement:create_expense_order')  
        else:
            print(form.errors)

    datas = ExpenseSubmissionOrder.objects.filter(created_at__range = [start_date,end_date]).order_by('-submission_date')
    paginator = Paginator(datas, 5)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

     
    return render(request, 'officemanagement/expenses/manage_expense_order.html', {
        'form': form,
        'instance': instance,
        'datas': datas,
        'page_obj': page_obj
    })



@login_required
def delete_expense_order(request, id):
    instance = get_object_or_404(ExpenseSubmissionOrder, id=id)
    if request.method == 'POST':
        instance.delete()
        messages.success(request, "Deleted successfully!")
        return redirect('officemanagement:create_expense_order')        

    messages.warning(request, "Invalid delete request!")
    return redirect('officemanagement:create_expense_order')  




@login_required
def manage_expense_item(request, id=None):  
    end_date = datetime.today().date()
    start_date = end_date - timedelta(days=30)
    instance = get_object_or_404(ExpenseSubmissionItem, id=id) if id else None
    message_text = "updated successfully!" if id else "added successfully!"  
    form = ExpenseSubmissionItemForm(request.POST or None, request.FILES or None, instance=instance)

    if request.method == 'POST' and form.is_valid():
        form_intance=form.save(commit=False)
        form_intance.user = request.user
        form_intance.save()        
        messages.success(request, message_text)
        return redirect('officemanagement:create_expense_item')  

    datas = ExpenseSubmissionItem.objects.filter(created_at__range = [start_date,end_date]).order_by('-created_at')
    paginator = Paginator(datas, 5)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    return render(request, 'officemanagement/expenses/manage_expense_item.html', {
        'form': form,
        'instance': instance,
        'datas': datas,
        'page_obj': page_obj
    })



@login_required
def delete_expense_item(request, id):
    instance = get_object_or_404(ExpenseSubmissionItem, id=id)
    if request.method == 'POST':
        instance.delete()
        messages.success(request, "Deleted successfully!")
        return redirect('officemanagement:create_expense_item')        

    messages.warning(request, "Invalid delete request!")
    return redirect('officemanagement:create_expense_item')  



@login_required
def expense_order_list(request):
    if request.method == 'GET':
        end_date = request.GET.get('end_date')
        start_date = request.GET.get('start_date')  
        submission_id = request.GET.get('submission_id')        

        objects = ExpenseSubmissionOrder.objects.all().order_by('-created_at')    

        if not start_date or not end_date: 
            end_date = datetime.today().date()
            start_date = end_date - timedelta(days=7)
            objects = objects.filter(created_at__range=[start_date,end_date])
        else:             
            start_date = datetime.strptime(start_date, "%Y-%m-%d").date()
            end_date = datetime.strptime(end_date, "%Y-%m-%d").date()
            objects=objects.filter(created_at__range=[start_date,end_date])
        if submission_id:
            objects = objects.filter(submission_id = submission_id )

 
    paginator = Paginator( objects, 10)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    return render(request, 'officemanagement/expenses/expense_order_list.html', {                 
        'user': request.user, 
        'page_obj': page_obj,
        
      
    })



def items_submitted(request,submission_id):
    order_instance = get_object_or_404(ExpenseSubmissionOrder,id = submission_id)
    items_submitted = order_instance.items_submitted.all()
    return render(request,'officemanagement/expenses/items_submitted.html',{'items_submitted':items_submitted})



def expense_approval(request,submission_id):
    order_instance = get_object_or_404(ExpenseSubmissionOrder,id = submission_id)
    form = ExpenseSubmissionOrderUpdateForm(request.POST,instance = order_instance)

    if request.method == 'POST':
        form = ExpenseSubmissionOrderUpdateForm(request.POST,instance = order_instance)
        if form.is_valid():
            form = form.save(commit=False)
            form.approved_by = request.user.user_profile.employee_user_profile.first()
            form.save()
            return redirect('officemanagement:expense_order_list')
        
    form = ExpenseSubmissionOrderUpdateForm(instance = order_instance)
    return render(request,'officemanagement/expenses/expense_approval.html',{'form':form})


from django.db.models import Sum, Count, Q

def top_expense_categories(request):
    start_date = request.GET.get("start_date")
    end_date = request.GET.get("end_date")
    filters = Q()
    if start_date and end_date:
        filters &= Q(submission_order__submission_date__range=[start_date, end_date])
    elif start_date:
        filters &= Q(submission_order__submission_date__gte=start_date)
    elif end_date:
        filters &= Q(submission_order__submission_date__lte=end_date)

    top_categories = list(
        ExpenseSubmissionItem.objects.filter(filters)
        .values("category")
        .annotate(total_spent=Sum("amount"), count=Count("id"))
        .order_by("-total_spent")[:5]  
    )
 
    for category in top_categories:
        category["total_spent"] = float(category["total_spent"])  

    context = {
        "top_categories": top_categories,
        "top_categories_json": json.dumps(top_categories), 
    }
    return render(request, "officemanagement/report/top_expense_categories.html", context)


from django.db.models import Sum, F, DecimalField

def advance_reconciliation_report(request):
    search_query = request.GET.get("search", "").strip()

    total_advance_taken = OfficeAdvance.objects.aggregate(
        total=Sum(F("amount"), output_field=DecimalField())
    )["total"] or 0 

    total_expenses_submitted = ExpenseSubmissionOrder.objects.filter(
        total_amount__isnull=False
    ).aggregate(
        total=Sum(F("total_amount"), output_field=DecimalField())
    )["total"] or 0

    total_balance = total_advance_taken - total_expenses_submitted

    employees = Employee.objects.all().order_by('-created_at')

    if search_query:
        employees = employees.filter(name__icontains=search_query).order_by('-created_at')  
    else:
        employees =  employees.order_by('-created_at')

    reconciliation_data = employees.annotate(
        total_advance_taken=Sum(
            "office_advance_employee__amount", output_field=DecimalField()
        ),
        total_expenses_submitted=Sum(
            "expense_submission_user__total_amount",
            distinct=True,
            output_field=DecimalField()
        )
    ).values("name", "total_advance_taken", "total_expenses_submitted")

    for data in reconciliation_data:
        advance = data["total_advance_taken"] or 0
        expenses = data["total_expenses_submitted"] or 0
        data["balance"] = advance - expenses
    
    paginator = Paginator(reconciliation_data, 6)  
    page_number = request.GET.get("page")
    page_obj = paginator.get_page(page_number)      
    context = {
        "reconciliation_data": reconciliation_data,
        "total_advance_taken": total_advance_taken,
        "total_expenses_submitted": total_expenses_submitted,
        "total_balance": total_balance,
        'page_obj':page_obj
    }
    return render(request, "officemanagement/report/advance_reconcilation_report.html", context)

########################### #####################################################################

@login_required
def manage_office_document(request, id=None):  
    end_date = datetime.today().date()
    start_date = end_date - timedelta(days=30)
    instance = get_object_or_404(OfficeDocument, id=id) if id else None
    message_text = "updated successfully!" if id else "added successfully!"  
    form = OfficeDocumentForm(request.POST or None, request.FILES or None, instance=instance)

    if request.method == 'POST' and form.is_valid():
        form_instance=form.save(commit=False)
        form_instance.user = request.user
        form_instance.uploaded_by = request.user.user_profile.employee_user_profile.first()
        form_instance.save()        
        messages.success(request, message_text)
        return redirect('officemanagement:create_office_document')  

    datas = OfficeDocument.objects.filter(created_at__range = [start_date,end_date]).order_by('-created_at')
    paginator = Paginator(datas, 5)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    return render(request, 'officemanagement/manage_office_documents.html', {
        'form': form,
        'instance': instance,
        'datas': datas,
        'page_obj': page_obj
    })



@login_required
def delete_office_document(request, id):
    instance = get_object_or_404(OfficeDocument, id=id)
    if request.method == 'POST':
        instance.delete()
        messages.success(request, "Deleted successfully!")
        return redirect('officemanagement:create_office_document')        

    messages.warning(request, "Invalid delete request!")
    return redirect('officemanagement:create_office_document')  




def office_document_list(request):
    if request.method == 'GET':
        end_date = request.GET.get('end_date')
        start_date = request.GET.get('start_date')  
        title = request.GET.get('title')   
        department_name = request.GET.get('department')           

        objects = OfficeDocument.objects.all().order_by('-created_at')   

        if not start_date or not end_date: 
            end_date = datetime.today().date()
            start_date = end_date - timedelta(days=7)
            objects = objects.filter(created_at__range = [start_date,end_date])
        else:
            objects = objects.filter(created_at__range = [start_date,end_date])     

        if title:
            objects = objects.filter(title__icontains=title)  

        if department_name:
            try:
                department = Department.objects.get(name__icontains=department_name)
                objects = objects.filter(department=department)
            except Department.DoesNotExist:
                objects = objects.none()  


    paginator = Paginator(objects, 10)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    return render(request, 'officemanagement/office_documents_list.html', {     
        'user': request.user, 
        'page_obj': page_obj,
        'start_date': start_date,
        'end_date': end_date,
        'title': title,
        'department_name': department_name,
    })


