from cu2.scrapers.dokireader import DokiReaderSeries, DokiReaderChapter
from cu2.scrapers.dynastyscans import DynastyScansChapter, DynastyScansSeries
from cu2.scrapers.madokami import MadokamiChapter, MadokamiSeries
from cu2.scrapers.mangadex_v5 import MangadexV5Series, MangadexV5Chapter
from cu2.scrapers.mangakakalot import MangakakalotSeries, MangakakalotChapter
from cu2.scrapers.mangakatana import MangakatanaSeries, MangakatanaChapter
from cu2.scrapers.mangasee import MangaseeSeries, MangaseeChapter
from cu2.scrapers.mangahere import MangahereSeries, MangahereChapter
from cu2.scrapers.yuriism import YuriismChapter, YuriismSeries

series_scrapers = [
    DokiReaderSeries,
    DynastyScansSeries,
    MadokamiSeries,
    MangadexV5Series,
    MangakakalotSeries,
    MangakatanaSeries,
    MangaseeSeries,
    MangahereSeries,
    YuriismSeries,
]
chapter_scrapers = [
    DokiReaderChapter,
    DynastyScansChapter,
    MadokamiChapter,
    MangadexV5Chapter,
    MangakakalotChapter,
    MangakatanaChapter,
    MangaseeChapter,
    MangahereChapter,
    YuriismChapter,
]
