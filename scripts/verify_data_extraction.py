import pandas as pd
import sys
import os
import re
from playwright.sync_api import sync_playwright

# Add project root
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), 'mvno_system')))

def extract_potential_fields(text):
    """
    Experimental logic to extract new fields from raw text.
    Returns a dictionary of found values.
    """
    result = {}
    
    # 1. Discount Period (e.g., "7개월 할인", "12개월간")
    discount_match = re.search(r'(\d+)개월\s*(?:할인|간|동안)', text)
    if discount_match:
        result['discount_duration'] = int(discount_match.group(1))
    else:
        result['discount_duration'] = None

    # 2. Normal Price (e.g., "이후 38,500원", "정상가 40000원")
    # Look for number after specific keywords
    price_match = re.search(r'(?:이후|정상가|종료 후)\s*월?\s*([\d,]+)원', text)
    if price_match:
        result['normal_price'] = int(price_match.group(1).replace(',', ''))
    else:
        result['normal_price'] = None

    # 3. Sim/NFC
    result['sim_fee'] = "Unknown"
    if "유심 무료" in text or "유심비 면제" in text:
        result['sim_fee'] = "Free"
    elif "유심비" in text and "유료" in text:
        result['sim_fee'] = "Paid"
        
    result['nfc'] = "Unknown"
    if "NFC 유심" in text:
        result['nfc'] = "Supported"
    elif "NFC 미지원" in text:
        result['nfc'] = "Not Supported"

    # 4. Gifts (Keywords)
    gifts = []
    for kw in ["상품권", "네이버페이", "스타벅스", "증정"]:
        if kw in text:
            gifts.append(kw)
    result['gifts'] = ", ".join(gifts) if gifts else None

    return result

def verify_extraction_potential():
    input_file = r"E:\알뜰폰\크롤링\storage\sessions\20260123_145859\merged_combined_results_20260123_145859.xlsx"
    
    # 1. Load Current Data
    try:
        df = pd.read_excel(input_file)
        # Select current columns for display
        current_columns = ["platform", "plan_name", "price", "data_raw", "voice_type", "sms_type", "network_type"]
        sample_rows = df.sample(3) if len(df) >= 3 else df
    except Exception as e:
        print(f"Error loading excel: {e}")
        return

    print("=== [Comparison Check] Current Data vs Potential Extraction ===\n")

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()

        for idx, row in sample_rows.iterrows():
            print(f"--- Case {idx+1}: {row['platform']} - {row['plan_name']} ---")
            
            # SHOW CURRENT
            print("[CURRENTLY COLLECTED]")
            for col in current_columns:
                val = row.get(col, "N/A")
                print(f"  - {col}: {val}")
            
            # ATTEMPT EXTRACTION
            url = row.get('url')
            if not url or not str(url).startswith('http'):
                print("  (No valid URL to check details)")
                continue
                
            print("\n[POTENTIAL EXPANSION] (Crawling & Detecting...)")
            try:
                page.goto(url, timeout=15000)
                page.wait_for_load_state('domcontentloaded')
                
                # Get full text for analysis
                full_text = page.inner_text("body")
                
                # Run experimental extraction
                extracted = extract_potential_fields(full_text)
                
                for k, v in extracted.items():
                    print(f"  + {k}: {v}")
                    
                # Show raw snippets for evidence
                print("  (Evidence Snippets)")
                if extracted['discount_duration']:
                    print(f"    Found '{extracted['discount_duration']}개월' pattern")
                if extracted['sim_fee'] != 'Unknown':
                    print(f"    Found Sim info")
                    
            except Exception as e:
                print(f"  Error accessing details: {e}")
            
            print("\n" + "="*50 + "\n")

        browser.close()

if __name__ == "__main__":
    verify_extraction_potential()
