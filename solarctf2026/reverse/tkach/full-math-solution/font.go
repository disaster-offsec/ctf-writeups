package main

// Минимальный парсер OpenType/CFF: cmap(4), hmtx, CFF (Type 2 charstrings),
// COLR v0, CPAL. Только stdlib.

import (
	"encoding/binary"
	"errors"
	"fmt"
	"math"
	"os"
	"sync"
)

var be = binary.BigEndian

func u16(b []byte, o int) int { return int(be.Uint16(b[o:])) }
func i16(b []byte, o int) int { return int(int16(be.Uint16(b[o:]))) }
func u32(b []byte, o int) int { return int(be.Uint32(b[o:])) }

type Pt struct{ X, Y float64 }

type RGBA struct {
	R, G, B float32
	A       float32
}

type ColorLayer struct {
	Glyph   uint16
	Palette int
}

type Font struct {
	tables    map[string][]byte
	NumGlyphs int
	advance   []int
	cmap      map[rune]uint16
	cs        cffIndex
	gsubrs    cffIndex
	lsubrs    cffIndex
	outCache  map[uint16][][]Pt
	outMu     sync.Mutex
	colr      map[uint16][]ColorLayer
	Pal       []RGBA
	GSUB      *Layout
	GPOS      *Layout
}

func LoadFont(path string) (*Font, error) {
	data, err := os.ReadFile(path)
	if err != nil {
		return nil, err
	}
	if len(data) < 12 {
		return nil, errors.New("short font")
	}
	f := &Font{tables: map[string][]byte{}, outCache: map[uint16][][]Pt{}}
	n := u16(data, 4)
	for i := 0; i < n; i++ {
		r := 12 + 16*i
		tag := string(data[r : r+4])
		off, ln := u32(data, r+8), u32(data, r+12)
		f.tables[tag] = data[off : off+ln]
	}
	for _, t := range []string{"maxp", "hhea", "hmtx", "cmap", "CFF ", "COLR", "CPAL", "GSUB", "GPOS"} {
		if f.tables[t] == nil {
			return nil, fmt.Errorf("table %s missing", t)
		}
	}
	f.NumGlyphs = u16(f.tables["maxp"], 4)
	// hmtx
	nh := u16(f.tables["hhea"], 34)
	hm := f.tables["hmtx"]
	f.advance = make([]int, f.NumGlyphs)
	last := 0
	for g := 0; g < f.NumGlyphs; g++ {
		if g < nh {
			last = u16(hm, 4*g)
		}
		f.advance[g] = last
	}
	if f.cmap, err = parseCmap(f.tables["cmap"]); err != nil {
		return nil, err
	}
	if err = f.parseCFF(f.tables["CFF "]); err != nil {
		return nil, err
	}
	f.parseCOLR()
	f.parseCPAL()
	if f.GSUB, err = parseLayout(f.tables["GSUB"], true); err != nil {
		return nil, fmt.Errorf("GSUB: %w", err)
	}
	if f.GPOS, err = parseLayout(f.tables["GPOS"], false); err != nil {
		return nil, fmt.Errorf("GPOS: %w", err)
	}
	return f, nil
}

func parseCmap(b []byte) (map[rune]uint16, error) {
	n := u16(b, 2)
	off := -1
	for i := 0; i < n; i++ {
		p, e, o := u16(b, 4+8*i), u16(b, 6+8*i), u32(b, 8+8*i)
		if ((p == 3 && e == 1) || p == 0) && u16(b, o) == 4 {
			off = o
			break
		}
	}
	if off < 0 {
		return nil, errors.New("cmap format 4 not found")
	}
	segX2 := u16(b, off+6)
	seg := segX2 / 2
	endO := off + 14
	startO := endO + segX2 + 2
	deltaO := startO + segX2
	rangeO := deltaO + segX2
	m := map[rune]uint16{}
	for i := 0; i < seg; i++ {
		end, start := u16(b, endO+2*i), u16(b, startO+2*i)
		delta, ro := i16(b, deltaO+2*i), u16(b, rangeO+2*i)
		for c := start; c <= end && c != 0xFFFF; c++ {
			var g int
			if ro == 0 {
				g = (c + delta) & 0xFFFF
			} else {
				g = u16(b, rangeO+2*i+ro+2*(c-start))
				if g != 0 {
					g = (g + delta) & 0xFFFF
				}
			}
			if g != 0 {
				m[rune(c)] = uint16(g)
			}
		}
	}
	return m, nil
}

func (f *Font) parseCOLR() {
	b := f.tables["COLR"]
	nb := u16(b, 2)
	bo := u32(b, 4)
	lo := u32(b, 8)
	f.colr = map[uint16][]ColorLayer{}
	for i := 0; i < nb; i++ {
		r := bo + 6*i
		g := uint16(u16(b, r))
		first, num := u16(b, r+2), u16(b, r+4)
		var ls []ColorLayer
		for k := 0; k < num; k++ {
			lr := lo + 4*(first+k)
			ls = append(ls, ColorLayer{uint16(u16(b, lr)), u16(b, lr+2)})
		}
		f.colr[g] = ls
	}
}

func (f *Font) parseCPAL() {
	b := f.tables["CPAL"]
	ne := u16(b, 2)
	arr := u32(b, 8)
	first := u16(b, 12)
	for i := 0; i < ne; i++ {
		o := arr + 4*(first+i)
		f.Pal = append(f.Pal, RGBA{float32(b[o+2]), float32(b[o+1]), float32(b[o]), float32(b[o+3]) / 255})
	}
}

func (f *Font) Layers(g uint16) []ColorLayer { return f.colr[g] }
func (f *Font) Advance(g uint16) int         { return f.advance[g] }

// ---------------- CFF ----------------

type cffIndex [][]byte

func readIndex(b []byte, pos int) (cffIndex, int) {
	cnt := u16(b, pos)
	if cnt == 0 {
		return nil, pos + 2
	}
	osz := int(b[pos+2])
	ob := pos + 3
	off := func(i int) int {
		v := 0
		for k := 0; k < osz; k++ {
			v = v<<8 | int(b[ob+i*osz+k])
		}
		return v
	}
	db := ob + (cnt+1)*osz - 1
	it := make(cffIndex, cnt)
	for i := 0; i < cnt; i++ {
		it[i] = b[db+off(i) : db+off(i+1)]
	}
	return it, db + off(cnt)
}

func parseDict(b []byte) map[int][]float64 {
	d := map[int][]float64{}
	var st []float64
	for i := 0; i < len(b); {
		b0 := int(b[i])
		i++
		switch {
		case b0 <= 21:
			op := b0
			if b0 == 12 {
				op = 1200 + int(b[i])
				i++
			}
			d[op] = st
			st = nil
		case b0 == 28:
			st = append(st, float64(i16(b, i)))
			i += 2
		case b0 == 29:
			st = append(st, float64(int32(be.Uint32(b[i:]))))
			i += 4
		case b0 == 30:
			for i < len(b) {
				x := b[i]
				i++
				if x&0xf == 0xf || x>>4 == 0xf {
					break
				}
			}
			st = append(st, 0)
		case b0 >= 32 && b0 <= 246:
			st = append(st, float64(b0-139))
		case b0 >= 247 && b0 <= 250:
			st = append(st, float64((b0-247)*256+int(b[i])+108))
			i++
		case b0 >= 251 && b0 <= 254:
			st = append(st, float64(-(b0-251)*256-int(b[i])-108))
			i++
		}
	}
	return d
}

func (f *Font) parseCFF(b []byte) error {
	pos := int(b[2])
	_, pos = readIndex(b, pos)
	top, pos := readIndex(b, pos)
	_, pos = readIndex(b, pos)
	f.gsubrs, _ = readIndex(b, pos)
	td := parseDict(top[0])
	cso, ok := td[17]
	if !ok {
		return errors.New("no CharStrings")
	}
	f.cs, _ = readIndex(b, int(cso[0]))
	if pv, ok := td[18]; ok && len(pv) == 2 {
		psz, poff := int(pv[0]), int(pv[1])
		pd := parseDict(b[poff : poff+psz])
		if so, ok := pd[19]; ok {
			f.lsubrs, _ = readIndex(b, poff+int(so[0]))
		}
	}
	return nil
}

// Outline: контуры в единицах шрифта (y вверх), кривые уже распрямлены в ломаные.
func (f *Font) Outline(g uint16) [][]Pt {
	f.outMu.Lock()
	defer f.outMu.Unlock()
	if c, ok := f.outCache[g]; ok {
		return c
	}
	st := &csState{f: f}
	err := st.run(f.cs[g], 0)
	if err != nil && err != errEnd {
		panic(fmt.Sprintf("charstring gid %d: %v", g, err))
	}
	st.closeContour()
	f.outCache[g] = st.out
	return st.out
}

var errEnd = errors.New("endchar")

type csState struct {
	f         *Font
	stack     []float64
	x, y      float64
	cur       []Pt
	out       [][]Pt
	nStems    int
	haveWidth bool
}

func (s *csState) closeContour() {
	if len(s.cur) > 2 {
		s.out = append(s.out, s.cur)
	}
	s.cur = nil
}
func (s *csState) moveTo(dx, dy float64) {
	s.closeContour()
	s.x += dx
	s.y += dy
	s.cur = []Pt{{s.x, s.y}}
}
func (s *csState) lineTo(dx, dy float64) {
	s.x += dx
	s.y += dy
	s.cur = append(s.cur, Pt{s.x, s.y})
}
func (s *csState) curve(d [6]float64) {
	p0 := Pt{s.x, s.y}
	p1 := Pt{p0.X + d[0], p0.Y + d[1]}
	p2 := Pt{p1.X + d[2], p1.Y + d[3]}
	p3 := Pt{p2.X + d[4], p2.Y + d[5]}
	const N = 12
	for i := 1; i <= N; i++ {
		t := float64(i) / N
		m := 1 - t
		s.cur = append(s.cur, Pt{
			m*m*m*p0.X + 3*m*m*t*p1.X + 3*m*t*t*p2.X + t*t*t*p3.X,
			m*m*m*p0.Y + 3*m*m*t*p1.Y + 3*m*t*t*p2.Y + t*t*t*p3.Y})
	}
	s.x, s.y = p3.X, p3.Y
}

func (s *csState) dropWidth(want int) {
	if !s.haveWidth && len(s.stack) > want {
		s.stack = s.stack[1:]
	}
	s.haveWidth = true
}

func bias(n int) int {
	if n < 1240 {
		return 107
	}
	if n < 33900 {
		return 1131
	}
	return 32768
}

func (s *csState) run(code []byte, depth int) error {
	if depth > 10 {
		return errors.New("subr depth")
	}
	for i := 0; i < len(code); {
		b0 := int(code[i])
		i++
		switch {
		case b0 >= 32 && b0 <= 246:
			s.stack = append(s.stack, float64(b0-139))
			continue
		case b0 >= 247 && b0 <= 250:
			s.stack = append(s.stack, float64((b0-247)*256+int(code[i])+108))
			i++
			continue
		case b0 >= 251 && b0 <= 254:
			s.stack = append(s.stack, float64(-(b0-251)*256-int(code[i])-108))
			i++
			continue
		case b0 == 28:
			s.stack = append(s.stack, float64(i16(code, i)))
			i += 2
			continue
		case b0 == 255:
			s.stack = append(s.stack, float64(int32(be.Uint32(code[i:])))/65536)
			i += 4
			continue
		}
		a := s.stack
		switch b0 {
		case 1, 3, 18, 23: // stems
			if len(a)%2 == 1 && !s.haveWidth {
				a = a[1:]
			}
			s.haveWidth = true
			s.nStems += len(a) / 2
			s.stack = s.stack[:0]
		case 19, 20: // hintmask / cntrmask
			if len(a)%2 == 1 && !s.haveWidth {
				a = a[1:]
			}
			s.haveWidth = true
			s.nStems += len(a) / 2
			s.stack = s.stack[:0]
			i += (s.nStems + 7) / 8
		case 21:
			s.dropWidth(2)
			a = s.stack
			s.moveTo(a[0], a[1])
			s.stack = s.stack[:0]
		case 22:
			s.dropWidth(1)
			s.moveTo(s.stack[0], 0)
			s.stack = s.stack[:0]
		case 4:
			s.dropWidth(1)
			s.moveTo(0, s.stack[0])
			s.stack = s.stack[:0]
		case 5:
			for k := 0; k+1 < len(a); k += 2 {
				s.lineTo(a[k], a[k+1])
			}
			s.stack = s.stack[:0]
		case 6, 7:
			h := b0 == 6
			for k := 0; k < len(a); k++ {
				if h {
					s.lineTo(a[k], 0)
				} else {
					s.lineTo(0, a[k])
				}
				h = !h
			}
			s.stack = s.stack[:0]
		case 8:
			for k := 0; k+5 < len(a); k += 6 {
				s.curve([6]float64{a[k], a[k+1], a[k+2], a[k+3], a[k+4], a[k+5]})
			}
			s.stack = s.stack[:0]
		case 24: // rcurveline
			k := 0
			for ; k+6 <= len(a)-2; k += 6 {
				s.curve([6]float64{a[k], a[k+1], a[k+2], a[k+3], a[k+4], a[k+5]})
			}
			s.lineTo(a[k], a[k+1])
			s.stack = s.stack[:0]
		case 25: // rlinecurve
			k := 0
			for ; k+2 <= len(a)-6; k += 2 {
				s.lineTo(a[k], a[k+1])
			}
			s.curve([6]float64{a[k], a[k+1], a[k+2], a[k+3], a[k+4], a[k+5]})
			s.stack = s.stack[:0]
		case 26: // vvcurveto
			k := 0
			dx1 := 0.0
			if len(a)%2 == 1 {
				dx1 = a[0]
				k = 1
			}
			for ; k+4 <= len(a); k += 4 {
				s.curve([6]float64{dx1, a[k], a[k+1], a[k+2], 0, a[k+3]})
				dx1 = 0
			}
			s.stack = s.stack[:0]
		case 27: // hhcurveto
			k := 0
			dy1 := 0.0
			if len(a)%2 == 1 {
				dy1 = a[0]
				k = 1
			}
			for ; k+4 <= len(a); k += 4 {
				s.curve([6]float64{a[k], dy1, a[k+1], a[k+2], a[k+3], 0})
				dy1 = 0
			}
			s.stack = s.stack[:0]
		case 30, 31: // vhcurveto / hvcurveto
			horiz := b0 == 31
			for k := 0; k+4 <= len(a); k += 4 {
				last := len(a)-k == 5
				if horiz {
					dx3 := 0.0
					if last {
						dx3 = a[k+4]
					}
					s.curve([6]float64{a[k], 0, a[k+1], a[k+2], dx3, a[k+3]})
				} else {
					dy3 := 0.0
					if last {
						dy3 = a[k+4]
					}
					s.curve([6]float64{0, a[k], a[k+1], a[k+2], a[k+3], dy3})
				}
				horiz = !horiz
			}
			s.stack = s.stack[:0]
		case 10, 29: // callsubr / callgsubr
			subrs := s.f.lsubrs
			if b0 == 29 {
				subrs = s.f.gsubrs
			}
			n := int(s.stack[len(s.stack)-1])
			s.stack = s.stack[:len(s.stack)-1]
			idx := n + bias(len(subrs))
			if idx < 0 || idx >= len(subrs) {
				return errors.New("bad subr")
			}
			if err := s.run(subrs[idx], depth+1); err != nil {
				return err
			}
		case 11:
			return nil
		case 14:
			s.closeContour()
			return errEnd
		default:
			return fmt.Errorf("unsupported charstring op %d", b0)
		}
	}
	return nil
}

func floorInt(x float64) int { return int(math.Floor(x)) }
func ceilInt(x float64) int  { return int(math.Ceil(x)) }
