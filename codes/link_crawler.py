import itertools
import threading
import requests
import time
import sys
import re
import multiprocessing
from urllib.parse import urlsplit
from bs4 import BeautifulSoup
from lxml.html import fromstring
from urllib.parse import urljoin
from urllib import robotparser
from codes.downloader import Downloader
from codes.crawl_queue import *
from codes.cache import DiskCache


def crawl_sitemap(url):  # 根据sitemap.xml文件来爬取网站
    download = Downloader()
    sitemap = download(url)
    links = re.findall("<loc>(.*?)</loc>", sitemap)
    for link in links:
        html = download(link)


def crawl_site(url, max_errors=5):  # 根据序号或id来爬取
    download = Downloader()
    num_errors = 0
    for page in itertools.count(1):
        pg_url = "{}{}".format(url, page)
        html = download(pg_url)
        if html is None:
            num_errors += 1
            if num_errors == max_errors:
                break
        else:
            num_errors = 0


SLEEP_TIME = 1
suffix = ["exe", "mp4", "aac", "mp3", "7z", "jar", "zip", "rar",
          "msi", "bmp", "gif", "jpg", "png", "avi", "flv", "rmvb"]
resource = DiskCache()


def is_resource(url):
    if not url:
        return False
    link_suffix = re.match(".*\\.({})$".format("|".join(suffix)), url)
    if link_suffix:
        return link_suffix
    return False


seen = {}


def download_resource(url, link_suffix, headers, filename=None):
    index = 1
    components = urlsplit(url)
    link_suffix = "." + link_suffix.group(1)
    if filename is None:
        filename = components.path.split("/")
        filename = filename[len(filename) - 1]
        filename = filename.split(".")[0]
    temp = filename
    while filename in seen and seen[filename] == link_suffix:  # 资源重名
        filename = temp + "_" + str(index)
        index += 1
    seen[filename] = link_suffix
    headers["Host"] = components.netloc
    resource.storage_resource(url, headers, filename, link_suffix)


def link_crawler(start_url, link_regex, headers, robots_url=None, num_retries=2, resources_dl=False,
                 cache={}, delay=2, max_threads=5, crawl_queue=DefaultQueue(), show_massage=False,
                 max_depth=1, scraper_cb=None, proxies=None):  # 根据html里记录的链接来爬取
    resources = {}

    def process_queue():
        while len(crawl_queue):
            url = crawl_queue.pop()
            if not rp or rp.can_fetch(headers["User-Agent"], url):
                depth = crawl_queue.get_depth(url) or 0
                if depth == max_depth + 1 and max_depth != -1:
                    if show_massage:
                        sys.stdout.write("Skipping %s due to depth\n" % url)
                    continue

                if is_resource(url):  # 记录资源链接
                    resources[url] = is_resource(url)
                    continue

                if hasattr(scraper_cb, "download"):  # 下载网页
                    html = scraper_cb.download(url)
                else:
                    html = download(url, num_retries=num_retries)

                if html is None:  # 跳过下载失败
                    continue
                cache.encoding = download.encoding
                if scraper_cb is not None:  # 抓取数据
                    links = scraper_cb(url, html) or []
                else:
                    links = []

                for link in get_links(html) + links:  # 从HTML里获取子链接
                    if isinstance(link, list):  # 来源于回调函数
                        filename = link[1]
                        link = link[0]
                    else:
                        filename = None

                    link_suffix = is_resource(link)
                    if link_suffix:  # 记录资源链接
                        resources[link] = [link_suffix, filename]
                        continue

                    if link and re.match(link_regex, link):
                        abs_link = urljoin(start_url, link)
                        if not crawl_queue.already_seen(abs_link) and "http" in abs_link:
                            crawl_queue.push(abs_link)
                            crawl_queue.set_depth(abs_link, depth + 1)
            else:
                print("Blocked by robots.txt", url)

    download = Downloader(delay=delay, headers=headers, cache=cache, proxies=proxies)
    threads = []
    crawl_queue.push(start_url)
    try:
        if robots_url is None:
            robots_url = "{}/robots.txt".format(start_url)
        rp = get_robots_parser(robots_url) if requests.get(robots_url) else None
    except requests.exceptions.RequestException:
        rp = None

    while threads or len(crawl_queue):
        for thread in threads:  # 去除完成任务的线程
            if not thread.is_alive():
                threads.remove(thread)
        while len(threads) < max_threads and len(crawl_queue):  # 可以建立新线程
            thread = threading.Thread(target=process_queue)
            thread.setDaemon(True)
            thread.start()
            threads.append(thread)
        # for thread in threads:
        #     thread.join()
        time.sleep(SLEEP_TIME)
    if resources_dl:  # 下载资源
        for re_link in resources:
            download_resource(re_link, resources[re_link][0], headers=headers, filename=resources[re_link][1])


def multiprocs_crawler(**kwargs):
    num_procs = multiprocessing.cpu_count()
    processes = []
    for i in range(num_procs):
        proc = multiprocessing.Process(target=link_crawler, kwargs=kwargs)
        proc.start()
        processes.append(proc)
    for proc in processes:
        proc.join()


def get_links(html):  # 获取html文件里的所有链接
    webpage_regex = re.compile("""<a[^>]+href=["'](.*?)["']""", re.IGNORECASE)
    return webpage_regex.findall(html)


def get_robots_parser(robots_url):
    rp = robotparser.RobotFileParser()
    rp.set_url(robots_url)
    rp.read()
    return rp


def bs_scraper(url, labelname, attrs=None):
    download = Downloader()
    html = download(url)
    soup = BeautifulSoup(html, "html5lib")
    temp = soup.find(labelname, attrs)
    return temp


def xpath_scraper(url, str):
    download = Downloader()
    html = download(url)
    tree = fromstring(html)
    result = tree.xpath(str)
    return result

# crawl_sitemap("http://example.python-scraping.com/sitemap.xml")
# crawl_site("http://example.python-scraping.com/view/-")
# link_crawler("http://example.python-scraping.com", ".*?")
# bs_scraper("http://example.python-scraping.com", "div", {"class": "row"})
# print(xpath_scraper("http://example.python-scraping.com", "//a/text()"))
