import copy,unittest
from types import SimpleNamespace
import torch
from city_relational_policy import RelativeRateAdam
from city_optimizer_settings import set_critic_lr_scale


def fixture():
    actor=torch.nn.Linear(2,1);critic=torch.nn.Linear(2,1)
    optimizer=RelativeRateAdam([dict(params=list(actor.parameters()),lr_scale=1.),dict(params=list(critic.parameters()),lr_scale=.1)],lr=.001)
    policy=SimpleNamespace(actor=actor,value_net=critic,optimizer=optimizer)
    for g in optimizer.param_groups:
        for p in g['params']:p.grad=torch.ones_like(p)*.2
    optimizer.step()
    return policy


class CriticScaleTests(unittest.TestCase):
    def test_only_critic_step_changes_and_adam_moments_survive(self):
        a=fixture();b=copy.deepcopy(a);old=copy.deepcopy(b.optimizer.state_dict())
        self.assertEqual(set_critic_lr_scale(b,1.),1)
        after=b.optimizer.state_dict()
        for key,state in old['state'].items():
            for name,value in state.items():self.assertTrue(torch.equal(value,after['state'][key][name]))
        before_a=[p.detach().clone() for p in a.value_net.parameters()]
        before_b=[p.detach().clone() for p in b.value_net.parameters()]
        for policy in (a,b):
            for g in policy.optimizer.param_groups:
                # Mimic SB3 reapplying its shared schedule each training update.
                g['lr']=.002
                for p in g['params']:p.grad=torch.ones_like(p)*.4
            policy.optimizer.step()
        for x,y in zip(a.actor.parameters(),b.actor.parameters()):self.assertTrue(torch.equal(x,y))
        for x,y,bx,by in zip(a.value_net.parameters(),b.value_net.parameters(),before_a,before_b):
            torch.testing.assert_close(by-y,10*(bx-x),rtol=2e-4,atol=2e-7)
        c=fixture();c.optimizer.load_state_dict(b.optimizer.state_dict())
        self.assertEqual(c.optimizer.param_groups[1]['lr_scale'],1.)
        self.assertEqual(float(next(iter(c.optimizer.state.values()))['step']),2.)

    def test_invalid_scales_and_shared_group_rejected(self):
        p=fixture()
        for value in (0,-1,float('inf'),float('nan')):
            with self.assertRaises(ValueError):set_critic_lr_scale(p,value)
        p.optimizer=RelativeRateAdam([*p.actor.parameters(),*p.value_net.parameters()],lr=.001)
        with self.assertRaises(ValueError):set_critic_lr_scale(p,1.)

if __name__=='__main__':unittest.main()
