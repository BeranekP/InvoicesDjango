
def list2dict(list_of_lists):
    '''
        Converts a list of lists to dict where 1st value is the key
        and last two values a are taken as value for the given key
    '''

    out = {}
    for lst in list_of_lists:
        out.setdefault(lst[-2], float(lst[-1]))

    return out


def get_exchange_rates(date):
    import requests
    '''
        date:  DD.MM.YYYY
        return dict of exchange rates from CNB
            exchange_rates['country'] = {ABBREV, VALUE}
    '''

    URL = 'https://www.cnb.cz/cs/financni-trhy/devizovy-trh/kurzy-devizoveho-trhu/kurzy-devizoveho-trhu/denni_kurz.txt'

    PARAMS = {'date': date}
    r = requests.get(url=URL, params=PARAMS)

    exchange_rates = r.content.decode().split('\n')[2:-1]
    exchange_rates = [rate.replace(',', '.').split('|')
                      for rate in exchange_rates]
    exchange_rates = list2dict(exchange_rates)

    return exchange_rates
