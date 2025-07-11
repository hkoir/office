from django.contrib import admin

from.models import StationaryCategory,StationaryProduct,StationaryBatch,StationaryInventory,StationaryInventoryTransaction
from.models import StationaryPurchaseOrder,StationaryPurchaseItem,MeetingRoomBooking,OfficeAdvance

from.models import MeetingRoom,ExpenseSubmissionItem,ExpenseSubmissionOrder,ITSupportTicket,StationaryUsageRequestOrder

admin.site.register(StationaryProduct)
admin.site.register(StationaryCategory)
admin.site.register(StationaryBatch)
admin.site.register(StationaryInventory)

admin.site.register(StationaryPurchaseOrder)
admin.site.register(StationaryPurchaseItem)
admin.site.register(StationaryInventoryTransaction)
admin.site.register(StationaryUsageRequestOrder)



admin.site.register(MeetingRoomBooking)
admin.site.register(MeetingRoom)
admin.site.register(OfficeAdvance)

admin.site.register(ExpenseSubmissionOrder)
admin.site.register(ExpenseSubmissionItem)

admin.site.register(ITSupportTicket)