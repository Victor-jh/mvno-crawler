import pandas as pd
import sys
import os
import re
import time
from playwright.sync_api import sync_playwright

# Add project root
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), 'mvno_system')))

def extract_potential_fields(text):
    """
    Extracts potential fields from page text using regex patterns.
    """
    result = {}
    
    # 1. Discount Period
    disc_match = re.search(r'(\d+)\s*개월\s*(?:할인|동만|간)', text)
    result['Discount_Period_Months'] = int(disc_match.group(1)) if disc_match else "N/A"

    # 2. Normal Price
    norm_match = re.search(r'(?:이후|정상가|종료 후|기본료)\s*(?:월)?\s*([\d,]+)원', text)
    result['Normal_Price_Won'] = norm_match.group(1).replace(',', '') if norm_match else "N/A"

    # 3. Sim Fee info
    if "유심 무료" in text or "유심비 면제" in text or "가입비 면제" in text:
        result['Sim_Fee_Status'] = "Free/Waived"
    elif "유심비" in text and "납부" in text:
        result['Sim_Fee_Status'] = "Paid"
    else:
        result['Sim_Fee_Status'] = "Unknown"

    # 4. Gifts
    gifts = []
    for g in ["상품권", "네이버페이", "스타벅스", "증정", "포인트"]:
        if g in text:
            gifts.append(g)
    result['Gifts_Keywords'] = ", ".join(gifts) if gifts else "None"

    # 5. Hotspot/Tethering
    if "핫스팟" in text or "테더링" in text:
        hs_match = re.search(r'(?:핫스팟|테더링)\s*(?:월)?\s*(\d+)(GB|MB)', text)
        result['Hotspot_Info'] = f"{hs_match.group(1)}{hs_match.group(2)}" if hs_match else "Mentioned"
    else:
        result['Hotspot_Info'] = "N/A"
        
    # 6. NFC
    if "NFC" in text:
        result['NFC_Support'] = "Mentioned"
    else:
        result['NFC_Support'] = "N/A"

    return result

def generate_report():
    input_file = r"E:\알뜰폰\크롤링\storage\sessions\20260123_145859\merged_combined_results_20260123_145859.xlsx"
    output_file = r"E:\알뜰폰\크롤링\comprehensive_data_report.xlsx"
    
    print(f"Reading input: {input_file}")
    try:
        df = pd.read_excel(input_file)
    except Exception as e:
        print(f"Error: {e}")
        return

    # --- Sheet 1: Currently Collected (Sample per platform) ---
    print("Generating [Current_Collection] sheet...")
    # Group by platform and take the first entry as a representative sample
    current_df = df.groupby('platform').first().reset_index()
    
    # Define columns to show (What we currently have in DB/Excel)
    # Check which columns actually exist
    available_cols = df.columns.tolist()
    
    # Target columns we WANT to show
    target_mapping = {
        'platform': 'Platform',
        'carrier': 'Carrier',
        'plan_name': 'Plan_Name_Example',
        'price': 'Price_Collected',
        'data_raw': 'Data_String_Collected',
        'voice_type': 'Voice_Parsed',
        'sms_type': 'SMS_Parsed',
        'network_type': 'Network_Parsed',
        'url': 'URL_Reference'
    }
    
    # Select only existing columns
    selected_cols = [c for c in target_mapping.keys() if c in available_cols]
    final_current_df = current_df[selected_cols].copy()
    
    # Rename them
    rename_dict = {k: v for k, v in target_mapping.items() if k in selected_cols}
    final_current_df.rename(columns=rename_dict, inplace=True)
    
    # Add missing columns as N/A for consistency
    for k, v in target_mapping.items():
        if k not in selected_cols:
            final_current_df[v] = "Not Collected Yet"

    # --- Sheet 2: Potential Collection (Crawled examples) ---
    print("Generating [Potential_Collection] sheet (Crawling)...")
    
    potential_data = []
    
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()
        
        # Iterate over the representative rows
        for idx, row in current_df.iterrows():
            platform = row['platform']
            url = row['url']
            
            print(f"[{idx+1}/{len(current_df)}] Scanning {platform}...")
            
            if not isinstance(url, str) or not url.startswith('http'):
                print(f"  Skipping invalid URL: {url}")
                continue
            
            entry = {
                'Platform': platform,
                'Sample_URL': url
            }
            
            try:
                page.goto(url, timeout=15000)
                page.wait_for_load_state('domcontentloaded')
                time.sleep(1) # tiny buffer
                
                text = page.inner_text("body")
                
                # Extract fields
                extracted = extract_potential_fields(text)
                entry.update(extracted)
                
            except Exception as e:
                print(f"  Error: {e}")
                entry.update({
                    'Discount_Period_Months': 'Error',
                    'Normal_Price_Won': 'Error',
                    'Sim_Fee_Status': 'Error',
                    'Gifts_Keywords': 'Error'
                })
            
            potential_data.append(entry)
            
        browser.close()

    potential_df = pd.DataFrame(potential_data)

    # --- Save to Excel ---
    with pd.ExcelWriter(output_file, engine='openpyxl') as writer:
        final_current_df.to_excel(writer, sheet_name='1_Collected_Columns', index=False)
        potential_df.to_excel(writer, sheet_name='2_Potential_Columns', index=False)
        
    print(f"SUCCESS: Report saved to {output_file}")

if __name__ == "__main__":
    generate_report()
