from django.contrib import admin

from .models import CustomUser,UserProfile,AllowedEmailDomain,PhoneOTP


admin.site.register(UserProfile)
admin.site.register(AllowedEmailDomain)
admin.site.register(PhoneOTP)


class CustomUserAdmin(admin.ModelAdmin):
    list_display = ("username", "user_department", "user_position")

admin.site.register(CustomUser, CustomUserAdmin)
