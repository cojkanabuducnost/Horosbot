import requests
from bs4 import BeautifulSoup
import xml.etree.ElementTree as ET
import os
import re

webhook_url = os.environ.get("SLACK_WEBHOOK")
rss_url = "https://lepaisrecna.mondo.rs/rss/97/Astrologija/Dnevni-horoskop"

target_signs = {
    "Lav": "🦁", "Devica": "👩", "Vaga": "⚖️", 
    "Škorpija": "🦂", "Vodolija": "🏺", "Ribe": "🐟"
}

headers = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
}

try:
    # 1. Fetch RSS and get latest article
    rss_response = requests.get(rss_url, headers=headers, timeout=60)
    root = ET.fromstring(rss_response.content)
    first_item = root.find('.//item')
    
    if first_item is None or first_item.find('link') is None:
        raise Exception("Could not find article link in RSS feed.")
        
    article_url = first_item.find('link').text.strip()
    print(f"Reading article: {article_url}")

    # 2. Fetch the article
    article_response = requests.get(article_url, headers=headers, timeout=60)
    soup = BeautifulSoup(article_response.content, 'html.parser')
    message_lines = ["*Dnevni Horoskop* ☕\n"]

    # 3. Extract text
    for sign, emoji in target_signs.items():
        sign_element = soup.find(
            lambda tag: tag.name in ['h2', 'h3', 'h4', 'strong', 'b', 'p'] 
            and sign.upper() in tag.get_text(strip=True).upper() 
            and len(tag.get_text(strip=True)) < 30
        )
        
        text_block = ""
        
        if sign_element:
            if sign_element.name in ['strong', 'b'] and sign_element.parent.name in ['p', 'div']:
                text_block = sign_element.parent.get_text(separator=" ", strip=True)
            else:
                next_element = sign_element.find_next(['p', 'div'])
                if next_element:
                    text_block = next_element.get_text(separator=" ", strip=True)

        if text_block.upper().startswith(sign.upper()):
            text_block = re.sub(f"^{sign.upper()}[\\s\\-\\:|\\.]*", "", text_block, flags=re.IGNORECASE).strip()

        if text_block and len(text_block) > 20:
            pattern = r"Posao\s*:?\s*(.*?)\s*Ljubav\s*:?\s*(.*?)\s*Zdravlje\s*:?\s*(.*)"
            match = re.search(pattern, text_block, re.DOTALL | re.IGNORECASE)
            
            if match:
                posao = ' '.join(match.group(1).split())
                ljubav = ' '.join(match.group(2).split())
                zdravlje = ' '.join(match.group(3).split())
                message_lines.append(f"*{sign}* {emoji}:\n*Posao:* {posao}\n*Ljubav:* {ljubav}\n*Zdravlje:* {zdravlje}\n")
            else:
                message_lines.append(f"*{sign}* {emoji}:\n{text_block}\n")

    # 4. Extract Author (RegEx Fix)
    author_text = ""
    author_element = soup.find(
        lambda tag: tag.name in ['p', 'span', 'div'] 
        and 'Autor:' in tag.get_text(strip=True)
        and len(tag.get_text(strip=True)) < 150
    )
    
    if author_element:
        raw_author_text = author_element.get_text(separator=" ", strip=True)
        
        # Hvata reč "Autor:" i sva slova nakon toga dok ne naiđe na prvi broj (datum)
        match = re.search(r'(Autor:\s*[A-Za-zČčĆćŽžŠšĐđ\-\s]+)', raw_author_text)
        if match:
            author_text = match.group(1).strip()
    
    # 5. Send to Slack
    if len(message_lines) > 1:
        if author_text:
            message_lines.append(f"\n_{author_text}_")
            
        requests.post(webhook_url, json={"text": "\n".join(message_lines)}, timeout=15)
        print("Successfully sent to Slack!")
    else:
        print("Error: Could not extract sign text from the article HTML.")

except Exception as e:
    print(f"Error running horoscope bot: {e}")
