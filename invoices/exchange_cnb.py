def exchange_rates_to_dict(list_of_lists, date):
    '''
        Converts xchange_rates as a list of lists to dict:
        {'CURRENCY': {'amount': 1, 'rate': 1.000, 'date': date}}
    '''

    out = {}
    for lst in list_of_lists:
        out.setdefault(
            'CZK', {'amount': 1, 'rate': 1.000, 'date': date})
        out.setdefault(
            lst[-2], {'amount': int(lst[-3]), 'rate': float(lst[-1]), 'date': date})

    return out


def get_exchange_rates(date):
    import requests
    '''
        date:  DD.MM.YYYY
        return dict of exchange rates for CZK from CNB
            exchange_rates = {'CURRENCY': {'amount': 1, 'rate': 1.000, 'date': date}}
    '''

    URL = 'https://www.cnb.cz/cs/financni-trhy/devizovy-trh/kurzy-devizoveho-trhu/kurzy-devizoveho-trhu/denni_kurz.txt'

    PARAMS = {'date': date}
    r = requests.get(url=URL, params=PARAMS)
    exchange_rates = r.content.decode().split('\n')[2:-1]
    exchange_rates = [rate.replace(',', '.').split('|')
                      for rate in exchange_rates]
    _date = r.content.decode().split('\n')[0]
    _date = _date.split()[0]

    exchange_rates = exchange_rates_to_dict(exchange_rates, _date)

    return exchange_rates
