from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
import yaml
import logging
from pathlib import Path
from .job_wrapper import run_crawler_job

class TaskScheduler:
    def __init__(self):
        self.scheduler = AsyncIOScheduler()
        self.logger = logging.getLogger('scheduler')
        self.config_path = Path(__file__).parent.parent / 'config' / 'schedule.yaml'
        
    def load_schedule(self):
        """설정 파일 로드 및 스케줄 등록"""
        try:
            with open(self.config_path, 'r', encoding='utf-8') as f:
                config = yaml.safe_load(f)
                
            self.scheduler.remove_all_jobs()
            
            for platform, setting in config.get('schedules', {}).items():
                if setting.get('enabled', False):
                    # Cron 표현식 파싱 (예: "0 */12 * * *")
                    cron_parts = setting['cron'].split()
                    if len(cron_parts) == 5:
                        trigger = CronTrigger(
                            minute=cron_parts[0],
                            hour=cron_parts[1],
                            day=cron_parts[2],
                            month=cron_parts[3],
                            day_of_week=cron_parts[4]
                        )
                        
                        self.scheduler.add_job(
                            run_crawler_job,
                            trigger=trigger,
                            args=[platform],
                            id=platform,
                            name=f"{platform}_crawl"
                        )
                        self.logger.info(f"스케줄 등록: {platform} ({setting['cron']})")
                    else:
                        self.logger.error(f"잘못된 Cron 형식: {setting['cron']}")
                        
        except Exception as e:
            self.logger.error(f"스케줄 로드 실패: {e}")

    def start(self):
        """스케줄러 시작"""
        if not self.scheduler.running:
            self.load_schedule()
            self.scheduler.start()
            self.logger.info("스케줄러 시작됨")
            
            # 등록된 작업 출력
            jobs = self.scheduler.get_jobs()
            print(f">>> 등록된 스케줄: {len(jobs)}개")
            for job in jobs:
                print(f" - [{job.id}] {job.name}: {job.trigger}")

    def stop(self):
        """스케줄러 중지"""
        if self.scheduler.running:
            self.scheduler.shutdown()
            self.logger.info("스케줄러 종료됨")
