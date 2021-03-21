from ._modules import *


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
