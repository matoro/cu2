from bs4 import BeautifulSoup
from cu2 import config, exceptions, output
from urllib.parse import urljoin
import tests.cu2test as cu2test
import os
import re
import requests
import tempfile
import unittest
import zipfile

class TestMangadexV5(cu2test.Cu2Test):
    MANGADEX_URL = 'https://mangadex.org/'
    MANGADEX_API_URL = "https://api.mangadex.org"

    def setUp(self):
        super().setUp()
        global mangadex_v5
        from cu2.scrapers import mangadex_v5

    def tearDown(self):
        self.directory.cleanup()

    def get_five_latest_releases(self):
        return [ TestMangadexV5.MANGADEX_API_URL + "/chapter/" + x["id"] 
            for x in mangadex_v5._decode_json(mangadex_v5._make_api_request(
            "/chapter?order[publishAt]=desc&translatedLanguage[]=en&limit=5&includeExternalUrl=0").text) ]

    def series_information_tester(self, data):
        series = mangadex_v5.MangadexV5Series(data['url'])
        if "name" in data:
            self.assertEqual(series.name, data['name'])
        if "alias" in data:
            self.assertEqual(series.alias, data['alias'])
        if "url" in data:
            self.assertEqual(series.url, data['url'])
        self.assertIs(series.directory, None)
        if "chapters" in data:
            self.assertEqual(len(series.chapters), len(data['chapters']))
            for chapter in series.chapters:
                self.assertEqual(chapter.name, data['name'])
                self.assertEqual(chapter.alias, data['alias'])
                self.assertIn(chapter.chapter, data['chapters'])
                data['chapters'].remove(chapter.chapter)
                if "groups" in data:
                    for group in chapter.groups:
                        self.assertIn(group, data['groups'])
                self.assertIs(chapter.directory, None)
            self.assertEqual(len(data['chapters']), 0)

    def test_chapter_download_latest(self):
        latest_releases = self.get_five_latest_releases()
        for release in latest_releases:
            try:
                chapter = mangadex_v5.MangadexV5Chapter.from_url(release)
            except exceptions.ScrapingError as e:
                output.error('Scraping error for {} - {}'.format(release, e))
                raise exceptions.ScrapingError
            else:
                try:
                    chapter.get(use_db=False)
                except exceptions.ScrapingError as e:
                    if e.message == "external":
                        continue
                    raise e

    def test_chapter_filename_decimal(self):
        URL = 'https://mangadex.org/chapter/24779'
        chapter = mangadex_v5.MangadexV5Chapter.from_url(URL)
        path = os.path.join(
            self.directory.name, 'Citrus',
            'Citrus - c020 x9 [Chaosteam].zip'
        )
        self.assertEqual(chapter.chapter, '20.9')
        self.assertEqual(chapter.filename, path)

    def test_chapter_filename_version2(self):
        # 1v2 style version numbers seem to be omitted on the current site
        URL = 'https://mangadex.org/chapter/12361'
        chapter = mangadex_v5.MangadexV5Chapter.from_url(URL)
        path = os.path.join(
            self.directory.name, 'Urara Meirochou',
            'Urara Meirochou - c001 [Kyakka].zip'
        )
        self.assertEqual(chapter.chapter, '1')
        self.assertEqual(chapter.filename, path)

    def test_chapter_information_ramen_daisuki_koizumi_san(self):
        URL = 'https://mangadex.org/chapter/26441'
        chapter = mangadex_v5.MangadexV5Chapter.from_url(URL)
        self.assertEqual(chapter.alias, 'ramen-daisuki-koizumi-san')
        self.assertTrue(chapter.available())
        self.assertEqual(chapter.chapter, '18')
        self.assertEqual(chapter.groups, ['Saiko Scans'])
        self.assertEqual(chapter.name, 'Ramen Daisuki Koizumi-san')
        self.assertEqual(chapter.title, 'Strange-flavored Ramen')
        path = os.path.join(self.directory.name,
                            'Ramen Daisuki Koizumi-san',
                            'Ramen Daisuki Koizumi-san - c018 [Saiko Scans].zip')
        self.assertEqual(chapter.filename, path)
        chapter.download()
        self.assertTrue(os.path.isfile(path))
        with zipfile.ZipFile(path) as chapter_zip:
            files = chapter_zip.infolist()
            self.assertEqual(len(files), 8)

    def test_chapter_information_hidamari_sketch(self):
        URL = 'https://mangadex.org/chapter/9833'
        chapter = mangadex_v5.MangadexV5Chapter.from_url(URL)
        self.assertEqual(chapter.alias, 'hidamari-sketch')
        self.assertEqual(chapter.chapter, '0')
        self.assertEqual(chapter.groups, ['Highlanders'])
        self.assertEqual(chapter.name, 'Hidamari Sketch')
        self.assertEqual(chapter.title, None)
        path = os.path.join(
            self.directory.name, 'Hidamari Sketch',
            'Hidamari Sketch - c000 [Highlanders].zip'
        )
        self.assertEqual(chapter.filename, path)
        chapter.download()
        self.assertTrue(os.path.isfile(path))
        with zipfile.ZipFile(path) as chapter_zip:
            files = chapter_zip.infolist()
            self.assertEqual(len(files), 11)

    def test_chapter_information_tomochan(self):
        URL = 'https://mangadex.org/chapter/28082'
        config.get().cbz = True
        chapter = mangadex_v5.MangadexV5Chapter.from_url(URL)
        self.assertEqual(chapter.alias, 'tomo-chan-wa-onna-no-ko')
        self.assertEqual(chapter.chapter, '1')
        self.assertEqual(chapter.groups, ['M@STER Scans'])
        self.assertEqual(chapter.name, 'Tomo-chan wa Onna no ko!')
        self.assertEqual(chapter.title, 'Once In A Life Time Misfire')
        path = os.path.join(
            self.directory.name, 'Tomo-chan wa Onna no ko',
            'Tomo-chan wa Onna no ko - c001 [MSTER Scans].cbz'
        )
        self.assertEqual(chapter.filename, path)
        chapter.download()
        self.assertTrue(os.path.isfile(path))
        with zipfile.ZipFile(path) as chapter_zip:
            files = chapter_zip.infolist()
            self.assertEqual(len(files), 1)

    def test_series_old_format(self):
        URL = 'https://mangadex.org/title/4049/joou-no-hana'
        series = mangadex_v5.MangadexV5Series(URL)
        self.assertEqual(series.alias, 'joou-no-hana')

    def test_chapter_unavailable(self):
        URL = ''.join(['https://mangadex.org/chapter/',
                       '9999999999999999999999999999999999999999999999',
                       '99999999999999999999999'])
        chapter = mangadex_v5.MangadexV5Chapter(url=URL)
        self.assertFalse(chapter.available())

    def test_series_aria(self):
        data = {'alias': 'aria',
                'chapters': ['1', '2', '3', '4', '5', '6', '7', '7.5', '8',
                             '9', '10', '11', '12', '13', '14', '15', '16',
                             '17', '18', '19', '20', '21', '22', '23', '24',
                             '25', '26', '27', '28', '29', '30', '30.5', '31',
                             '32', '33', '34', '35', '35.5', '36', '37',
                             '37.5', '38', '39', '40', '41', '42', '43', '44',
                             '45', '45.5', '46', '47', '48', '49', '50',
                             '50.5', '51', '52', '53', '54', '55', '56', '57',
                             '57.5', '58', '59', '60', '60.1', '60.2'],
                'groups': ['promfret', 'Amano Centric Scans', 'INKR Comics'],
                'name': 'Aria',
                'url': 'https://mangadex.org/manga/2007'}
        self.series_information_tester(data)

    def test_series_prunus_girl(self):
        data = {'alias': 'prunus-girl',
                'chapters': ['1', '2', '3', '4', '5', '6', '6.5', '7', '8',
                             '9', '10', '11', '11.5', '12', '13', '14', '15',
                             '16', '16.5', '17', '18', '19', '20', '21', '22',
                             '23', '24', '25', '26', '27', '28', '29', '30',
                             '31', '32', '32.5', '33', '34', '35', '36', '37',
                             '38', '39', '40', '41', '42', '43'],
                'groups': ['Unknown', 'WOW!Scans', 'Maigo'],
                'name': 'Prunus Girl',
                'url': 'https://mangadex.org/manga/18'}
        self.series_information_tester(data)

    def test_series_no_chapters(self):
        data = {'alias': 'my-hero-academia',
                'chapters': [],
                'groups': [],
                'name': 'My Hero Academia',
                'url': 'https://mangadex.org/title/4f3bcae4-2d96-4c9d-932c-90181d9c873e'}
        self.series_information_tester(data)

    def test_series_trailing_name(self):
        data = {'alias': 'hatenkou-yuugi',
                'name': 'Hatenkou Yuugi',
                'url': 'https://mangadex.org/title/09a5f228-f6b2-42a0-9d37-f661ebc6ad35/hatenkou-yuugi'}
        self.series_information_tester(data)

    def test_chapter_zero(self):
        URL = 'https://mangadex.org/chapter/4e163f46-e47e-4bd4-aa25-055718862d76'
        chapter = mangadex_v5.MangadexV5Chapter.from_url(URL)
        self.assertTrue(chapter.available())
        self.assertEqual(chapter.title, 'Oneshot - ZONE')
        self.assertEqual(chapter.chapter, '0')

if __name__ == '__main__':
    unittest.main()
