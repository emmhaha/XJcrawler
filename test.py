from codes.callback import *
from codes.link_crawler import *
from codes.cache import *
from lxml.html import fromstring
import requests
import re
from PyQt5.QtGui import *
from PyQt5.QtCore import *
from selenium import webdriver
from selenium.webdriver.firefox import options
from codes.decode import *
import time


def main():
    headers = {
        # "Accept": "text/html, application/xhtml+xml, application/xml; q=0.9, */*; q=0.8",
        # "Accept-Encoding": "gzip, deflate",
        # "Accept-Language": "zh-Hans-CN, zh-Hans; q=0.8, en-US; q=0.5, en; q=0.3",
        # "Cache - Control": "max - age = 0",
        # "Connection": "Keep - Alive",
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:66.0) Gecko/20100101 Firefox/66.0"
    }
    disk_cache = DiskCache(compress=False, expires=timedelta(seconds=1))
    browser_crawler = BrowserCrawler(cache=disk_cache)
    i = 0
    while True:
        link_crawler("http://share.fhyx.hk/item/419.html#rent", "", show_massage=False,
                     max_depth=0, crawl_queue=DefaultQueue(), headers=headers, scraper_cb=browser_crawler,
                     cache=disk_cache, delay=1, max_threads=1, resources_dl=False)
        i += 1
        print("times: " + str(i) + "\n")
        time.sleep(60)


#     multiprocs_crawler(start_url="http://example.python-scraping.com", link_regex="", crawl_queue=RedisQueue(),
#                        max_depth=-1, scraper_cb=None, cache=DiskCache(), delay=0)
#
#


if __name__ == "__main__":
    main()
