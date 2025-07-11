from django.contrib import admin

from.models import Transport,TransportRequest,BookingHistory,ManagerApproval,Penalty,TransportUsage
from.models import TransportExtension,VehicleRentalCost,FuelRefill,PenaltyPayment

admin.site.register(Transport)
admin.site.register(TransportRequest)
admin.site.register(BookingHistory)
admin.site.register(ManagerApproval)
admin.site.register(Penalty)
admin.site.register(TransportUsage)
admin.site.register(TransportExtension)
admin.site.register(VehicleRentalCost)
admin.site.register(FuelRefill)
admin.site.register(PenaltyPayment)


