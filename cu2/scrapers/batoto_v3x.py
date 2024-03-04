from cu2 import config, exceptions, output
from cu2.scrapers.base import BaseChapter, BaseSeries, download_pool

from bs4 import BeautifulSoup
from functools import partial
import concurrent.futures, re, subprocess, tempfile, json, os
from requests import get
from requests.adapters import HTTPAdapter, Retry
from requests.exceptions import ConnectionError, ReadTimeout

class BatotoV3XSeries(BaseSeries):
    url_re = re.compile(r'^https?://bato.to/[0-9]+(-[0-9\-a-z]+)?$')

    def __init__(self, url, **kwargs):
        super().__init__(url, **kwargs)
        self.chapters = self.get_chapters()

    def __del__(self):
        self.req_session.close()

    def get_chapters(self):
        chapters = []
        req = self.req_session.get(self.url)
        self.soup = BeautifulSoup(req.text, config.get().html_parser)
        for chapter in self.soup.find("div", attrs = { "name": "chapter-list" }).find("astro-slot").find_all("a", attrs = { "href": lambda s: s and s.startswith("/title") }):
            chapters.append(
                BatotoV3XChapter(
                    name = self.name,
                    alias = self.alias,
                    chapter = re.search(r"ch_([0-9\.]+)$", chapter["href"]).groups()[0],
                    groups = [ x.text for x in chapter.parent.parent.find_all("a", attrs = { "href": lambda s: s and s.startswith("/g") }) ],
                    url = "https://bato.to" + chapter["href"],
                    title = chapter.text + ( chapter.parent.find("span").text if chapter.parent.find("span") else "" ),
                    upload_date = chapter.parent.parent.find("time")["time"]
                )
            )
        return chapters

    @property
    def name(self):
        return self.soup.title.text.replace(" - Read Free Manga Online at Bato.To", "")

class BatotoV3XChapter(BaseChapter):
    url_re = re.compile(r'^https?://bato.to/title/[0-9]+-[0-9\-a-z]+/[0-9]+-(vol_[0-9+]-)?ch_[0-9]+$')
    uses_pages = True

    def __del__(self):
        self.req_session.close()

    def page_list(self):
        if hasattr(self, "pages"):
            return self.pages
        if not hasattr(self, "req"):
            self.req = self.req_session.get(self.url)
        if not hasattr(self, "soup"):
            self.soup = BeautifulSoup(self.req.text, config.get().html_parser)
        return list(list(zip(*json.loads(json.loads(self.soup.find("astro-island", attrs = { "component-url": lambda s: s and s.startswith("/_astro/ImageList") })["props"])["imageFiles"][1])))[1])

    def available(self):
        if not hasattr(self, "req"):
            self.req = self.req_session.get(self.url)
        return self.req.status_code == 200

    @staticmethod
    def page_download_task(page_num, r, page_url = None):
        index, f = super(BatotoV3XChapter, BatotoV3XChapter).page_download_task(page_num, r, page_url)
        if f.name.endswith(".webp"):
            f.close()
            g = tempfile.NamedTemporaryFile(suffix = ".png", delete = False)
            subprocess.run([ "dwebp", f.name, "-o", g.name ], stdout = subprocess.DEVNULL, stderr = subprocess.DEVNULL)
            os.remove(f.name)
            return (index, g)
        return (index, f)

    def download(self):
        if not self.available():
            raise exceptions.ScrapingError
        if not hasattr(self, "pages"):
            self.pages = self.page_list()
        files = [None] * len(self.pages)
        futures = []
        with self.progress_bar(self.pages) as bar:
            for i, page in enumerate(self.pages):
                try:
                    r = self.req_session.get(page, stream = True, timeout = 18)
                except ConnectionError as e:
                    output.error("{}: connection error for page {}".format(self.alias, i))
                    raise exceptions.ScrapingError
                except ReadTimeout as e:
                    output.error("{}: connection timed out for page {}".format(self.alias, i))
                    raise exceptions.ScrapingError
                if r.status_code != 200:
                    output.error("{}: failed request for page {} due to status {}".format(self.alias, i, r.status_code))
                    raise exceptions.ScrapingError
                fut = download_pool.submit(self.page_download_task, i, r, page_url = page)
                fut.add_done_callback(partial(self.page_download_finish, bar, files))
                futures.append(fut)
            concurrent.futures.wait(futures)
            self.create_zip(files)

    def from_url(url):
        series = BatotoV3XSeries("/".join(url.split("/")[:-1]))
        for chapter in series.chapters:
            if chapter.url == url:
                return chapter
        raise exceptions.ScrapingError
