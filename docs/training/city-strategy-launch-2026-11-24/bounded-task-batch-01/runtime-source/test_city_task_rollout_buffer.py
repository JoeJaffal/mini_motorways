import unittest
import gymnasium as gym
import numpy as np
import torch
from city_task_rollout_buffer import CityTaskRolloutBuffer


class TaskBufferTests(unittest.TestCase):
    def make_buffer(self):
        buffer=CityTaskRolloutBuffer(4,gym.spaces.Dict({'marker':gym.spaces.Box(0,100,(1,),dtype=np.float32)}),
                                    gym.spaces.Discrete(3),n_envs=4,device='cpu',worker_tasks=['city','city','reserve','reserve'])
        for step in range(4):
            ids=np.arange(4)*4+step
            buffer.add({'marker':ids[:,None].astype(np.float32)},(ids%3)[:,None],ids.astype(float),
                       np.zeros(4),torch.tensor(ids+100.),torch.tensor(ids+200.),
                       action_masks=np.eye(3)[ids%3])
        ids=np.arange(16).reshape(4,4).T
        buffer.advantages=ids.astype(np.float32)+300
        buffer.returns=ids.astype(np.float32)+400
        return buffer

    def test_every_sample_once_and_all_fields_stay_aligned(self):
        buffer=self.make_buffer()
        for _ in range(2):
            seen=[]
            for batch in buffer.get(3):
                ids=batch.observations['marker'].cpu().numpy().flatten().astype(int)
                self.assertEqual(len(set(ids//8)),1)
                seen.extend(ids.tolist())
                np.testing.assert_array_equal(batch.actions.cpu().numpy().flatten(),ids%3)
                np.testing.assert_array_equal(batch.old_values.cpu().numpy(),ids+100)
                np.testing.assert_array_equal(batch.old_log_prob.cpu().numpy(),ids+200)
                np.testing.assert_array_equal(batch.advantages.cpu().numpy(),ids+300)
                np.testing.assert_array_equal(batch.returns.cpu().numpy(),ids+400)
                np.testing.assert_array_equal(batch.action_masks.cpu().numpy(),np.eye(3)[ids%3])
            self.assertEqual(sorted(seen),list(range(16)))

    def test_unbatched_inspection_and_worker_contract(self):
        buffer=self.make_buffer()
        batches=list(buffer.get(None))
        self.assertEqual(len(batches),1)
        self.assertEqual(len(batches[0].actions),16)
        with self.assertRaises(ValueError):
            CityTaskRolloutBuffer(4,buffer.observation_space,buffer.action_space,n_envs=4,worker_tasks=['city'])


if __name__=='__main__':unittest.main()
