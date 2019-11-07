import requests
from bs4 import BeautifulSoup
import config
from contextlib import closing

# Constants
PARSER = "lxml"  # Html parser for BeautifulSoup
TIMEOUT = 5  # Request max_timeout (in seconds)


class SessionToken(object):
    def __init__(self, session):
        self.session = session
        self.credentials = dict(username=config.USERNAME, password=config.PASSWORD)

    def __str__(self):
        with closing(
            self.session.request(
                "POST",
                "https://tcu.okta.com/api/v1/authn",
                json=self.credentials,
                timeout=TIMEOUT,
            )
        ) as response:
            response.raise_for_status()
            return response.json()["sessionToken"]


class RedirectUrl(object):
    def __init__(self, session):
        self.session = session

    def __str__(self):
        with closing(
            self.session.request(
                "GET", "https://get.cbord.com/tcu/full/login.php", timeout=TIMEOUT
            )
        ) as response:
            response.raise_for_status()
            redirect_url_tag = BeautifulSoup(response.text, PARSER).select_one(
                "#fromURI", timeout=TIMEOUT
            )
            return redirect_url_tag.get("value")


class AuthSSO(object):
    def __init__(self, session, session_token, redirect_url):
        self.session = session
        self.session_token = session_token
        self.redirect_url = redirect_url
        self.query_params = dict(token=session_token, redirectUrl=redirect_url)
        self.values = self.get_cookie_response()

    def get_cookie_response(self):
        with closing(
            self.session.request(
                "GET",
                "https://tcu.okta.com/login/sessionCookieRedirect",
                params=self.query_params,
                timeout=TIMEOUT,
            )
        ) as response:
            response.raise_for_status()
            soup = BeautifulSoup(response.text, PARSER)
            return [
                (desired_elem.get("name"), desired_elem.get("value"))
                for desired_elem in soup.find_all("input")
            ]

    def __dict__(self):
        return self.values


class FundsHome(object):
    def __init__(self, session):
        self.session = session
        self.page = self.get_page()
        self.user_id = self.get_user_id()
        self.form_token = self.get_form_token()

    def get_page(self):
        with closing(
            self.session.request(
                "GET", "https://get.cbord.com/tcu/full/funds_home.php", timeout=TIMEOUT
            )
        ) as response:
            response.raise_for_status()
            return BeautifulSoup(response.text, PARSER)

    def get_user_id(self):
        return (
            self.page.find("option", text="Frog Bucks (refundable)")
            .get("value")
            .split(":")[2]
        )

    def get_form_token(self):
        return self.page.find(attrs=dict(name="formToken", type="hidden")).get("value")

    def __dict__(self):
        return dict(userId=self.user_id, formToken=self.form_token)


class FundsOverview(object):
    def __init__(self, session, session_token, redirect_url):
        self.session = session
        self.session_token = session_token
        self.redirect_url = redirect_url
        self.request_body = dict(token=session_token, redirectUrl=redirect_url)
        self.html_table = self.parse_page(self.get_overview())

    def get_overview(self):
        self.session.request(
            "POST",
            "https://get.cbord.com/tcu/Shibboleth.sso/SAML2/POST",
            data=self.request_body,
        )
        with closing(
            self.session.request(
                "POST",
                "https://get.cbord.com/tcu/full/funds_overview_partial.php",
                timeout=TIMEOUT,
            )
        ) as response:
            response.raise_for_status()
        return response.text

    @classmethod
    def parse_page(cls, html_markup):
        soup = BeautifulSoup(html_markup, PARSER)
        table = soup.find("table").find_all("tr")[1:]
        return table

    def __dict__(self):
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
            get_account_name(row): get_balance(row) for row in self.html_table
        }  # Formatting dict

        return table_dict


def sso_auth(session, session_token, redirect_url):
    params = {
        "token": session_token,
        "redirectUrl": redirect_url,
    }  # from get_session_token and get_redirect_url
    with closing(
        session.request(
            "GET",
            "https://tcu.okta.com/login/sessionCookieRedirect",
            params=params,
            timeout=TIMEOUT,
        )
    ) as response:
        response.raise_for_status()
        soup = BeautifulSoup(response.text, PARSER)
        return [
            (desired_elem.get("name"), desired_elem.get("value"))
            for desired_elem in soup.find_all("input")
        ]


def get_funds_overview(session, params):  # Funds request via php (JSON response)
    with closing(
        session.request(
            "POST",
            "https://get.cbord.com/tcu/full/funds_overview_partial.php",
            data=params,
            timeout=TIMEOUT,
        )
    ) as response:
        response.raise_for_status()
        return BeautifulSoup(response.text, PARSER).find("table").find_all("tr")[1:]


def main():
    with requests.Session() as session:  # Entering Session
        session_token = str(SessionToken(session))
        redirect_url = str(RedirectUrl(session))
        saml_response = sso_auth(session, session_token, redirect_url)
        session.request(
            "POST",
            "https://get.cbord.com/tcu/Shibboleth.sso/SAML2/POST",
            data=saml_response,
            timeout=TIMEOUT,
        )
        funds_home = FundsHome(session)
        print(
            get_funds_overview(
                session,
                dict(userId=funds_home.user_id, formToken=funds_home.form_token),
            )
        )


if __name__ == "__main__":
    main()
