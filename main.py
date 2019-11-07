import requests
from bs4 import BeautifulSoup
import config
from contextlib import closing

# Constants
PARSER = "lxml"  # Html parser for BeautifulSoup
TIMEOUT = 5  # Request max_timeout (in seconds)


class SessionToken(object):
    def __init__(self, s):
        credentials = dict(username=config.username, password=config.password)
        with closing(
            s.post(
                "https://tcu.okta.com/api/v1/authn", json=credentials, timeout=TIMEOUT,
            )
        ) as r:
            r.raise_for_status()
            self.value = r.json()["sessionToken"]

    def __repr__(self):
        return self.value


class RedirectUrl(object):
    def __init__(self, s):
        with closing(
            s.get("https://get.cbord.com/tcu/full/login.php", timeout=TIMEOUT)
        ) as r:
            r.raise_for_status()
            redirect_url = (
                BeautifulSoup(r.text, PARSER)
                .select_one("#fromURI", timeout=TIMEOUT)
                .get("value")
            )
            self.value = redirect_url

    def __repr__(self):
        return self.value


class UserId(object):
    def __init__(self, r):
        soup = BeautifulSoup(r.text, PARSER)
        self.value = (
            soup.find("option", text="Frog Bucks (refundable)")
            .get("value")
            .split(":")[2]
        )

    def __repr__(self):
        return self.value


class FormToken(object):
    def __init__(self, r):
        soup = BeautifulSoup(r.text, PARSER)
        self.value = soup.find(attrs=dict(name="formToken", type="hidden")).get("value")

    def __repr__(self):
        return self.value


class Table(object):
    def __init__(self, s):
        with closing(s.get("https://get.cbord.com/tcu/full/funds_home.php")) as r:
            payload = dict(userId=UserId(r), formToken=FormToken(r))
        with closing(
            s.post(
                "https://get.cbord.com/tcu/full/funds_overview_partial.php",
                data=payload,
                timeout=TIMEOUT,
            )
        ) as response:
            response.raise_for_status()
        self.html = (
            BeautifulSoup(response.text, PARSER).find("table").find_all("tr")[1:]
        )
        self.dict = self.to_dict()

    def to_dict(self):
        def get_account_name(row):
            tags = ["(refundable)", "(non-refundable)"]  # Filter out extraneous ids
            account_name = row.find("td", class_="first-child account_name").get_text()
            for tag in tags:
                if tag in account_name:
                    account_name = account_name[: account_name.find(tag)].strip()

            return account_name

        def get_balance(row):
            balance = row.find("td", class_="last-child balance").get_text()
            return balance

        table_dict = {
            get_account_name(row): get_balance(row) for row in self.html
        }  # Formatting dict
        return table_dict

    def get_balance(self, account_name):
        return self.dict[account_name]


def auth(s):
    with closing(
        s.get(
            "https://tcu.okta.com/login/sessionCookieRedirect",
            params=dict(token=SessionToken(session), redirectUrl=RedirectUrl(session)),
            timeout=TIMEOUT,
        )
    ) as response:
        response.raise_for_status()
        soup = BeautifulSoup(response.text, PARSER)
        return {
            desired_elem.get("name"): desired_elem.get("value")
            for desired_elem in soup.find_all("input")
        }


if __name__ == "__main__":
    with requests.Session() as session:
        session.post(
            "https://get.cbord.com/tcu/Shibboleth.sso/SAML2/POST", data=auth(session)
        )
        print(
            Table(session).get_balance("Meal Plan Frog Bucks")
        )  # Get an account balance
