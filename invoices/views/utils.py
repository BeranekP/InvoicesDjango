from ._modules import *


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
            logo = userprofile.logo.read().decode()
        except Exception as e:
            print(e)
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
        try:
            if datetime.now().year == year:
                total = graph_data[year]['total'][-1]
            else:
                total = 0
        except UnboundLocalError:
            total = 0
        context = {"data": data, "logo": logo,
                   "profile": userprofile, "total": total if total != 'null' else 0, "graphdata": graph_data}
        return render(request, self.template_name, context)


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

# serve robots.txt
@require_GET
def robots(request):
    lines = [
        "User-Agent: *",
        "Disallow: /static/",
    ]
    return HttpResponse("\n".join(lines), content_type="text/plain")


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


def clear_pdf(path):
    for parent, dirnames, filenames in os.walk(path):
        for fn in filenames:
            if fn.lower().endswith('.pdf'):
                os.remove(os.path.join(parent, fn))

def clear_session_data(request):
    request.session['pdf'] = None
    request.session['filename'] = None
    request.session['type'] = None
    request.session['invoice'] = None
    request.session['asset'] = None