import csv
import re
import base64
import pytesseract
import requests
import io
from bs4 import BeautifulSoup
from io import BytesIO
from PIL import Image
from urllib.parse import urlsplit

from selenium.common.exceptions import TimeoutException

from codes.cache import *
from lxml.html import fromstring
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.firefox import options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions
from codes.throttle import Throttle
from codes.decode import *
from playsound import playsound


class CsvCallback:
    def __init__(self):
        self.writer = csv.writer(open("./data/data.csv", "w", newline=""))
        # self.fields = ("country_or_district", "area", "population", "capital")
        # self.writer.writerow(self.fields)
        # self.driver = webdriver.Firefox(options=None)

    def __call__(self, url, html):
        urls = []
        if re.search("(toplist|playlist)", url):
            components = urlsplit(url)
            tree = fromstring(html)
            temp = tree.cssselect("ul.f-hide a")
            for t in temp:
                song = str(t.text_content()).encode("gbk", "ignore").decode("gbk")
                href = t.get("href")
                self.writer.writerow([song, components.scheme + "://" + components.netloc + href])
                song_id = href.split('=')[1]
                url = get_song_url(song_id) if get_song_url(song_id) else get_song_url(getOnePatam(song)[0]["id"])
                urls.append([url, song])
                print(str(len(urls)) + " The url of " + song + " have been obtained")
                if len(urls) == 5:
                    break
        return urls


class BrowserCrawler:
    def __init__(self, cache=RedisCache(), delay=2):
        option = options.Options()
        option.add_argument('-headless')
        self.cache = cache
        self.throttle = Throttle(delay)
        self.driver = webdriver.Firefox(options=option)
        self.driver.set_page_load_timeout(20)

        self.writer = csv.writer(open("./data/data.csv", "w", newline=""))
        # self.fields = ("country_or_district", "area", "population", "capital")
        # self.writer.writerow(self.fields)

    def __del__(self):
        try:
            self.driver.close()
            self.driver.quit()
            print('webdriver close and quit success!')
        except Exception as e:
            print(e)

    def __call__(self, url, html):
        is_free = False
        tree = fromstring(html)
        temp = tree.cssselect("ul.acountListContainer li div.accountRight em")
        for i in range(len(temp)):
            print(temp[i].text)
            if i + 1 < len(temp) and temp[i].text == "可用" and temp[i + 1].text == "4":
                is_free = True
                requests.get("http://miaotixing.com/trigger?id=trPKqfH&text=" + "检测到可用账号")
                # playsound('D:/MY/Projects/PyCharm/untitled/cache/resource/mp3/123.mp3')
                # break
            elif is_free:
                is_free = False
                requests.get("http://miaotixing.com/trigger?id=trPKqfH&text=" + "已租完")

        # row = []
        # if re.search("/default/view/", url):
        #     tree = fromstring(html)
        #     for field in self.fields:
        #         temp = tree.xpath("//tr[@id='places_%s__row']/td[@class='w2p_fw']/text()" % field)
        #         if temp:
        #             row.append(temp[0])
        #     self.writer.writerow(row)

    def download(self, url):
        try:
            result = self.cache[url]
            print("Loaded from cache:", url)
        except KeyError:
            result = None
        if result is None:
            self.throttle.wait(url)
            result = self.get_html(url)
            self.cache[url] = result
        return result["html"]

    def get_html(self, url):
        print("Downloading:", url)
        # self.driver.get(url)
        try:
            if self.driver.current_url is None or self.driver.current_url != url:
                self.driver.get(url)
            else:
                self.driver.refresh()
        except TimeoutException:
            print('time out after 20 seconds when loading page！\n')
            self.driver.execute_script("window.stop()")
        return {"html": self.driver.page_source, "code": None}
