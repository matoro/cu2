from bs4 import BeautifulSoup
from cu2 import config, exceptions, output, version
from cu2.scrapers.base import BaseChapter, BaseSeries, download_pool
from functools import partial
import concurrent.futures
import json
import re
import requests

PAGE_ONE = "-page-1"

# Python translation of vm.ChapterDisplay
# see notes/mangasee.js
def _mangasee_decode_chap_num(chap_code):
    t = int(chap_code[1:-1])
    n = chap_code[len(chap_code) - 1]
    return str(t) if "0" == n else str(t) + "." + n

# Python translation of vm.ChapterURLEncode
# see notes/mangasee.js
def _mangasee_decode_chap_url(chap_code):
    index = "";
    t = chap_code[0:1]
    if t != "1":
        index = "-index-" + t
    n = int(chap_code[1:-1])
    m = ""
    a = chap_code[len(chap_code) - 1]
    if a != "0":
        m = "." + a
    return "-chapter-" + str(n) + m + index + PAGE_ONE + ".html"

# chapter URLs may have the chapter number zero-padded or not;
# they render the same with no redirects.  thus we need a
# more complicated comparison test to see if two chapter URLs
# are equal
def _mangasee_chapters_are_equal(one, two):
    one_split = one[:-12].split("-")
    two_split = two[:-12].split("-")
    if "index" not in one and "index" not in two:
        return float(one_split[-1]) == float(two_split[-1])
    return int(one_split[-1]) == int(two_split[-1]) and float(one_split[-3]) == float(two_split[-3])

class MangaseeSeries(BaseSeries):
    url_re = re.compile(r'https?://mangasee123\.com/manga/.+')

    def __init__(self, url, **kwargs):
        super().__init__(url, **kwargs)
        spage = self.req_session.get(url, headers = { "User-Agent": version.version_string() })
        if spage.status_code == 404:
            raise exceptions.ScrapingError
        self.soup = BeautifulSoup(spage.text, config.get().html_parser)
        self.chapters = self.get_chapters()

    def get_chapters(self):
        # the new React-based site uses "chapter codes" which encode both
        # the chapter number, the URL, and season (where applicable)
        # the original JS implementations can be found at notes/mangasee.js

        # attempt to extract the index name first, as it is guaranteed to fail
        # for bad series URLs
        try:
            index_name = re.search(r"vm\.IndexName = \"(.+?)\";",
                                    str(self.soup.find_all("script")[-1].contents)).groups()[0]
        except AttributeError:
            output.error(self.alias + ': Unable to extract series index name')
            raise exceptions.ScrapingError
        chap_codes = re.findall(r"\"Chapter\":\"([0-9]+?)\"",
                                str(self.soup.find_all("script")[-1].contents))
        chap_types = re.findall(r"\"Type\":\"(.+?)\"",
                                str(self.soup.find_all("script")[-1].contents))
        chap_dates = re.findall(r"\"Date\":\"(.+?)\"",
                                str(self.soup.find_all("script")[-1].contents))
        chapters = []
        season_names = []
        for i, chap_code in enumerate(chap_codes):
            chap_url = "https://mangasee123.com/read-online/" + index_name + \
                       _mangasee_decode_chap_url(chap_code)
            # unfortunately complex heuristic for identifying if a work is multi-season
            # or not.  originally this just check if it had some chapter prefix other
            # than "Chapter", but it seems there are some series that were using
            # a special name during the old site but the site admins just got lazy
            # and started using "Chapter" for everything on the new site.  so instead,
            # check if there is at least one digit in the chapter type before
            # declaring that type a "season".
            # https://stackoverflow.com/a/11232474/6214870
            if any(char.isdigit() for char in chap_types[i]):
                if chap_types[i] not in season_names:
                    season_names.append(chap_types[i])
            chap_num = _mangasee_decode_chap_num(chap_code)
            chap_name = chap_types[i] + " " + chap_num
            chap_date = chap_dates[i]
            result = MangaseeChapter(name=self.name,
                                     alias=self.alias,
                                     chapter=chap_num,
                                     url=chap_url,
                                     title=chap_name,
                                     groups=[],
                                     upload_date=chap_date)
            chapters.append(result)

        # the chapters in the first season of a multi-season title
        # are indistinguishable from a non-multi-season title.  thus
        # we must retroactively reanalyze all chapters and adjust
        # chapter numbers if *any* are multi-season
        if len(season_names) > 0:
            # chapters are sorted in reverse chronological order
            working_season = 0
            for i, chapter in enumerate(chapters):
                try:
                    if chap_types[i] != season_names[working_season]:
                        working_season += 1
                except IndexError:
                    # heuristic for season identification failed
                    # this is a TODO.  sample title: Kiba no Tabishounin: The Arms Peddler
                    output.error('Unable to identify season delineation: {}'.format(self.alias))
                    raise exceptions.ScrapingError

                # working_season will be zero-indexed, but seasons should start from 1
                chapter.chapter = str(len(season_names) - working_season).zfill(2) + "." + chapter.chapter.zfill(3)

        return chapters

    @property
    def name(self):
        try:
            return re.match(r"(.+) \| MangaSee",
                            self.soup.find("title").text).groups()[0]
        except AttributeError:
            raise exceptions.ScrapingError


class MangaseeChapter(BaseChapter):
    url_re = re.compile((r'https?://mangasee123\.com/'
                        r'read-online/.+-chapter-[0-9\.]+-page-[0-9]+\.html'))
    upload_date = None
    uses_pages = True

    def download(self):
        if not getattr(self, "cpage", None):
            self.cpage = self.req_session.get(self.url, headers = { "User-Agent": version.version_string() })
        if not getattr(self, "soup", None):
            self.soup = BeautifulSoup(self.cpage.text,
                                      config.get().html_parser)

        current_chap_code = re.search(r"vm.CurChapter = {\"Chapter\":\"([0-9]+)\"", \
                            str(self.soup.find_all("script")[-1].contents)).groups()[0]
        chap_codes = re.findall(r"\"Chapter\":\"([0-9]+?)\"",
                                str(self.soup.find_all("script")[-1].contents))
        chap_pages = re.findall(r"\"Page\":\"([0-9]+?)\"",
                                str(self.soup.find_all("script")[-1].contents))

        # find number of pages in this chapter
        num_pages = 0
        for i, chap in enumerate(chap_codes):
            if current_chap_code == chap:
                num_pages = int(chap_pages[i])
                break

        # we weren't able to identify the number of pages
        if num_pages <= 0:
            output.error('Failed to extract pages for chapter code: {}'.format(current_chap_code))
            raise exceptions.ScrapingError

        # we need the pre-decimal portion of the chapter number to be padded to 4 digits
        current_chap_num = _mangasee_decode_chap_num(current_chap_code)
        if "." in current_chap_num:
            current_chap_num = current_chap_num.zfill(6)
        else:
            current_chap_num = current_chap_num.zfill(4)

        # three more pieces of data we need to extract.  first is the "directory" attribute
        # which seems to be used for multi-season works.  it is an empty string for
        # non-multi-season works.
        directory = re.search(r"vm.CurChapter.+?\"Directory\":\"(.*?)\"", \
                              str(self.soup.find_all("script")[-1].contents)).groups()[0]
        if directory == "":
            directory = "/"
        else:
            directory = "/" + directory + "/"

        # second is the domain name the images are hosted on.  they have been moved off of
        # blogspot and now use cycle round-robin to servers behind cloudflare.
        domain = re.search(r"vm.CurPathName = \"(.+?)\";", \
                           str(self.soup.find_all("script")[-1].contents)).groups()[0]

        # third is the index name.
        index_name = re.search(r"vm\.IndexName = \"(.+?)\";",
                                str(self.soup.find_all("script")[-1].contents)).groups()[0]

        # now we're finally read to start assembling the image urls.
        pages = []
        for i in range(0, num_pages):
            pages.append("https://" + domain + "/manga/" + index_name + directory + \
                         current_chap_num + "-" + str(i + 1).zfill(3) + ".png")

        futures = []
        files = [None] * len(pages)
        with self.progress_bar(pages) as bar:
            for i, page in enumerate(pages):
                retries = 0
                while retries < 5:
                    try:
                        r = self.req_session.get(page, stream=True)
                        if r.status_code != 200:
                            output.warning('Failed to fetch page with status {}, retrying #{}'
                                            .format(str(r.status_code), str(retries)))
                            retries += 1
                        else:
                            break
                    except (requests.exceptions.ConnectionError, requests.exceptions.ReadTimeout):
                        retries += 1
                if r.status_code != 200:
                    output.error('Failed to fetch page with status {}, giving up'
                                    .format(str(r.status_code)))
                    raise exceptions.ScrapingError
                fut = download_pool.submit(self.page_download_task, i, r)
                fut.add_done_callback(partial(self.page_download_finish,
                                              bar, files))
                futures.append(fut)
            concurrent.futures.wait(futures)
            self.create_zip(files)

    def from_url(url):
        cpage = requests.get(url, headers = { "User-Agent": version.version_string() })
        soup = BeautifulSoup(cpage.text, config.get().html_parser)
        iname = soup.find("a", class_="btn btn-sm btn-outline-secondary")["href"]
        series = MangaseeSeries("https://mangasee123.com" + iname)
        for chapter in series.chapters:
            if _mangasee_chapters_are_equal(chapter.url, url):
                return chapter
        raise exceptions.ScrapingError

    # new site no longer returns 404 on bad chapter
    def available(self):
        if not getattr(self, "cpage", None):
            self.cpage = self.req_session.get(self.url, headers = { "User-Agent": version.version_string() })
        if not getattr(self, "soup", None):
            self.soup = BeautifulSoup(self.cpage.text,
                                      config.get().html_parser)
        if self.soup.find("title").text == "404 Page Not Found":
            return False
        return True
