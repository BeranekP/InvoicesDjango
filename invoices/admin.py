from django.contrib import admin

from .models import Invoice, Recipient, UserProfile, InvoiceItem, Advance

admin.site.register(UserProfile)
admin.site.register(Invoice)
admin.site.register(Recipient)
admin.site.register(InvoiceItem)
admin.site.register(Advance)
