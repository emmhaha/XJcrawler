import requests
import sys
from codes.throttle import Throttle
from random import choice


class Downloader:
    def __init__(self, headers, delay=2, proxies=None, cache={}):
        self.throttle = Throttle(delay)
        self.headers = headers
        self.proxies = proxies
        self.num_retries = None
        self.cache = cache
        self.encoding = "utf-8"

    def __call__(self, url, num_retries=2):
        self.num_retries = num_retries
        try:
            result = self.cache[url]
            sys.stdout.write("Loaded from cache:%s\n" % url)
        except KeyError:
            result = None
        if result is None:
            self.throttle.wait(url)
            proxies = choice(self.proxies) if self.proxies else None
            result = self.download(url, self.headers, proxies)
            self.cache[url] = result
        return result["html"]

    def download(self, url, headers, proxies):
        sys.stdout.write("Downloading:%s\n" % url)
        try:
            resp = requests.session().get(url, headers=headers, proxies=proxies)
            resp.encoding = resp.apparent_encoding
            self.encoding = resp.encoding
            html = resp.text
            if resp.status_code >= 400:
                print("Download error:[%s] %s" % (resp.status_code, resp.text))
                html = None
                if self.num_retries and 500 <= resp.status_code < 600:
                    self.num_retries -= 1
                    return self.download(url, self.num_retries)
        except requests.exceptions.RequestException as e:
            print("Download error:", e)
            html = None
        return {"html": html, "code": resp.status_code}
