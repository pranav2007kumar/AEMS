import unittest
from monitor_server import validate_filters

class FilterValidation(unittest.TestCase):
    def test_valid(self):
        data={'from':'2026-10-06','to':'2026-10-06','startHour':18,'endHour':6,'vehicleType':'Van'}
        self.assertEqual(validate_filters(data),data)
    def test_invalid(self):
        for data in [{'sql':'DROP TABLE visits'}, {'startHour':25,'endHour':6}, {'startHour':18}, {'from':'2026-02-30'}, {'from':'2026-10-12','to':'2026-10-11'}, {'status':'auto-approved'}, {'text':['invalid']}]:
            with self.subTest(data=data), self.assertRaises((ValueError,TypeError)):
                validate_filters(data)

if __name__=='__main__': unittest.main()
