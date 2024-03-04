from bs4 import BeautifulSoup
from cu2 import config, exceptions, output, version
from json import loads
from re import search
from urllib.parse import urljoin
import tests.cu2test as cu2test
import os
import requests
import unittest
import zipfile

class TestBatotoV3X(cu2test.Cu2Test):
    BATOTO_V3X_URL = 'https://bato.to'

    def setUp(self):
        super().setUp()
        global batoto_v3x
        from cu2.scrapers import batoto_v3x

    def tearDown(self):
        self.directory.cleanup()

    def get_five_latest_releases(self):
        r = requests.get(self.BATOTO_V3X_URL + "/v3x", headers = { "User-Agent": version.version_string() })
        self.assertEqual(r.status_code, 200)
        soup = BeautifulSoup(r.text, config.get().html_parser)
        chaps = [ x for x in soup.find("div", attrs = { "name": "home-release" }).find_all("h3") if not x.find("span", class_ = "font-family-NotoColorEmoji") ]
        links = [ self.BATOTO_V3X_URL + x.parent.find_all("div", recursive = False)[-1].find("a")["href"] for x in chaps ]
        return links[:5]

    def test_chapter_download_latest(self):
        latest_releases = self.get_five_latest_releases()
        for release in latest_releases:
            try:
                chapter = batoto_v3x.BatotoV3XChapter.from_url(release)
            except exceptions.ScrapingError as e:
                output.error('Scraping error for {} - {}'.format(release, e))
                raise exceptions.ScrapingError
            else:
                chapter.get(use_db=False)

    def test_oneshot(self):
        chapter = batoto_v3x.BatotoV3XChapter.from_url("https://bato.to/title/90127-look-back/1729292-ch_1")
        self.assertEqual(chapter.name, "Look Back")
        self.assertEqual(chapter.alias, "look-back")
        self.assertEqual(chapter.chapter, "1")
        self.assertEqual(chapter.groups, [])
        chapter.get(use_db = False)
        series = batoto_v3x.BatotoV3XSeries("https://bato.to/title/90127-look-back")
        self.assertEqual(len(series.chapters), 1)
        self.assertEqual(series.name, "Look Back")
        self.assertEqual(series.alias, "look-back")
        self.assertEqual(series.chapters[0].chapter, "1")

    def test_with_groups(self):
        chapter = batoto_v3x.BatotoV3XChapter.from_url("https://bato.to/title/88017-chorokute-kawaii-kimi-ga-suki/2740093-vol_4-ch_16")
        self.assertEqual(chapter.groups, ['Lovesick Alley'])
        chapter.get(use_db = False)

    def test_chapter_decimal(self):
        chapter = batoto_v3x.BatotoV3XChapter.from_url("https://bato.to/title/70599-petit-mignon/2712554-ch_6.5")
        self.assertEqual(chapter.name, "Petit Mignon")
        self.assertEqual(chapter.alias, "petit-mignon")
        self.assertEqual(chapter.chapter, "6.5")
        self.assertEqual(chapter.title, "Chapter 06 Extras")
        chapter.get(use_db = False)

    def test_chapter_jpg(self):
        chapter = batoto_v3x.BatotoV3XChapter.from_url("https://bato.to/title/38148-m-to-n-no-shouzou/684454-vol_1-ch_2")
        self.assertEqual(chapter.name, "M to N no Shouzou")
        self.assertEqual(chapter.alias, "m-to-n-no-shouzou")
        self.assertEqual(chapter.chapter, "2")
        self.assertEqual(chapter.title, "Volume 1 Chapter 2")
        chapter.get(use_db = False)

if __name__ == '__main__':
    unittest.main()
