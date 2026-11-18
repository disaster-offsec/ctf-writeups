# Lab: Insecure direct object references

Level: `APPRENTICE`

## Description

> This lab stores user chat logs directly on the server's file system, and retrieves them using static URLs.

Solve the lab by finding the password for the user carlos, and logging into their account.

# Solution

Если мы зайдем в чат и поотправляем сообщения, то потыкав по кнопкам сможем
скачать файл чата и он будет иметь название `n.txt`, где n>1.

Затем зайдем в историю загрузок и увидим откуда скачался файл(это ведь `REST-api`)

И увидим `https://0ae0000d04c42369807a672600680091.web-security-academy.net/download-transcript/5.txt`

Откроем эту же ссылку но для файла `1.txt` и увидим следующее:

```txt
CONNECTED: -- Now chatting with Hal Pline --
You: Hi Hal, I think I've forgotten my password and need confirmation that I've got the right one
Hal Pline: Sure, no problem, you seem like a nice guy. Just tell me your password and I'll confirm whether it's correct or not.
You: Wow you're so nice, thanks. I've heard from other people that you can be a right ****
Hal Pline: Takes one to know one
You: Ok so my password is k9wxx2mhbiis5wtif9wr. Is that right?
Hal Pline: Yes it is!
You: Ok thanks, bye!
Hal Pline: Do one!
```

Вот мы и получили пароль от аккаунта через IDOR для скачивания файла.

Осталось залогиниться:
- username: `carlos`
- password: `k9wxx2mhbiis5wtif9wr`

Вот мы и прошли лабу

# Remediation

Для устранения `IDOR` надо: 
- проверять, что текущий пользователь (сессия) имеет право на доступ к запрашиваемому ресурсу (объекту).
- использовать непредсказуемые идентификаторы (`UUID`) вместо последовательных номеров
