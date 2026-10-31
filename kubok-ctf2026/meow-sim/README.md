# MeowSim: Schrödinger E... — райтап

**Категория:** mobile · **Баллы:** 100 · **Решивших:** 345 · **Формат:** Android APK (46 KiB)

**Флаг:** `ctfcup{cat_0bserv3r_92}`

---

## TL;DR

Android-тамагочи «кот Шрёдингера». Флаг зашифрован XOR-гаммой, которая выводится из SHA-256 от склейки состояния игры. Открыть хранилище можно только в «правильной невозможности»: питомец уверен, что кот жив, коробка помнит, что кот мёртв, а наблюдатель ничего не видел. Через UI это состояние недостижимо — его создаёт скрытая `RestoreExperimentActivity`, которую интерфейс не запускает ни разу. Я пошёл дальше и вообще не стал запускать приложение: воспроизвёл deriveKey + stream на Python и перебрал единственный свободный параметр (`stability` из 11 значений), используя встроенный в задачу оракул — проверку `startsWith("ctfcup{")`.

---

## Легенда

Таск описывает «квантового кота»: прило­жение, где коробка при закрытой крышке не может определить состояние кота — «часть кода считает кота живым, другая помнит другой исход, а наблюдатель всегда всё ломает». Это не декорация, а документация уязвимости, размазанная по интерфейсу. Особенно полезны записи Дневника внутри приложения:

- *Запись 02:* «если смотреть на кота слишком внимательно, он выбирал одно состояние… коробка продолжала помнить больше, чем должна»
- *Запись 03:* «режим восстановления… иногда восстанавливал кота и коробку отдельно от того, кто на них смотрел»
- *Запись 04:* «правильная невозможность» — коробка уверена в одном, питомец в другом, наблюдатель ничего не видел.

---

## Разведка

APK крошечный: один `classes.dex` (~54 KiB), **нет** `lib/` (нативного кода нет), нет обфускации имён. Значит, вся логика — в Java-байткоде, и достаточно статики.

Открываю в **jadx-gui** (взял релиз `with-jre`, Java ставить не пришлось). Карта пакетов сразу рисует архитектуру:

| Пакет/класс | Роль |
|---|---|
| `flag/FlagVault` | хранит `ENCRYPTED_FLAG`, метод `open()`, `canOpenFlagVault` |
| `security/HashKit` | SHA-256 + hex — просто калькулятор |
| `security/TamperDetector` | анти-патч (`isUnexpectedPackage`) |
| `state/BoxStore` | SQLite `box_state.db` + «печать» `sealFor` |
| `state/PetStore`, `state/ObserverStore` | SharedPreferences: питомец и наблюдатель |
| `state/SealVerifier` | проверка печати снимка |
| `state/StateRepository` | все игровые действия |
| `lab/RestoreExperimentActivity` | скрытый режим восстановления |

Тексты дневника лежат в ресурсах — их стоит прочитать до анализа кода, экономит время.

---

## Анатомия состояния

Ядро задачи — `QuantumState.canOpenFlagVault()`:

```java
public boolean canOpenFlagVault() {
    return this.pet.catAlive && this.box.catDead && this.box.superposition
        && this.box.stability >= 90 && !this.observer.observed && !this.tampered;
}
```

Разбираю на составляющие. Где живут данные и как их изменить:

| Условие | Хранилище | Можно ли честно? |
|---|---|---|
| `pet.catAlive` | SharedPreferences | да, по умолчанию `true` |
| `box.catDead` | SQLite | **только через `observe()`** — и он же ставит `observed=true` |
| `box.superposition` | SQLite | да, дефолт `true` |
| `box.stability >= 90` | SQLite | да, кнопка «Стабилизировать» (потолок **92**) |
| `!observer.observed` | SharedPreferences | да, просто не нажимать «Наблюдать» |
| `!tampered` | TamperDetector | да, не патчить APK / не переименовывать пакет |

Ключевой конфликт: единственный способ получить `box.catDead = true` — нажать «Наблюдать», но это же действие ставит `observed = true` и схлопывает суперпозицию. `stabilize()` наоборот — жёстко пишет `catDead = false`. Вывод: **честной игрой парадокс не собрать**, это подтверждено кодом, а не легендой.

---

## Хранилище флага

`FlagVault.open()` — классическая схема «ключ из состояния → гамма → XOR»:

```java
byte[] key = deriveKey(quantumState);
byte[] ks  = stream(key, ENCRYPTED_FLAG.length);
byte[] out = new byte[ENCRYPTED_FLAG.length];
for (int i = 0; i < ENCRYPTED_FLAG.length; i++)
    out[i] = (byte) (ENCRYPTED_FLAG[i] ^ ks[i]);
String s = new String(out, StandardCharsets.UTF_8);
return !s.startsWith("ctfcup{") ? "Коробка открылась, но флаг декогерировал." : s;
```

Ключ:

```java
private static byte[] deriveKey(QuantumState q) {
    return HashKit.sha256Bytes(q.observer.observerToken + "|" + q.box.boxSeal + "|"
        + q.box.stability + "|" + q.pet.catAlive + "|" + q.box.catDead + "|"
        + q.box.superposition + "|" + q.observer.observed + "|meowsim-v1");
}
```

Гамма: `stream` кладёт в буфер ключ + `int`-счётчик (big-endian) и хэширует блоками по 32 байта:

```java
ByteBuffer buf = ByteBuffer.allocate(key.length + 4);
buf.put(key);
buf.putInt(i2);                    // big-endian!
out.write(HashKit.sha256Bytes(buf.array()), 0, 32);
```

Полезная арифметика: `ENCRYPTED_FLAG` — **23 байта**, значит флаг длиной 23 символа (`ctfcup{` + 15 + `}`), и для расшифровки хватит первого блока гаммы (`counter = 0`).

---

## Скрытая дверь

`RestoreExperimentActivity` ждёт три extra:

- `mode` — должен быть строкой `"restore"`;
- `snapshot` — строка состояния, которую распарсит `ExperimentSnapshot.parse()`;
- `seal` — печать: `SealVerifier.verify(snapshot, observerToken, seal)`.

И вот наблюдение, которое всё решает: **я прошёлся поиском по `MainActivity` — этот Activity не запускается из UI ни разу.** Ни кнопки, ни Intent. В Android Activity — компонент, который можно стартовать извне (`adb shell am start`, Activity Launcher), вопрос только в `exported` из манифеста. Это скрытая поверхность атаки, оставленная автором намеренно.

Дальше — три находки, которые снимают всю «криптографическую» сложность:

1. **Печать снимка вычислима.** `SealVerifier.verify` — это просто `sha256(snapshot + "|" + token + "|restore-v1")`. А `observerToken` берётся из `ObserverStore.DEFAULT_TOKEN = "ny4n-lab-token"` и **нигде в коде не меняется** (его сохраняет даже `observe()`).
2. **Печать коробки подделывать не нужно.** `ExperimentSnapshot.toBoxState()` при restore **сам** пересчитывает `boxSeal` через `sealFor(catDead, superposition, stability)`. Машина ставит пломбу на мой снимок.
3. **Снимок почти пустой.** У `parse()` щедрые дефолты: `catAlive=true`, `superposition=true`, `observed=false`, `restoreObserverState=false`. Реально нужно переопределить только `catDead=true` и `stability`. Наблюдателя restore не трогает — «отдельно от того, кто на них смотрел», ровно как в Дневнике.

Формат снимка: пары `key=value` через `;`, например `catDead=true;stability=92`.

---

## Два пути к флагу

**Путь А — через приложение.** Эмулятор (LDPlayer / AVD), установка APK, запуск скрытого Activity через adb с тремя extras, кнопка «Открыть коробку». Ловушки: никогда не жать «Наблюдать»; не жать «Стабилизировать» **после** restore (затрёт `catDead=false` и пересчитает печать); перед этим снести данные приложения до заводского состояния.

**Путь Б (мой выбор) — полностью офлайн.** Ключ выводится из конечного состояния, состояние известно с точностью до одного параметра — значит, ключ воспроизводится на Python без запуска приложения вообще. Единственная неизвестная — `stability`: условие требует ≥ 90, клэмп в `toBoxState` режет до ≤ 100, итого 11 кандидатов. Перебор легален: у задачи встроенный оракул `startsWith("ctfcup{")` — он же работает и внутри самого приложения при открытии коробки.

Скрипт:

```python
import hashlib, struct

ENCRYPTED_FLAG = [-39, -35, 55, 54, 127, -92, 31, 97, 23, -55, 17, 11,
                  12, -63, 42, -110, 29, 8, -113, 91, -96, 117, 36]
TOKEN = "ny4n-lab-token"  # ObserverStore.DEFAULT_TOKEN

def jb(b):                      # Java пишет булевы как true/false
    return "true" if b else "false"

def sha256_hex(s):
    return hashlib.sha256(s.encode("utf-8")).hexdigest()

def sha256_bytes(b):
    return hashlib.sha256(b).digest()

def box_seal(cat_dead, sup, stability):
    return sha256_hex(f"box|{jb(cat_dead)}|{jb(sup)}|{stability}|meowsim-v1")

def derive_key(token, seal, stability, cat_alive, cat_dead, sup, observed):
    s = (f"{token}|{seal}|{stability}|{jb(cat_alive)}|{jb(cat_dead)}"
         f"|{jb(sup)}|{jb(observed)}|meowsim-v1")
    return sha256_bytes(s.encode("utf-8"))

def stream(key, n):
    out, counter = b"", 0
    while len(out) < n:
        out += sha256_bytes(key + struct.pack(">I", counter))  # big-endian int32
        counter += 1
    return out[:n]

def decrypt(key):
    data = bytes(x & 0xFF for x in ENCRYPTED_FLAG)  # Java byte знаковый
    ks = stream(key, len(data))
    raw = bytes(a ^ b for a, b in zip(data, ks))
    try:
        return raw.decode("utf-8")
    except UnicodeDecodeError:
        return None

for s in range(90, 101):
    out = decrypt(derive_key(TOKEN, box_seal(True, True, s), s, True, True, True, False))
    if out and out.startswith("ctfcup{"):
        print(f"stability = {s} -> {out}")
        break
```

Грабли, о которые я спотыкался по дороге: Java `byte` знаковый (−39 в Python — это 217, лечится `& 0xFF`); булевы в склейке обязаны быть `true`/`false` строчными, а не питоновскими `True`; `derive_key` возвращает **байты** дайджеста, а `box_seal` — **hex-строку** (она подставляется внутрь второй строки); счётчик гаммы — ровно 4 байта big-endian, `struct.pack(">I", ...)`.

---

## Флаг

```
ctfcup{cat_0bserv3r_92}
```

Перебор нашёл `stability = 92` — потолок кнопки «Стабилизировать». Автор шифровал флаг для каноничного конечного состояния: кот мёртв по коробке, жив по питомцу, суперпозиция, наблюдатель чист, стабильность на максимуме лаборатории.

---

## Уроки

1. **Имена классов — карта сокровищ.** Пакеты `flag/`, `security/`, `state/`, `lab/` рассказали всю архитектуру до чтения единой строчки кода. В не обфусцированном APK разведка начинается с дерева классов, а не с `main()`.
2. **«Не запускается из UI» ≠ «не запускается».** Скрытые Activity, экспортированные сервисы и ресиверы — классическая поверхность атаки в Android. Поиск «мёртвых» компонентов, на которые никто не ссылается, — отдельный чеклист реверса мобилок.
3. **Крипта без соли на предсказуемом состоянии — не крипта.** Ключ выводится из игрового состояния, все ингредиенты которого известны или вычислимы → офлайн-расшифровка. А `startsWith("ctfcup{")` — подарок: локальный оракул для перебора свободного параметра.
4. **Легенда — это спойлер, а не украшение.** Дневник приложения честно описал и парадокс, и механизм (restore «отдельно от наблюдателя»). Читать её стоило в первый день, а не после.
5. **Аккуратность с типами решает больше, чем знание алгоритмов.** Хэш-гамма на 15 строк; почти всё время съели детали: знаковый байт, регистр булевых, hex-строка против байтов, порядок байт счётчика.


