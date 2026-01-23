import asyncio
import sys
import os
from datetime import datetime

# 프로젝트 루트 경로 추가 (mvno_system 폴더)
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from storage.database import init_db
from scheduler.task_scheduler import TaskScheduler
from core.platform_loader import PlatformLoader

async def main():
    print(f"=== MVNO Monitoring System Started at {datetime.now()} ===")
    
    # Generate Session ID (Global for this run)
    session_id = datetime.now().strftime('%Y%m%d_%H%M%S')
    print(f">>> Session ID: {session_id}")
    
    # 0. DB 초기화 (테이블 생성)
    init_db()
    print(">>> Database Initialized")
    
    loader = PlatformLoader()
    platforms = loader.get_enabled_platforms()
    
    # 모드 선택 (인수 또는 입력)
    if len(sys.argv) > 1 and sys.argv[1] == '--scheduler':
        mode = 'scheduler'
    else:
        print("\n[모드 선택]")
        # 0 is reserved for special? No, usually 1-based.
        # Let's map dynamically using indices.
        
        menu_map = {} # choice_str -> platform_key
        
        # Fixed Scheduler option
        print("0. 스케줄러 모드 실행 (데몬)")
        
        idx = 1
        for key, data in platforms:
            print(f"{idx}. 단일 크롤링 실행 ({data.get('name')})")
            menu_map[str(idx)] = key
            idx += 1
            
        choice = input("선택 (기본값 1): ").strip()
        if not choice:
            choice = '1'
        
        if choice == '0':
            mode = 'scheduler'
        else:
            mode = 'single'
            target_platform = menu_map.get(choice)
            limit_input = input("수집 제한 개수 (0: 무제한, 엔터: 10): ").strip()
            limit = int(limit_input) if limit_input.isdigit() else 10
    
    if mode == 'scheduler':
        # 스케줄러 실행
        scheduler = TaskScheduler()
        scheduler.start()
        
        print("\n>>> Scheduler is running. Press Ctrl+C to exit.")
        
        try:
            # 무한 대기 (스케줄러가 백그라운드에서 실행됨)
            while True:
                await asyncio.sleep(60)
        except asyncio.CancelledError:
            scheduler.stop()
            
    elif mode == 'single':
        if not target_platform:
            print("잘못된 선택입니다.")
            return

        print(f"\n>>> Starting Single Crawl ({target_platform})... Limit: {limit}")
        crawler = loader.get_crawler(target_platform)
        if crawler:
            crawler.set_session(session_id)
            await crawler.crawl(headless=False, test_mode=True, limit=limit)
        else:
            print("크롤러 로드 실패.")
    
    print("\n=== All Tasks Completed ===")

if __name__ == "__main__":
    try:
        # if sys.platform == 'win32':
        #      asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n중단됨.")
    except Exception as e:
        print(f"Fatal Error: {e}")
        import traceback
        # 파일로 에러 저장
        with open("error_log.txt", "w", encoding="utf-8") as f:
            f.write(traceback.format_exc())
        traceback.print_exc()
