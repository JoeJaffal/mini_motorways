import unittest
from run_city_strategy_long import review_decision

class LongStrategyGuardTests(unittest.TestCase):
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
