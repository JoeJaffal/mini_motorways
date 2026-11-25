"""Specific regression checks for curriculum action geometry and native controls."""
import os
import unittest

import numpy as np

from construction_practice import (
    EDGE_END, FINISH, NATIVE_TO_ALIGNED, ConstructionPractice, endpoints, inside, turn,
)


class CurriculumChecks(unittest.TestCase):
    def setUp(self):
        dll = os.environ.get('STAGE1_CURRICULUM_DLL')
        if not dll:
            self.skipTest('Set STAGE1_CURRICULUM_DLL to the curriculum Release host')
        self.env = ConstructionPractice(dll)
        self.addCleanup(self.env.close)

    def test_rotations_bijectively_map_interior_edge_slots(self):
        for count, mapping in enumerate(NATIVE_TO_ALIGNED):
            valid = np.flatnonzero(mapping >= 0)
            self.assertCountEqual(mapping[valid], valid)
            for action in valid:
                if not 0 < action < EDGE_END:
                    continue
                a, b = endpoints(action)
                self.assertTrue(inside(b))
                self.assertEqual({turn(a, count), turn(b, count)}, set(endpoints(mapping[action])))

    def test_blocked_endpoints_are_never_legal(self):
        self.env.reset('obstacle', 'validation', 38000)
        blocked = np.asarray(self.env.raw['terrain'])[self.env.cells] == 2
        self.assertEqual(blocked.sum(), 2)
        for action in np.flatnonzero(self.env.legal):
            self.assertTrue(0 < action < EDGE_END)
            for x, y in endpoints(action):
                self.assertFalse(blocked[y, x])

    def test_driveway_native_rotation_and_finish_are_distinct(self):
        env = self.env
        env.reset('driveway', 'validation', 34000)
        self.assertTrue(env.connected())
        self.assertEqual(env.reference(), [FINISH])
        self.assertTrue(env.step(FINISH))
        env.reset('driveway', 'validation', 34001)
        self.assertFalse(env.connected())
        rotation, = env.reference()
        self.assertGreaterEqual(rotation, EDGE_END)
        self.assertTrue(env.legal[rotation])
        self.assertTrue(env.step(rotation))
        self.assertTrue(env.connected())


if __name__ == '__main__':
    unittest.main()
