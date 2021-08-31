from cu2 import sanity
import tests.cu2test as cu2test
import os


class TestCLIRepairDB(cu2test.Cu2CLITest):
    def test_repair_db(self):
        MESSAGES = ['Backing up database to cu2.db.bak',
                    'Running database repair']

        self.copy_broken_database()
        backup_database = os.path.join(self.directory.name, 'cu2.db.bak')

        result = self.invoke('repair-db')
        self.assertTrue(os.path.isfile(backup_database))
        self.assertEqual(result.exit_code, 0)
        for message in MESSAGES:
            self.assertIn(message, result.output)
        sanity_tester = sanity.DatabaseSanity(self.db.Base, self.db.engine)
        sanity_tester.test()
        self.assertTrue(sanity_tester.is_sane)
