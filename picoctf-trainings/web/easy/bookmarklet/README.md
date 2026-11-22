<!-- конвертировано из bookmarklet.typ, tools/typ2readme.py -->

| | |
|---|---|
| **Платформа / Событие** | picoCTF Trainings |
| **Категория** | Web |
| **Сложность** | Easy 50 pts |
| **Статус** | done |
| **Дата решения** | 19 июля 2026 |
| **Ссылка на таск** | — |

# Bookmarklet

## Задание

Why search for the flag when I can make a bookmarklet to print it for me?

## Решение

Заходим на страницу и видим:

```text
javascript:(function() {
    var encryptedFlag = "àÒÆÞ¦È¬ëÙ£Ö�ÓÚåÛÑ¢ÕÓ�¨Í�ÕÄ¦�í";
    var key = "picoctf";
    var decryptedFlag = "";
    for (var i = 0; i < encryptedFlag.length; i++) {
        decryptedFlag += String.fromCharCode((encryptedFlag.charCodeAt(i) - key.charCodeAt(i % key.length) + 256) % 256);
    }
    alert(decryptedFlag);
})();
```

Получаем флаг в алерте:

```text
picoCTF{p@g3_turn3r_18d2fa20}
```
