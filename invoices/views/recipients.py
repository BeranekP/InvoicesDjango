from ._modules import *


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
            request, mark_safe(f'Odběratel <em>{recipient.surname} {recipient.name}</em> úspěšně přidán.'))
        ref = request.COOKIES.get('ref')
        return redirect(ref)


class RecipientOverView(LoginRequiredMixin, View):
    template_name = 'recipient/overview.html'
    login_url = '/'
    redirect_field_name = 'recipient/'

    def get(self, request):
        try:
            userprofile = UserProfile.objects.get(user=request.user)
        except Exception:
            userprofile = None

        try:
            logo = userprofile.logo.read()
        except Exception:
            logo = None

        recipients = Recipient.objects.filter(
            owner=request.user).order_by('surname')

        years = []
        yr = request.GET.get('yr', datetime.now().year)
    
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
            request, mark_safe(f'Odběratel <em>{recipient.surname} {recipient.name}</em> aktualizován.'))
        ref = request.COOKIES.get('ref')
        return redirect(ref)
