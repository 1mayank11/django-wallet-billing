from django.contrib import admin

# Register your models here.

from .models import Wallet, RechargeTransaction, UserProfile


admin.site.register(Wallet)
admin.site.register(RechargeTransaction)
admin.site.register(UserProfile)
