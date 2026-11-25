import unittest
import subprocess
import sys
import tempfile
import time
from pathlib import Path
from run_city_strategy_long import review_decision,run_child

class LongStrategyGuardTests(unittest.TestCase):
    def test_failed_child_cleans_its_orphan_worker(self):
        with tempfile.TemporaryDirectory() as directory:
            marker=Path(directory)/'worker.pid'
            ready=Path(directory)/'ready'
            worker_code=("import signal,time,sys,pathlib; "
                         "signal.signal(signal.SIGTERM,signal.SIG_IGN); "
                         "pathlib.Path(sys.argv[1]).write_text('ready'); time.sleep(60)")
            script=("import subprocess,sys,time,pathlib\n"
                    f"p=subprocess.Popen([sys.executable,'-c',{worker_code!r},{str(ready)!r}])\n"
                    f"pathlib.Path({str(marker)!r}).write_text(str(p.pid))\n"
                    f"while not pathlib.Path({str(ready)!r}).exists(): time.sleep(.01)\n"
                    "raise SystemExit(3)\n")
            with self.assertRaises(subprocess.CalledProcessError):
                run_child([sys.executable,'-c',script],cwd=directory,timeout=5)
            worker=Path('/proc')/marker.read_text()/'stat'
            for _ in range(50):
                if not worker.exists() or worker.read_text().split()[2]=='Z':break
                time.sleep(.02)
            else:self.fail('Failed child left a running worker')

    def test_child_timeout_and_success(self):
        with tempfile.TemporaryDirectory() as directory:
            run_child([sys.executable,'-c','pass'],cwd=directory,timeout=5)
            with self.assertRaises(subprocess.TimeoutExpired):
                run_child([sys.executable,'-c','import time; time.sleep(60)'],cwd=directory,timeout=.1)

    def test_promotion_and_two_consecutive_regressions(self):
        ref=dict(mean_score=100.,scoring_games=23)
        self.assertTrue(review_decision(ref,dict(mean_score=121.,scoring_games=23),0)['promote'])
        first=review_decision(ref,dict(mean_score=85.,scoring_games=23),0)
        self.assertFalse(first['stop']);self.assertEqual(first['failures'],1)
        second=review_decision(ref,dict(mean_score=85.,scoring_games=23),first['failures'])
        self.assertTrue(second['stop'])
        recovery=review_decision(ref,dict(mean_score=96.,scoring_games=23),1)
        self.assertEqual(recovery['failures'],0);self.assertFalse(recovery['promote'])
        self.assertFalse(review_decision(ref,dict(mean_score=150.,scoring_games=22),0)['retained'])
        self.assertTrue(review_decision(ref,dict(mean_score=40.,scoring_games=23),0)['stop'])

if __name__=='__main__':unittest.main()
