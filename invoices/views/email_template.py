def template(name, invoice):

    return f'''<!DOCTYPE html>
                <html>
                    <head>
                        <meta http-equiv="Content-Type" content="text/html; charset=utf-8" />
                        <meta name="viewport" content="width=device-width, initial-scale=1.0"/>
                    <style rel='stylesheet' type='text/css'>
                        body,table,thead,tbody,tr,td,img {{
                                padding: 0;
                                margin: 0;
                                border: none;
                                border-spacing: 0px;
                                border-collapse: collapse;
                                vertical-align: top;
                                font-family: 'Open Sans', sans-serif !important;
                            }}

                        .bg{{
                            
                            padding:5px;
                            width:100%; 
                            margin-top:10px;
                            border-collapse:collapse;
                            

                            }}
                        .wrapper {{
                                padding-left: 10px;
                                padding-right: 10px;
                            }}
                        img {{
                                width: 75%;
                                display: block;
                            }}
                        .padded {{
                            padding-top:10px;
                            padding-bottom:10px;
                        }}    
                        @media only screen and (max-width: 600px)
                        {{.wrapper table {{
                                width: 100% !important;
                            }}

                            .wrapper .column {{
                                width: 100% !important;
                                display: block !important;
                            }}
                        }}
                    </style>
                    
                    </head>
                    
                    <body>
                        <p>{name.title()} za provedené služby je přílohou tohoto emailu.</p>
                            <center>
                                <table class='bg'>
                                    <tr>
                                        <td class="wrapper" width="600" align="center">
                                            <table cellpadding="0" cellspacing="0">
                                                <tr>
                                                    <td class="column" width="300">
                                                        <table>
                                                            <tr>
                                                                <td align="left">
                                                                    <h2 style='padding-left:5px; padding-bottom:10px; border-bottom: 1px solid black;'>Faktura č. {invoice.iid}</h2>
                                                                    <ul style='list-style: none;'>
                                                                        <li>{invoice.recipient.name} {invoice.recipient.surname}</li>
                                                                        <li>{invoice.recipient.street}, {invoice.recipient.zipcode} {invoice.recipient.town}</li>

                                                                        <li class='padded'><em>{invoice.description}</em></li>
                                                                        
                                                                        <li class='padded'><h4>Splatnost: {invoice.datedue.strftime("%d.%m.%Y")}</h4></li>

                                                                        <li><h3>Celkem: {invoice.amount} {'Kč' if invoice.currency == 'CZK' else invoice.currency}</h3></li>
                                                                    </ul>
                                                                </td>
                                                            </tr>
                                                        </table>
                                                    </td>
                                                    <td class="column" width="300">
                                                        <table>
                                                            <tr>
                                                                <td align="right">
                                                                    <center><img width="220" src="cid:qr_code"/></center>
                                                                </td>
                                                            </tr>
                                                        </table>
                                                    </td>
                                                </tr>
                                            </table>
                                        </td>
                                    </tr>
                                </table>
                            </center>
                            <div style='font-size:8px;padding-top:10px;'><em>Tento email je generován automaticky.</em></div>
                    </body>
                </html>
                        '''
