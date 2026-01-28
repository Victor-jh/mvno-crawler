import re
import logging

logger = logging.getLogger("parsers")

def parse_data_str(text):
    """
    Parse complex data strings into structured components.
    
    Examples:
    - "11GB+일2GB+3Mbps" -> {'base': 11.0, 'daily': 2.0, 'qos': 3.0}
    - "15GB+3Mbps" -> {'base': 15.0, 'daily': 0.0, 'qos': 3.0}
    - "무제한" -> {'base': 999.0, 'daily': 0.0, 'qos': 0.0} (Logic TBD)
    - "7GB" -> {'base': 7.0, 'daily': 0.0, 'qos': 0.0}
    """
    if not text:
        return {'base': 0.0, 'daily': 0.0, 'qos': 0.0}
        
    text = text.replace(" ", "").upper()
    
    result = {
        'base': 0.0,
        'daily': 0.0,
        'qos': 0.0
    }
    
    # 1. QoS Speed (Mbps/Kbps)
    # Pattern: 3Mbps, 1Mbps, 400Kbps
    # If found, extract and remove from text to simplify base parsing
    qos_match = re.search(r'(\d+(?:\.\d+)?)(MBPS|KBPS)', text)
    if qos_match:
        speed = float(qos_match.group(1))
        unit = qos_match.group(2)
        if unit == 'KBPS':
            speed = speed / 1000.0 # Normalize to Mbps
        result['qos'] = speed
        # Remove matched qos part effectively? 
        # Actually, "11GB+일2GB+3Mbps" structure is common.
        
    # 2. Daily Data (일2GB, 매일2GB)
    # Pattern: 일(\d+)GB
    daily_match = re.search(r'(?:일|매일)(\d+(?:\.\d+)?)GB', text)
    if daily_match:
        result['daily'] = float(daily_match.group(1))
        
    # 3. Base Data
    # Pattern: (\d+)GB or (\d+)MB at the start or before +
    # Be careful not to match '일2GB' as base data.
    # We can rely on position. Usually Base comes first.
    # Or strict matching: look for number followed by GB/MB that is NOT preceded by '일'/'매일'
    # Use negative lookbehind is tricky in Python if variable length, but '일' is fixed length.
    
    # Simpler approach: Split by '+'
    parts = text.split('+')
    
    for part in parts:
        # Check for Daily
        if '일' in part or '매일' in part:
            continue # Already handled or strictly handled here?
            
        # Check for QoS
        if 'BPS' in part:
            continue
            
        # Remaining is likely Base Data
        # 11GB, 15GB, 500MB
        base_gb_match = re.search(r'(\d+(?:\.\d+)?)GB', part)
        base_mb_match = re.search(r'(\d+(?:\.\d+)?)MB', part)
        
        if base_gb_match:
            result['base'] += float(base_gb_match.group(1))
        elif base_mb_match:
            result['base'] += float(base_mb_match.group(1)) / 1024.0
            
    return result

def parse_voice_str(text):
    """
    Parse voice text to minute value or special flag.
    Returns: string ('unlimited', '100', etc)
    """
    if not text: return "0"
    text = text.replace(" ", "")
    
    if "무제한" in text or "기본제공" in text:
        return "unlimited"
        
    # Extract number (분)
    match = re.search(r'(\d+)분', text)
    if match:
        return match.group(1)
        
    return text

def parse_sms_str(text):
    """
    Parse SMS text.
    """
    if not text: return "0"
    text = text.replace(" ", "")
    
    if "무제한" in text or "기본제공" in text:
        return "unlimited"
        
    match = re.search(r'(\d+)건', text)
    if match:
        return match.group(1)
        
    return text

def determine_network_type(plan_name, page_text=""):
    """
    Determine if plan is 5G or LTE based on name and context.
    """
    target = (plan_name + " " + page_text).upper()
    
    if "5G" in target:
        return "5G"
    # Default to LTE for now if not 5G? Or 3G?
    # Most MVNOs are LTE.
    return "LTE"
