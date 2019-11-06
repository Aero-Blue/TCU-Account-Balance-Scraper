import requests
from bs4 import BeautifulSoup
import config
from contextlib import closing

# Constants
PARSER = "lxml"  # Html parser for BeautifulSoup
TIMEOUT = 5  # Request max_timeout (in seconds)


def get_session_token(session):  # Retrieve session token ID for Okta
    credentials = {  # Okta credentials (set in config.py)
        "username": config.username,
        "password": config.password,
    }
    with closing(
        session.request(
            "POST",
            "https://tcu.okta.com/api/v1/authn",
            json=credentials,
            timeout=TIMEOUT,
        )
    ) as response:
        response.raise_for_status()
        session_token = response.json()["sessionToken"]
        return session_token


def get_redirect_url(session):  # Scrape redirect URL for sso
    with closing(
        session.request(
            "GET", "https://get.cbord.com/tcu/full/login.php", timeout=TIMEOUT
        )
    ) as response:
        response.raise_for_status()
        redirect_url_tag = BeautifulSoup(response.text, PARSER).select_one(
            "#fromURI", timeout=TIMEOUT
        )
        return redirect_url_tag.get("value")


def auth_via_sso(
    session, session_token, redirect_url
):  # Get SAML response for sso request
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


def get_funds_home(
    session,
):  # Visit web homepage in order to get userId and formToken to get overview
    with closing(
        session.request(
            "GET", "https://get.cbord.com/tcu/full/funds_home.php", timeout=TIMEOUT
        )
    ) as response:
        response.raise_for_status()
        soup = BeautifulSoup(response.text, PARSER)
        user_id = (
            soup.find("option", text="Frog Bucks (refundable)")
            .get("value")
            .split(":")[2]
        )
        form_token = soup.find(attrs=dict(name="formToken", type="hidden")).get("value")
        return dict(userId=user_id, formToken=form_token)


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


def get_current_account_balances(session):  # Get html table
    session.request(
        "POST",
        "https://get.cbord.com/tcu/Shibboleth.sso/SAML2/POST",
        data=auth_via_sso(
            session, get_session_token(session), get_redirect_url(session)
        ),
        timeout=TIMEOUT,
    )  # REQUIRED request for __shibsession_ cookie
    funds_overview = get_funds_overview(session, get_funds_home(session))
    return funds_table_to_dict(funds_overview)


def funds_table_to_dict(
    html_table,
):  # Convert html table to dictionary: f{"Account name": "Balance"}
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
        get_account_name(row): get_balance(row) for row in html_table
    }  # Formatting dict

    return table_dict


def main():
    with requests.Session() as session:  # Entering Session
        balances = get_current_account_balances(session)
        # Exiting session
    for acc, bal in balances.items():  # Printing output
        print(f"{acc} | Balance: {bal}")


if __name__ == "__main__":
    main()
