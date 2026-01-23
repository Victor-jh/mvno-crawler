import asyncio
import logging
from datetime import datetime
from core.platform_loader import PlatformLoader

logger = logging.getLogger('scheduler')

async def run_crawler_job(platform_key, **kwargs):
    """
    각 플랫폼별 크롤러를 실행하는 래퍼 함수
    APScheduler의 Job으로 등록됨
    """
    logger.info(f"작업 실행: {platform_key} 크롤링")
    
    try:
        loader = PlatformLoader()
        crawler = loader.get_crawler(platform_key)
        
        if not crawler:
            logger.warning(f"크롤러 로드 실패: {platform_key}")
            return
            
        # Session ID for this job run
        session_id = datetime.now().strftime('%Y%m%d_%H%M%S')
        crawler.set_session(session_id)
        
        # 크롤링 실행
        await crawler.crawl(**kwargs)
        logger.info(f"작업 완료: {platform_key}")
        
    except Exception as e:
        logger.error(f"작업 실패 ({platform_key}): {e}")
        import traceback
        logger.error(traceback.format_exc())
