from django.db import models
from django.db.models import F,Q,Sum,Case, When
from django.db import transaction
from django.core.exceptions import ObjectDoesNotExist

from django.contrib.auth.models import User

import logging
logger = logging.getLogger(__name__)
from django import forms

from product.models import Product,Category
from core.models import Employee
from finance.models import PurchaseInvoice,SaleInvoice
from logistics.models import PurchaseShipment,SaleShipment
from repairreturn.models import Replacement,ReturnOrRefund,FaultyProduct  
from manufacture.models import MaterialsRequestOrder
from operations.models import OperationsRequestOrder,ExistingOrder
from purchase.models import PurchaseOrder, PurchaseRequestOrder
from inventory.models import InventoryTransaction,Warehouse,TransferOrder
from sales.models import SaleOrder,SaleRequestOrder
from reporting.models import Notification




def create_notification(user,notification_type, message):   
    Notification.objects.create(user=user, message=message,notification_type=notification_type)
    

def mark_notification_as_read(notification_id):
    try:
        notification = Notification.objects.get(id=notification_id)
        notification.is_read = True
        notification.save()
    except Notification.DoesNotExist:
        pass  




# for purchase update ######################################################################
def update_purchase_order(purchase_order_id):
    try:
        with transaction.atomic():
            purchase_order = PurchaseOrder.objects.get(id=purchase_order_id)         
            print(f"Updating Purchase Order ID: {purchase_order_id}")
            
            shipments = purchase_order.purchase_shipment.all()
            
            if shipments.exists(): 
                all_shipments_delivered = (
                    shipments.filter(status__in=['DELIVERED','REACHED','OBI']).count()
                    == shipments.count()
                )
                if all_shipments_delivered:
                    print("All shipments delivered. Updating status to DELIVERED.")
                    purchase_order.status = 'DELIVERED'
                    purchase_order.save()
                else:
                    print("Not all shipments delivered. Status remains unchanged.")
            else:
                print("No shipments found for this purchase order. Status remains unchanged.")
    except Exception as e:
        print(f"Error updating purchase order {purchase_order_id}: {e}")



def update_purchase_request_order(request_order_id):
    try:
        with transaction.atomic():
            request_order = PurchaseRequestOrder.objects.get(id=request_order_id)
            total_requested_product = request_order.purchase_request_order.aggregate(total_requested_product=Sum('quantity'))['total_requested_product'] or 0

            total_dispatch_quantity = 0

            for purchase_order in request_order.purchase_order_request_order.all():
                for shipment in purchase_order.purchase_shipment.all():
                    dispatch_sum = shipment.shipment_dispatch_item.aggregate(total_dispatch=Sum('dispatch_quantity'))['total_dispatch'] or 0
                    total_dispatch_quantity += dispatch_sum

            if total_dispatch_quantity == total_requested_product:
                request_order.status = 'DELIVERED'
            elif 0 < total_dispatch_quantity < total_requested_product:
                request_order.status = 'PARTIAL_DELIVERED'
            elif total_dispatch_quantity == 0:
                request_order.status = 'IN_PROCESS'

            request_order.save()

    except Exception as e:
        print(f"Error updating sale request order: {e}")
       
    


def update_shipment_status(shipment_id):
    try:
        shipment = PurchaseShipment.objects.get(id=shipment_id)
        all_items_delivered = shipment.shipment_dispatch_item.filter(status='DELIVERED').count() == shipment.shipment_dispatch_item.count()
        if all_items_delivered:
            shipment.status = 'DELIVERED'
            shipment.save()
            logger.info(f"Shipment {shipment_id} marked as DELIVERED.")
    except PurchaseShipment.DoesNotExist:
        logger.error(f"Shipment {shipment_id} not found.")



# for sale update ########################################################################

def update_sale_order(sale_order_id):
    sale_order = SaleOrder.objects.get(id=sale_order_id)
    all_shipments_delivered = sale_order.sale_shipment.filter(status='DELIVERED').count() == sale_order.sale_shipment.count()
    if all_shipments_delivered:
        sale_order.status = 'DELIVERED'       
        sale_order.save()      



def update_sale_request_order(request_order_id):
    try:
        with transaction.atomic():
            request_order = SaleRequestOrder.objects.get(id=request_order_id)
            total_requested_product = request_order.sale_request_order.aggregate(total_requested_product=Sum('quantity'))['total_requested_product'] or 0

            total_dispatch_quantity = 0
            for sale_order in request_order.sale_request.all():
                for shipment in sale_order.sale_shipment.all():
                    dispatch_sum = shipment.sale_shipment_dispatch.aggregate(total_dispatch=Sum('dispatch_quantity'))['total_dispatch'] or 0
                    total_dispatch_quantity += dispatch_sum

            if total_dispatch_quantity == total_requested_product:
                request_order.status = 'DELIVERED'
            elif 0 < total_dispatch_quantity < total_requested_product:
                request_order.status = 'PARTIAL_DELIVERED'
            elif total_dispatch_quantity == 0:
                request_order.status = 'IN_PROCESS'

            request_order.save()
            
    except Exception as e:
        print(f"Error updating sale request order: {e}")

    

def update_sale_shipment_status(shipment_id):
    shipment = SaleShipment.objects.get(id=shipment_id)
    all_items_delivered = shipment.sale_shipment_dispatch.filter(status__in=['DELIVERED','REACHED','OBI']).count() == shipment.sale_shipment_dispatch.count()
    if all_items_delivered:
        shipment.status = 'DELIVERED'
        shipment.save()


############################################################################


def assign_roles(order, requester, reviewer, approver):
    order.requester = requester
    order.reviewer = reviewer
    order.approver = approver
    order.save()  




def get_warehouse_stock(warehouse, product):
    transactions = InventoryTransaction.objects.filter(
        warehouse=warehouse, product=product
    ).values('transaction_type').annotate(total=Sum('quantity'))

    inbound = sum(t['total'] for t in transactions if t['transaction_type'] in ['INBOUND', 'TRANSFER_IN','MANUFACTURE_IN','REPLACEMENT_IN','EXISTING_ITEM_IN'])
    outbound = sum(t['total'] for t in transactions if t['transaction_type'] in ['OUTBOUND', 'TRANSFER_OUT','REPLACEMENT_OUT','OPERATIONS_OUT','MANUFACTURE_OUT'])

    return inbound - outbound



def calculate_stock_value(product, warehouse): 
    total_purchase = InventoryTransaction.objects.filter(
        product=product,
        warehouse=warehouse, 
        transaction_type='INBOUND',
        purchase_order__isnull=False
    ).aggregate(total=Sum('quantity'))['total'] or 0

    total_manufacture_in = InventoryTransaction.objects.filter(
        product=product,
        warehouse=warehouse,  
        transaction_type='MANUFACTURE_IN',
        manufacture_order__isnull=False
    ).aggregate(total=Sum('quantity'))['total'] or 0

    total_manufacture_out = InventoryTransaction.objects.filter(
        product=product,
        warehouse=warehouse,  
        transaction_type='MANUFACTURE_OUT',
        manufacture_order__isnull=False
    ).aggregate(total=Sum('quantity'))['total'] or 0

    total_sold = InventoryTransaction.objects.filter(
        product=product,
        warehouse=warehouse,  
        transaction_type='OUTBOUND',
        sales_order__isnull=False
    ).exclude(
        Q(remarks__icontains='transfer') |
        Q(remarks__icontains='replacement')
    ).aggregate(total=Sum('quantity'))['total'] or 0


    total_replacement_out = InventoryTransaction.objects.filter(
        product=product,
        warehouse=warehouse,  
        transaction_type='REPLACEMENT_OUT',  
    ).aggregate(total=Sum('quantity'))['total'] or 0

    total_replacement_in = InventoryTransaction.objects.filter(
        product=product,
        warehouse=warehouse,  
        transaction_type='REPLACEMENT_IN',  
    ).aggregate(total=Sum('quantity'))['total'] or 0

    total_transfer_in = InventoryTransaction.objects.filter(
        product=product,
        warehouse=warehouse,
        transaction_type='TRANSFER_IN',  
    ).aggregate(total=Sum('quantity'))['total'] or 0


    total_transfer_out = InventoryTransaction.objects.filter(
        product=product,
        warehouse=warehouse,
        transaction_type='TRANSFER_OUT', 
    ).aggregate(total=Sum('quantity'))['total'] or 0

    total_Existing_in = InventoryTransaction.objects.filter(
        product=product,
        warehouse=warehouse,
        transaction_type='EXISTING_ITEM_IN', 
    ).aggregate(total=Sum('quantity'))['total'] or 0
    total_operations_out = InventoryTransaction.objects.filter(
        product=product,
        warehouse=warehouse,
        transaction_type='OPERATIONS_OUT', 
    ).aggregate(total=Sum('quantity'))['total'] or 0

    total_scrapped_out = InventoryTransaction.objects.filter(
        product=product,
        warehouse=warehouse,
        transaction_type='SCRAPPED_OUT', 
    ).aggregate(total=Sum('quantity'))['total'] or 0

    total_scrapped_in = InventoryTransaction.objects.filter(
        product=product,
        warehouse=warehouse,
        transaction_type='SCRAPPED_IN', 
    ).aggregate(total=Sum('quantity'))['total'] or 0




    total_available = (
        total_purchase + total_manufacture_in + total_transfer_in + total_Existing_in + total_scrapped_in
        - (total_sold + total_transfer_out + total_replacement_out + total_operations_out + total_manufacture_out + total_scrapped_out)
    )   
    total_stock = total_purchase + total_manufacture_in + total_transfer_in + total_Existing_in
    
    if total_available < 0:
        logger.warning(f"Negative stock detected for {product.name} in {warehouse.name}.")
        total_available = 0 

    return {
        'total_purchase': total_purchase,
        'total_manufacture_in': total_manufacture_in,
        'total_manufacture_out': total_manufacture_out,
        'total_existing_in': total_Existing_in,
        'total_operations_out': total_operations_out,
        'total_sold': total_sold,
        'total_replacement_in': total_replacement_in,
        'total_replacement_out': total_replacement_out,
        'total_transfer_in': total_transfer_in,
        'total_transfer_out': total_transfer_out,
        'total_scrapped_in': total_scrapped_in,
        'total_scrapped_out': total_scrapped_out,
        'total_available': total_available,
        'total_stock':total_stock
    }




def calculate_stock_value2(product, warehouse=None): 
    filters = {'product': product}
    if warehouse:
        if isinstance(warehouse, Warehouse):  
            filters['warehouse'] = warehouse
        else:
            logger.error("Invalid warehouse instance provided.")
            raise ValueError("Invalid warehouse instance provided.")


    total_purchase = InventoryTransaction.objects.filter(
        transaction_type='INBOUND',
        purchase_order__isnull=False,
        **filters
    ).aggregate(total=Sum('quantity'))['total'] or 0

    total_manufacture_in = InventoryTransaction.objects.filter(
        transaction_type='MANUFACTURE_IN',
        manufacture_order__isnull=False,
        **filters
    ).aggregate(total=Sum('quantity'))['total'] or 0

    total_manufacture_out = InventoryTransaction.objects.filter(
        transaction_type='MANUFACTURE_OUT',
        manufacture_order__isnull=False,
        **filters
    ).aggregate(total=Sum('quantity'))['total'] or 0

    total_sold = InventoryTransaction.objects.filter(
        transaction_type='OUTBOUND',
        sales_order__isnull=False,
        **filters
    ).exclude(
        Q(remarks__icontains='transfer') |
        Q(remarks__icontains='replacement')
    ).aggregate(total=Sum('quantity'))['total'] or 0

    total_replacement_out = InventoryTransaction.objects.filter(
        transaction_type='REPLACEMENT_OUT',
        **filters
    ).aggregate(total=Sum('quantity'))['total'] or 0

    total_replacement_in = InventoryTransaction.objects.filter(
        transaction_type='REPLACEMENT_IN',
        **filters
    ).aggregate(total=Sum('quantity'))['total'] or 0

    total_transfer_in = InventoryTransaction.objects.filter(
        transaction_type='TRANSFER_IN',
        **filters
    ).aggregate(total=Sum('quantity'))['total'] or 0

    total_transfer_out = InventoryTransaction.objects.filter(
        transaction_type='TRANSFER_OUT',
        **filters
    ).aggregate(total=Sum('quantity'))['total'] or 0

    total_existing_in = InventoryTransaction.objects.filter(
        transaction_type='EXISTING_ITEM_IN',
        **filters
    ).aggregate(total=Sum('quantity'))['total'] or 0

    total_operations_out = InventoryTransaction.objects.filter(
        transaction_type='OPERATIONS_OUT',
        **filters
    ).aggregate(total=Sum('quantity'))['total'] or 0

    
    total_scrapped_out = InventoryTransaction.objects.filter(
        transaction_type='SCRAPPED_OUT',
        **filters
    ).aggregate(total=Sum('quantity'))['total'] or 0

    total_scrapped_in = InventoryTransaction.objects.filter(
        transaction_type='SCRAPPED_IN',
        **filters
    ).aggregate(total=Sum('quantity'))['total'] or 0

      

  

    total_available = (
        total_purchase + total_manufacture_in + total_transfer_in + total_existing_in + total_scrapped_in
        - (total_sold + total_transfer_out + total_replacement_out + total_operations_out + total_manufacture_out + total_scrapped_out)
    )

    total_stock = total_purchase + total_manufacture_in + total_transfer_in + total_existing_in
    
    if total_available < 0:
        logger.warning(
            f"Negative stock detected for {product.name} in "
            f"{warehouse.name if warehouse else 'all warehouses'}"
        )
        total_available = 0

    return {
        'total_purchase': total_purchase,
        'total_manufacture_in': total_manufacture_in,
        'total_manufacture_out': total_manufacture_out,
        'total_existing_in': total_existing_in,
        'total_operations_out': total_operations_out,
        'total_sold': total_sold,
        'total_replacement_out': total_replacement_out,
        'total_replacement_in': total_replacement_in,
        'total_transfer_in': total_transfer_in,
        'total_transfer_out': total_transfer_out,
        'total_scrapped_in': total_scrapped_in,
        'total_scrapped_out': total_scrapped_out,
        'total_available': total_available,
        'total_stock': total_stock
    }

def calculate_batch_stock_value(product, warehouse, valuation_method="FIFO"):
    total_purchase = InventoryTransaction.objects.filter(
        product=product,
        warehouse=warehouse, 
        transaction_type='INBOUND',
        purchase_order__isnull=False
    ).aggregate(total=Sum('quantity'))['total'] or 0

    total_manufacture_in = InventoryTransaction.objects.filter(
        product=product,
        warehouse=warehouse,  
        transaction_type='MANUFACTURE_IN',
        manufacture_order__isnull=False
    ).aggregate(total=Sum('quantity'))['total'] or 0

    total_manufacture_out = InventoryTransaction.objects.filter(
        product=product,
        warehouse=warehouse,  
        transaction_type='MANUFACTURE_OUT',
        manufacture_order__isnull=False
    ).aggregate(total=Sum('quantity'))['total'] or 0

    total_sold = InventoryTransaction.objects.filter(
        product=product,
        warehouse=warehouse,  
        transaction_type='OUTBOUND',
        sales_order__isnull=False
    ).exclude(
        Q(remarks__icontains='transfer') |
        Q(remarks__icontains='replacement')
    ).aggregate(total=Sum('quantity'))['total'] or 0


    total_replacement_out = InventoryTransaction.objects.filter(
        product=product,
        warehouse=warehouse,  
        transaction_type='REPLACEMENT_OUT',  
    ).aggregate(total=Sum('quantity'))['total'] or 0

    total_replacement_in = InventoryTransaction.objects.filter(
        product=product,
        warehouse=warehouse,  
        transaction_type='REPLACEMENT_IN',  
    ).aggregate(total=Sum('quantity'))['total'] or 0

    total_transfer_in = InventoryTransaction.objects.filter(
        product=product,
        warehouse=warehouse,
        transaction_type='TRANSFER_IN',  
    ).aggregate(total=Sum('quantity'))['total'] or 0


    total_transfer_out = InventoryTransaction.objects.filter(
        product=product,
        warehouse=warehouse,
        transaction_type='TRANSFER_OUT', 
    ).aggregate(total=Sum('quantity'))['total'] or 0

    total_Existing_in = InventoryTransaction.objects.filter(
        product=product,
        warehouse=warehouse,
        transaction_type='EXISTING_ITEM_IN', 
    ).aggregate(total=Sum('quantity'))['total'] or 0
    total_operations_out = InventoryTransaction.objects.filter(
        product=product,
        warehouse=warehouse,
        transaction_type='OPERATIONS_OUT', 
    ).aggregate(total=Sum('quantity'))['total'] or 0

    total_scrapped_out = InventoryTransaction.objects.filter(
        product=product,
        warehouse=warehouse,
        transaction_type='SCRAPPED_OUT', 
    ).aggregate(total=Sum('quantity'))['total'] or 0

    total_scrapped_in = InventoryTransaction.objects.filter(
        product=product,
        warehouse=warehouse,
        transaction_type='SCRAPPED_IN', 
    ).aggregate(total=Sum('quantity'))['total'] or 0




    total_available = (
        total_purchase + total_manufacture_in + total_transfer_in + total_Existing_in + total_scrapped_in
        - (total_sold + total_transfer_out + total_replacement_out + total_operations_out + total_manufacture_out + total_scrapped_out)
    )   
    total_stock =  total_purchase + total_manufacture_in + total_transfer_in + total_Existing_in + total_scrapped_in

    order_by = "created_at" if valuation_method == "FIFO" else "-created_at"
    latest_transaction = InventoryTransaction.objects.filter(
        product=product,
        warehouse=warehouse,
        transaction_type='INBOUND'
    ).select_related("batch").order_by(order_by).first()

    unit_cost = latest_transaction.batch.unit_price if latest_transaction and latest_transaction.batch  is not None else 0
    stock_value = total_available * unit_cost          

    return {
        'total_purchase': total_purchase,
        'total_manufacture_in': total_manufacture_in,
        'total_manufacture_out': total_manufacture_out,
        'total_existing_in': total_Existing_in,
        'total_operations_out': total_operations_out,
        'total_sold': total_sold,
        'total_replacement_out': total_replacement_out,
        'total_replacement_in': total_replacement_in,
        'total_transfer_in': total_transfer_in,
        'total_transfer_out': total_transfer_out,
        'total_scrapped_in': total_scrapped_in,
        'total_scrapped_out': total_scrapped_out,
        'total_available': total_available,
        'total_stock': total_stock,
        'stock_value': stock_value
    }



######################### Performance evaluation service ######################

from tasks.models import PerformanceEvaluation

def calculate_total_performance(employee):
    evaluations = PerformanceEvaluation.objects.filter(employee=employee)
    total_score = sum(evaluation.score for evaluation in evaluations)
    max_score = evaluations.count() * 100  # Assuming each task is scored out of 100
    return (total_score / max_score) * 100 if max_score > 0 else 0



def calculate_task_score(task):
    """
    Calculate the score for a given task.
    Example scoring logic:
    - Timely completion: 70% weight
    - Quality of work: 20% weight
    - Collaboration: 10% weight
    """
    timely_score = 70 if task.due_date >= task.assigned_date else 40  # Adjust based on timeliness
    quality_score = 20  # Placeholder; you can customize this based on task quality
    collaboration_score = 10  # Placeholder; you can customize this based on team input
    
    return timely_score + quality_score + collaboration_score



def distribute_team_score(task):
    if task.assigned_to_team:
        team_members = task.assigned_to_team.members.all()
        individual_score = task.score / team_members.count()

        for member in team_members:
            PerformanceEvaluation.objects.create(
                employee=member,
                task=task,
                task_score=individual_score,
                remarks=f"Team task: {task.title}"
            )







