import sys,tempfile,unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/"scripts"))
import local_batch_review as m

class BatchTests(unittest.TestCase):
    def test_dedup_and_no_nonvideo(self):
        with tempfile.TemporaryDirectory() as temp:
            folder=Path(temp)
            a=folder/"example.mp4";a.write_bytes(b"abc")
            b=folder/"note.txt";b.write_text("ignore")
            self.assertEqual([x.name for x in m.pending(folder,{})],["example.mp4"])
            state={"example.mp4":m.signature(a)}
            self.assertEqual(len(m.pending(folder,state)),0)
            a.write_bytes(b"change")
            self.assertEqual(len(m.pending(folder,state)),1)
if __name__=="__main__":
    unittest.main()
