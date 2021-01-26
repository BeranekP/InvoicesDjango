from invoices.ares import ARES
import json
from django.shortcuts import render, redirect
from django.views import View
from django.http import HttpResponse
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.auth.models import User
from invoices.models import Invoice, Recipient, UserProfile, InvoiceItem, Advance
from invoices.models import randstring
from django.db.models.functions import ExtractYear
from datetime import datetime, timedelta
from django.contrib.auth import authenticate, login, logout
from django.conf import settings
from qrplatba import QRPlatbaGenerator
from django.utils.safestring import mark_safe
from django.core.files.base import ContentFile
from django.views.decorators.http import require_GET
from django.template.loader import get_template
from django.contrib.staticfiles import finders
from xhtml2pdf import pisa
import os
from io import BytesIO
from invoices.exchange_cnb import get_exchange_rates
from svglib.svglib import svg2rlg
from reportlab.graphics import renderPM
from sendgrid import SendGridAPIClient
from sendgrid.helpers.mail import (
    Mail, Bcc, Attachment, FileContent, FileName, FileType, Disposition, ContentId)
import base64
from django.contrib import messages
from protected import SENDGRID_API_KEY, EMAIL  # ,OTHER_EMAIL


# serve robots.txt
@require_GET
def robots(request):
    lines = [
        "User-Agent: *",
        "Disallow: /static/",
    ]
    return HttpResponse("\n".join(lines), content_type="text/plain")


class SignupView(LoginRequiredMixin, View):
    template_name = 'signup/form.html'
    login_url = '/'
    redirect_field_name = ''

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
            return redirect('/dash')
        else:
            messages.error(request, 'Neplatné uživatelské jméno nebo heslo.')
            return redirect('/')


class LogoutView(View):
    def get(self, request):
        logout(request)
        return redirect('/')


class HomeView(View):
    template_name = 'home/index.html'

    def get(self, request):
        if request.user.is_authenticated:
            return redirect('dash/')

        profile = None
        context = {'user': request.user, 'profile': profile}
        return render(request, self.template_name, context)


class DashView(LoginRequiredMixin, View):
    template_name = 'dash/dash.html'
    login_url = '/'
    redirect_field_name = ''

    def get(self, request):
        try:
            userprofile = UserProfile.objects.get(user=request.user)
        except:
            userprofile = None

        try:
            logo = userprofile.logo.read()
        except:
            logo = None

        data = Invoice.objects.filter(
            owner=request.user).order_by('-iid')
        invoices = Invoice.objects.filter(
            owner=request.user).order_by('iid')
        graph_data = dict()
        for invoice in invoices:
            graph_data.setdefault(invoice.date.year, {
                                  'labels': list(range(1, 13)),
                                  'amount': ['null' for _ in range(1, 13)],
                                  'total': ['null' for _ in range(1, 13)],
                                  })
            idx = graph_data[invoice.date.year]['labels'].index(
                int(invoice.date.strftime("%m")))
            if graph_data[invoice.date.year]['amount'][idx] != 'null':
                graph_data[invoice.date.year]['amount'][idx] += invoice.amount * invoice.exchange_rate['rate'] / \
                    invoice.exchange_rate['amount']
            else:
                graph_data[invoice.date.year]['amount'][idx] = invoice.amount * invoice.exchange_rate['rate'] / \
                    invoice.exchange_rate['amount']

        for year in graph_data:
            running_total = 0
            for i, val in enumerate(graph_data[year]['amount']):
                if val != 'null':
                    running_total += val
                graph_data[year]['total'][i] = running_total

        if datetime.now().year == year:
            total = graph_data[year]['total'][-1]
        else:
            total = 0
        context = {"data": data, "logo": logo,
                   "profile": userprofile, "total": total if total != 'null' else 0, "graphdata": graph_data}
        return render(request, self.template_name, context)


class InvoiceView(LoginRequiredMixin, View):
    template_name = 'invoices/create.html'
    login_url = '/'
    redirect_field_name = 'invoices/create/'

    def get(self, request):
        ref = request.META['HTTP_REFERER']
        d = datetime.now()
        dt = timedelta(days=14)
        rates = get_exchange_rates(d.strftime('%d.%m.%Y'))
        recipients = Recipient.objects.filter(
            owner=request.user).order_by('surname')
        invoices_id = Invoice.objects.filter(
            owner=request.user).values_list('iid', flat=True)
        if invoices_id and max(invoices_id) // 10000 == d.year:
            iid = max(list(invoices_id)) + 1
        else:
            iid = d.year * 10000 + 1
        default_dates = {'created': d, 'due': d + dt}

        advances = Advance.objects.filter(
            owner=request.user, linked=False)

        context = {'recipients': recipients, 'iid': iid,
                   'user': request.user, 'default_dates': default_dates, 'rates': rates, 'type': 'faktura', 'advances': advances, 'ref': ref}
        response = render(request, self.template_name, context)
        response.set_cookie(key='ref', value=ref)
        return response

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
        if currency != 'CZK':
            invoice.exchange_rate = get_exchange_rates(
                d.strftime('%d.%m.%Y'))[invoice.currency]
        else:
            invoice.exchange_rate = {
                'amount': 1, 'rate': 1.000, 'date': d.strftime('%d.%m.%Y')}
        invoice.datedue = request.POST.get('due')
        invoice.iid = request.POST.get('id')
        invoice.payment = request.POST.get('payment')
        invoice.owner = request.user
        invoice.has_items = request.POST.get('hasItems') == 'on'
        paid = request.POST.get('paid')
        if paid:
            invoice.paid = paid
            d_paid = datetime.strptime(paid, '%Y-%m-%d')
            if invoice.currency != 'CZK':
                invoice.paid_exchange_rate = get_exchange_rates(
                    d_paid.strftime('%d.%m.%Y'))[invoice.currency]
            else:
                invoice.paid_exchange_rate = {
                    'amount': 1, 'rate': 1.000, 'date': d_paid.strftime('%d.%m.%Y')}
        advance_id = request.POST.get('advance')
        if advance_id:
            advance = Advance.objects.filter(
                owner=request.user).get(pk=int(advance_id))
            advance.linked = True
            invoice.advance = advance
            advance.save()

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
        messages.success(request, f'Faktura {invoice.iid} úspěšně vytvořena.')
        ref = request.COOKIES.get('ref')
        return redirect(ref)


class AdvanceView(LoginRequiredMixin, View):
    template_name = 'invoices/create.html'
    login_url = '/'
    redirect_field_name = 'invoices/create/'

    def get(self, request):
        ref = request.META['HTTP_REFERER']
        d = datetime.now()
        dt = timedelta(days=14)
        rates = get_exchange_rates(d.strftime('%d.%m.%Y'))
        recipients = Recipient.objects.filter(
            owner=request.user).order_by('surname')
        invoices_id = Advance.objects.filter(
            owner=request.user).values_list('iid', flat=True)
        if invoices_id and max(invoices_id) // 10000 == d.year:
            iid = max(list(invoices_id)) + 1
        else:
            iid = d.year * 10000 + 1
        default_dates = {'created': d, 'due': d + dt}
        context = {'recipients': recipients, 'iid': iid,
                   'user': request.user, 'default_dates': default_dates, 'rates': rates, 'type': 'záloha', 'ref': ref}
        response = render(request, self.template_name, context)
        response.set_cookie(key='ref', value=ref)
        return response

    def post(self, request):

        invoice = Advance()
        rid = request.POST.get('recipient')
        invoice.recipient = Recipient.objects.filter(
            owner=request.user).get(pk=int(rid))
        invoice.description = request.POST.get('description')
        invoice.amount = request.POST.get('amount')

        invoice.date = request.POST.get('created')
        d = datetime.strptime(invoice.date, '%Y-%m-%d')
        invoice.currency = request.POST.get('currency')
        if invoice.currency != 'CZK':
            invoice.exchange_rate = get_exchange_rates(
                d.strftime('%d.%m.%Y'))[invoice.currency]
        else:
            invoice.exchange_rate = {
                'amount': 1, 'rate': 1.000, 'date': d.strftime('%d.%m.%Y')}
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
        messages.success(request, f'Záloha {invoice.iid} úspěšně vytvořena.')
        ref = request.COOKIES.get('ref')
        return redirect(ref)


class InvoiceDetailView(LoginRequiredMixin, View):
    login_url = '/'
    redirect_field_name = 'invoices/'
    template_name = 'invoices/detail.html'

    def get(self, request, id):
        ref = request.META['HTTP_REFERER']
        invoice = Invoice.objects.filter(
            owner=request.user).get(id=id)
        if invoice.advance:
            advance = Advance.objects.filter(
                owner=request.user).get(pk=invoice.advance.pk)
        else:
            advance = None
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
                   "items": items, 'iban': iban, "svg": mark_safe(svg_output.getvalue().decode()), 'type': "Faktura", 'advance': advance, 'ref': ref}

        return render(request, self.template_name, context)


class AdvanceDetailView(LoginRequiredMixin, View):
    login_url = '/'
    redirect_field_name = 'invoices/'
    template_name = 'invoices/detail.html'

    def get(self, request, id):
        invoice = Advance.objects.filter(
            owner=request.user).get(id=id)
        ref = request.META['HTTP_REFERER']

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
                   "items": items, 'iban': iban, "svg": mark_safe(svg_output.getvalue().decode()), 'type': "Záloha", 'ref': ref}

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
        if str(datetime.now().year) not in years:
            years.insert(0, str(datetime.now().year))

        for invoice in invoices:

            total += invoice.amount * \
                invoice.exchange_rate['rate'] / invoice.exchange_rate['amount']

        context = {'invoices': invoices,
                   'user': request.user,
                   'profile': userprofile,
                   'logo': logo,
                   'total': total,
                   'years': sorted(list(set(years)), reverse=True),
                   'selected_year': str(yr),
                   'type': 'Přehled faktur'}
        return render(request, self.template_name, context)


class AdvanceOverView(LoginRequiredMixin, View):
    template_name = 'invoices/overview.html'
    login_url = '/'
    redirect_field_name = 'advances/'

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
            invoices = Advance.objects.filter(
                date__year=yr, owner=request.user).order_by('-iid')
        else:
            invoices = Advance.objects.filter(
                owner=request.user).order_by('-iid')

        dates = Advance.objects.filter(
            owner=request.user).dates('date', 'year')
        years = [str(date.year) for date in dates]
        if str(datetime.now().year) not in years:
            years.insert(0, str(datetime.now().year))
        for invoice in invoices:

            total += invoice.amount * \
                invoice.exchange_rate['rate'] / \
                invoice.exchange_rate['amount']

        context = {'invoices': invoices,
                   'user': request.user,
                   'profile': userprofile,
                   'logo': logo,
                   'total': total,
                   'years': sorted(list(set(years)), reverse=True),
                   'selected_year': str(yr),
                   'type': 'Přehled záloh'}
        return render(request, self.template_name, context)


class InvoiceDeleteView(LoginRequiredMixin, View):
    login_url = '/'
    redirect_field_name = 'invoices/'

    def post(self, request, id):
        ref = request.META['HTTP_REFERER']
        invoice = Invoice.objects.filter(
            owner=request.user).get(id=id)
        invoice.delete()
        messages.warning(request, f'Faktura {invoice.iid} odstraněna.')
        return redirect(ref)


class AdvanceDeleteView(LoginRequiredMixin, View):
    login_url = '/'
    redirect_field_name = 'advances/'

    def post(self, request, id):
        ref = request.META['HTTP_REFERER']
        invoice = Advance.objects.filter(
            owner=request.user).get(id=id)
        invoice.delete()
        messages.warning(request, f'Záloha {invoice.iid} odstraněna.')
        return redirect(ref)


class InvoiceUpdateView(LoginRequiredMixin, View):
    login_url = '/'
    redirect_field_name = 'invoices/'
    template_name = 'invoices/update.html'

    def get(self, request, id):
        ref = request.META['HTTP_REFERER']
        invoice = Invoice.objects.filter(
            owner=request.user).get(id=id)
        if invoice.has_items:
            items = InvoiceItem.objects.filter(invoice=invoice)
        else:
            items = []

        advances = Advance.objects.filter(
            owner=request.user, linked=False)

        # d = datetime.strptime(invoice.date, '%Y-%m-%d')
        rates = get_exchange_rates(invoice.date.strftime('%d.%m.%Y'))
        context = {'invoice': invoice, "items": items,
                   'rates': rates, 'type': 'faktura', 'advances': advances, 'ref': ref}

        response = render(request, self.template_name, context)
        response.set_cookie(key='ref', value=ref)
        return response

    def post(self, request, id):
        invoice = Invoice.objects.filter(
            owner=request.user).get(id=id)
        invoice.description = request.POST.get('description')
        invoice.amount = request.POST.get('amount')
        invoice.date = request.POST.get('created')
        invoice.datedue = request.POST.get('due')
        paid = request.POST.get('paid')
        invoice.currency = request.POST.get('currency')
        d = datetime.strptime(invoice.date, '%Y-%m-%d')
        if paid:
            invoice.paid = paid
            d_paid = datetime.strptime(paid, '%Y-%m-%d')
            if invoice.currency != 'CZK':
                invoice.paid_exchange_rate = get_exchange_rates(
                    d_paid.strftime('%d.%m.%Y'))[invoice.currency]
            else:
                invoice.paid_exchange_rate = {
                    'amount': 1, 'rate': 1.000, 'date': d_paid.strftime('%d.%m.%Y')}

        if invoice.currency != 'CZK':
            invoice.exchange_rate = get_exchange_rates(
                d.strftime('%d.%m.%Y'))[invoice.currency]
        else:
            invoice.exchange_rate = {
                'amount': 1, 'rate': 1.000, 'date': d.strftime('%d.%m.%Y')}
        invoice.iid = request.POST.get('id')
        invoice.payment = request.POST.get('payment')
        invoice.owner = request.user
        invoice.has_items = request.POST.get('hasItems') == 'on'

        advance_id = request.POST.get('advance')
        if advance_id:
            advance = Advance.objects.filter(
                owner=request.user).get(pk=int(advance_id))
            advance.linked = True
            invoice.advance = advance
            advance.save()

        invoice.save()
        if invoice.has_items:
            try:
                items_db = InvoiceItem.objects.filter(invoice=invoice)
            except:
                items_db = []
            try:
                i = 0
                while True:

                    items_post = request.POST.getlist('items' + str(i) + '[]')
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
        messages.success(request, f'Faktura {invoice.iid} aktualizována.')
        ref = request.COOKIES.get('ref')
        return redirect(ref)


class AdvanceUpdateView(LoginRequiredMixin, View):
    login_url = '/'
    redirect_field_name = 'advance/'
    template_name = 'invoices/update.html'

    def get(self, request, id):
        ref = request.META['HTTP_REFERER']
        invoice = Advance.objects.filter(
            owner=request.user).get(id=id)
        if invoice.has_items:
            items = InvoiceItem.objects.filter(invoice=invoice)
        else:
            items = []

        rates = get_exchange_rates(invoice.date.strftime('%d.%m.%Y'))
        context = {'invoice': invoice, "items": items,
                   'rates': rates, 'type': 'záloha', 'ref': ref}

        response = render(request, self.template_name, context)
        response.set_cookie(key='ref', value=ref)
        return response

    def post(self, request, id):
        invoice = Advance.objects.filter(
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
            invoice.exchange_rate = {
                'amount': 1, 'rate': 1.000, 'date': d.strftime('%d.%m.%Y')}
        paid = request.POST.get('paid')
        if paid:
            invoice.paid = paid
            d_paid = datetime.strptime(paid, '%Y-%m-%d')
            if invoice.currency != 'CZK':
                invoice.paid_exchange_rate = get_exchange_rates(
                    d_paid.strftime('%d.%m.%Y'))[invoice.currency]
            else:
                invoice.paid_exchange_rate = {
                    'amount': 1, 'rate': 1.000, 'date': d_paid.strftime('%d.%m.%Y')}

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
                while True:

                    items_post = request.POST.getlist('items' + str(i) + '[]')
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
        messages.success(request, f'Záloha {invoice.iid} aktualizována.')
        ref = request.COOKIES.get('ref')
        return redirect(ref)


class RecipientView(LoginRequiredMixin, View):
    template_name = 'recipient/create.html'
    login_url = '/'
    redirect_field_name = 'invoices/'

    def get(self, request):
        ref = request.META['HTTP_REFERER']
        context = {'ref': ref}
        response = render(request, self.template_name, context)
        response.set_cookie(key='ref', value=ref)
        return response

    def post(self, request):

        recipient = Recipient()
        recipient.name = request.POST.get('name')
        recipient.surname = request.POST.get('surname')
        recipient.form = request.POST.get('form')
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
        messages.success(
            request, mark_safe(f'Odběratel <em>{recipient.name}</em> úspěšně přidán.'))
        ref = request.COOKIES.get('ref')
        return redirect(ref)


class UserProfileUpdateView(LoginRequiredMixin, View):
    login_url = '/'
    redirect_field_name = 'invoices/'
    template_name = 'user/profile.html'

    def get(self, request, id):
        ref = request.META['HTTP_REFERER']
        profile = UserProfile.objects.get(id=id, user=request.user)
        context = {'profile': profile,
                   'user': request.user,
                   'ref': ref}
        response = render(request, self.template_name, context)
        response.set_cookie(key='ref', value=ref)
        return response

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

        user = User.objects.get(id=request.user.id)
        password1 = request.POST['password']
        password2 = request.POST['password-confirm']
        if password1 and password2:
            if password1 == password2:
                user.set_password(password1)
                user.save()
                messages.success(
                    request, 'Heslo změněno.')
            else:
                messages.warning(request, 'Hesla se neshodují.')
                return redirect(ref)

        user_profile.save()
        messages.success(
            request, 'Vaše údaje byly aktualizovány.')
        ref = request.COOKIES.get('ref')
        return redirect(ref)


class MailCopy(LoginRequiredMixin, View):
    login_url = '/'
    redirect_field_name = 'overview/'

    def post(self, request):
        ref = request.META['HTTP_REFERER']
        user_profile = UserProfile.objects.get(user=request.user)
        try:
            mail = bool(request.POST['mailcopy'])
        except:
            mail = False

        if mail:
            user_profile.mailcopy = True
            messages.success(
                request, f'Kopie faktur budou zasílány na adresu {user_profile.email}.')
        else:
            user_profile.mailcopy = False
            messages.warning(
                request, mark_safe(f'Kopie faktur <strong>nebudou</strong> zasílány na adresu {user_profile.email}.'))

        user_profile.save()

        return redirect(ref)


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
            owner=request.user).order_by('surname')

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
        if str(datetime.now().year) not in years:
            years.insert(0, str(datetime.now().year))

        for recipient in recipients:
            if yr and not yr == 'all':
                invoices = Invoice.objects.filter(
                    date__year=yr, owner=request.user, recipient=recipient).order_by('iid')
            else:
                invoices = Invoice.objects.filter(
                    owner=request.user, recipient=recipient).order_by('iid')

            total = 0
            for invoice in invoices:
                total += invoice.amount * \
                    invoice.exchange_rate['rate'] / \
                    invoice.exchange_rate['amount']
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
        ref = request.META['HTTP_REFERER']
        recipient = Recipient.objects.get(id=id, owner=request.user)
        context = {'recipient': recipient,
                   'user': request.user,
                   'ref': ref}

        response = render(request, self.template_name, context)
        response.set_cookie(key='ref', value=ref)

        return response

    def post(self, request, id):
        recipient = Recipient.objects.get(id=id, owner=request.user)
        recipient.name = request.POST['name']
        recipient.surname = request.POST.get('surname')
        recipient.form = request.POST.get('form')
        recipient.street = request.POST['street']
        recipient.town = request.POST['town']
        recipient.zipcode = request.POST['zipcode']
        recipient.state = request.POST['state']

        if request.POST['dic']:
            recipient.dic = request.POST['dic']
        if request.POST['ic']:
            recipient.ic = request.POST['ic']

        recipient.save()
        messages.success(
            request, mark_safe(f'Odběratel <em>{recipient.surname}{recipient.name}</em> aktualizován.'))
        ref = request.COOKIES.get('ref')
        return redirect(ref)


def link_callback(uri, rel):
    """
    Convert HTML URIs to absolute system paths so xhtml2pdf can access those
    resources
    """
    result = finders.find(uri)
    if result:
        if not isinstance(result, (list, tuple)):
            result = [result]

        result = list(os.path.realpath(path) for path in result)
        path = result[0]
    else:
        sUrl = settings.STATIC_URL        # Typically /static/
        sRoot = settings.STATIC_ROOT      # Typically /home/userX/project_static/
        mUrl = settings.MEDIA_URL         # Typically /media/
        mRoot = settings.MEDIA_ROOT       # Typically /home/userX/project_static/media/

        if uri.startswith(mUrl):
            path = os.path.join(mRoot, uri.replace(mUrl, ""))
        elif uri.startswith(sUrl):
            path = os.path.join(sRoot, uri.replace(sUrl, ""))
        else:
            return uri

    # make sure that file exists
    if not os.path.isfile(path):
        raise Exception(
            'media URI must start with %s or %s' % (sUrl, mUrl)
        )
    #print('****', path)
    return path


class PrintInvoiceView(LoginRequiredMixin, View):
    template_name = 'invoices/print.html'
    login_url = '/'
    redirect_field_name = '/'

    def get(self, request, id=None):
        template = get_template(self.template_name)
        sign = request.GET['sign']
        try:
            asset = request.GET['asset']
        except:
            asset = None
        name = "faktura"
        if asset == 'advance':
            name = 'záloha'
        if id:
            invoice = Invoice.objects.get(id=id, owner=request.user)
            if invoice.has_items:
                items = InvoiceItem.objects.filter(invoice=invoice)
            else:
                items = []

            user = UserProfile.objects.get(user=invoice.owner)
            generator = QRPlatbaGenerator(user.bank, invoice.amount, x_vs=invoice.iid, currency=invoice.currency,
                                          message=f'{name.upper()} {invoice.iid}', due_date=invoice.datedue)
            iban = generator._account[4:-1]
            img = generator.make_image()
            svg_output = os.path.join(os.path.dirname(
                user.logo.name), 'conversionQR.svg')
            img.save(svg_output)
            user_qr = svg2rlg(svg_output)
            qr_png = os.path.join(os.path.dirname(
                user.logo.name), 'conversionQR.png')
            renderPM.drawToFile(user_qr, qr_png, fmt="PNG")

        else:
            user = UserProfile.objects.get(user=request.user)
            invoice = Invoice()
            invoice.iid = ''
            invoice.payment = ''
            invoice.date = None
            invoice.datedue = None
            qr_png = None
            iban = None
            items = []

        user_logo_png = svg2rlg(user.logo.name)

        logo_png = os.path.join(
            os.path.dirname(user.logo.name), 'conversionLG.png')
        renderPM.drawToFile(user_logo_png, logo_png, fmt="PNG")

        context = {"invoice": invoice, "user": user, 'logo': logo_png,
                   "items": items, 'iban': iban, "qr": qr_png, 'sign': sign,  'type': name.title()}

        html = template.render(context)
        result = BytesIO()
        pdf = pisa.pisaDocument(
            BytesIO(html.encode("utf-8")), result, encoding='UTF-8', link_callback=link_callback)

        if not pdf.err:
            response = HttpResponse(
                result.getvalue(), content_type='application/pdf')
            response['Content-Disposition'] = f'filename="{invoice.iid if invoice.iid else name}.pdf"'
            if user.mailcopy and user.email:
                bytes = result.getvalue()
                encoded_file = base64.b64encode(bytes).decode()
                base64_png = base64.b64encode(
                    open(qr_png, "rb").read()).decode()
                message = Mail(
                    from_email=EMAIL,
                    to_emails=EMAIL,
                    subject=f'{name.title()} č. {invoice.iid}',
                    html_content=f'''
                    {name.title()} za provedené služby je přílohou tohoto emailu.
                    <table style='width:75%;border: 1px solid black; margin-top:10px;border-collapse:collapse;'>
                        <tr style="padding: 5px 10px">
                            <td>
                                <h3 style='padding-left:5px; padding-bottom:10px; border-bottom: 1px solid black;'>Faktura č. {invoice.iid}</h3>
                                <ul style='list-style: none;'>
                                    <li>{invoice.recipient.name}</li>
                                    <li>{invoice.recipient.street}, {invoice.recipient.zipcode} {invoice.recipient.town}</li>

                                    <li style='padding-top:10px;padding-bottom:10px;'><em>{invoice.description}</em></li>
                                    
                                    <li style='padding-top:10px;padding-bottom:10px;'><h4>Splatnost: {invoice.datedue.strftime("%d.%m.%Y")}</h4></li>

                                    <li><h4>Celkem: {invoice.amount} {invoice.currency}</h4></li>
                                </ul>
                            </td>
                            <td>
                                <img src="cid:qr_code"/>
                            </td>
                        </tr>
                    </table>

                    <div style='font-size:8px;padding-top:10px;'><em>Tento email je generován automaticky.</em></div>
                    '''
                )
                attachedFile = Attachment(
                    FileContent(encoded_file),
                    FileName(f"{name.title()}_{invoice.iid}.pdf"),
                    FileType('application/pdf'),
                    Disposition('attachment')
                )
                attached_qr = Attachment(
                    FileContent(base64_png),
                    FileName('qrplatba.png'),
                    FileType('image/png'),
                    Disposition('inline'),
                    ContentId('qr_code')
                )

                message.attachment = attachedFile
                message.attachment = attached_qr
                #message.bcc = Bcc(OTHER_EMAIL)

                try:
                    sg = SendGridAPIClient(SENDGRID_API_KEY)
                    res = sg.send(message)
                    messages.success(request, f'Email odeslán.')
                except Exception as e:
                    messages.warning(
                        request, f'Při odesílání emailu došlo k chybě.')
                    print('**', e)
            return response

        return None


class PrintAdvanceView(LoginRequiredMixin, View):
    template_name = 'invoices/print.html'
    login_url = '/'
    redirect_field_name = '/'

    def get(self, request, id):
        template = get_template(self.template_name)
        invoice = Advance.objects.get(id=id, owner=request.user)
        sign = request.GET['sign']
        if invoice.has_items:
            items = InvoiceItem.objects.filter(invoice=invoice)
        else:
            items = []

        user = UserProfile.objects.get(user=invoice.owner)
        generator = QRPlatbaGenerator(user.bank, invoice.amount, x_vs=invoice.iid, currency=invoice.currency,
                                      message=f'ZALOHA {invoice.iid}', due_date=invoice.datedue)
        iban = generator._account[4:-1]
        img = generator.make_image()

        logo = user.logo.name
        with open(logo) as l:
            user_logo = l.read()

        svg_output = os.path.join(os.path.dirname(
            user.logo.name), 'conversionQR.svg')
        img.save(svg_output)

        user_logo_png = svg2rlg(user.logo.name)
        user_qr = svg2rlg(svg_output)
        qr_png = os.path.join(os.path.dirname(
            user.logo.name), 'conversionQR.png')
        logo_png = os.path.join(
            os.path.dirname(user.logo.name), 'conversionLG.png')
        renderPM.drawToFile(user_logo_png, logo_png, fmt="PNG")
        renderPM.drawToFile(user_qr, qr_png, fmt="PNG")

        context = {"invoice": invoice, "user": user, 'logo': logo_png,
                   "items": items, 'iban': iban, "qr": qr_png, 'sign': sign,  'type': "Záloha"}

        html = template.render(context)
        result = BytesIO()
        pdf = pisa.pisaDocument(
            BytesIO(html.encode("utf-8")), result, encoding='UTF-8', link_callback=link_callback)

        if not pdf.err:
            response = HttpResponse(
                result.getvalue(), content_type='application/pdf')
            response['Content-Disposition'] = f'filename="Z{invoice.iid}.pdf"'

            return response

        return None


class CheckICOView(LoginRequiredMixin, View):
    login_url = '/'
    redirect_field_name = '/'

    def get(self, request):
        ic = request.GET['ic']
        validator = ARES(ic=ic)
        response = validator.check_ic()
        return HttpResponse(
            json.dumps(response),
            content_type='application/javascript; charset=utf8'
        )
