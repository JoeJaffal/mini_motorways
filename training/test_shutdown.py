"""Shutdown failures must not prevent checkpoint persistence."""
from contextlib import redirect_stdout
import io
from pathlib import Path
import signal
import tempfile
import unittest
from unittest.mock import patch

from shutdown import stop_and_save


class ShutdownChecks(unittest.TestCase):
    def test_dead_worker_and_callback_do_not_lose_checkpoint(self):
        events=[]
        class Model:
            def save(self,path):events.append('save');Path(path).write_text('TEST MODEL')
        class Env:
            def wait_pending(self):
                events.append('drain')
                raise RuntimeError('Host exited')
        class Callback:
            def on_training_end(self):
                events.append('callback')
                raise OSError('closed pipe')
        with tempfile.TemporaryDirectory() as directory,patch('shutdown.signal.signal'),redirect_stdout(io.StringIO()) as output:
            stop_and_save(Model(),Env(),Callback(),Path(directory))
            self.assertEqual((Path(directory)/'final.zip').read_text(),'TEST MODEL')
            self.assertEqual(events,['save','drain','callback'])
            self.assertIn('CHECKPOINT SAVED',output.getvalue())
            self.assertIn('checkpoint is already safe',output.getvalue())


if __name__=='__main__':unittest.main()
