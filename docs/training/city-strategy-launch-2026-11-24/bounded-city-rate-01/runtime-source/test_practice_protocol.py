"""Protocol rejection and cleanup, without launching a learner."""
import unittest
from unittest.mock import patch

from connection_practice import ConnectionPractice


class StubHost:
    last=None
    changes={}
    error=False
    def __init__(self,*args):self.closed=False;StubHost.last=self
    def call(self,**request):
        if self.error:raise ConnectionError('fixture transport failure')
        result=dict(accepted=True,terminated=False,truncated=False,
            protocolVersion='maskable-direct-hierarchy-v1',simulatorVersion='2026-11-10.f34',
            capabilities=['connection-practice-v1','practice-pure-mask-v1','displayed-state-flags-v1','bounded-native-wait-v1'])
        result.update(self.changes)
        return result
    def close(self):self.closed=True


class ProtocolChecks(unittest.TestCase):
    def tearDown(self):StubHost.changes={};StubHost.error=False

    def test_wrong_protocol_build_or_capability_closes_host(self):
        for changes in ({'protocolVersion':'old'},{'simulatorVersion':'other'},
                        {'capabilities':[]},{'accepted':False},{'terminated':True}):
            StubHost.changes=changes
            with self.subTest(changes=changes),patch('connection_practice.Host',StubHost):
                with self.assertRaisesRegex(RuntimeError,'handshake mismatch'):ConnectionPractice()
                self.assertTrue(StubHost.last.closed)

    def test_transport_failure_closes_host(self):
        StubHost.error=True
        with patch('connection_practice.Host',StubHost):
            with self.assertRaises(ConnectionError):ConnectionPractice()
            self.assertTrue(StubHost.last.closed)

    def test_mask_schema_is_not_silently_converted(self):
        with patch('connection_practice.Host',StubHost):
            env=ConnectionPractice()
            try:
                for values in ([1]*8,['false']*8,[True]*7):
                    with self.assertRaisesRegex(RuntimeError,'boolean mask schema'):env._boolean_mask(values,8)
                    self.assertTrue(env.done)
            finally:env.close()


if __name__=='__main__':unittest.main()
