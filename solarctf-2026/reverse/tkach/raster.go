package main

// Растеризация слоёв глифов (правило nonzero, AA: 4 подстроки по вертикали,
// точное покрытие по горизонтали), композиция полупрозрачных слоёв и оценка
// «допустимости» кандидата под уже известными глифами.

import (
	"math"
	"sort"
	"sync"
)

const ssy = 4

type Cov struct {
	w, h   int
	lx, ly int // смещение bbox относительно целого пикселя начала координат
	a      []uint8
}

type covKey struct {
	g      uint16
	s      float64
	fx, fy uint8
}

type Rast struct {
	f  *Font
	mu sync.RWMutex
	m  map[covKey]*Cov
}

func NewRast(f *Font) *Rast { return &Rast{f: f, m: map[covKey]*Cov{}} }

// Layer: покрытие + положение (левый верхний пиксель) + индекс цвета палитры.
type Layer struct {
	c      *Cov
	px, py int
	pal    int
}

// LayerCov возвращает растр слоя-глифа g при масштабе s (px/ед.) и начале координат (ox,oy) в пикселях.
func (r *Rast) LayerCov(g uint16, s, ox, oy float64) (*Cov, int, int) {
	ix, iy := floorInt(ox), floorInt(oy)
	qx, qy := int(math.Round((ox-float64(ix))*8)), int(math.Round((oy-float64(iy))*8))
	if qx == 8 {
		qx, ix = 0, ix+1
	}
	if qy == 8 {
		qy, iy = 0, iy+1
	}
	k := covKey{g, s, uint8(qx), uint8(qy)}
	r.mu.RLock()
	c := r.m[k]
	r.mu.RUnlock()
	if c == nil {
		c = r.render(g, s, float64(qx)/8, float64(qy)/8)
		r.mu.Lock()
		r.m[k] = c
		r.mu.Unlock()
	}
	return c, ix + c.lx, iy + c.ly
}

type edge struct{ x0, y0, x1, y1 float64 }

func (r *Rast) render(g uint16, s, fx, fy float64) *Cov {
	cs := r.f.Outline(g)
	var edges []edge
	minX, minY, maxX, maxY := math.Inf(1), math.Inf(1), math.Inf(-1), math.Inf(-1)
	for _, c := range cs {
		for i := range c {
			p, q := c[i], c[(i+1)%len(c)]
			x0, y0 := fx+p.X*s, fy-p.Y*s
			x1, y1 := fx+q.X*s, fy-q.Y*s
			minX, maxX = math.Min(minX, x0), math.Max(maxX, x0)
			minY, maxY = math.Min(minY, y0), math.Max(maxY, y0)
			if y0 != y1 {
				edges = append(edges, edge{x0, y0, x1, y1})
			}
		}
	}
	if len(edges) == 0 {
		return &Cov{}
	}
	lx, ly := floorInt(minX)-1, floorInt(minY)-1
	w, h := ceilInt(maxX)+1-lx, ceilInt(maxY)+1-ly
	nrow := h * ssy
	// сортировка пересечений по подстрокам (counting sort)
	type cross struct {
		x   float64
		dir int8
	}
	cnt := make([]int, nrow+1)
	span := func(e edge) (int, int, bool) {
		ymin, ymax := e.y0, e.y1
		if ymin > ymax {
			ymin, ymax = ymax, ymin
		}
		k0 := ceilInt((ymin-float64(ly))*ssy - 0.5)
		k1 := ceilInt((ymax-float64(ly))*ssy-0.5) - 1
		if k0 < 0 {
			k0 = 0
		}
		if k1 > nrow-1 {
			k1 = nrow - 1
		}
		return k0, k1, k0 <= k1
	}
	for _, e := range edges {
		if k0, k1, ok := span(e); ok {
			for k := k0; k <= k1; k++ {
				cnt[k+1]++
			}
		}
	}
	for k := 0; k < nrow; k++ {
		cnt[k+1] += cnt[k]
	}
	xs := make([]cross, cnt[nrow])
	pos := make([]int, nrow)
	copy(pos, cnt[:nrow])
	for _, e := range edges {
		k0, k1, ok := span(e)
		if !ok {
			continue
		}
		var dir int8 = 1
		if e.y1 < e.y0 {
			dir = -1
		}
		inv := (e.x1 - e.x0) / (e.y1 - e.y0)
		for k := k0; k <= k1; k++ {
			yc := float64(ly) + (float64(k)+0.5)/ssy
			xs[pos[k]] = cross{e.x0 + (yc-e.y0)*inv - float64(lx), dir}
			pos[k]++
		}
	}
	acc := make([]float32, w*h)
	for k := 0; k < nrow; k++ {
		row := xs[cnt[k]:cnt[k+1]]
		sort.Slice(row, func(i, j int) bool { return row[i].x < row[j].x })
		base := (k / ssy) * w
		wind := 0
		for i := 0; i+1 < len(row); i++ {
			wind += int(row[i].dir)
			if wind == 0 {
				continue
			}
			xa, xb := row[i].x, row[i+1].x
			if xa < 0 {
				xa = 0
			}
			if xb > float64(w) {
				xb = float64(w)
			}
			if xb <= xa {
				continue
			}
			ia, ib := int(xa), int(xb)
			if ia == ib {
				acc[base+ia] += float32(xb - xa)
				continue
			}
			acc[base+ia] += float32(float64(ia+1) - xa)
			for x := ia + 1; x < ib; x++ {
				acc[base+x]++
			}
			if ib < w {
				acc[base+ib] += float32(xb - float64(ib))
			}
		}
	}
	c := &Cov{w: w, h: h, lx: lx, ly: ly, a: make([]uint8, w*h)}
	for i, v := range acc {
		v /= ssy
		if v > 1 {
			v = 1
		}
		c.a[i] = uint8(v*255 + 0.5)
	}
	return c
}

// ---------------- изображения и композиция ----------------

type Img struct {
	W, H int
	Pix  []float32 // RGB
}

// Above хранит преобразование «что лежит поверх»: итог = M*под + B.
type Above struct {
	W, H int
	M    []float32
	B    []float32
}

func NewAbove(w, h int) *Above {
	a := &Above{W: w, H: h, M: make([]float32, w*h), B: make([]float32, w*h*3)}
	for i := range a.M {
		a.M[i] = 1
	}
	return a
}
func (a *Above) Copy() *Above {
	b := &Above{W: a.W, H: a.H, M: append([]float32(nil), a.M...), B: append([]float32(nil), a.B...)}
	return b
}

func bbox(ls []Layer, W, H int) (x0, y0, x1, y1 int, ok bool) {
	x0, y0, x1, y1 = W, H, 0, 0
	for _, l := range ls {
		if l.c.w == 0 {
			continue
		}
		x0, y0 = min(x0, max(l.px, 0)), min(y0, max(l.py, 0))
		x1, y1 = max(x1, min(l.px+l.c.w, W)), max(y1, min(l.py+l.c.h, H))
	}
	return x0, y0, x1, y1, x1 > x0 && y1 > y0
}

// AddBelow: слои кладутся ПОД уже известные (порядок слоёв = порядок рисования).
func (a *Above) AddBelow(f *Font, ls []Layer) {
	x0, y0, x1, y1, ok := bbox(ls, a.W, a.H)
	if !ok {
		return
	}
	w, h := x1-x0, y1-y0
	Mc := make([]float32, w*h)
	Bc := make([]float32, w*h*3)
	for i := range Mc {
		Mc[i] = 1
	}
	compose(f, ls, x0, y0, w, h, Mc, Bc, nil)
	for y := 0; y < h; y++ {
		for x := 0; x < w; x++ {
			i := (y+y0)*a.W + x + x0
			j := y*w + x
			m := a.M[i]
			for c := 0; c < 3; c++ {
				a.B[i*3+c] += m * Bc[j*3+c]
			}
			a.M[i] = m * Mc[j]
		}
	}
}

// compose накладывает слои в ROI (x0,y0,w,h): Mc *= (1-a), Bc = Bc*(1-a)+a*цвет.
func compose(f *Font, ls []Layer, x0, y0, w, h int, Mc, Bc, any []float32) {
	for _, l := range ls {
		if l.c.w == 0 {
			continue
		}
		p := f.Pal[l.pal]
		ax0, ay0 := max(l.px, x0), max(l.py, y0)
		ax1, ay1 := min(l.px+l.c.w, x0+w), min(l.py+l.c.h, y0+h)
		for y := ay0; y < ay1; y++ {
			cr := l.c.a[(y-l.py)*l.c.w:]
			for x := ax0; x < ax1; x++ {
				cv := cr[x-l.px]
				if cv == 0 {
					continue
				}
				c := float32(cv) / 255
				al := c * p.A
				j := (y-y0)*w + (x - x0)
				Mc[j] *= 1 - al
				Bc[j*3] = Bc[j*3]*(1-al) + al*p.R
				Bc[j*3+1] = Bc[j*3+1]*(1-al) + al*p.G
				Bc[j*3+2] = Bc[j*3+2]*(1-al) + al*p.B
				if any != nil && c > any[j] {
					any[j] = c
				}
			}
		}
	}
}

type scratch struct{ Mc, Bc, any []float32 }

var scratchPool = sync.Pool{New: func() any { return &scratch{} }}

func grow(s []float32, n int) []float32 {
	if cap(s) < n {
		return make([]float32, n)
	}
	return s[:n]
}

// FeasScore: суммарное нарушение допустимости кандидата, лежащего под `ab`.
// Для правильного кандидата «цвет под ним» (ref-B)/M обязан лежать в [0,255].
func FeasScore(f *Font, ref *Img, ab *Above, ls []Layer, thr float32) float64 {
	x0, y0, x1, y1, ok := bbox(ls, ref.W, ref.H)
	if !ok {
		return 0
	}
	w, h := x1-x0, y1-y0
	sc := scratchPool.Get().(*scratch)
	defer scratchPool.Put(sc)
	sc.Mc, sc.Bc, sc.any = grow(sc.Mc, w*h), grow(sc.Bc, w*h*3), grow(sc.any, w*h)
	for i := range sc.Mc {
		sc.Mc[i] = 1
		sc.any[i] = 0
	}
	for i := range sc.Bc {
		sc.Bc[i] = 0
	}
	compose(f, ls, x0, y0, w, h, sc.Mc, sc.Bc, sc.any)
	var total float64
	for y := 0; y < h; y++ {
		for x := 0; x < w; x++ {
			j := y*w + x
			if sc.any[j] <= 0.5 {
				continue
			}
			i := (y+y0)*ref.W + x + x0
			m := ab.M[i]
			if m <= thr {
				continue
			}
			den := m * sc.Mc[j]
			for c := 0; c < 3; c++ {
				num := ref.Pix[i*3+c] - ab.B[i*3+c] - m*sc.Bc[j*3+c]
				v := float32(0)
				if -num > v {
					v = -num
				}
				if num-255*den > v {
					v = num - 255*den
				}
				total += float64(v)
			}
		}
	}
	return total / 1000
}

// Render рисует готовую последовательность глифов на белом фоне (для проверки).
func Render(f *Font, r *Rast, gl []uint16, s, X0, Yb float64, W, H int) *Img {
	Mc := make([]float32, W*H)
	Bc := make([]float32, W*H*3)
	for i := range Mc {
		Mc[i] = 1
	}
	pl, _ := f.Layout(gl)
	for _, p := range pl {
		compose(f, f.glyphLayers(r, p.G, s, X0+p.X*s, Yb-p.Y*s), 0, 0, W, H, Mc, Bc, nil)
	}
	im := &Img{W: W, H: H, Pix: make([]float32, W*H*3)}
	for i := range Mc {
		for c := 0; c < 3; c++ {
			im.Pix[i*3+c] = Mc[i]*255 + Bc[i*3+c]
		}
	}
	return im
}

func (f *Font) glyphLayers(r *Rast, g uint16, s, ox, oy float64) []Layer {
	var out []Layer
	for _, cl := range f.Layers(g) {
		c, px, py := r.LayerCov(cl.Glyph, s, ox, oy)
		out = append(out, Layer{c, px, py, cl.Palette})
	}
	return out
}
