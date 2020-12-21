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
from django.core.mail import EmailMessage

# serve robots.txt
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

        advances = Advance.objects.filter(
            owner=request.user, linked=False)

        context = {'recipients': recipients, 'iid': iid,
                   'user': request.user, 'default_dates': default_dates, 'rates': rates, 'type': 'faktura', 'advances': advances}
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

        return redirect('../')


class AdvanceView(LoginRequiredMixin, View):
    template_name = 'invoices/create.html'
    login_url = '/'
    redirect_field_name = 'invoices/create/'

    def get(self, request):
        d = datetime.now()
        dt = timedelta(days=14)
        rates = get_exchange_rates(d.strftime('%d.%m.%Y'))
        recipients = Recipient.objects.filter(
            owner=request.user).order_by('name')
        invoices_id = Advance.objects.filter(
            owner=request.user).values_list('iid', flat=True)
        if invoices_id:
            iid = max(list(invoices_id)) + 1
        else:
            iid = d.year * 10000 + 1
        default_dates = {'created': d, 'due': d + dt}
        context = {'recipients': recipients, 'iid': iid,
                   'user': request.user, 'default_dates': default_dates, 'rates': rates, 'type': 'záloha'}
        return render(request, self.template_name, context)

    def post(self, request):

        invoice = Advance()
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
                   "items": items, 'iban': iban, "svg": mark_safe(svg_output.getvalue().decode()), 'type': "Faktura", 'advance': advance}

        return render(request, self.template_name, context)


class AdvanceDetailView(LoginRequiredMixin, View):
    login_url = '/'
    redirect_field_name = 'invoices/'
    template_name = 'invoices/detail.html'

    def get(self, request, id):
        invoice = Advance.objects.filter(
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
                   "items": items, 'iban': iban, "svg": mark_safe(svg_output.getvalue().decode()), 'type': "Záloha"}

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

            total += invoice.amount *   \
                invoice.exchange_rate['rate'] / \
                invoice.exchange_rate['amount']

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
        for invoice in invoices:

            total += invoice.amount *   \
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
        invoice = Invoice.objects.filter(
            owner=request.user).get(id=id)
        invoice.delete()
        return redirect('../../')


class AdvanceDeleteView(LoginRequiredMixin, View):
    login_url = '/'
    redirect_field_name = 'advances/'

    def post(self, request, id):
        invoice = Advance.objects.filter(
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

        advances = Advance.objects.filter(
            owner=request.user, linked=False)

        # d = datetime.strptime(invoice.date, '%Y-%m-%d')
        rates = get_exchange_rates(invoice.date.strftime('%d.%m.%Y'))
        context = {'invoice': invoice, "items": items,
                   'rates': rates, 'type': 'faktura', 'advances': advances}
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

        return redirect('../../')


class AdvanceUpdateView(LoginRequiredMixin, View):
    login_url = '/'
    redirect_field_name = 'advance/'

    def get(self, request, id):
        invoice = Advance.objects.filter(
            owner=request.user).get(id=id)
        if invoice.has_items:
            items = InvoiceItem.objects.filter(invoice=invoice)
        else:
            items = []

        # d = datetime.strptime(invoice.date, '%Y-%m-%d')
        rates = get_exchange_rates(invoice.date.strftime('%d.%m.%Y'))
        context = {'invoice': invoice, "items": items,
                   'rates': rates, 'type': 'záloha'}
        return render(request, 'invoices/update.html', context)

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
    print('****', path)
    return path


class PrintInvoiceView(LoginRequiredMixin, View):
    template_name = 'invoices/print.html'
    login_url = '/'
    redirect_field_name = '/'

    def get(self, request, id):
        template = get_template(self.template_name)
        invoice = Invoice.objects.get(id=id, owner=request.user)
        sign = request.GET['sign']
        if invoice.has_items:
            items = InvoiceItem.objects.filter(invoice=invoice)
        else:
            items = []

        user = UserProfile.objects.get(user=invoice.owner)
        generator = QRPlatbaGenerator(user.bank, invoice.amount, x_vs=invoice.iid, currency=invoice.currency,
                                      message=f'FAKTURA {invoice.iid}', due_date=invoice.datedue)
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
                   "items": items, 'iban': iban, "qr": qr_png, 'sign': sign,  'type': "Faktura"}

        html = template.render(context)
        result = BytesIO()
        pdf = pisa.pisaDocument(
            BytesIO(html.encode("utf-8")), result, encoding='UTF-8', link_callback=link_callback)

        if not pdf.err:
            response = HttpResponse(
                result.getvalue(), content_type='application/pdf')
            response['Content-Disposition'] = f'filename="{invoice.iid}.pdf"'

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
