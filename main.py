import requests
from bs4 import BeautifulSoup
from config import username, password
from contextlib import closing
PARSER = 'lxml'


def main():
    ###
    with requests.Session() as s:
        with closing(s.get('https://get.cbord.com/tcu/full/login.php')) as r:
            fromURI = BeautifulSoup(r.text, PARSER).select_one('#fromURI').get('value')

        with closing(s.post('https://tcu.okta.com/api/v1/authn', json=dict(username=username, password=password))) as r:
            sessionToken = r.json()['sessionToken']

        with closing(s.get('https://tcu.okta.com/login/sessionCookieRedirect', params=dict(token=sessionToken, redirectUrl=fromURI))) as r:
            data = {desired_elem.get('name'): desired_elem.get('value') for desired_elem in
                    BeautifulSoup(r.text, PARSER).find_all('input')}

        s.post('https://get.cbord.com/tcu/Shibboleth.sso/SAML2/POST', data=data)  #application/x-www-form-urlencoded
    ###
        with closing(s.get('https://get.cbord.com/tcu/full/funds_home.php')) as r:
            soup = BeautifulSoup(r.text, PARSER)
            userId = soup.find('option', text='Frog Bucks (refundable)').get('value').split(':')[2]
            formToken = soup.find(attrs=dict(name='formToken', type='hidden')).get('value')

        with closing(s.post('https://get.cbord.com/tcu/full/funds_overview_partial.php', data=dict(userId=userId, formToken=formToken))) as r:
            return table_to_dict(BeautifulSoup(r.text, PARSER).find('table').find_all('tr')[1:])


def table_to_dict(table):
    return {row.find('td', class_='first-child account_name').text: row.find('td', class_='last-child balance').text for row in table}


if __name__ == "__main__":
    table = main()
    print(table)
