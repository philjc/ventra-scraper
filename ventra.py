from __future__ import print_function
import json
import os

import requests
from lxml.html import fromstring


_ventra_url = "https://www.ventrachicago.com/"
_base_headers = {
    "Host": "www.ventrachicago.com",
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10.9; rv:35.0) Gecko/20100101 Firefox/35.0",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.5",
    "Accept-Encoding": "gzip, deflate"
}


def _get_login_payload(user_name, password):
    return {
        "__CALLBACKID": "CT_Header$ccHeaderLogin",
        "__CALLBACKPARAM": "",
        "__EVENTARGUMENT": "",
        "__EVENTTARGET": "",
        "f": "search",
        "p": password,
        "pc": "false",
        "u": user_name
    }


def _handle_json_response(json_doc):
    d = json_doc['d']
    if not d['success']:
        raise Exception(d['error'])

    return d['result']


def _get_attribute(el, att, default=None):
    return el.pop().get(att) if el else default


def get_info(user_name, password, include_account_balance=True, include_transit_history=True):
    if not (include_transit_history or include_account_balance):
        raise Exception("Noting to do, you haven't requested any information")

    session = requests.Session()
    home_page = session.get(_ventra_url, headers=_base_headers)
    home_page_response = fromstring(home_page.content)
    verification_token = _get_attribute(home_page_response.cssselect("#hdnRequestVerificationToken"), 'value')

    login_headers = {
        "Referer": _ventra_url,
        "RequestVerificationToken": verification_token,
    }
    login_headers.update(_base_headers)

    login_response = session.post(_ventra_url, data=_get_login_payload(user_name, password), headers=login_headers)
    json_response = json.loads(login_response.content[2:])

    redirect_url = json_response['Redir']

    session.get(redirect_url, headers=_base_headers)
    login_headers.update({"Referer": redirect_url, 'Content-Type': 'application/json'})

    transit_value = session.post("https://www.ventrachicago.com/ajax/NAM.asmx/GetTransitInfo",
                                 data=json.dumps({"s": 1, "IncludePassSupportsTal": True}),
                                 headers=login_headers) if include_account_balance else None

    transit_history = session.post("https://www.ventrachicago.com/ajax/NAM.asmx/GetTransactionHistorySimple",
                                   data=json.dumps({"s": 1, "PageSize": 5, "PageNum": 1}),
                                   headers=login_headers) if include_transit_history else None

    ret_val = {}
    if transit_value:
        ret_val.update(_handle_json_response(transit_value.json()))
    if transit_history:
        ret_val.update({"transit_history": _handle_json_response(transit_history.json())})

    return ret_val


def _main():
    user_name = os.getenv("VENTRA_USER_NAME")
    if user_name is None:
        user_name = raw_input("Enter Username: ")

    password = os.getenv("VENTRA_PASSWORD")
    if password is None:
        from getpass import getpass

        password = getpass("Enter Password: ")

    print(json.dumps(get_info(user_name, password), indent=2))


if __name__ == "__main__":
    _main()