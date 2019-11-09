import requests
from bs4 import BeautifulSoup
import config
from pprint import pprint
# Constants
PARSER = "lxml"  # Html parser for BeautifulSoup
TIMEOUT = 5  # Request max_timeout (in seconds)


class SessionToken(object):
    def __init__(self, s):
        # TCU login / Okta login (Not your email!)
        credentials = dict(username=config.username, password=config.password)
        resp = s.post("https://tcu.okta.com/api/v1/authn", json=credentials)  # Auth credentials
        self.value = resp.json()["sessionToken"]  # Session token value (str)

    def __repr__(self):
        return self.value


class RedirectUrl(object):
    def __init__(self, s):
        resp = s.get("https://get.cbord.com/tcu/full/login.php")  # Login page contains static link
        soup = BeautifulSoup(resp.text, PARSER)
        self.value = soup.select_one("#fromURI").get("value")  # Link needed for session cookie redirect

    def __repr__(self):
        return self.value


class UserId(object):
    def __init__(self, resp):
        soup = BeautifulSoup(resp.text, PARSER)
        self.value = (
            soup.find("option", text="Frog Bucks (refundable)")
            .get("value")
            .split(":")[2]
        )

    def __repr__(self):
        return self.value
        
        
class FormToken(object):
    def __init__(self, resp):
        soup = BeautifulSoup(resp.text, PARSER)
        self.value = soup.find(attrs=dict(name="formToken", type="hidden")).get("value")

    def __repr__(self):
        return self.value


class Table(object):
    def __init__(self, s):
        with s.get("https://get.cbord.com/tcu/full/funds_home.php") as resp:
            payload = dict(userId=UserId(resp), formToken=FormToken(resp))
        resp = s.post("https://get.cbord.com/tcu/full/funds_overview_partial.php", data=payload)
        soup = BeautifulSoup(resp.text, PARSER)
        self.table = soup.select("tbody > tr")
        self.dict = self.to_dict()
        
    def to_dict(self):
        def get_account_name(row):
            tags = ["(refundable)", "(non-refundable)"]  # Filter out extraneous ids
            account_name = row.select_one("td.first-child").get_text()
            for tag in tags:
                if tag in account_name:
                    account_name = account_name[: account_name.find(tag)].strip()

            return account_name

        def get_balance(row):
            balance = row.select_one("td.last-child").get_text()
            return balance

        table_dict = {
            get_account_name(row): get_balance(row) for row in self.table
        }  # Formatting dict
        return table_dict
    
    def bal(self, account_name):
        return self.dict[account_name]


def auth(s):
    params = dict(token=SessionToken(session), redirectUrl=RedirectUrl(session))  # Build query params for request
    resp = s.get("https://tcu.okta.com/login/sessionCookieRedirect", params=params)  # cookie redirect
    soup = BeautifulSoup(resp.text, PARSER)
    return {desired_elem.get("name"): desired_elem.get("value") for desired_elem in soup.find_all("input")}


if __name__ == "__main__":
    with requests.Session() as session:
        session.post("https://get.cbord.com/tcu/Shibboleth.sso/SAML2/POST", data=auth(session))
        pprint(Table(session).dict)  # Get an account balance
