from cu2 import config, exceptions, output
from cu2.scrapers.base import BaseChapter, BaseSeries, download_pool
import json, re, requests, time, concurrent.futures
from functools import partial
from tempfile import NamedTemporaryFile
from cu2.version import __version__, __upstream_link__

debug = False

def _make_api_request(url, session = None, extra_headers = { }):
    while True:
        if debug:
            output.warning("Mangadex API: requesting -> " + url)
        try:
            if session:
                r = session.get('https://api.mangadex.org/' + url.strip('/'), headers = { **MangadexV5Series.headers, **extra_headers })
            else:
                r = requests.get('https://api.mangadex.org/' + url.strip('/'), headers = { **MangadexV5Series.headers, **extra_headers })
        except requests.exceptions.ConnectionError:
            output.error("Mangadex API: request to endpoint failed: {}".format(url))
            raise exceptions.ScrapingError
        if r.status_code == 200:
            return r
        elif r.status_code == 429:
            retry_delay = int(r.headers["retry-after"])
            output.warning("Mangadex API: wait {} seconds...".format(retry_delay))
            time.sleep(retry_delay)
        else:
            output.error("Mangadex API: got bad status code {}".format(r.status_code))
            return r

# unlike _make_api_request, this function directly returns the decoded JSON
# rather than a requests.Response object
def _make_paginated_api_request(url, session = None, extra_headers = { }):
    results = [ ]
    offset = 0
    limit = 100
    while True:
        page = _make_api_request(url + "&offset=" + str(offset) + "&limit=" + str(limit),
            session = session, extra_headers = extra_headers)
        j = _decode_json(page.text)
        if not page.json().get("total"):
            return j
        results += j
        offset += 100
        if offset >= page.json()["total"]:
            break
    return results

def _decode_json(string):
    try:
        try:
            return json.loads(string)["data"]
        except json.decoder.JSONDecodeError:
            output.error(self.alias + ": Mangadex API: failed to decode JSON response")
            raise exceptions.ScrapingError
        except KeyError:
            output.error(self.alias + ": Mangadex API: request returned status: " + json.loads(string)["result"])
            raise exceptions.ScrapingError
    except NameError:
        output.error("Mangadex API: request returned status: " + json.loads(string)["result"])

class MangadexV5Series(BaseSeries):
    url_re = re.compile(r'^https?://mangadex\.org/(title/[0-9a-fA-F]{8}(-[a-fA-F0-9]{4}){3}-[a-fA-F0-9]{12}(/.+)?|manga/[0-9]+|title/[0-9]+/.+(/chapters/?)?)$')
    headers = { "User-Agent": "cu2/{} {}".format(__version__, __upstream_link__) }

    def __init__(self, url, **kwargs):
        super().__init__(url, **kwargs)
        self._get_page(self.url)
        self.chapters = self.get_chapters()

    def __del__(self):
        self.req_session.close()

    @staticmethod
    def _translate_manga_id(manga_id):
        try:
            legacy_manga_id = int(manga_id)
            if debug:
                output.warning("Mangadex API: querying legacy series {} -> /legacy/mapping".format(str(legacy_manga_id)))
            r = requests.post("https://api.mangadex.org/legacy/mapping", json = { "type": "manga", "ids": [ legacy_manga_id ] })
            try:
                return r.json()["data"][0]["attributes"]["newId"]
            except KeyError:
                return "invalid"
        except ValueError:
            return manga_id

    def _get_page(self, url):
        if len(url.rstrip('/').split('/')) == 7:
            manga_id = MangadexV5Series._translate_manga_id(url.rstrip('/').split('/')[-3])
        elif len(url.rstrip('/').split('/')) == 6:
            manga_id = MangadexV5Series._translate_manga_id(url.rstrip('/').split('/')[-2])
        elif url.rstrip('/').split('/')[-1].isdigit():
            manga_id = MangadexV5Series._translate_manga_id(url.rstrip('/').split('/')[-1])
        else:
            manga_id = url.rstrip('/').split('/')[-1]
        r = _make_api_request('/manga/' + manga_id, session = self.req_session)
        # this bit is duplicated in _decode_json because at this point we don't have
        # enough data from the API to call self.alias
        try:
            self.json = json.loads(r.text)
        except json.decoder.JSONDecodeError:
            output.error("Mangadex API: failed to decode JSON response")
            raise exceptions.ScrapingError

    def _get_group_names(self, groups):
        if not hasattr(self, "group_names"):
            self.group_names = {}
        ret_group_names = []
        for group in groups:
            if not group in self.group_names:
                r = _make_api_request("/group/" + group, session = self.req_session)
                self.group_names[group] = _decode_json(r.text)["attributes"]["name"]
            ret_group_names.append(self.group_names[group])
        return ret_group_names

    def get_chapters(self):
        chapter_data = _make_paginated_api_request('/chapter?translatedLanguage[]=en&includeExternalUrl=0&manga=' + self.json["data"]["id"],
            session = self.req_session)
        chapters = []
        for chapter in chapter_data:
            chapters.append(
                MangadexV5Chapter(
                    name = self.name,
                    alias = self.alias,
                    chapter = chapter["attributes"]["chapter"] if chapter["attributes"]["chapter"] is not None else "0",
                    url = "https://mangadex.org/chapter/" + chapter["id"],
                    groups = self._get_group_names([ relationship["id"] for relationship in chapter["relationships"]
                        if relationship["type"] == "scanlation_group" ]),
                    title = None if chapter["attributes"]["title"] == "" else chapter["attributes"]["title"],
                    upload_date = chapter["attributes"]["updatedAt"]
                )
            )
        return chapters

    @property
    def name(self):
        return self.json["data"]["attributes"]["title"]["en"]

class MangadexV5Chapter(BaseChapter):
    url_re = re.compile(r'^https://mangadex\.org/chapter/[0-9a-fA-F]{8}(-[a-fA-F0-9]{4}){3}-[a-fA-F0-9]{12}$')
    uses_pages = True

    def __del__(self):
        self.req_session.close()

    @staticmethod
    def page_download_task(page_num, r, page_url = None):
        ext = BaseChapter.guess_extension(r.headers.get("content-type"))
        f = NamedTemporaryFile(suffix = ext, delete = False)
        download_start_time = int(time.time())
        try:
            for chunk in r.iter_content(chunk_size = 4096):
                if chunk:
                    f.write(chunk)
        except ConnectionError:
            f.flush()
            # page failed to download, send failure report
            if debug:
                output.warning("Mangadex API: send failure report")
            requests.post("https://api.mangadex.network/report", data =
                {
                    "url": page_url,
                    "success": False,
                    "bytes": f.tell(),
                    "duration": int(time.time()) - download_start_time,
                    "cached": True if r.headers.get("X-Cache") else False
                }
            )
            raise exceptions.ScrapingError
        f.flush()
        # page download successful, send success report
        if debug:
            output.warning("Mangadex API: send success report")
        requests.post("https://api.mangadex.network/report", data =
            {
                "url": page_url,
                "success": True,
                "bytes": f.tell(),
                "duration": int(time.time()) - download_start_time,
                "cached": True if r.headers.get("X-Cache") else False
            }
        )
        f.close()
        r.close()
        return ((page_num, f))

    @staticmethod
    def _translate_chapter_id(chapter_id):
        try:
            legacy_chapter_id = int(chapter_id)
            if debug:
                output.warning("Mangadex API: querying legacy chapter {} -> /legacy/mapping".format(str(legacy_chapter_id)))
            r = requests.post("https://api.mangadex.org/legacy/mapping", json = { "type": "chapter", "ids": [ legacy_chapter_id ] })
            try:
                return r.json()["data"][0]["attributes"]["newId"]
            except KeyError:
                return "invalid"
        except ValueError:
            return chapter_id

    def available(self):
        if not hasattr(self, "req"):
            try:
                self.req = _make_api_request("/chapter/" + MangadexV5Chapter._translate_chapter_id(self.url.split('/')[-1]),
                    session = self.req_session)
                self.json = _decode_json(self.req.text)
            except exceptions.ScrapingError:
                pass
        return True if self.req.status_code == 200 else False

    def download(self):
        if not self.available():
            raise exceptions.ScrapingError
        at_home_data = _make_api_request("/at-home/server/" + self.json["id"]).json()
        pages = [ at_home_data["baseUrl"] + "/data/" + at_home_data["chapter"]["hash"] + "/" + x
            for x in at_home_data["chapter"]["data"] ]
        if len(pages) <= 0:
            output.error("{}: chapter is hosted externally".format(self.alias))
            raise exceptions.ScrapingError("external")
        files = [None] * len(pages)
        futures = []
        with self.progress_bar(pages) as bar:
            for i, page in enumerate(pages):
                try:
                    r = self.req_session.get(page, stream = True)
                except requests.exceptions.ConnectionError as e:
                    output.error("{}: connection error for page {}".format(self.alias, i))
                    raise exceptions.ScrapingError
                if not r or r.status_code == 404:
                    output.error("{}: failed request for page {}".format(self.alias, i))
                    raise exceptions.ScrapingError
                fut = download_pool.submit(self.page_download_task, i, r, page_url = page)
                fut.add_done_callback(partial(self.page_download_finish, bar, files))
                futures.append(fut)
            concurrent.futures.wait(futures)
            self.create_zip(files)

    def from_url(url):
        chapter_id = MangadexV5Chapter._translate_chapter_id(url.split('/')[-1])
        for relationship in _decode_json(_make_api_request("/chapter/" + chapter_id).text)["relationships"]:
            if relationship["type"] == "manga":
                series = MangadexV5Series("https://mangadex.org/title/" + relationship["id"])
                for chapter in series.chapters:
                    if chapter_id == chapter.url.split('/')[-1]:
                        return chapter
        raise exceptions.ScrapingError
