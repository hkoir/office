from django.shortcuts import render,redirect,get_object_or_404
from django.contrib.auth.decorators import login_required
from logistics.models import PurchaseShipment,SaleShipment
from.models import PurchaseShipmentTracking,SaleShipmentTracking



@login_required
def update_shipment_tracking(request, shipment_id):
    shipment = get_object_or_404(PurchaseShipment, id=shipment_id)
    status_options = ['PENDING','IN_PROCESS','READY_FOR_QC','DISPATCHED','ON_BOARD','IN_TRANSIT','CUSTOM_CLEARANCE_IN_PROCESS', 'REACHED','OBI', 'DELIVERED', 'PARTIAL_DELIVERED', 'CANCELLED']

    if request.method == 'POST':
        status_update = request.POST.get('status_update')
        remarks = request.POST.get('remarks')

        PurchaseShipmentTracking.objects.create(
            purchase_shipment=shipment,
            user=request.user,
            status_update=status_update,
            remarks=remarks
        )
        return redirect('logistics:purchase_shipment_detail', shipment_id=shipment.id)
    return render(request, 'shipment/purchase/update_shipment_tracking.html', {
        'shipment': shipment,
        'status_options':status_options
    })



############################################# for sale ##########################

@login_required
def update_sale_shipment_tracking(request, shipment_id):
    shipment = get_object_or_404(SaleShipment, id=shipment_id)
    status_options = ['PENDING','IN_PROCESS','READY_FOR_QC','DISPATCHED','ON_BOARD','IN_TRANSIT','CUSTOM_CLEARANCE_IN_PROCESS', 'REACHED','OBI', 'DELIVERED', 'PARTIAL_DELIVERED', 'CANCELLED']

    if request.method == 'POST':
        status_update = request.POST.get('status_update')
        remarks = request.POST.get('remarks')

        SaleShipmentTracking.objects.create(
            sale_shipment=shipment,
            user=request.user,
            status_update=status_update, 
            remarks=remarks
        )
        shipment.status = status_update
        shipment.save()

        return redirect('logistics:sale_shipment_detail', shipment_id=shipment.id)

    return render(request, 'shipment/sales/update_shipment_tracking.html', {
        'shipment': shipment,
        'status_options':status_options
    })




