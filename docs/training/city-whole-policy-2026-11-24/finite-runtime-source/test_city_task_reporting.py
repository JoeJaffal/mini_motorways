import io
import json
import unittest
from train_city_curriculum import TaskEpisodes


class TaskReportingTests(unittest.TestCase):
    def test_native_future_service_is_preserved_and_city_is_not_mislabelled(self):
        output=io.StringIO();callback=TaskEpisodes(output)
        callback.num_timesteps=123
        callback.locals={'infos':[
            {'episode':{'r':7,'trips':7,'exercise':'midgame-network-reserve'},
             'TimeLimit.truncated':False,'new_deliveries':3,'future_stock':2,
             'future_targets':1,'urgent_deliveries':4},
            {'episode':{'r':7,'trips':7,'exercise':'city'},'TimeLimit.truncated':True}]}
        self.assertTrue(callback._on_step())
        reserve,city=map(json.loads,output.getvalue().splitlines())
        self.assertEqual(reserve['new_deliveries'],3)
        self.assertEqual(reserve['future_stock'],2)
        self.assertEqual(reserve['future_targets'],1)
        self.assertEqual(reserve['urgent_deliveries'],4)
        self.assertIsNone(city['new_deliveries'])
        self.assertEqual(city['r'],7)
        self.assertEqual(callback.completed,2)


if __name__=='__main__':unittest.main()
