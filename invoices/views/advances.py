from ._modules import *


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
                   'user': request.user, 'default_dates': default_dates, 'rates': rates, 'type': "záloha", 'ref': ref}
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
        return redirect('/advance/')


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
                   'type': 'záloha'}
        return render(request, self.template_name, context)


class AdvanceDeleteView(LoginRequiredMixin, View):
    login_url = '/'
    redirect_field_name = 'advances/'

    def post(self, request, id):
        invoice = Advance.objects.filter(
            owner=request.user).get(id=id)
        invoice.delete()
        messages.warning(request, f'Záloha {invoice.iid} odstraněna.')
        return redirect('/advance/')


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

        return redirect('/advance/')
