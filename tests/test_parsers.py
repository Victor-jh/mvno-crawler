import unittest
import sys
import os

# Adjust path to import parsers
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'mvno_system')))

from utils.parsers import parse_data_str, parse_voice_str, parse_sms_str

class TestParsers(unittest.TestCase):
    def test_parse_data_str(self):
        # Case 1: Standard Infinite
        res = parse_data_str("11GB+일2GB+3Mbps")
        self.assertEqual(res['base'], 11.0)
        self.assertEqual(res['daily'], 2.0)
        self.assertEqual(res['qos'], 3.0)
        
        # Case 2: QoS Only
        res = parse_data_str("15GB+3Mbps")
        self.assertEqual(res['base'], 15.0)
        self.assertEqual(res['daily'], 0.0)
        self.assertEqual(res['qos'], 3.0)
        
        # Case 3: MB Unit
        res = parse_data_str("500MB")
        self.assertAlmostEqual(res['base'], 0.488, places=3) # 500/1024
        
        # Case 4: Kbps Unit
        res = parse_data_str("1GB+400Kbps")
        self.assertEqual(res['base'], 1.0)
        self.assertEqual(res['qos'], 0.4) # 400/1000 = 0.4 Mbps
        
        # Case 5: Complex Daily Pattern
        res = parse_data_str("매일2GB+3Mbps")
        self.assertEqual(res['base'], 0.0) 
        self.assertEqual(res['daily'], 2.0)
        
    def test_parse_voice(self):
        self.assertEqual(parse_voice_str("기본제공"), "unlimited")
        self.assertEqual(parse_voice_str("무제한"), "unlimited")
        self.assertEqual(parse_voice_str("100분"), "100")
        
    def test_parse_sms(self):
        self.assertEqual(parse_sms_str("100건"), "100")
        self.assertEqual(parse_sms_str("기본제공"), "unlimited")

if __name__ == '__main__':
    unittest.main()
