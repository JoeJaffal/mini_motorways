import json,tempfile,unittest
from pathlib import Path
import torch
from city_gradient_audit import GradientAudit

class GradientAuditTests(unittest.TestCase):
    def test_logging_does_not_change_gradients_or_updates(self):
        with tempfile.TemporaryDirectory() as folder:
            p=torch.nn.Parameter(torch.tensor([3.,4.]));q=torch.nn.Parameter(p.detach().clone())
            opt=torch.optim.Adam([p],lr=.01);ref=torch.optim.Adam([q],lr=.01)
            path=Path(folder)/'audit.jsonl';audit=GradientAudit(opt,path,1,lambda:'reserve')
            for _ in range(2):
                for value,optimizer in ((p,opt),(q,ref)):
                    optimizer.zero_grad();value.square().sum().backward()
                    torch.nn.utils.clip_grad_norm_([value],.5);optimizer.step()
                torch.testing.assert_close(p,q,rtol=0,atol=0)
            audit.close()
            rows=[json.loads(x) for x in path.read_text().splitlines()]
            self.assertEqual(len(rows),1);self.assertEqual(rows[0]['task'],'reserve')
            self.assertAlmostEqual(rows[0]['groups'][0]['before_clip'],10.)
            self.assertAlmostEqual(rows[0]['groups'][0]['after_clip'],.5,places=6)

if __name__=='__main__':unittest.main()
