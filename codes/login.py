from lxml.html import fromstring
from selenium import webdriver
from selenium.webdriver.firefox import options
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions
import requests
import os
import json


class Login:
    def __init__(self):
        option = options.Options()
        option.add_argument('-headless')
        self.LOGIN_URL = "http://example.python-scraping.com/user/login"
        self.LOGIN_NAME = "example@python-scraping.com"
        self.LOGIN_PASSWORD = "example"
        self.driver = webdriver.Firefox(options=None)

    def selenium_login(self):
        self.driver.get(self.LOGIN_URL)
        self.driver.find_element_by_id("auth_user_email").send_keys(self.LOGIN_NAME)
        self.driver.find_element_by_id("auth_user_password").send_keys(self.LOGIN_PASSWORD + Keys.RETURN)
        pg_loaded = WebDriverWait(self.driver, 10).until(
            expected_conditions.presence_of_element_located((By.ID, "results"))
        )
        assert "login" not in self.driver.current_url
        print(pg_loaded.text)

    def requests_login(self, session=None):
        if session is None:
            html = requests.get(self.LOGIN_URL)
        else:
            html = session.get(self.LOGIN_URL)

        data = self.parse_form(html.content)
        data["email"] = self.LOGIN_NAME
        data["password"] = self.LOGIN_PASSWORD

        if session is None:
            response = requests.post(self.LOGIN_URL, data, cookies=html.cookies)
        else:
            response = session.post(self.LOGIN_URL, data)
        assert "login" not in response.url
        return response, session

    @staticmethod
    def load_sessions(session_filename):
        cookies = {}
        if os.path.exists(session_filename):
            json_data = json.loads(open(session_filename, "rb").read())
            for window in json_data.get("windows", []):
                for cookie in window.get("cookies", []):
                    cookies[cookie.get("name")] = cookie.get("value")
        else:
            print("Session filename does not exist:", session_filename)
        return cookies

    @staticmethod
    def parse_form(html):
        tree = fromstring(html)
        data = {}
        for e in tree.cssselect("form input"):
            if e.get("name"):
                data[e.get("name")] = e.get("value")
        return data


# se = requests.Session()
# login = Login()
# login.selenium_login()
# print(se.cookies)
# re, se = login.login(se)
# print(se.cookies)
# html = requests.get("http://example.python-scraping.com", cookies=cookies)
# tree = fromstring(html.content)
# a = tree.cssselect("ul#navbar li a")[0].text
# print(a)
