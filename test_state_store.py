import tempfile,unittest
from pathlib import Path
from state_store import read,write

class SharedStore(unittest.TestCase):
    def test_revision_and_preservation(self):
        with tempfile.TemporaryDirectory(dir=Path(__file__).resolve().parent) as directory:
            path=Path(directory)/'state.sqlite3'
            data={'visits':[{'id':'VISIT-1','status':'approved'}],'logs':[],'headSettings':{},'incidents':[]}
            self.assertEqual(read(path)['revision'],0)
            self.assertTrue(write(0,data,path)[0])
            second={**data,'incidents':[{'id':'INC-1','status':'open'}]}
            self.assertTrue(write(1,second,path)[0])
            ok,latest=write(1,data,path)
            self.assertFalse(ok)
            self.assertEqual(latest['state']['incidents'][0]['id'],'INC-1')
            self.assertEqual(read(path)['revision'],2)
    def test_duplicate_ids(self):
        with self.assertRaises(ValueError):
            write(0,{'visits':[{'id':'same'},{'id':'same'}],'logs':[],'headSettings':{},'incidents':[]})

if __name__=='__main__':unittest.main()
