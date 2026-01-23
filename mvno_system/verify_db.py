from storage.database import SessionLocal, CrawlLog, Plan
import sys
import os

# 현재 디렉토리를 경로에 추가
sys.path.append(os.getcwd())

def verify():
    db = SessionLocal()
    try:
        print("=== Database Verification ===")
        
        # 로그 확인
        logs = db.query(CrawlLog).all()
        print(f"Total Crawl Logs: {len(logs)}")
        for log in logs:
            print(f" - ID: {log.id}, Platform: {log.platform}, Status: {log.status}, Items: {log.items_count}, Start: {log.start_time}, End: {log.end_time}")
            
        # 요금제 확인
        plans = db.query(Plan).all()
        print(f"\nTotal Plans: {len(plans)}")
        for plan in plans[:5]: # 5개만 출력
            print(f" - ID: {plan.id}, LogID: {plan.crawl_log_id}, Carrier: {plan.carrier}, Plan: {plan.plan_name}, Price: {plan.price}")
            
    finally:
        db.close()

if __name__ == "__main__":
    verify()
