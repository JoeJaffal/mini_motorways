"""Authorization boundary only: this check never invokes learning."""
import unittest
from hierarchy_updater import HierarchyUpdater
class UpdaterChecks(unittest.TestCase):
    def test_updates_are_disabled_by_default(self):
        updater=HierarchyUpdater(object())
        with self.assertRaises(PermissionError):updater.update([])
if __name__=='__main__':unittest.main()
