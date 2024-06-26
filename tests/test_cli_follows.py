from unittest import mock
import tests.cu2test as cu2test


class TestCLIFollows(cu2test.Cu2CLITest):
    def test_follows(self):
        FOLLOWS = [
            {'url': ('https://manga.madokami.al/Manga/B/B_/B_GA/B%20Gata%20H'
                     '%20Kei'),
             'alias': 'b-gata-h-kei'},
            {'url': 'https://manga.madokami.al/Manga/C/CE/CERB/Cerberus',
             'alias': 'cerberus'},
            {'url': ('https://manga.madokami.al/Manga/S/SA/SAKI/Sakigake%21%21'
                     '%20Cromartie%20Koukou'),
             'alias': 'cromartie-high-school'}
        ]

        for follow in FOLLOWS:
            series = self.create_mock_series(**follow)
            series.follow()

        result = self.invoke('follows')
        self.assertEqual(result.exit_code, 0)
        for follow in FOLLOWS:
            self.assertIn(follow['alias'], result.output)
