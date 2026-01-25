"""
전체 크롤러 통합 테스트 스크립트
- 각 크롤러당 3개 요금제 수집
- 엑셀 출력 및 스크린샷 저장
"""

import asyncio
import sys
import os
from datetime import datetime

# Add project path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(os.path.join(os.path.dirname(os.path.abspath(__file__)), 'mvno_system'))

from mvno_system.storage.database import init_db
from mvno_system.core.platform_loader import PlatformLoader

async def run_all_tests():
    print(f"=== 전체 크롤러 통합 테스트 시작: {datetime.now()} ===\n")
    
    # Initialize DB
    init_db()
    
    # Session ID for this test run
    session_id = datetime.now().strftime('%Y%m%d_%H%M%S')
    print(f">>> Session ID: {session_id}\n")
    
    loader = PlatformLoader()
    platforms = loader.get_enabled_platforms()
    
    results_summary = []
    
    for platform_key, platform_data in platforms:
        platform_name = platform_data.get('name', platform_key)
        print(f"\n{'='*50}")
        print(f"[{platform_name}] 테스트 시작...")
        print(f"{'='*50}")
        
        try:
            crawler = loader.get_crawler(platform_key)
            if not crawler:
                print(f"  ❌ 크롤러 로드 실패")
                results_summary.append({'platform': platform_name, 'status': 'LOAD_FAIL', 'count': 0})
                continue
            
            crawler.set_session(session_id)
            
            # Run with limit=3, headless=True, test_mode=True
            await crawler.crawl(headless=True, test_mode=True, limit=3)
            
            # Export Excel
            if crawler.results:
                excel_path = crawler.export_excel()
                print(f"  ✅ 수집 완료: {len(crawler.results)}개")
                print(f"  📊 엑셀: {excel_path}")
                results_summary.append({
                    'platform': platform_name, 
                    'status': 'SUCCESS', 
                    'count': len(crawler.results),
                    'excel': excel_path
                })
            else:
                print(f"  ⚠️ 수집된 데이터 없음")
                results_summary.append({'platform': platform_name, 'status': 'NO_DATA', 'count': 0})
                
        except Exception as e:
            print(f"  ❌ 에러: {e}")
            results_summary.append({'platform': platform_name, 'status': 'ERROR', 'count': 0, 'error': str(e)})
    
    # Print Summary
    print(f"\n\n{'='*60}")
    print("테스트 결과 요약")
    print(f"{'='*60}")
    
    success_count = 0
    for r in results_summary:
        status_icon = "✅" if r['status'] == 'SUCCESS' else "❌"
        print(f"{status_icon} {r['platform']}: {r['status']} ({r['count']}개)")
        if r['status'] == 'SUCCESS':
            success_count += 1
    
    print(f"\n총 {len(results_summary)}개 중 {success_count}개 성공")
    print(f"세션 디렉토리: storage/sessions/{session_id}/")
    print(f"\n=== 테스트 완료: {datetime.now()} ===")

if __name__ == "__main__":
    asyncio.run(run_all_tests())
