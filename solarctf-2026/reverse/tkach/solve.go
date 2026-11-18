package main

// Автомат шрифта и декодер «справа налево».
//
//   F[j] = T(F[j-1], c[j])           — прямой проход (lookup calt #1), состояние = выданный глиф
//   H[j] = R(F[j], H[j+1]), H[n+1]=']' — обратный проход (lookup calt #2, reverse chain)
//   (G[a],G[b]) = P(H[a],H[b])       — ss01: пары (1,2),(3,4),...
//   GPOS: у пары шаг 300 и небольшие сдвиги
// T — латинский квадрат, поэтому по (H[j],H[j+1]) однозначно находится F[j],
// а по (F[j-1],F[j]) — символ c[j].

import (
	"fmt"
	"runtime"
	"sort"
	"strings"
	"sync"
)

type tk struct {
	s uint16
	c byte
}

type Auto struct {
	f          *Font
	start, end uint16
	chars      []byte
	cg         map[byte]uint16
	fwdL, revL int // индексы lookup'ов calt
	ssL        int // индекс lookup'а ss01
	T, Tprev   map[tk]uint16
	Tinv       map[[2]uint16]byte
	gen        [5][]uint16 // gen[1..4]: множества состояний F по позициям (j-1)%4+1
	mu         sync.Mutex
	revMemo    map[[2]uint16]uint16
	pairMemo   map[[2]uint16][2]uint16
	mid        []byte
	isMid      [256]bool
}

func NewAuto(f *Font) *Auto {
	a := &Auto{f: f, cg: map[byte]uint16{}, T: map[tk]uint16{}, Tprev: map[tk]uint16{},
		Tinv: map[[2]uint16]byte{}, revMemo: map[[2]uint16]uint16{}, pairMemo: map[[2]uint16][2]uint16{}}
	calt := f.GSUB.FeatureLookups("calt")
	ss := f.GSUB.FeatureLookups("ss01")
	if len(calt) != 2 || len(ss) != 1 {
		panic("неожиданная структура фич calt/ss01")
	}
	a.fwdL, a.revL, a.ssL = calt[0], calt[1], ss[0]
	a.start, a.end = f.cmap['['], f.cmap[']']
	for c := 'a'; c <= 'z'; c++ {
		a.chars = append(a.chars, byte(c))
	}
	for c := 'A'; c <= 'Z'; c++ {
		a.chars = append(a.chars, byte(c))
	}
	for c := '0'; c <= '9'; c++ {
		a.chars = append(a.chars, byte(c))
	}
	a.mid = append([]byte(nil), a.chars...)
	a.mid = append(a.mid, '_')
	for _, c := range a.mid {
		a.isMid[c] = true
	}
	a.chars = append(a.chars, '_', '{', '}')
	for _, c := range a.chars {
		a.cg[c] = f.cmap[rune(c)]
	}
	// BFS по поколениям состояний
	cur := []uint16{a.start}
	for g := 1; g <= 5; g++ {
		seen := map[uint16]bool{}
		var next []uint16
		for _, s := range cur {
			for _, c := range a.chars {
				n := a.fwd(s, c)
				a.T[tk{s, c}] = n
				if s != a.start {
					a.Tprev[tk{n, c}] = s
				}
				a.Tinv[[2]uint16{s, n}] = c
				if !seen[n] {
					seen[n] = true
					next = append(next, n)
				}
			}
		}
		if g <= 4 {
			a.gen[g] = next
		}
		cur = next
	}
	return a
}

func (a *Auto) fwd(s uint16, c byte) uint16 {
	buf := []uint16{s, a.cg[c]}
	a.f.GSUB.applyAt(buf, a.fwdL, 1)
	return buf[1]
}

// R: глиф позиции j по состоянию F[j] и уже готовому правому соседу.
func (a *Auto) R(F, Hn uint16) uint16 {
	k := [2]uint16{F, Hn}
	a.mu.Lock()
	v, ok := a.revMemo[k]
	a.mu.Unlock()
	if ok {
		return v
	}
	buf := []uint16{F, Hn}
	a.f.GSUB.applyAt(buf, a.revL, 0)
	a.mu.Lock()
	a.revMemo[k] = buf[0]
	a.mu.Unlock()
	return buf[0]
}

// P: результат ss01 для пары (Ha,Hb), стоящей на позициях (нечётная, чётная).
func (a *Auto) P(Ha, Hb uint16) [2]uint16 {
	k := [2]uint16{Ha, Hb}
	a.mu.Lock()
	v, ok := a.pairMemo[k]
	a.mu.Unlock()
	if ok {
		return v
	}
	buf := []uint16{a.start, Ha, Hb, a.end}
	a.f.GSUB.runLookup(buf, a.ssL)
	v = [2]uint16{buf[1], buf[2]}
	a.mu.Lock()
	a.pairMemo[k] = v
	a.mu.Unlock()
	return v
}

func (a *Auto) genOf(j int) []uint16 { return a.gen[(j-1)%4+1] }

// Fseq: состояния F[0..len(text)] для известного текста.
func (a *Auto) Fseq(text string) []uint16 {
	F := []uint16{a.start}
	for i := 0; i < len(text); i++ {
		F = append(F, a.T[tk{F[i], text[i]}])
	}
	return F
}

// ---------------- декодер ----------------

type Solver struct {
	f      *Font
	a      *Auto
	r      *Rast
	ref    *Img
	s      float64 // px на единицу шрифта
	X0, Yb float64
	n      int
	prefix string
	beam   int
	thr    float32
	log    func(string, ...any)
}

type Hyp struct {
	err   float64
	x     int
	F, H  uint16
	chars []byte
	ab    *Above
}

func (sv *Solver) pairLayers(g [2]uint16, p int) []Layer {
	var items [2]struct{ x, y float64 }
	items[0].x, items[1].x = float64(600*p), float64(600*p+300)
	if pv, ok := sv.f.PairGeom(g[0], g[1]); ok {
		items[0].x += float64(pv.x1)
		items[0].y = float64(pv.y1)
		items[1].x += float64(pv.x2)
		items[1].y = float64(pv.y2)
	} else {
		items[1].x = float64(600*p + 1300)
	}
	ls := sv.f.glyphLayers(sv.r, g[0], sv.s, sv.X0+items[0].x*sv.s, sv.Yb-items[0].y*sv.s)
	return append(ls, sv.f.glyphLayers(sv.r, g[1], sv.s, sv.X0+items[1].x*sv.s, sv.Yb-items[1].y*sv.s)...)
}

func (sv *Solver) singleLayers(g uint16, p int) []Layer {
	return sv.f.glyphLayers(sv.r, g, sv.s, sv.X0+float64(600*p)*sv.s, sv.Yb)
}

func (sv *Solver) init() []*Hyp {
	n, a := sv.n, sv.a
	type ini struct {
		Fn, Fp, Hn, Hp uint16
		ls             []Layer
		err            float64
	}
	var items []*ini
	for _, Fn := range a.genOf(n) {
		Fp, ok := a.Tprev[tk{Fn, '}'}]
		if !ok {
			continue
		}
		it := &ini{Fn: Fn, Fp: Fp, Hn: a.R(Fn, a.end)}
		if n%2 == 1 {
			it.ls = sv.singleLayers(it.Hn, (n-1)/2)
		} else {
			it.Hp = a.R(Fp, it.Hn)
			it.ls = sv.pairLayers(a.P(it.Hp, it.Hn), (n-2)/2)
		}
		items = append(items, it)
	}
	empty := NewAbove(sv.ref.W, sv.ref.H)
	var wg sync.WaitGroup
	ch := make(chan *ini, len(items))
	for _, it := range items {
		ch <- it
	}
	close(ch)
	for w := 0; w < runtime.NumCPU(); w++ {
		wg.Add(1)
		go func() {
			defer wg.Done()
			for it := range ch {
				it.err = FeasScore(sv.f, sv.ref, empty, it.ls, sv.thr)
			}
		}()
	}
	wg.Wait()
	sort.Slice(items, func(i, j int) bool { return items[i].err < items[j].err })
	if len(items) > sv.beam {
		items = items[:sv.beam]
	}
	var out []*Hyp
	for _, it := range items {
		ab := NewAbove(sv.ref.W, sv.ref.H)
		ab.AddBelow(sv.f, it.ls)
		h := &Hyp{err: it.err, ab: ab}
		if n%2 == 1 {
			h.x, h.F, h.H = n, it.Fn, it.Hn
		} else {
			h.x, h.F, h.H, h.chars = n-1, it.Fp, it.Hp, []byte{'}'}
		}
		out = append(out, h)
	}
	return out
}

type cand struct {
	err    float64
	cx, cy byte
	F2, H2 uint16
	ls     []Layer
}

func (sv *Solver) step(h *Hyp) []*Hyp {
	a := sv.a
	x := h.x
	opts := a.mid
	if x == sv.n {
		opts = []byte{'}'}
	}
	type job struct {
		key [2]uint16
		ls  []Layer
	}
	var cands []cand
	keyIdx := map[[2]uint16]int{}
	var jobs []job
	for _, cx := range opts {
		F1, ok := a.Tprev[tk{h.F, cx}]
		if !ok {
			continue
		}
		H1 := a.R(F1, h.H)
		for _, cy := range a.mid {
			F2, ok := a.Tprev[tk{F1, cy}]
			if !ok {
				continue
			}
			H2 := a.R(F2, H1)
			key := [2]uint16{H2, H1}
			if _, ok := keyIdx[key]; !ok {
				keyIdx[key] = len(jobs)
				jobs = append(jobs, job{key: key})
			}
			cands = append(cands, cand{cx: cx, cy: cy, F2: F2, H2: H2, err: float64(keyIdx[key])})
		}
	}
	scores := make([]float64, len(jobs))
	var wg sync.WaitGroup
	next := make(chan int, len(jobs))
	for i := range jobs {
		next <- i
	}
	close(next)
	for w := 0; w < runtime.NumCPU(); w++ {
		wg.Add(1)
		go func() {
			defer wg.Done()
			for i := range next {
				ls := sv.pairLayers(a.P(jobs[i].key[0], jobs[i].key[1]), (x-3)/2)
				jobs[i].ls = ls
				scores[i] = FeasScore(sv.f, sv.ref, h.ab, ls, sv.thr)
			}
		}()
	}
	wg.Wait()
	for i := range cands {
		cands[i].err = h.err + scores[int(cands[i].err)]
	}
	sort.Slice(cands, func(i, j int) bool { return cands[i].err < cands[j].err })
	var out []*Hyp
	seen := map[[2]uint16]bool{}
	for _, c := range cands {
		k := [2]uint16{c.F2, c.H2}
		if seen[k] {
			continue
		}
		seen[k] = true
		F1, _ := a.Tprev[tk{h.F, c.cx}]
		H1 := a.R(F1, h.H)
		ab := h.ab.Copy()
		ab.AddBelow(sv.f, jobs[keyIdx[[2]uint16{c.H2, H1}]].ls)
		ch := append(append([]byte(nil), h.chars...), c.cx, c.cy)
		out = append(out, &Hyp{err: c.err, x: x - 2, F: c.F2, H: c.H2, chars: ch, ab: ab})
		if len(out) >= sv.beam {
			break
		}
	}
	return out
}

type Result struct {
	Score float64
	Text  string
}

func (sv *Solver) Run() []Result {
	a := sv.a
	hyps := sv.init()
	sv.log("init: %d гипотез, лучшая оценка %.1f", len(hyps), hyps[0].err)
	n0 := len(sv.prefix)
	for hyps[0].x > n0+2 {
		var all []*Hyp
		for _, h := range hyps {
			all = append(all, sv.step(h)...)
		}
		sort.Slice(all, func(i, j int) bool { return all[i].err < all[j].err })
		if len(all) > sv.beam {
			all = all[:sv.beam]
		}
		hyps = all
		sv.log("x=%2d  best=%8.0f  ...%s", hyps[0].x, hyps[0].err, revStr(hyps[0].chars))
	}
	// замыкание на известный префикс "SOLARCTF{"
	Fpre := a.Fseq(sv.prefix)
	var res []Result
	for _, h := range hyps {
		for _, c11 := range a.mid {
			F10, ok := a.Tprev[tk{h.F, c11}]
			if !ok {
				continue
			}
			c10, ok := a.Tinv[[2]uint16{Fpre[n0], F10}]
			if !ok || !a.isMid[c10] {
				continue
			}
			Hs := make([]uint16, n0+2)
			Hs[n0+1] = a.R(F10, h.H)
			for j := n0; j >= 1; j-- {
				Hs[j] = a.R(Fpre[j], Hs[j+1])
			}
			ab := h.ab.Copy()
			sc := h.err
			for p := n0; p >= 1; p -= 2 {
				ls := sv.pairLayers(a.P(Hs[p], Hs[p+1]), (p-1)/2)
				sc += FeasScore(sv.f, sv.ref, ab, ls, sv.thr)
				ab.AddBelow(sv.f, ls)
			}
			txt := sv.prefix + string([]byte{c10, c11}) + revStr(h.chars)
			res = append(res, Result{sc, txt})
		}
	}
	sort.Slice(res, func(i, j int) bool { return res[i].Score < res[j].Score })
	return res
}

func revStr(b []byte) string {
	var sb strings.Builder
	for i := len(b) - 1; i >= 0; i-- {
		sb.WriteByte(b[i])
	}
	return sb.String()
}

// LastScore — оценка правого края: нужна для подбора длины/масштаба/смещения.
func (sv *Solver) LastScore() float64 {
	b := sv.beam
	sv.beam = 1
	hs := sv.init()
	sv.beam = b
	if len(hs) == 0 {
		return 1e18
	}
	return hs[0].err
}

func (sv *Solver) String() string {
	return fmt.Sprintf("n=%d s=%.4f X0=%.1f Yb=%.1f", sv.n, sv.s, sv.X0, sv.Yb)
}
