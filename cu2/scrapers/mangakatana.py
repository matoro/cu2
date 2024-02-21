from cu2 import config, exceptions, output
from cu2.scrapers.base import BaseChapter, BaseSeries, download_pool

from bs4 import BeautifulSoup
from functools import partial
import concurrent.futures, re
from requests import get
from requests.adapters import HTTPAdapter, Retry

class MangakatanaSeries(BaseSeries):
    url_re = re.compile(r'^https?://mangakatana.com/manga/[0-9a-z-]+\.[0-9]+$')

    def __init__(self, url, **kwargs):
        super().__init__(url, **kwargs)
        self.chapters = self.get_chapters()

    def __del__(self):
        self.req_session.close()

    def get_chapters(self):
        chapters = []
        req = self.req_session.get(self.url)
        self.soup = BeautifulSoup(req.text, config.get().html_parser)
        for chapter in self.soup.find("div", class_="chapters").find_all("a"):
            try:
                chapters.append(
                    MangakatanaChapter(
                        name = self.name,
                        alias = self.alias,
                        chapter = re.search(r"^Chapter ([0-9\.]+)", chapter.text).groups()[0],
                        groups = [],
                        url = chapter["href"],
                        title = chapter.text,
                        upload_date = chapter.parent.parent.parent.find("div", class_="update_time").text
                    )
                )
            except AttributeError:
                from pdb import set_trace ; set_trace()
        return chapters

    @property
    def name(self):
        return self.soup.title.text

class MangakatanaChapter(BaseChapter):
    url_re = re.compile(r'^https?://mangakatana.com/manga/[0-9a-z-]+\.[0-9]+/c[0-9\.]+$')
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
        return next(x.text for x in self.soup.find_all("script") if re.search("var thzq=", x.text)).splitlines()[7].split(";")[0][11:-2].replace("'", "").split(",")

    def available(self):
        if not hasattr(self, "req"):
            self.req = self.req_session.get(self.url)
        if not hasattr(self, "soup"):
            self.soup = BeautifulSoup(self.req.text, config.get().html_parser)
        if not hasattr(self, "pages"):
            self.pages = self.page_list()
        return len(self.pages) > 0 and "coming_soon" not in self.pages[0]

    def download(self):
        if not self.available():
            raise exceptions.ScrapingError
        files = [None] * len(self.pages)
        futures = []
        with self.progress_bar(self.pages) as bar:
            for i, page in enumerate(self.pages):
                try:
                    r = self.req_session.get(page, stream = True, timeout = 18)
                except requests.exceptions.ConnectionError as e:
                    output.error("{}: connection error for page {}".format(self.alias, i))
                    raise exceptions.ScrapingError
                except requests.exceptions.ReadTimeout as e:
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
        series = MangakatanaSeries("/".join(url.split("/")[:-1]))
        for chapter in series.chapters:
            if chapter.url == url:
                return chapter
        raise exceptions.ScrapingError
