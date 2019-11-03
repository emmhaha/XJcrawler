import os
import re
import json
import zlib
import sys
import time
import threading
import requests
from urllib.parse import urlsplit
from datetime import datetime, timedelta
from redis import StrictRedis


class DiskCache:
    def __init__(self, cache_dir="cache", max_len=255, compress=True, resource_dir="cache/resource/",
                 encoding="utf-8", expires=timedelta(days=5)):
        self.cache_dir = cache_dir
        self.max_len = max_len
        self.compress = compress
        self.encoding = encoding
        self.expires = expires
        if resource_dir[len(resource_dir) - 1] != "/":
            resource_dir += "/"
        self.resource_dir = resource_dir

    def __getitem__(self, url):
        path = self.url_to_path(url)
        if os.path.exists(path):
            mode = "rb" if self.compress else "r"
            with open(path, mode) as file:
                if self.compress:
                    data = zlib.decompress(file.read()).decode(self.encoding)
                    data = json.loads(data)
                else:
                    data = json.load(file)
                exp_date = data.get("expires")
                if exp_date and datetime.strptime(exp_date, "%Y-%m-%dT%H:%M:%S") <= datetime.utcnow():
                    print("Cache expired!", exp_date)
                    raise KeyError(url + " has expired")
                return data
        else:
            raise KeyError(url + " does not exist")

    def __setitem__(self, url, result):
        result["expires"] = (datetime.utcnow() + self.expires).isoformat(timespec="seconds")
        path = self.url_to_path(url)
        folder = os.path.dirname(path)
        if not os.path.exists(folder):
            os.makedirs(folder)
        mode = "wb" if self.compress else "w"
        with open(path, mode) as file:
            if self.compress:
                data = bytes(json.dumps(result, ensure_ascii=False), self.encoding)
                file.write(zlib.compress(data))
            else:
                json.dump(result, file)

    def storage_resource(self, url, headers, filename, suffix):
        try:
            filename = re.sub("[^/0-9a-zA-Z-,;_\u4e00-\u9fa5\x3130-\x318F\u0800-\u4e00]", "_", filename)
            filename = "/".join(seg[:self.max_len] for seg in filename.split("/"))
            path = self.resource_dir + suffix[1:] + "/" + filename + suffix
            folder = os.path.dirname(path)
            if not os.path.exists(folder):
                os.makedirs(folder)

            print("Downloading resource:%s " % url)
            resource = requests.get(url, headers=headers, stream=True)
            try:
                if "Content-Range" in resource.headers:
                    content_range = resource.headers["Content-Range"].spilt("/")
                    total_length = int(content_range[len(content_range) - 1])
                else:
                    total_length = int(resource.headers["content-length"])
            except requests.exceptions.RequestException:
                total_length = None

            if os.path.exists(path) and os.path.getsize(path) == total_length:    # 跳过已下载的资源
                print(filename + suffix + " downloaded")
                return

            def show_download_progress():
                downloaded = os.path.getsize(path)
                if total_length is not None:
                    sys.stdout.write("\r%s   [%d/%d Bytes] %.2f%%" % (filename + suffix, downloaded,
                                                                      total_length, 100 * downloaded / total_length))
                    sys.stdout.flush()
                else:
                    sys.stdout.write("\r%s   [%d/unknown Bytes] " % (filename + suffix, downloaded))
                    sys.stdout.flush()

            with open(path, "wb") as file:
                for chunk in resource.iter_content(chunk_size=512*512):
                    if chunk:
                        file.write(chunk)
                        file.flush()
                        show_download_progress()
            print()
        except requests.exceptions.RequestException as e:
            print("Download error:", e)

    def url_to_path(self, url):
        components = urlsplit(url)
        path = components.path
        query = components.query
        suffix = "" if self.compress else ".html"
        if not path:
            path = "/index" + suffix
        elif path.endswith("/"):
            path += "index" + suffix
        else:
            if components.query == "":
                path += suffix
            else:
                query += suffix
        filename = components.netloc + path + query
        filename = re.sub("[^/0-9a-zA-Z-.,;_]", "_", filename)
        filename = "/".join(seg[:self.max_len] for seg in filename.split("/"))
        return os.path.join(self.cache_dir, filename)


class RedisCache:
    def __init__(self, client=None, expires=timedelta(days=5), encoding="utf-8", compress=True):
        self.client = StrictRedis(host="localhost", port=6379, db=0) if client is None else client
        self.expires = expires
        self.encoding = encoding
        self.compress = compress

    def __getitem__(self, url):
        record = self.client.get(url)
        if record:
            if self.compress:
                try:
                    record = zlib.decompress(record)
                except Exception:
                    raise KeyError(url + " cache loading error!")
            return json.loads(record.decode(self.encoding))
        else:
            raise KeyError(url + " does not exist")

    def __setitem__(self, url, result):
        data = bytes(json.dumps(result), self.encoding)
        if self.compress:
            data = zlib.compress(data)
        self.client.setex(url, self.expires, data)
