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

class TestMangakatana(cu2test.Cu2Test):
    MANGAKATANA_URL = 'https://mangakatana.com'

    def setUp(self):
        super().setUp()
        global mangakatana
        from cu2.scrapers import mangakatana

    def tearDown(self):
        self.directory.cleanup()

    def get_five_latest_releases(self):
        r = requests.get(self.MANGAKATANA_URL + "/latest", headers = { "User-Agent": version.version_string() })
        self.assertEqual(r.status_code, 200)
        soup = BeautifulSoup(r.text, config.get().html_parser)
        chaps = soup.find("div", id = "book_list").find_all("div", class_ = "item")
        links = [chap.find("div", class_ = "chapter").find("a")["href"] for chap in chaps]
        if len(links) < 5:
            output.error('Unable to extract latest releases')
            raise exceptions.ScrapingError
        return links[:5]

    def test_chapter_download_latest(self):
        latest_releases = self.get_five_latest_releases()
        for release in latest_releases:
            try:
                chapter = mangakatana.MangakatanaChapter.from_url(release)
            except exceptions.ScrapingError as e:
                output.error('Scraping error for {} - {}'.format(release, e))
                raise exceptions.ScrapingError
            else:
                chapter.get(use_db=False)

    def test_bad_chapters(self):
        # This has no space between the word "Chapter" and the number
        chap = mangakatana.MangakatanaChapter.from_url("https://mangakatana.com/manga/martial-peak.20405/c1833")
        self.assertEqual(chap.title, "Chapter1833: The Preciousness of Source Crystals")

        # This has the word "Chapter" misspelled as "Chaprer"
        chap = mangakatana.MangakatanaChapter.from_url("https://mangakatana.com/manga/martial-peak.20405/c441")
        self.assertEqual(chap.title, "Chaprer 441")

if __name__ == '__main__':
    unittest.main()
