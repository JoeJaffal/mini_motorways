"""Analytical PPO checks only; no policy or optimizer is created."""
import math
import unittest
import torch
from hierarchy_objective import joint_log_probability,clipped_ppo_terms


def vector(values):return torch.tensor(values,dtype=torch.float64)


class ObjectiveChecks(unittest.TestCase):
    def terms(self,ratio,advantage,**extra):
        n=len(ratio)
        args=dict(new_log_probability=vector([math.log(r) for r in ratio]),
            old_log_probability=vector([0]*n),advantages=vector(advantage),
            values=vector([0]*n),returns=vector([0]*n),entropy=vector([1]*n),normalize_advantage=False)
        args.update(extra)
        with torch.inference_mode():return clipped_ppo_terms(**args)

    def test_unchanged_policy_ratio_one_matches_unclipped_objective(self):
        terms=self.terms([1,1],[2,-1])
        self.assertEqual(terms['policy_loss'].item(),-.5)
        self.assertEqual(terms['clip_fraction'].item(),0)
        self.assertEqual(terms['approximate_kl'].item(),0)

    def test_positive_and_negative_advantages_clip_in_correct_direction(self):
        terms=self.terms([2,.5],[1,-1])
        self.assertAlmostEqual(terms['policy_loss'].item(),-.2)
        self.assertEqual(terms['clip_fraction'].item(),1)
        # Deterioration is not clipped away: retain pressure to correct it.
        worse=self.terms([.5,2],[1,-1])
        self.assertAlmostEqual(worse['policy_loss'].item(),.75)

    def test_manager_clips_one_joint_ratio_not_two_independent_ratios(self):
        with torch.inference_mode():
            old=joint_log_probability(vector([math.log(.5)]),vector([math.log(.5)]))
            new=joint_log_probability(vector([math.log(.55)]),vector([math.log(.55)]))
            ratio=(new-old).exp().item()
        self.assertAlmostEqual(ratio,1.21)
        self.assertAlmostEqual(self.terms([ratio],[1])['policy_loss'].item(),-1.2)

    def test_value_and_entropy_terms_keep_published_coefficients_external(self):
        terms=self.terms([1],[0],values=vector([2]),returns=vector([5]),entropy=vector([.7]))
        self.assertEqual(terms['value_loss'].item(),9)
        self.assertAlmostEqual(terms['entropy_loss'].item(),-.7)

    def test_missing_joint_entropy_and_nonfinite_inputs_fail(self):
        with self.assertRaisesRegex(ValueError,'entropy'):self.terms([1],[1],entropy=None)
        with self.assertRaisesRegex(ValueError,'Nonfinite'):
            self.terms([1],[1],values=vector([float('nan')]))


if __name__=='__main__':unittest.main()
