from cu2 import config, exceptions
import tests.cu2test as cu2test

from bs4 import BeautifulSoup
from requests import get

class TestMangakakalot(cu2test.Cu2Test):
    def setUp(self):
        super().setUp()
        global mangakakalot
        from cu2.scrapers import mangakakalot

    def tearDown(self):
        self.directory.cleanup()

    def get_five_latest_releases(self):
        return ["https://ww7.mangakakalot.tv" + \
            x["href"] for x in \
            BeautifulSoup(get("https://ww7.mangakakalot.tv/manga_list/?type=latest").text, \
            config.get().html_parser).find_all("a", \
            class_="list-story-item-wrap-chapter")][:5]

    def test_chapter_download_latest(self):
        latest_releases = self.get_five_latest_releases()
        for release in latest_releases:
            try:
                chapter = mangakakalot.MangakakalotChapter.from_url(release)
            except exceptions.ScrapingError as e:
                output.error('Scraping error for {} - {}'.format(release, e))
                raise exceptions.ScrapingError
            else:
                chapter.get(use_db=False)

if __name__ == '__main__':
    unittest.main()
