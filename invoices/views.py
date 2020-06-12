from django.shortcuts import render, redirect
from django.views import View
from django.http import HttpResponse
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.auth.models import User
from invoices.models import Invoice, Recipient, UserProfile, InvoiceItem
from invoices.models import randstring
from django.db.models.functions import ExtractYear
from datetime import datetime, timedelta
from django.contrib.auth import authenticate, login, logout
from django.conf import settings
from qrplatba import QRPlatbaGenerator
from django.utils.safestring import mark_safe
from django.core.files.base import ContentFile


# Create your views here.

class SignupView(View):
    template_name = 'signup/form.html'

    def get(self, request):
        if request.user.is_authenticated:
            return redirect('/invoices')
        return render(request, self.template_name)

    def post(self, request):
        username = request.POST['username']
        password = request.POST['password']
        user = User.objects.create_user(username, '', password)
        user_profile = UserProfile()
        user_profile.user = user
        user_profile.email = request.POST['email']
        user_profile.web = request.POST['web']
        user_profile.name = request.POST['name']
        user_profile.street = request.POST['street']
        user_profile.town = request.POST['town']
        user_profile.zipcode = request.POST['zipcode']
        user_profile.ic = request.POST['ic']
        user_profile.logo = request.FILES['logo']
        user_profile.sign = request.FILES['sign']
        user_profile.rnd_id = randstring(25)
        if request.POST['dic']:
            user_profile.dic = request.POST['dic']
        user_profile.bank = request.POST['bank']

        user_profile.save()
        user.save()
        return redirect('/')


class LoginView(View):
    def post(self, request):
        username = request.POST['username']
        password = request.POST['password']
        user = authenticate(request, username=username, password=password)
        if user is not None:
            login(request, user)
            return redirect('/invoices')
        else:
            return redirect('/')


class LogoutView(View):
    def get(self, request):
        logout(request)
        return redirect('/')


class HomeView(View):
    template_name = 'home/index.html'

    def get(self, request):
        if request.user.is_authenticated:
            return redirect('invoices/')

        profile = None
        context = {'user': request.user, 'profile': profile}
        return render(request, self.template_name, context)


class InvoiceView(LoginRequiredMixin, View):
    template_name = 'invoices/create.html'
    login_url = '/'
    redirect_field_name = 'invoices/create/'

    def get(self, request):
        d = datetime.now()
        dt = timedelta(days=14)
        recipients = Recipient.objects.filter(
            owner=request.user).order_by('name')
        invoices_id = Invoice.objects.filter(
            owner=request.user).values_list('iid', flat=True)
        if invoices_id:
            iid = max(list(invoices_id)) + 1
        else:
            iid = d.year * 10000 + 1
        default_dates = {'created': d, 'due': d + dt}
        context = {'recipients': recipients, 'iid': iid,
                   'user': request.user, 'default_dates': default_dates}
        return render(request, self.template_name, context)

    def post(self, request):

        invoice = Invoice()
        rid = request.POST.get('recipient')
        invoice.recipient = Recipient.objects.filter(
            owner=request.user).get(pk=int(rid))
        invoice.description = request.POST.get('description')
        invoice.amount = request.POST.get('amount')
        invoice.date = request.POST.get('created')
        invoice.datedue = request.POST.get('due')
        invoice.iid = request.POST.get('id')
        invoice.payment = request.POST.get('payment')
        invoice.owner = request.user
        invoice.has_items = request.POST.get('hasItems') == 'on'
        invoice.save()
        if invoice.has_items:

            try:
                i = 0

                while True:
                    items = request.POST.getlist('items' + str(i) + '[]')
                    if items:
                        invoice_item = InvoiceItem()
                        invoice_item.item_name = items[0]
                        invoice_item.num_items = items[1]
                        invoice_item.price_item = items[2]
                        invoice_item.price = items[3]
                        invoice_item.invoice = invoice

                        invoice_item.save()
                        i += 1
                    else:
                        break
            except:
                pass

        return redirect('../')


class InvoiceDetailView(LoginRequiredMixin, View):
    login_url = '/'
    redirect_field_name = 'invoices/'
    template_name = 'invoices/detail.html'

    def get(self, request, id):
        invoice = Invoice.objects.filter(
            owner=request.user).get(id=id)
        if invoice.has_items:
            items = InvoiceItem.objects.filter(invoice=invoice)
        else:
            items = []

        user = UserProfile.objects.get(user=invoice.owner)
        qrpath = '/temp/' + 'QR_Platba.svg'
        generator = QRPlatbaGenerator(user.bank, invoice.amount, x_vs=invoice.iid,
                                      message=f'FAKTURA {invoice.iid}', due_date=invoice.datedue)

        img = generator.make_image()

        img.save(settings.STATICFILES_DIRS[0] + qrpath)

        context = {"invoice": invoice, "user": user,
                   "qr": qrpath, "items": items, "svg": mark_safe(img)}

        return render(request, self.template_name, context)


class InvoiceOverView(LoginRequiredMixin, View):
    template_name = 'invoices/overview.html'
    login_url = '/'
    redirect_field_name = 'invoices/'

    def get(self, request):
        try:
            userprofile = UserProfile.objects.get(user=request.user)
        except:
            userprofile = None

        try:
            logo = userprofile.logo.read()
        except:
            logo = None

        total = 0
        years = []
        try:
            yr = request.GET['yr']
        except:
            yr = datetime.now().year

        if yr and not yr == 'all':
            invoices = Invoice.objects.filter(
                date__year=yr, owner=request.user).order_by('-iid')
        else:
            invoices = Invoice.objects.filter(
                owner=request.user).order_by('-iid')

        dates = Invoice.objects.filter(
            owner=request.user).dates('date', 'year')
        years = [str(date.year) for date in dates]
        for invoice in invoices:
            total += invoice.amount
        context = {'invoices': invoices,
                   'user': request.user,
                   'profile': userprofile,
                   'logo': logo,
                   'total': total,
                   'years': sorted(list(set(years)), reverse=True),
                   'selected_year': str(yr)}
        return render(request, self.template_name, context)


class InvoiceDeleteView(LoginRequiredMixin, View):
    login_url = '/'
    redirect_field_name = 'invoices/'

    def post(self, request, id):
        invoice = Invoice.objects.filter(
            owner=request.user).get(id=id)
        invoice.delete()
        return redirect('../../')


class InvoiceUpdateView(LoginRequiredMixin, View):
    login_url = '/'
    redirect_field_name = 'invoices/'

    def get(self, request, id):
        invoice = Invoice.objects.filter(
            owner=request.user).get(id=id)
        if invoice.has_items:
            items = InvoiceItem.objects.filter(invoice=invoice)
        else:
            items = []
        context = {'invoice': invoice, "items": items}
        return render(request, 'invoices/update.html', context)

    def post(self, request, id):
        invoice = Invoice.objects.filter(
            owner=request.user).get(id=id)
        invoice.description = request.POST.get('description')
        invoice.amount = request.POST.get('amount')
        invoice.date = request.POST.get('created')
        invoice.datedue = request.POST.get('due')
        invoice.iid = request.POST.get('id')
        invoice.payment = request.POST.get('payment')
        invoice.owner = request.user
        invoice.has_items = request.POST.get('hasItems') == 'on'
        invoice.save()
        if invoice.has_items:
            try:
                items_db = InvoiceItem.objects.filter(invoice=invoice)
            except:
                items_db = []
            try:
                i = 0
                #print('ITEMS', i)
                while True:
                    # print('ITEMS')

                    items_post = request.POST.getlist('items' + str(i) + '[]')
                    print('items' + str(i) + '[]', items_post)
                    if items_post:
                        if i <= len(items_db)-1:
                            items_db[i].item_name = items_post[0]
                            items_db[i].num_items = items_post[1]
                            items_db[i].price_item = items_post[2]
                            items_db[i].price = items_post[3]
                            items_db[i].save()
                        else:
                            invoice_item = InvoiceItem()
                            invoice_item.item_name = items_post[0]
                            invoice_item.num_items = items_post[1]
                            invoice_item.price_item = items_post[2]
                            invoice_item.price = items_post[3]
                            invoice_item.invoice = invoice

                            invoice_item.save()
                        i += 1
                    else:
                        break
            except:
                pass

        return redirect('../../')


class RecipientView(LoginRequiredMixin, View):
    template_name = 'recipient/create.html'
    login_url = '/'
    redirect_field_name = 'invoices/'

    def get(self, request):
        context = {}
        return render(request, self.template_name, context)

    def post(self, request):

        recipient = Recipient()
        recipient.name = request.POST.get('name')
        recipient.street = request.POST.get('street')
        recipient.town = request.POST.get('town')
        recipient.zipcode = request.POST.get('zipcode')
        if request.POST.get('ic'):
            recipient.ic = request.POST.get('ic')
        if request.POST.get('dic'):
            recipient.dic = request.POST.get('dic')
        recipient.owner = request.user
        recipient.save()

        return redirect('../../invoices/create/')


class UserProfileUpdateView(LoginRequiredMixin, View):
    login_url = '/'
    redirect_field_name = 'invoices/'
    template_name = 'user/profile.html'

    def get(self, request, id):
        profile = UserProfile.objects.get(id=id)
        context = {'profile': profile,
                   'user': request.user}
        print(settings.AUTH_USER_MODEL)
        return render(request, self.template_name, context)

    def post(self, request, id):
        user_profile = UserProfile.objects.get(id=id)
        user_profile.email = request.POST['email']
        user_profile.web = request.POST['web']
        user_profile.name = request.POST['name']
        user_profile.street = request.POST['street']
        user_profile.town = request.POST['town']
        user_profile.zipcode = request.POST['zipcode']
        user_profile.ic = request.POST['ic']
        if request.POST['dic']:
            user_profile.dic = request.POST['dic']
        user_profile.bank = request.POST['bank']
        try:
            user_profile.logo = request.FILES['logo']
        except:
            pass
        try:
            user_profile.sign = request.FILES['sign']
        except:
            pass
        user_profile.save()

        return redirect('../../../invoices')
