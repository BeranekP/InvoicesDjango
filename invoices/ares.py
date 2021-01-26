import requests
import xml.etree.ElementTree as ET


class ARES():
    '''
        Get info on registered czech economical subjects from https://wwwinfo.mfcr.cz/ares/ares_es.html.cz
        Initialized e.g. a = ARES(ic='1234567')
    '''

    def __init__(self, **ic):
        self.ic = ic['ic']
        self.subject_name = None
        self.subject_ic = None
        self.subject_town = None
        self.subject_street = None
        self.subject_house_no = None
        self.subject_zipcode = None
        self.subject_pf = None
        self.check_ic()

    def check_ic(self):
        '''
        Connects to ARES, receives XML response, parse useful data
        returns - dict {'name': self.subject_name, 'ic': self.subject_ic, 'town': self.subject_town,
                'street': self.subject_street, 'house_no': self.subject_house_no, 'zipcode': self.subject_zipcode, 'pf': self.subject_pf}
                or Not found
        '''
        response = requests.get(
            'https://wwwinfo.mfcr.cz/cgi-bin/ares/darv_std.cgi?ico=' + self.ic)
        xml = ET.fromstring(response.content.decode('utf-8'))
        tree = ET.ElementTree(xml)
        root = tree.getroot()
        try:
            for pf in root.iter('{http://wwwinfo.mfcr.cz/ares/xml_doc/schemas/ares/ares_datatypes/v_1.0.4}Kod_PF'):
                self.subject_pf = {'code': pf.text,
                                   'desc': self.pravni_formy(pf.text)}
            for name in root.iter('{http://wwwinfo.mfcr.cz/ares/xml_doc/schemas/ares/ares_answer/v_1.0.1}Obchodni_firma'):
                self.subject_name = name.text
            for ico in root.iter('{http://wwwinfo.mfcr.cz/ares/xml_doc/schemas/ares/ares_answer/v_1.0.1}ICO'):
                self.subject_ic = ico.text
            for town in root.iter('{http://wwwinfo.mfcr.cz/ares/xml_doc/schemas/ares/ares_datatypes/v_1.0.4}Nazev_obce'):
                self.subject_town = town.text
            for town_part in root.iter('{http://wwwinfo.mfcr.cz/ares/xml_doc/schemas/ares/ares_datatypes/v_1.0.4}Nazev_casti_obce'):
                self.subject_town_part = town_part.text
            for street in root.iter('{http://wwwinfo.mfcr.cz/ares/xml_doc/schemas/ares/ares_datatypes/v_1.0.4}Nazev_ulice'):
                self.subject_street = street.text
            for house_no in root.iter('{http://wwwinfo.mfcr.cz/ares/xml_doc/schemas/ares/ares_datatypes/v_1.0.4}Cislo_domovni'):
                self.subject_house_no = house_no.text
            for zipcode in root.iter('{http://wwwinfo.mfcr.cz/ares/xml_doc/schemas/ares/ares_datatypes/v_1.0.4}PSC'):
                self.subject_zipcode = zipcode.text

            if not self.subject_street:
                self.subject_street = self.subject_town_part

            return {'name': self.subject_name, 'ic': self.subject_ic, 'town': self.subject_town,
                    'street': self.subject_street, 'house_no': self.subject_house_no, 'zipcode': self.subject_zipcode, 'pf': self.subject_pf}
        except:
            return "Not found"

    def __repr__(self):
        '''
            returns readable represention if subject found, else Not found
        '''
        if self.subject_name:
            return f'''
            {self.subject_name}
            {self.subject_street} {self.subject_house_no}
            {self.subject_zipcode} {self.subject_town}
            IČ: {self.subject_ic}
            {self.subject_pf}
            '''
        return "Not found"

    def pravni_formy(self, id):
        '''
            input - id of desired form
            returns - returns desired form
        '''
        FORMY = {
            '100': 'Podnikající osoba tuzemská',
            '101': 'Fyzická osoba podnikající dle živnostenského zákona nezapsaná v obchodním rejstříku',
            '102': 'Fyzická osoba podnikající dle živnostenského zákona zapsaná v obchodním rejstříku',
            '104': 'Samostatně hospodařící rolník zapsaný v obchodním rejstříku',
            '105': 'Fyzická osoba podnikající dle jiných zákonů než živnostenského a zákona o zemědělství nezapsaná v obchodním rejstříku',
            '106': 'Fyzická osoba podnikající dle jiných zákonů než živnostenského a zákona o zemědělství zapsaná v obchodním rejstříku',
            '107': 'Zemědělský podnikatel - fyzická osoba nezapsaná v obchodním rejstříku',
            '108': 'Zemědělský podnikatel - fyzická osoba zapsaná v obchodním rejstříku',
            '111': 'Veřejná obchodní společnost',
            '112': 'Společnost s ručením omezeným',
            '113': 'Společnost komanditní',
            '115': 'Společný podnik',
            '116': 'Zájmové sdružení',
            '117': 'Nadace',
            '118': 'Nadační fond',
            '121': 'Akciová společnost',
            '141': 'Obecně prospěšná společnost',
            '145': 'Společenství vlastníků jednotek',
            '151': 'Komoditní burza',
            '152': 'Garanční fond obchodníků s cennými papíry',
            '161': 'Ústav',
            '201': 'Zemědělské družstvo',
            '205': 'Družstvo',
            '231': 'Výrobní družstvo',
            '232': 'Spotřební družstvo',
            '233': 'Bytové družstvo',
            '234': 'Jiné družstvo',
            '241': 'Družstevní podnik (s jedním zakladatelem)',
            '242': 'Společný podnik (s více zakladateli)',
            '251': 'Zájmová organizace družstev',
            '261': 'Společná zájmová organizace družstev',
            '301': 'Státní podnik',
            '302': 'Národní podnik',
            '312': 'Banka-státní peněžní ústav',
            '313': 'Česká národní banka',
            '314': 'Česká konsolidační agentura',
            '325': 'Organizační složka státu',
            '331': 'Příspěvková organizace',
            '332': 'Státní příspěvková organizace',
            '352': 'Správa železniční dopravní cesty, státní organizace',
            '353': 'Rada pro veřejný dohled nad auditem',
            '361': 'Veřejnoprávní instituce (ČT,ČRo,ČTK)',
            '362': 'Česká tisková kancelář',
            '381': 'Fond (ze zákona)',
            '382': 'Státní fond ze zákona',
            '391': 'Zdravotní pojišťovna',
            '401': 'Sdružení mezinárodního obchodu',
            '411': 'Podnik se zahraniční majetkovou účastí',
            '421': 'Odštěpný závod zahraniční právnické osoby',
            '422': 'Organizační složka zahraničního nadačního fondu',
            '423': 'Organizační složka zahraniční nadace',
            '424': 'Zahraniční',
            '425': 'Odštěpný závod zahraniční fyzické osoby',
            '426': 'Zastoupení zahraniční banky',
            '441': 'Podnik zahraničního obchodu',
            '501': 'Odštěpný závod nebo jiná organizační složka podniku zapisující se do obchodního rejstříku',
            '521': 'Samostatná drobná provozovna obecního úřadu',
            '525': 'Vnitřní organizační jednotka organizační složky státu',
            '541': 'Podílový fond',
            '601': 'Vysoká škola',
            '641': 'Školská právnická osoba',
            '651': 'Zdravotnické zařízení',
            '661': 'Veřejná výzkumná instituce',
            '671': 'Veřejné neziskové ústavní zdravotnické zařízení',
            '701': 'Sdružení (svaz, spolek, společnost, klub aj.)',
            '703': 'Odborová organizace a organizace zaměstnavatelů',
            '704': 'Zvláštní organizace pro zastoupení českých zájmů v mezinárodních nevládních organizacích',
            '705': 'Podnik nebo hospodářské zařízení sdružení',
            '706': 'Spolek',
            '707': 'Odborová organizace',
            '708': 'Organizace zaměstnavatelů',
            '711': 'Politická strana, politické hnutí',
            '715': 'Podnik nebo hospodářské zařízení politické strany',
            '721': 'Církevní organizace',
            '722': 'Evidované církevní právnické osoby',
            '723': 'Svazy církví a náboženských společností',
            '731': 'Organizační jednotka sdružení',
            '732': 'Organizační jednotka politické strany, politického hnutí',
            '733': 'Organizační jednotka odborové organizace a organizace zaměstnavatelů',
            '736': 'Pobočný spolek',
            '741': 'Stavovská organizace - profesní komora',
            '745': 'Komora (s výjimkou profesních komor)',
            '751': 'Zájmové sdružení právnických osob',
            '761': 'Honební společenstvo',
            '771': 'Svazek obcí',
            '801': 'Obec nebo městská část hlavního města Prahy',
            '804': 'Kraj',
            '805': 'Regionální rada regionu soudržnosti',
            '811': 'Městská část, městský obvod',
            '901': 'Zastupitelský orgán jiných států',
            '906': 'Zahraniční spolek',
            '907': 'Mezinárodní odborová organizace',
            '908': 'Mezinárodní organizace zaměstnavatelů',
            '911': 'Zahraniční kulturní, informační středisko, rozhlasová, tisková a televizní agentura',
            '921': 'Mezinárodní organizace a sdružení',
            '922': 'Organizační jednotka organizace s mezinárodním prvkem',
            '931': 'Evropské hospodářské zájmové sdružení',
            '932': 'Evropská společnost',
            '933': 'Evropská družstevní společnost',
            '936': 'Zahraniční pobočný spolek',
            '937': 'Pobočná mezinárodní odborová organizace',
            '938': 'Pobočná mezinárodní organizace zaměstnavatelů',
            '941': 'Evropské seskupení pro územní spolupráci',
            '950': 'Subjekt právním řádem výslovně neupravený',
            '951': 'Mezinárodní vojenská organizace vzniklá na základě mezinárodní smlouvy',
            '952': 'Konsorcium evropské výzkumné infrastruktury',
            '960': 'Právnická osoba zřízená zvláštním zákonem zapisovaná do veřejného rejstříku',
            '961': 'Svěřenský fond',
            '962': 'Zahraniční svěřenský fond'}
        return FORMY[id]


if __name__ == "__main__":
    # cmd line interface example
    ic = input('Zadejte IC: ')
    validator = ARES(ic=ic)
    print(validator)
