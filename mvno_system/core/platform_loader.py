import yaml
import os
import importlib
import logging

logger = logging.getLogger('core')

class PlatformLoader:
    _instance = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(PlatformLoader, cls).__new__(cls)
            cls._instance.config_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'config', 'platforms.yaml')
            cls._instance.platforms = {}
            cls._instance.load_config()
        return cls._instance

    def load_config(self):
        try:
            with open(self.config_path, 'r', encoding='utf-8') as f:
                data = yaml.safe_load(f)
                self.platforms = data.get('platforms', {})
                logger.info(f"Loaded {len(self.platforms)} platforms from config.")
        except Exception as e:
            logger.error(f"Failed to load platforms config: {e}")
            self.platforms = {}

    def get_enabled_platforms(self):
        """
        Returns a list of enabled platforms sorted by priority.
        Each item is a tuple (key, platform_data).
        """
        enabled = []
        for key, data in self.platforms.items():
            if data.get('enabled', False):
                enabled.append((key, data))
        
        # Sort by priority
        enabled.sort(key=lambda x: x[1].get('priority', 999))
        return enabled

    def get_crawler(self, platform_key):
        """
        Dynamically imports and returns an instance of the crawler for the given platform key.
        """
        if platform_key not in self.platforms:
            logger.error(f"Platform key {platform_key} not found.")
            return None
            
        data = self.platforms[platform_key]
        module_path = data.get('module')
        class_name = data.get('class')
        
        if not module_path or not class_name:
            logger.error(f"Module or class configuration missing for {platform_key}")
            return None
            
        try:
            # Import module
            # If the system is running from project root, 'mvno_system.' prefix might be needed if not in path?
            # 'sys.path.append' in main.py adds 'mvno_system' directory? No, it adds 'mvno_system' directory usually.
            # Use 'mvno_system.crawlers...' ?
            # Let's try importing as configured first. 'crawlers.phoneb_crawler'
            
            # Since main.py adds os.path.dirname(os.path.abspath(__file__)) which is mvno_system/,
            # inputs like 'crawlers.phoneb_crawler' should work.
            
            module = importlib.import_module(module_path)
            crawler_class = getattr(module, class_name)
            return crawler_class()
            
        except ImportError as e:
            logger.error(f"Failed to import module {module_path}: {e}")
            return None
        except AttributeError as e:
            logger.error(f"Class {class_name} not found in {module_path}: {e}")
            return None
        except Exception as e:
            logger.error(f"Error instantiating crawler for {platform_key}: {e}")
            return None
