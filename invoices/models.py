from django.db import models
from datetime import datetime
from django.contrib.auth.models import User
from django.conf import settings
from django.db.models.signals import post_save
import os


def get_path(instance, filename):
    path = settings.STATICFILES_DIRS[0] + \
        f'/logo/{instance.user.username}/{instance.user.username}_logo.svg'
    if os.path.exists:
        os.remove(path)
    return path


class UserProfile(models.Model):
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL, editable=False, on_delete=models.CASCADE)
    name = models.CharField(max_length=120, default='')
    street = models.CharField(max_length=120, default='')
    town = models.CharField(max_length=120, default='')
    zipcode = models.IntegerField(default=00000)
    ic = models.CharField(max_length=20, default=None, null=True, unique=True)
    dic = models.CharField(max_length=20, default=None, null=True, blank=True)
    email = models.EmailField(
        default=None, null=True, unique=True, blank=True)
    web = models.URLField(max_length=250,
                          default=None, null=True, unique=True, blank=True)
    bank = models.CharField(max_length=120, default='')
    logo = models.ImageField(
        upload_to=get_path, blank=True, null=True)

    def __str__(self):
        return ', '.join([self.name, self.user.username, self.email])


class Recipient(models.Model):
    name = models.CharField(max_length=120, default='')
    street = models.CharField(max_length=120, default='')
    town = models.CharField(max_length=120, default='')
    zipcode = models.IntegerField(default=00000)
    ic = models.CharField(max_length=20, default=None,
                          null=True, unique=True, blank=True)
    dic = models.CharField(max_length=20, default=None,
                           null=True, unique=True, blank=True)
    owner = models.ForeignKey(
        User, on_delete=models.CASCADE, null=True, blank=True)

    def __str__(self):
        return ', '.join([self.name, self.street, self.town, str(self.zipcode)])


class Invoice(models.Model):
    recipient = models.ForeignKey(Recipient, on_delete=models.CASCADE)
    description = models.TextField(max_length=1000, default='')
    amount = models.IntegerField(default=0)
    date = models.DateField(default=datetime.now, blank=True)
    datedue = models.DateField(default=datetime.now, blank=True)
    iid = models.IntegerField(default=0, null=True, blank=True)
    payment = models.CharField(max_length=25, default='bankovním převodem')
    owner = models.ForeignKey(
        User, on_delete=models.CASCADE, null=True, blank=True)
    has_items = models.BooleanField(default=False, null=True)

    def __str__(self):
        return ', '.join([str(self.iid), self.recipient.name, str(self.amount), 'CZK'])


class InvoiceItem(models.Model):
    invoice = models.ForeignKey(Invoice, on_delete=models.CASCADE)
    item_name = models.CharField(max_length=50, default='')
    num_items = models.IntegerField(default=0)
    price_item = models.FloatField(default=0)
    price = models.FloatField(default=0)

    def __str__(self):
        return ', '.join([self.item_name, str(self.price), str(self.invoice.iid)])
