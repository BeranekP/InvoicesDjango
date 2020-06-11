from django.contrib import admin

from .models import Invoice, Recipient, UserProfile, InvoiceItem

admin.site.register(UserProfile)
admin.site.register(Invoice)
admin.site.register(Recipient)
admin.site.register(InvoiceItem)
