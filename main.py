from requests import Session
from bs4 import BeautifulSoup as bs
from config import username, password
import json
import asyncio
from contextlib import closing


# def main():
#     session = Session()
#     ###
#     login_page = session.request("GET","https://get.cbord.com/tcu/full/login.php")
#     from_uri = bs(login_page.text, "lxml").select_one("#fromURI").get("value")
#     session.headers.update({"Content-Type": "application/json"})
#     _json = {
#         "password": password,
#         "username": username,
#         "options": dict(warnBeforePasswordExpired="true",multiOptionalFactorEnroll="true")
#     }
#     json_resp = session.request("POST", "https://tcu.okta.com/api/v1/authn", json=_json)
#     session_token = json.loads(json_resp.content)['sessionToken']
#     ###
#     params = {
#         "checkAccountSetupComplete":True,
#         "token": session_token,
#         "redirectUrl": from_uri
#     }
#     redirect_resp = session.request("GET", "https://tcu.okta.com/login/sessionCookieRedirect", params=params)
#     data = {desired_elem.get("name"): desired_elem.get("value") for desired_elem in bs(redirect_resp.text, "lxml").find_all("input")}
#     session.headers.update({"Content-Type": "application/x-www-form-urlencoded"})
#     session.request("POST", "https://get.cbord.com/tcu/Shibboleth.sso/SAML2/POST", data=data)
#     ###
#     funds_home = session.request("GET", "https://get.cbord.com/tcu/full/funds_home.php")
#     soup = bs(funds_home.text, "lxml")
#     user_id = soup.find("option", text="Frog Bucks (refundable)").get("value").split(":")[2]
#     form_token = soup.find(attrs={"name": "formToken", "type": "hidden"}).get("value")
#     session.headers.update({
#             "Content-Type": "application/x-www-form-urlencoded; charset=UTF-8",
#             "Referrer": "https://get.cbord.com/tcu/full/funds_home.php",
#             "X-Requested-With": "XMLHttpRequest"
#         })
#     funds_overview = session.request("POST", "https://get.cbord.com/tcu/full/funds_overview_partial.php", data=dict(userId=user_id, formToken=form_token))
#     return table_to_dict(bs(funds_overview.text, "lxml").find("table").find_all("tr")[1:])
import aiohttp
import asyncio


async def get_from_uri(session, url):
    async with session.get(url) as response:
        html = await response.text()
        return bs(html, "lxml").select_one("#fromURI").get("value")


async def get_session_token(session, url):
    _json = {
        "password": password,
        "username": username,
        "options": dict(warnBeforePasswordExpired="true", multiOptionalFactorEnroll="true")
    }
    async with session.post(url, json=_json, headers={"Content-Type": "application/json"}) as response:
        resp = await response.text()
        return json.loads(resp)['sessionToken']


async def main():
    async with aiohttp.ClientSession() as session:
        from_uri = await get_from_uri(session, 'https://get.cbord.com/tcu/full/login.php')
        session_token = await get_session_token(session, 'https://tcu.okta.com/api/v1/authn')
        print(session_token)

if __name__ == '__main__':
    loop = asyncio.get_event_loop()
    loop.run_until_complete(main())