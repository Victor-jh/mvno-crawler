import unittest
import sys
import os
import asyncio
from datetime import datetime

# Path setup
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'mvno_system')))

from crawlers.base_crawler import BaseCrawler
from storage.database import SessionLocal, Plan, init_db

# Create a Dummy Crawler
class MockCrawler(BaseCrawler):
    def __init__(self):
        # Skip config loading for mock
        self.platform_key = 'mock_platform'
        self.logger = None
        self.config = {}
        self.selectors = {}
        self.results = []
        self.db = SessionLocal()
        self.crawl_log = None
        
        # Manually set logger to avoid errors if used
        import logging
        self.logger = logging.getLogger('mock')

    async def crawl(self):
        pass

class TestBaseCrawlerLogic(unittest.TestCase):
    def setUp(self):
        # Ensure DB tables exist
        init_db()
        self.crawler = MockCrawler()
        self.crawler.start_crawl_log()

    def tearDown(self):
        if self.crawler.crawl_log:
            self.crawler.finish_crawl_log()
        self.crawler.db.close()

    def test_save_plan_parsing(self):
        # 1. Define Raw Data
        raw_data = {
            'carrier': 'TestCarrier',
            'plan_name': '5G Special Plan',
            'price': '35,000원',
            'data_raw': '150GB+5Mbps',
            'voice': '기본제공',
            'sms': '100건',
            'network': 'SKT',
            'url': 'http://mock.com',
            'screenshot_path': ''
        }
        
        # 2. Call save_plan
        self.crawler.save_plan(raw_data)
        
        # 3. Verify DB
        # Query the latest plan
        last_plan = self.crawler.db.query(Plan).filter_by(platform='mock_platform').order_by(Plan.id.desc()).first()
        
        print(f"\nSaved Plan ID: {last_plan.id}")
        print(f"Data Raw: {last_plan.data_raw}")
        print(f"Data Base GB: {last_plan.data_base_gb}")
        print(f"QoS: {last_plan.data_qos_mbps}")
        print(f"Voice: {last_plan.voice_type}")
        
        # Assertions
        self.assertIsNotNone(last_plan)
        self.assertEqual(last_plan.data_base_gb, 150.0)
        self.assertEqual(last_plan.data_qos_mbps, 5.0)
        self.assertEqual(last_plan.voice_type, 'unlimited')
        self.assertEqual(last_plan.sms_type, '100')
        self.assertEqual(last_plan.host_network, 'SKT')

if __name__ == '__main__':
    unittest.main()
