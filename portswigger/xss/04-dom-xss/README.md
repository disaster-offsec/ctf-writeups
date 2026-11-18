# Lab: DOM XSS in innerHTML sink using source location.search

Level: `APPRENTICE`

## Description

> This lab contains a DOM-based cross-site scripting vulnerability in the search blog functionality. It uses an innerHTML assignment, which changes the HTML contents of a div element, using data from location.search.

To solve this lab, perform a cross-site scripting attack that calls the alert function.

# Solution

## Recon

Чтож, снова вводим `test123` и видим, что это видимо DOM-XSS

![fig1.png](fig1.png)

## Source & Sink

```html
<section class="blog-header">
    <h1><span>0 search results for '</span><span id="searchMessage">test123</span><span>'</span></h1>
    <script>
        function doSearchQuery(query) {
            document.getElementById('searchMessage').innerHTML = query;
        }
        var query = (new URLSearchParams(window.location.search)).get('search');
        if(query) {
            doSearchQuery(query);
        }
    </script>
    <hr>
</section>
<section class="search">
    <form action="/" method="GET">
        <input type="text" placeholder="Search the blog..." name="search">
        <button type="submit" class="button">Search</button>
    </form>
</section>
```

Подтверждено: это `DOM-based XSS`. Данные из `location.search` попадают в `innerHTML` без санитизации

## Exploitation

Payload: `<svg onload=alert(1)>`

![fig2.png](fig2.png)

---

# Explanation

Но почему именно так?

Почему не так:
- `'><svg onload=alert(1)>`
- `<script>alert(1)</script>`

Все просто:
1. Почему `<svg onload=...>` работает:
    > Функция `innerHTML` берет строку и парсит её как `HTML`-код.
    > Когда браузер видит `<svg onload=...>`, он создает элемент `SVG`, добавляет его в `DOM`,
    > и как только элемент загружается, срабатывает событие `onload`. Это стандартное поведение для `HTML`-элементов.
2. Почему `<script>alert(1)</script>` НЕ работает:
    > Это особенность спецификации `HTML5`.
    > Когда ты используешь `innerHTML` для вставки контента,
    > браузер специально игнорирует (не исполняет) теги `<script>`, по соображениям безопасности.

    Что происходит внутри:
    1. Браузер парсит строку `<script>alert(1)</script>`.
    2. Создает `DOM`-узел `<script>`.
    3. **Но не выполняет его код**. Тег просто вставляется в `DOM`, но не запускается.

    > **Примечание**:
    > Если ты вставишь `<script>` через `document.write` (как в прошлой лабе), он сработает,
    > потому что `document.write` работает иначе. Но `innerHTML` -- это "безопасный" метод вставки
    > (относительно XSS через скрипты, но не через события).
3. Почему `'><svg onload=...>` тоже сработал бы:
    > Потому что внутри `innerHTML` получим такое:
    > ```html
    > <span id="searchMessage">'><svg onload=alert(1)></span>
    > ```
    > И того получим текст `'>` и `HTML` тег `<svg ...>`

# Remediation

Чтобы избежать данный тип уязвимостей:
- используйте `textContent`, который работает с данными как с обычным текстом (`plain text`),
- либо обрабатывайте ввод, используя либы такие как `DOMPurify` перед вставкой в `DOM`
