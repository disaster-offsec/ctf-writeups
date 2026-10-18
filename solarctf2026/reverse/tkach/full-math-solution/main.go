package main

// weaver — PoC решения таска «Ткач» (SolarCTF, reverse): восстановление флага по картинке,
// нарисованной шрифтом-автоматом. Только stdlib.
//
//   go run . -font glyphs.otf -img glyphs.png            # автоподбор геометрии + декодирование
//   go run . -font glyphs.otf -selftest 'SOLARCTF{abc_DEF_ghi_012345}'   # проверка на собственном рендере

import (
	"flag"
	"fmt"
	"image"
	"image/color"
	"image/png"
	"math"
	"os"
	"strconv"
	"strings"
	"time"
)

func loadImg(path string) (*image.RGBA, error) {
	fh, err := os.Open(path)
	if err != nil {
		return nil, err
	}
	defer fh.Close()
	im, err := png.Decode(fh)
	if err != nil {
		return nil, err
	}
	b := im.Bounds()
	out := image.NewRGBA(image.Rect(0, 0, b.Dx(), b.Dy()))
	for y := 0; y < b.Dy(); y++ {
		for x := 0; x < b.Dx(); x++ {
			out.Set(x, y, im.At(b.Min.X+x, b.Min.Y+y))
		}
	}
	return out, nil
}

func savePNG(path string, im *Img) error {
	out := image.NewRGBA(image.Rect(0, 0, im.W, im.H))
	cl := func(v float32) uint8 { return uint8(math.Max(0, math.Min(255, float64(v)+0.5))) }
	for y := 0; y < im.H; y++ {
		for x := 0; x < im.W; x++ {
			i := (y*im.W + x) * 3
			out.Set(x, y, color.RGBA{cl(im.Pix[i]), cl(im.Pix[i+1]), cl(im.Pix[i+2]), 255})
		}
	}
	fh, err := os.Create(path)
	if err != nil {
		return err
	}
	defer fh.Close()
	return png.Encode(fh, out)
}

// Находит рамку блока превью (цвет #eee) и вырезает её внутренность.
func cropPreview(im *image.RGBA, box string) (*Img, float64, int, int) {
	W, H := im.Bounds().Dx(), im.Bounds().Dy()
	var x0, y0, x1, y1 int // границы-рамки (включительно)
	if box != "" {
		p := strings.Split(box, ",")
		x0, _ = strconv.Atoi(p[0])
		y0, _ = strconv.Atoi(p[1])
		x1, _ = strconv.Atoi(p[2])
		y1, _ = strconv.Atoi(p[3])
	} else {
		col := make([]int, W)
		row := make([]int, H)
		for y := 0; y < H; y++ {
			for x := 0; x < W; x++ {
				c := im.RGBAAt(x, y)
				if c.R == 238 && c.G == 238 && c.B == 238 {
					col[x]++
					row[y]++
				}
			}
		}
		x0, y0, x1, y1 = -1, -1, -1, -1
		for x := 0; x < W; x++ {
			if col[x] >= 300 {
				if x0 < 0 {
					x0 = x
				}
				x1 = x
			}
		}
		for y := 0; y < H; y++ {
			if row[y] >= 1000 {
				if y0 < 0 {
					y0 = y
				}
				y1 = y
			}
		}
		if x0 < 0 || y0 < 0 {
			fatal("не нашёл рамку превью; задай -box x0,y0,x1,y1")
		}
	}
	cx := float64(x0+x1) / 2
	ox, oy := x0+1, y0+1
	w, h := x1-x0-1, y1-y0-1
	out := &Img{W: w, H: h, Pix: make([]float32, w*h*3)}
	for y := 0; y < h; y++ {
		for x := 0; x < w; x++ {
			c := im.RGBAAt(ox+x, oy+y)
			i := (y*w + x) * 3
			out.Pix[i], out.Pix[i+1], out.Pix[i+2] = float32(c.R), float32(c.G), float32(c.B)
		}
	}
	return out, cx - float64(ox), ox, oy
}

func fatal(f string, a ...any) {
	fmt.Fprintf(os.Stderr, f+"\n", a...)
	os.Exit(1)
}

func width(n int) float64 { // суммарный advance, ед. шрифта (пары по 300, одиночный последний — 1300)
	if n%2 == 1 {
		return float64(300*n + 1000)
	}
	return float64(300 * n)
}

func main() {
	fontPath := flag.String("font", "glyphs.otf", "путь к glyphs.otf")
	imgPath := flag.String("img", "glyphs.png", "скриншот с флагом")
	nFlag := flag.Int("n", 0, "длина флага (0 — подобрать)")
	nRange := flag.String("nrange", "20,34", "диапазон длин для подбора")
	sFlag := flag.Float64("S", 0, "px на em (0 — подобрать)")
	ybFlag := flag.Float64("yb", 0, "базовая линия в координатах превью (с -S)")
	dxFlag := flag.Float64("dx", 0, "сдвиг X0 от формулы центрирования (с -S)")
	beam := flag.Int("beam", 3, "ширина beam search")
	prefix := flag.String("prefix", "SOLARCTF{", "известный префикс (нечётной длины)")
	box := flag.String("box", "", "рамка превью x0,y0,x1,y1")
	out := flag.String("out", "", "сохранить рендер найденного флага в PNG")
	self := flag.String("selftest", "", "флаг для самопроверки на собственном рендере")
	flag.Parse()

	t0 := time.Now()
	f, err := LoadFont(*fontPath)
	if err != nil {
		fatal("font: %v", err)
	}
	r := NewRast(f)
	a := NewAuto(f)
	logf := func(s string, args ...any) {
		fmt.Printf("[%5.1fs] "+s+"\n", append([]any{time.Since(t0).Seconds()}, args...)...)
	}
	logf("шрифт: %d глифов, состояний автомата: %d+%d+%d+%d", f.NumGlyphs, len(a.gen[1]), len(a.gen[2]), len(a.gen[3]), len(a.gen[4]))

	var ref *Img
	var cx float64
	var S, Yb, X0 float64
	n := *nFlag

	if *self != "" {
		text := *self
		n = len(text)
		S = 178
		gl := f.Shape(text)
		_, tot := f.Layout(gl)
		W, H := int(math.Ceil(3.2*S+tot*S/1000)), int(math.Ceil(3*S))
		X0, Yb = 1.6*S, 1.7*S
		ref = Render(f, r, gl, S/1000, X0, Yb, W, H)
		logf("selftest: отрисовал %q (%dx%d), декодирую без знания середины", text, W, H)
	} else {
		im, err := loadImg(*imgPath)
		if err != nil {
			fatal("img: %v", err)
		}
		var ox, oy int
		ref, cx, ox, oy = cropPreview(im, *box)
		logf("превью: %dx%d (смещение %d,%d), центр x=%.1f", ref.W, ref.H, ox, oy, cx)
		mk := func(n int, S, yb, dx float64) *Solver {
			X0 := cx - S*width(n)/2000 + dx
			return &Solver{f: f, a: a, r: r, ref: ref, s: S / 1000, X0: X0, Yb: yb, n: n, prefix: *prefix, beam: *beam, thr: 0.01, log: logf}
		}
		if *sFlag > 0 {
			S, Yb = *sFlag, *ybFlag
			if n == 0 {
				fatal("с -S нужно указать и -n")
			}
			X0 = cx - S*width(n)/2000 + *dxFlag
		} else {
			// подбор геометрии по правому краю: оценка последнего глифа резко падает при верных n,S,Yb,X0
			S0 := float64(ref.H) / 3
			Yb0 := 1.7*S0 - 1
			lo, hi := 20, 34
			fmt.Sscanf(*nRange, "%d,%d", &lo, &hi)
			bestN, bestSc := n, math.Inf(1)
			if n == 0 {
				for nn := lo; nn <= hi; nn++ {
					for _, yb := range []float64{Yb0 - 2, Yb0, Yb0 + 2} {
						for _, dx := range []float64{-8, -4, 0, 4, 8} {
							if sc := mk(nn, S0-0.5, yb, dx).LastScore(); sc < bestSc {
								bestSc, bestN = sc, nn
							}
						}
					}
					logf("n=%d: лучшая оценка правого края %.0f (лучшее n пока %d)", nn, bestSc, bestN)
				}
				n = bestN
			}
			bestSc = math.Inf(1)
			var bS, bY, bD float64
			for S := S0 - 1.5; S <= S0+1.51; S += 0.5 {
				for yb := Yb0 - 3; yb <= Yb0+3.01; yb++ {
					for dx := -4.0; dx <= 8.01; dx++ {
						if sc := mk(n, S, yb, dx).LastScore(); sc < bestSc {
							bestSc, bS, bY, bD = sc, S, yb, dx
						}
					}
				}
			}
			S, Yb = bS, bY
			X0 = cx - S*width(n)/2000 + bD
			logf("геометрия: n=%d S=%.1f Yb=%.1f dx=%.0f (оценка %.1f)", n, S, Yb, bD, bestSc)
		}
	}

	sv := &Solver{f: f, a: a, r: r, ref: ref, s: S / 1000, X0: X0, Yb: Yb, n: n, prefix: *prefix, beam: *beam, thr: 0.01, log: logf}
	mad := func(sv *Solver, text string) float64 {
		im := Render(f, r, f.Shape(text), sv.s, sv.X0, sv.Yb, ref.W, ref.H)
		var s float64
		for i := range im.Pix {
			s += math.Abs(float64(im.Pix[i] - ref.Pix[i]))
		}
		return s / float64(len(im.Pix))
	}
	var res []Result
	autoGeom := *self == "" && *sFlag == 0
	last := ""
	for iter := 0; ; iter++ {
		logf("декодирование: %s", sv)
		res = sv.Run()
		if len(res) == 0 {
			fatal("кандидатов нет — проверь геометрию (-S/-yb/-dx/-n)")
		}
		if !autoGeom || iter >= 4 || res[0].Text == last {
			break
		}
		last = res[0].Text
		// уточняем геометрию по полному изображению (лучший кандидат даёт почти правильную картинку)
		best := res[0].Text
		cur := [3]float64{sv.s * 1000, sv.Yb, sv.X0 - (cx - sv.s*1000*width(n)/2000)}
		eval := func(p [3]float64) float64 {
			t := *sv
			t.s, t.Yb, t.X0 = p[0]/1000, p[1], cx-p[0]*width(n)/2000+p[2]
			return mad(&t, best)
		}
		bestV := eval(cur)
		for _, st := range []float64{0.5, 0.25, 0.12, 0.06} {
			for improved := true; improved; {
				improved = false
				for k := 0; k < 3; k++ {
					for _, d := range []float64{-st, st} {
						p := cur
						p[k] += d
						if v := eval(p); v < bestV-1e-6 {
							cur, bestV, improved = p, v, true
						}
					}
				}
			}
		}
		logf("уточнение геометрии по %q: S=%.2f Yb=%.2f dx=%.2f (отличие %.3f)", best, cur[0], cur[1], cur[2], bestV)
		sv.s, sv.Yb, sv.X0 = cur[0]/1000, cur[1], cx-cur[0]*width(n)/2000+cur[2]
	}
	fmt.Println("\nТоп кандидатов (меньше — лучше):")
	for i, c := range res {
		if i >= 6 {
			break
		}
		fmt.Printf("  %2d. %10.1f  %s\n", i+1, c.Score, c.Text)
	}
	// контроль: честный рендер найденного флага и среднее абсолютное отличие от эталона
	fmt.Println("\nКонтрольный рендер (среднее |отличие| от эталона):")
	for i, c := range res {
		if i >= 3 {
			break
		}
		fmt.Printf("  %-40s %.3f\n", c.Text, mad(sv, c.Text))
	}
	if *out != "" {
		im := Render(f, r, f.Shape(res[0].Text), sv.s, sv.X0, sv.Yb, ref.W, ref.H)
		if err := savePNG(*out, im); err != nil {
			fatal("%v", err)
		}
		logf("сохранён %s", *out)
	}
	fmt.Printf("\nФЛАГ: %s\n", res[0].Text)
}
