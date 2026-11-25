"""Head routing, masking and save/reload inference; never runs an optimizer."""
import tempfile
from pathlib import Path
import unittest

import gymnasium as gym
import numpy as np
import torch
from hierarchy_policy import HierarchyPolicy
from visible_observation import observation_space


class PolicyChecks(unittest.TestCase):
    def setUp(self):
        torch.set_num_threads(1);torch.manual_seed(731)
        self.space=observation_space()
        self.space.spaces['focus']=gym.spaces.Box(0,1,(2,30,50),np.float32)
        self.space.spaces['context']=gym.spaces.Box(0,1,(8,),np.float32)
        self.policy=HierarchyPolicy(self.space,gym.spaces.Discrete(1501),lambda _:0.)
        self.policy.set_training_mode(False)
        self.obs={k:np.zeros((2,*v.shape),np.float32) for k,v in self.space.spaces.items()}
        self.obs['context'][0,0]=1
        self.obs['context'][1,2]=1
        self.obs['context'][:,3]=1

    def test_manager_and_executor_route_to_distinct_heads(self):
        tensor={k:torch.as_tensor(v) for k,v in self.obs.items()}
        with torch.inference_mode():
            features=self.policy.extract_features(tensor)
            actual=self.policy.action_net(features)
            np.testing.assert_array_equal(actual[0].numpy(),self.policy.action_net.manager(features[:,:256])[0].numpy())
            np.testing.assert_array_equal(actual[1].numpy(),self.policy.action_net.executor(features[:,:256])[1].numpy())
        manager={id(p) for p in self.policy.action_net.manager.parameters()}
        executor={id(p) for p in self.policy.action_net.executor.parameters()}
        self.assertFalse(manager&executor)
        self.assertEqual(features.shape,(2,257))
        self.assertFalse(self.policy.optimizer.state)

    def test_padding_cannot_change_motorway_pooling(self):
        a={k:v.copy() for k,v in self.obs.items()}
        b={k:v.copy() for k,v in self.obs.items()}
        b['motorways'][...,:5]=.75
        with torch.inference_mode():
            x=self.policy.extract_features({k:torch.as_tensor(v) for k,v in a.items()})
            y=self.policy.extract_features({k:torch.as_tensor(v) for k,v in b.items()})
        torch.testing.assert_close(x,y,rtol=0,atol=0)
        self.assertTrue(torch.isfinite(x).all())

    def test_masked_predictions_survive_save_reload(self):
        mask=np.zeros((2,1501),bool);mask[0,100]=True;mask[1,0]=True
        before={k:v.clone() for k,v in self.policy.state_dict().items()}
        actions,_=self.policy.predict(self.obs,deterministic=True,action_masks=mask)
        np.testing.assert_array_equal(actions,[100,0])
        with tempfile.TemporaryDirectory() as directory:
            path=Path(directory)/'untrained-policy.pt'
            self.policy.save(path)
            loaded=HierarchyPolicy.load(path,device='cpu')
            loaded.set_training_mode(False)
            again,_=loaded.predict(self.obs,deterministic=True,action_masks=mask)
            np.testing.assert_array_equal(actions,again)
        for k,v in self.policy.state_dict().items():
            torch.testing.assert_close(before[k],v,rtol=0,atol=0)
        self.assertFalse(self.policy.optimizer.state)


if __name__=='__main__':unittest.main()
