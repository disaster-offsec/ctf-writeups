package main

// GSUB (lookup 1, 5/fmt1, 6/fmt2, 8, extension 7) и GPOS (PairPos fmt1, extension 9).
// Семантика применения повторяет HarfBuzz: lookup'ы по возрастанию индекса;
// для контекстных правил позиция после срабатывания перепрыгивает совпавший вход.

import (
	"errors"
	"fmt"
	"sort"
)

type Coverage map[uint16]int
type ClassDef map[uint16]int

func parseCoverage(b []byte, o int) Coverage {
	m := Coverage{}
	n := u16(b, o+2)
	if u16(b, o) == 1 {
		for i := 0; i < n; i++ {
			m[uint16(u16(b, o+4+2*i))] = i
		}
		return m
	}
	for i := 0; i < n; i++ {
		s, e, sc := u16(b, o+4+6*i), u16(b, o+6+6*i), u16(b, o+8+6*i)
		for g := s; g <= e; g++ {
			m[uint16(g)] = sc + g - s
		}
	}
	return m
}

func parseClassDef(b []byte, o int) ClassDef {
	m := ClassDef{}
	if o == 0 {
		return m
	}
	if u16(b, o) == 1 {
		sg, n := u16(b, o+2), u16(b, o+4)
		for i := 0; i < n; i++ {
			m[uint16(sg+i)] = u16(b, o+6+2*i)
		}
		return m
	}
	n := u16(b, o+2)
	for i := 0; i < n; i++ {
		s, e, c := u16(b, o+4+6*i), u16(b, o+6+6*i), u16(b, o+8+6*i)
		for g := s; g <= e; g++ {
			m[uint16(g)] = c
		}
	}
	return m
}

type seqRec struct{ seq, lookup int }
type seqRule struct {
	input []uint16
	recs  []seqRec
}
type chainRule struct {
	bt, in, la []int
	recs       []seqRec
}
type pairVal struct {
	x1, y1, a1, x2, y2, a2 int
	has2                   bool
}

type subtable struct {
	typ       int
	single    map[uint16]uint16
	cov       Coverage
	seqRules  [][]seqRule
	chainSets [][]chainRule
	btCD      ClassDef
	inCD      ClassDef
	laCD      ClassDef
	btCov     []Coverage
	laCov     []Coverage
	subst     []uint16
	pairs     map[[2]uint16]pairVal
}

type lookup struct{ subs []*subtable }

type Layout struct {
	lookups  []*lookup
	features map[string][]int
}

func parseRecs(b []byte, o, n int) []seqRec {
	r := make([]seqRec, n)
	for i := range r {
		r[i] = seqRec{u16(b, o+4*i), u16(b, o+4*i+2)}
	}
	return r
}

func parseSub(b []byte, o, typ int, gsub bool) (*subtable, error) {
	st := &subtable{typ: typ}
	if gsub {
		switch typ {
		case 1:
			st.single = map[uint16]uint16{}
			cov := parseCoverage(b, o+u16(b, o+2))
			if u16(b, o) == 1 {
				d := i16(b, o+4)
				for g := range cov {
					st.single[g] = uint16(int(g) + d)
				}
			} else {
				for g, i := range cov {
					st.single[g] = uint16(u16(b, o+6+2*i))
				}
			}
		case 5:
			if u16(b, o) != 1 {
				return nil, errors.New("GSUB5 format != 1")
			}
			st.cov = parseCoverage(b, o+u16(b, o+2))
			n := u16(b, o+4)
			st.seqRules = make([][]seqRule, n)
			for i := 0; i < n; i++ {
				so := o + u16(b, o+6+2*i)
				rc := u16(b, so)
				for k := 0; k < rc; k++ {
					ro := so + u16(b, so+2+2*k)
					gc, sc := u16(b, ro), u16(b, ro+2)
					in := make([]uint16, gc-1)
					for j := range in {
						in[j] = uint16(u16(b, ro+4+2*j))
					}
					st.seqRules[i] = append(st.seqRules[i], seqRule{in, parseRecs(b, ro+4+2*(gc-1), sc)})
				}
			}
		case 6:
			if u16(b, o) != 2 {
				return nil, errors.New("GSUB6 format != 2")
			}
			st.cov = parseCoverage(b, o+u16(b, o+2))
			opt := func(off int) int {
				if v := u16(b, o+off); v != 0 {
					return o + v
				}
				return 0
			}
			st.btCD = parseClassDef(b, opt(4))
			st.inCD = parseClassDef(b, opt(6))
			st.laCD = parseClassDef(b, opt(8))
			n := u16(b, o+10)
			st.chainSets = make([][]chainRule, n)
			for i := 0; i < n; i++ {
				off := u16(b, o+12+2*i)
				if off == 0 {
					continue
				}
				so := o + off
				rc := u16(b, so)
				for k := 0; k < rc; k++ {
					p := so + u16(b, so+2+2*k)
					var r chainRule
					nb := u16(b, p)
					p += 2
					for j := 0; j < nb; j++ {
						r.bt = append(r.bt, u16(b, p+2*j))
					}
					p += 2 * nb
					ni := u16(b, p)
					p += 2
					for j := 0; j < ni-1; j++ {
						r.in = append(r.in, u16(b, p+2*j))
					}
					p += 2 * (ni - 1)
					nl := u16(b, p)
					p += 2
					for j := 0; j < nl; j++ {
						r.la = append(r.la, u16(b, p+2*j))
					}
					p += 2 * nl
					r.recs = parseRecs(b, p+2, u16(b, p))
					st.chainSets[i] = append(st.chainSets[i], r)
				}
			}
		case 8:
			st.cov = parseCoverage(b, o+u16(b, o+2))
			p := o + 4
			nb := u16(b, p)
			for j := 0; j < nb; j++ {
				st.btCov = append(st.btCov, parseCoverage(b, o+u16(b, p+2+2*j)))
			}
			p += 2 + 2*nb
			nl := u16(b, p)
			for j := 0; j < nl; j++ {
				st.laCov = append(st.laCov, parseCoverage(b, o+u16(b, p+2+2*j)))
			}
			p += 2 + 2*nl
			ng := u16(b, p)
			for j := 0; j < ng; j++ {
				st.subst = append(st.subst, uint16(u16(b, p+2+2*j)))
			}
		default:
			return nil, fmt.Errorf("unsupported GSUB lookup type %d", typ)
		}
		return st, nil
	}
	// GPOS
	if typ != 2 || u16(b, o) != 1 {
		return nil, fmt.Errorf("unsupported GPOS lookup type %d", typ)
	}
	cov := parseCoverage(b, o+u16(b, o+2))
	vf1, vf2 := u16(b, o+4), u16(b, o+6)
	n := u16(b, o+8)
	size := func(vf int) int {
		c := 0
		for ; vf != 0; vf >>= 1 {
			c += vf & 1
		}
		return 2 * c
	}
	readVal := func(p, vf int) (x, y, a int) {
		for bit := 0; bit < 4; bit++ {
			if vf&(1<<bit) == 0 {
				continue
			}
			v := i16(b, p)
			p += 2
			switch bit {
			case 0:
				x = v
			case 1:
				y = v
			case 2:
				a = v
			}
		}
		return
	}
	st.pairs = map[[2]uint16]pairVal{}
	s1, s2 := size(vf1), size(vf2)
	for g, idx := range cov {
		if idx >= n {
			continue
		}
		so := o + u16(b, o+10+2*idx)
		pc := u16(b, so)
		p := so + 2
		for k := 0; k < pc; k++ {
			sg := uint16(u16(b, p))
			var pv pairVal
			pv.x1, pv.y1, pv.a1 = readVal(p+2, vf1)
			pv.x2, pv.y2, pv.a2 = readVal(p+2+s1, vf2)
			pv.has2 = vf2 != 0
			st.pairs[[2]uint16{g, sg}] = pv
			p += 2 + s1 + s2
		}
	}
	return st, nil
}

func parseLayout(b []byte, gsub bool) (*Layout, error) {
	l := &Layout{features: map[string][]int{}}
	fl := u16(b, 6)
	ll := u16(b, 8)
	nf := u16(b, fl)
	for i := 0; i < nf; i++ {
		tag := string(b[fl+2+6*i : fl+6+6*i])
		fo := fl + u16(b, fl+6+6*i)
		nl := u16(b, fo+2)
		for k := 0; k < nl; k++ {
			l.features[tag] = append(l.features[tag], u16(b, fo+4+2*k))
		}
	}
	nl := u16(b, ll)
	extType := 7
	if !gsub {
		extType = 9
	}
	for i := 0; i < nl; i++ {
		lo := ll + u16(b, ll+2+2*i)
		typ, sc := u16(b, lo), u16(b, lo+4)
		lk := &lookup{}
		for k := 0; k < sc; k++ {
			so := lo + u16(b, lo+6+2*k)
			t := typ
			if typ == extType {
				t = u16(b, so+2)
				so += u32(b, so+4)
			}
			st, err := parseSub(b, so, t, gsub)
			if err != nil {
				return nil, fmt.Errorf("lookup %d: %w", i, err)
			}
			lk.subs = append(lk.subs, st)
		}
		l.lookups = append(l.lookups, lk)
	}
	return l, nil
}

// FeatureLookups: объединённые, отсортированные индексы lookup'ов фич.
func (l *Layout) FeatureLookups(tags ...string) []int {
	set := map[int]bool{}
	for _, t := range tags {
		for _, i := range l.features[t] {
			set[i] = true
		}
	}
	var out []int
	for i := range set {
		out = append(out, i)
	}
	sort.Ints(out)
	return out
}

// ---- применение GSUB ----

func (l *Layout) applyAt(buf []uint16, li, pos int) bool {
	for _, st := range l.lookups[li].subs {
		if l.trySub(buf, st, pos) > 0 {
			return true
		}
	}
	return false
}

// возвращает длину совпавшего входа (0 — нет совпадения)
func (l *Layout) trySub(buf []uint16, st *subtable, pos int) int {
	g := buf[pos]
	switch st.typ {
	case 1:
		if v, ok := st.single[g]; ok {
			buf[pos] = v
			return 1
		}
	case 5:
		ci, ok := st.cov[g]
		if !ok || ci >= len(st.seqRules) {
			return 0
		}
	rules5:
		for _, r := range st.seqRules[ci] {
			n := len(r.input) + 1
			if pos+n > len(buf) {
				continue
			}
			for j, gi := range r.input {
				if buf[pos+1+j] != gi {
					continue rules5
				}
			}
			for _, rec := range r.recs {
				l.applyAt(buf, rec.lookup, pos+rec.seq)
			}
			return n
		}
	case 6:
		if _, ok := st.cov[g]; !ok {
			return 0
		}
		c := st.inCD[g]
		if c >= len(st.chainSets) {
			return 0
		}
	rules6:
		for _, r := range st.chainSets[c] {
			nb, ni, nl := len(r.bt), len(r.in), len(r.la)
			if pos-nb < 0 || pos+1+ni+nl > len(buf) {
				continue
			}
			for j := 0; j < nb; j++ {
				if st.btCD[buf[pos-1-j]] != r.bt[j] {
					continue rules6
				}
			}
			for j := 0; j < ni; j++ {
				if st.inCD[buf[pos+1+j]] != r.in[j] {
					continue rules6
				}
			}
			for j := 0; j < nl; j++ {
				if st.laCD[buf[pos+1+ni+j]] != r.la[j] {
					continue rules6
				}
			}
			for _, rec := range r.recs {
				l.applyAt(buf, rec.lookup, pos+rec.seq)
			}
			return 1 + ni
		}
	case 8:
		ci, ok := st.cov[g]
		if !ok {
			return 0
		}
		nb, nl := len(st.btCov), len(st.laCov)
		if pos-nb < 0 || pos+1+nl > len(buf) {
			return 0
		}
		for j := 0; j < nb; j++ {
			if _, ok := st.btCov[j][buf[pos-1-j]]; !ok {
				return 0
			}
		}
		for j := 0; j < nl; j++ {
			if _, ok := st.laCov[j][buf[pos+1+j]]; !ok {
				return 0
			}
		}
		buf[pos] = st.subst[ci]
		return 1
	}
	return 0
}

func (l *Layout) runLookup(buf []uint16, li int) {
	lk := l.lookups[li]
	if len(lk.subs) > 0 && lk.subs[0].typ == 8 { // обратный проход
		for pos := len(buf) - 1; pos >= 0; pos-- {
			for _, st := range lk.subs {
				if l.trySub(buf, st, pos) > 0 {
					break
				}
			}
		}
		return
	}
	for pos := 0; pos < len(buf); {
		adv := 0
		for _, st := range lk.subs {
			if adv = l.trySub(buf, st, pos); adv > 0 {
				break
			}
		}
		if adv == 0 {
			adv = 1
		}
		pos += adv
	}
}

// ---- GPOS: раскладка ----

type Placed struct {
	G    uint16
	X, Y float64 // единицы шрифта: позиция пера + смещение
}

func (f *Font) Layout(gl []uint16) ([]Placed, float64) {
	n := len(gl)
	adv := make([]int, n)
	xo := make([]int, n)
	yo := make([]int, n)
	for i, g := range gl {
		adv[i] = f.Advance(g)
	}
	for _, li := range f.GPOS.FeatureLookups("kern") {
		lk := f.GPOS.lookups[li]
		for i := 0; i < n-1; {
			var hit *pairVal
			for _, st := range lk.subs {
				if v, ok := st.pairs[[2]uint16{gl[i], gl[i+1]}]; ok {
					v := v
					hit = &v
					break
				}
			}
			if hit == nil {
				i++
				continue
			}
			xo[i] += hit.x1
			yo[i] += hit.y1
			adv[i] += hit.a1
			xo[i+1] += hit.x2
			yo[i+1] += hit.y2
			adv[i+1] += hit.a2
			if hit.has2 {
				i += 2
			} else {
				i++
			}
		}
	}
	out := make([]Placed, n)
	x := 0
	for i := range gl {
		out[i] = Placed{gl[i], float64(x + xo[i]), float64(yo[i])}
		x += adv[i]
	}
	return out, float64(x)
}

// PairGeom: смещения GPOS для пары (нужны декодеру).
func (f *Font) PairGeom(a, b uint16) (pairVal, bool) {
	for _, li := range f.GPOS.FeatureLookups("kern") {
		for _, st := range f.GPOS.lookups[li].subs {
			if v, ok := st.pairs[[2]uint16{a, b}]; ok {
				return v, true
			}
		}
	}
	return pairVal{}, false
}

// Shape: полный прогон calt+ss01 по строке "[text]".
func (f *Font) Shape(text string) []uint16 {
	buf := []uint16{f.cmap['[']}
	for _, c := range text {
		buf = append(buf, f.cmap[c])
	}
	buf = append(buf, f.cmap[']'])
	for _, li := range f.GSUB.FeatureLookups("calt", "ss01") {
		f.GSUB.runLookup(buf, li)
	}
	return buf
}
