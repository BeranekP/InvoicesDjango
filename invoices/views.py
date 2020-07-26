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
from django.views.decorators.http import require_GET
import os
from io import BytesIO
from invoices.exchange_cnb import get_exchange_rates


# Create your views here.
@require_GET
def robots(request):
    lines = [
        "User-Agent: *",
        "Disallow: /static/",
    ]
    return HttpResponse("\n".join(lines), content_type="text/plain")


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
        rates = get_exchange_rates(d.strftime('%d.%m.%Y'))
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
                   'user': request.user, 'default_dates': default_dates, 'rates': ['CZK', *rates.keys()]}
        return render(request, self.template_name, context)

    def post(self, request):

        invoice = Invoice()
        rid = request.POST.get('recipient')
        invoice.recipient = Recipient.objects.filter(
            owner=request.user).get(pk=int(rid))
        invoice.description = request.POST.get('description')
        invoice.amount = request.POST.get('amount')
        currency = request.POST.get('currency')

        invoice.date = request.POST.get('created')
        d = datetime.strptime(invoice.date, '%Y-%m-%d')
        invoice.currency = request.POST.get('currency')
        if invoice.currency != 'CZK':
            invoice.exchange_rate = get_exchange_rates(
                d.strftime('%d.%m.%Y'))[invoice.currency]
        else:
            invoice.exchange_rate = 1
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

        generator = QRPlatbaGenerator(user.bank, invoice.amount, x_vs=invoice.iid, currency=invoice.currency,
                                      message=f'FAKTURA {invoice.iid}', due_date=invoice.datedue)
        iban = generator._account[4:-1]
        img = generator.make_image()

        svg_output = BytesIO()
        img.save(svg_output)

        context = {"invoice": invoice, "user": user,
                   "items": items, 'iban': iban, "svg": mark_safe(svg_output.getvalue().decode())}

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
            total += invoice.amount * invoice.exchange_rate

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

        #d = datetime.strptime(invoice.date, '%Y-%m-%d')
        rates = get_exchange_rates(invoice.date.strftime('%d.%m.%Y'))
        context = {'invoice': invoice, "items": items,
                   'rates': ['CZK', *rates.keys()]}
        return render(request, 'invoices/update.html', context)

    def post(self, request, id):
        invoice = Invoice.objects.filter(
            owner=request.user).get(id=id)
        invoice.description = request.POST.get('description')
        invoice.amount = request.POST.get('amount')
        invoice.date = request.POST.get('created')
        invoice.datedue = request.POST.get('due')
        d = datetime.strptime(invoice.date, '%Y-%m-%d')
        invoice.currency = request.POST.get('currency')
        if invoice.currency != 'CZK':
            invoice.exchange_rate = get_exchange_rates(
                d.strftime('%d.%m.%Y'))[invoice.currency]
        else:
            invoice.exchange_rate = 1
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
        recipient.state = request.POST['state']
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
        profile = UserProfile.objects.get(id=id, user=request.user)
        context = {'profile': profile,
                   'user': request.user}

        return render(request, self.template_name, context)

    def post(self, request, id):
        user_profile = UserProfile.objects.get(id=id, user=request.user)
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


class RecipientOverView(LoginRequiredMixin, View):
    template_name = 'recipient/overview.html'
    login_url = '/'
    redirect_field_name = 'recipient/'

    def get(self, request):
        try:
            userprofile = UserProfile.objects.get(user=request.user)
        except:
            userprofile = None

        try:
            logo = userprofile.logo.read()
        except:
            logo = None

        recipients = Recipient.objects.filter(
            owner=request.user).order_by('name')

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

        for recipient in recipients:
            if yr and not yr == 'all':
                invoices = Invoice.objects.filter(
                    date__year=yr, owner=request.user, recipient=recipient).order_by('iid')
            else:
                invoices = Invoice.objects.filter(
                    owner=request.user, recipient=recipient).order_by('iid')

            total = 0
            for invoice in invoices:
                total += invoice.amount
            recipient.invoices = invoices
            recipient.total = total

        context = {'user': request.user,
                   'profile': userprofile,
                   'logo': logo,
                   'recipients': recipients,
                   'years': sorted(list(set(years)), reverse=True),
                   'selected_year': str(yr)
                   }
        return render(request, self.template_name, context)


class RecipientUpdateView(LoginRequiredMixin, View):
    template_name = 'recipient/update.html'
    login_url = '/'
    redirect_field_name = 'recipient/'

    def get(self, request, id):
        recipient = Recipient.objects.get(id=id, owner=request.user)
        context = {'recipient': recipient,
                   'user': request.user}

        return render(request, self.template_name, context)

    def post(self, request, id):
        recipient = Recipient.objects.get(id=id, owner=request.user)
        recipient.name = request.POST['name']
        recipient.street = request.POST['street']
        recipient.town = request.POST['town']
        recipient.zipcode = request.POST['zipcode']
        recipient.state = request.POST['state']
        recipient.ic = request.POST['ic']
        if request.POST['dic']:
            recipient.dic = request.POST['dic']
        if request.POST['ic']:
            recipient.ic = request.POST['ic']

        recipient.save()

        return redirect('/recipient')
