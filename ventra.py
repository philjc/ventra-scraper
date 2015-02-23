from __future__ import print_function
import json
import os

import requests
from lxml.html import fromstring


class Ventra:
    base_headers = {
        "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10.9; rv:35.0) Gecko/20100101 Firefox/35.0",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Accept-Language": "en-US,en;q=0.5",
        "Accept-Encoding": "gzip, deflate"
    }

    def __init__(self, user_name, password, ventra_url="https://www.ventrachicago.com/"):
        self.session = requests.Session()
        self.ventra_url = ventra_url
        self.user_name = user_name
        self.password = password

    def login(self):
        # we've already logged in, so get out of here
        if hasattr(self, 'redirect_url'):
            return

        login_payload = {
            "__CALLBACKID": "CT_Header$ccHeaderLogin",
            "__CALLBACKPARAM": "",
            "__EVENTARGUMENT": "",
            "__EVENTTARGET": "",
            "pc": "false",
            "f": "search",
            "p": self.password,
            "u": self.user_name
        }

        home_page = self.session.get(self.ventra_url, headers=Ventra.base_headers)
        home_page_response = fromstring(home_page.content)
        self.verification_token = Ventra.__get_attribute(home_page_response.cssselect("#hdnRequestVerificationToken"), 'value')

        login_headers = self.__headers_with_verification_token(self.ventra_url)

        login_response = self.session.post(self.ventra_url, data=login_payload, headers=login_headers)
        json_response = json.loads(login_response.content[2:])

        self.redirect_url = json_response['Redir']
        self.session.get(self.redirect_url, headers=Ventra.base_headers)

    def get_info(self):
        ret_val = {}
        ret_val.update(self.get_transit_value())
        ret_val.update(self.get_transit_history())
        return ret_val

    def get_transit_value(self):
        self.login()
        transit_value = self.session.post("https://www.ventrachicago.com/ajax/NAM.asmx/GetTransitInfo",
                                          data=json.dumps({"s": 1, "IncludePassSupportsTal": True}),
                                          headers=(self.__xhr_headers(self.redirect_url)))
        return Ventra.__handle_json_response(transit_value.json())

    def get_transit_history(self):
        self.login()
        transit_history = self.session.post("https://www.ventrachicago.com/ajax/NAM.asmx/GetTransactionHistorySimple",
                                            data=json.dumps({"s": 1, "PageSize": 5, "PageNum": 1}),
                                            headers=(self.__xhr_headers(self.redirect_url)))

        return {"transit_history": Ventra.__handle_json_response(transit_history.json())}

    def __headers_with_verification_token(self, referer_url):
        headers = {
            "Referer": referer_url,
            "RequestVerificationToken": self.verification_token,
        }
        headers.update(Ventra.base_headers)
        return headers

    def __xhr_headers(self, referer_url):
        headers = {'Content-Type': 'application/json'}
        headers.update(self.__headers_with_verification_token(referer_url))
        return headers

    @staticmethod
    def __get_attribute(el, att, default=None):
        return el.pop().get(att) if el else default

    @staticmethod
    def __handle_json_response(json_doc):
        d = json_doc['d']
        if not d['success']:
            raise Exception(d['error'])

        return d['result']


def _main():
    user_name = os.getenv("VENTRA_USER_NAME")
    if user_name is None:
        user_name = raw_input("Enter Username: ")

    password = os.getenv("VENTRA_PASSWORD")
    if password is None:
        from getpass import getpass

        password = getpass("Enter Password: ")

    ventra = Ventra(user_name, password)
    print(json.dumps(ventra.get_info(), indent=2))


if __name__ == "__main__":
    _main()