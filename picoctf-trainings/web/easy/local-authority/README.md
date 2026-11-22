<!-- конвертировано из local-authority.typ, tools/typ2readme.py -->

| | |
|---|---|
| **Платформа / Событие** | picoCTF Trainings |
| **Категория** | Web |
| **Сложность** | Easy 100 pts |
| **Статус** | done |
| **Дата решения** | 19 июля 2026 |
| **Ссылка на таск** | — |

# Local Authority

## Задание

Can you get the flag?

## Решение

Смотрим DevTools:Sources: secure.js
```javascript
function checkPassword(username, password)
{
  if( username === 'admin' && password === 'strongPassword098765' )
  {
    return true;
  }
  else
  {
    return false;
  }
}
```

И получаем: 

```text
picoCTF{j5_15_7r4n5p4r3n7_a8788e61}
```
