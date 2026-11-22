<!-- конвертировано из cookie-monster-secret-recipe.typ, tools/typ2readme.py -->

| | |
|---|---|
| **Платформа / Событие** | picoCTF Trainings |
| **Категория** | Web |
| **Сложность** | Easy 50 pts |
| **Статус** | done |
| **Дата решения** | 19 июля 2026 |
| **Ссылка на таск** | — |

# Cookie Monster Secret Recipe

## Задание

Cookie Monster has hidden his top-secret cookie recipe somewhere on his website. As an aspiring cookie detective, your mission is to uncover this delectable secret. Can you outsmart Cookie Monster and find the hidden recipe?

## Решение

Вводим любой логин и пароль, проваливаемя на страничку с Access Denied.

Затем просто берем cookie из DevTools

```text
secret_recipe:cGljb0NURntjMDBrMWVfbTBuc3Rlcl9sMHZlc19jMDBraWVzXzJDODA0MEVGfQ%3D%3D
```

Затем прогоняем в base64 -d:

```bash
echo cGljb0NURntjMDBrMWVfbTBuc3Rlcl9sMHZlc19jMDBraWVzXzJDODA0MEVGfQ%3D%3D | base64 -d

picoCTF{c00k1e_m0nster_l0ves_c00kies_2C8040EF}
```
