from ._modules import *
from .utils import link_callback, clear_pdf, clear_session_data
import cairosvg
from invoices.views.email_template import template as t
from django.core import serializers


class PDFView(LoginRequiredMixin, View):
    template_name = 'invoices/pdf.html'
    login_url = '/'
    redirect_field_name = '/'

    def get(self, request):
        template = get_template(self.template_name)
        pdf = request.session['pdf']
        filename = request.session['filename']
        doctype = request.session['type']

        pk = request.session.get('invoice', None)
        user = UserProfile.objects.get(user=request.user)
        
        try:
            logo = user.logo.read()
        except Exception:
            logo = None
        
        return render(request, self.template_name, {'user': user, 'logo': logo, 'pdf': pdf, 'filename': filename, 'type': doctype, 'pk': pk})

    def post(self, request):
        asset = request.session['asset']
        pk = request.session['invoice']
        encoded_file = request.session['pdf']
        if asset.lower() == 'advance':
            invoice = Advance.objects.get(pk=pk, owner=request.user)
        if asset.lower() == 'invoice':
            invoice = Invoice.objects.get(pk=pk, owner=request.user)

        base64_png = request.session['qr']
        message = Mail(
            from_email=EMAIL,
            to_emails=EMAIL,
            subject=f'{request.session["type"]} č. {request.session["filename"]}',
            html_content=t(request.session["type"], invoice)
        )
        attachedFile = Attachment(
            FileContent(encoded_file),
            FileName(
                f'{request.session["type"]}_{request.session["filename"]}.pdf'),
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
        # message.bcc = Bcc(OTHER_EMAIL)

        try:
            sg = SendGridAPIClient(SENDGRID_API_KEY)
            res = sg.send(message)
            messages.success(request, f'Email odeslán.')
        except Exception as e:
            messages.warning(request, f'Při odesílání emailu došlo k chybě.')
            #print('**', e)

        return redirect('/pdf/')


class PrintInvoiceView(LoginRequiredMixin, View):
    template_name = 'invoices/print.html'
    login_url = '/'
    redirect_field_name = '/'

    def get(self, request, id=None):
        template = get_template(self.template_name)
        clear_session_data(request)

        sign = request.GET.get('sign', None)
        asset = request.GET.get('asset', None)

        name = None
        if asset.lower() == 'advance':
            name = 'záloha'
        if asset.lower() == 'invoice':
            name = "faktura"

        if id:
            if asset.lower() == 'advance':
                invoice = Advance.objects.get(id=id, owner=request.user)
            if asset.lower() == 'invoice':
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
            print('***', svg_output)
            qr_png = os.path.join(os.path.dirname(
                user.logo.name), 'conversionQR.png')
            img.save(svg_output)
            cairosvg.svg2png(url=svg_output, write_to=qr_png, scale=8)
            request.session['qr'] = base64.b64encode(
                open(qr_png, "rb").read()).decode()

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

        logo_png = os.path.join(os.path.dirname(
            user.logo.name), 'conversionLG.png')
            
        cairosvg.svg2png(url=user.logo.name, write_to=logo_png, scale=5)

        context = {"invoice": invoice, "user": user, 'logo': logo_png,
                   "items": items, 'iban': iban, "qr": qr_png, 'sign': sign,  'type': asset.lower()}

        html = template.render(context)
        result = BytesIO()
        pdf_path = os.path.join(
            os.path.dirname(user.logo.name), f'{invoice.iid if invoice.iid else name}.pdf')
        pdf = pisa.pisaDocument(
            BytesIO(html.encode("utf-8")), result, encoding='UTF-8', link_callback=link_callback)
        clear_pdf(os.path.dirname(user.logo.name))
        

        if not pdf.err:
            response = HttpResponse(
                result.getvalue(), content_type='application/pdf')
            response['Content-Disposition'] = f'filename="{invoice.iid if invoice.iid else name}.pdf"'
            bytes = result.getvalue()
            encoded_file = base64.b64encode(bytes).decode()
            request.session['pdf'] = encoded_file
            request.session['filename'] = f"{invoice.iid if invoice.iid else name}"
            request.session['type'] = asset.lower()
            request.session['invoice'] = invoice.pk
            request.session['asset'] = asset.lower()

            return redirect('/pdf/')

        return None
