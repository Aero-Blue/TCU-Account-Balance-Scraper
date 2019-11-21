import configparser
import requests
from bs4 import BeautifulSoup

# Constants
PARSER = "lxml"  # Html parser for BeautifulSoup
session = requests.Session()


def get_session_token(**kwargs):
    with session.post("https://tcu.okta.com/api/v1/authn", json=kwargs,) as response:
        token = response.json()["sessionToken"]
        return token


def get_redirect_url():
    with session.get("https://get.cbord.com/tcu/full/login.php") as response:
        page = BeautifulSoup(response.text, PARSER)
        redirect_url = page.select_one("#fromURI").get("value")
        return redirect_url


def get_user_values():
    with session.get("https://get.cbord.com/tcu/full/funds_home.php") as response:
        page = BeautifulSoup(response.text, PARSER)
        form_token = page.find(attrs=dict(name="formToken", type="hidden")).get("value")
        user_id = (
            page.find("option", text="Frog Bucks (refundable)")
            .get("value")
            .split(":")[2]
        )
        return user_id, form_token


def session_redirect(**kwargs):
    with session.get(
        "https://tcu.okta.com/login/sessionCookieRedirect", params=kwargs
    ) as response:
        page = BeautifulSoup(response.text, PARSER)
        desired_elems = {
            desired_elem.get("name"): desired_elem.get("value")
            for desired_elem in page.find_all("input")
        }
        session.post(
            "https://get.cbord.com/tcu/Shibboleth.sso/SAML2/POST", data=desired_elems
        )


def get_account_balances(**kwargs):
    with session.get("https://get.cbord.com/tcu/full/funds_home.php") as response:
        response = session.post(
            "https://get.cbord.com/tcu/full/funds_overview_partial.php", data=kwargs
        )
        page = BeautifulSoup(response.text, PARSER)
        table = page.select("tbody > tr")
    return table


if __name__ == "__main__":
    cfg = configparser.ConfigParser()
    cfg.read("config.ini")
    session_token = get_session_token(**cfg["CREDENTIALS"])
    redirect_url = get_redirect_url()
    session_redirect(token=session_token, redirectUrl=redirect_url)
    user_id, form_token = get_user_values()
    account_balances = get_account_balances(userId=user_id, formToken=form_token)
    for balance in account_balances:
        print(balance.text)
