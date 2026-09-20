extends RefCounted
# Jenerik UI kontrolleri — oyundan bağımsız, ölçümle çalışır.
#
# Neden: playtest-qa-checklist B/C/D/K maddeleri şimdiye kadar yalnız GÖZLE
# denetleniyordu ("ikon butonun %40'ını doldurmalı" gibi sayısal bir kural bile).
# Göz turdan tura kayar; sessiz regresyonu tutmaz. Bu dosya aynı maddeleri
# sahne ağacından ölçer.
#
# Kullanım (oyunun kendi tools/qa_kontrol.gd'sinden):
#   const Ortak = preload("res://../tools/qa_kontrol_ortak.gd")
#   var bulgular := Ortak.hepsi(sahne_koku, viewport_boyutu)
#   Ortak.rapor(bulgular)   # -> "KIRMIZI n" / "YESIL", çıkış kodu için
#
# Her bulgu: {"kod", "dugum", "mesaj", "olcum", "esik"}

# Checklist B: "Menü ikonu butonun ≥ %40'ını dolduruyor (ufak nokta ikon = kırmızı)"
const IKON_DOLULUK_MIN := 0.40
# Checklist B: "Boş alan oranı: kutu içeriğin 2×'inden geniş/yüksek değil"
const MODAL_BOSLUK_MAX := 2.0
# Checklist K: "Modal / panel: ekranın ~%35–55 genişliği bandında"
const MODAL_EN_MIN := 0.35
const MODAL_EN_MAX := 0.55
# WCAG AA büyük metin eşiği. Oyun HUD'unda sayılar ~15–18 px + outline.
const KONTRAST_MIN := 3.0
# Ekran dışı: 1 px yuvarlama payı bırak, gerçek taşmayı yakala.
const TASMA_PAY := 1.0
# Aynı koddan en çok bu kadar örnek yazdırılır; gerisi sayılır.
const RAPOR_ORNEK := 3


static func hepsi(kok: Node, vp: Vector2, kare: Image = null) -> Array:
	var b: Array = []
	b.append_array(ikon_doluluk(kok))
	b.append_array(ekran_disi(kok, vp))
	b.append_array(metin_kontrast(kok, kare))
	return b


static func kare_al(agac: SceneTree) -> Image:
	"""Kontrast ölçümü için çizilen kare. `await RenderingServer.frame_post_draw`
	SONRASI çağır, yoksa bir önceki karenin pikselleri gelir."""
	var vp := agac.get_root().get_viewport()
	if vp == null or vp.get_texture() == null:
		return null
	return vp.get_texture().get_image()


# ── 1. İkon / buton alan oranı ────────────────────────────────────────────
# Kural YALNIZ metinsiz butonlara uygulanır. Anlamı tek başına ikon taşıyorsa
# ikon kutuyu doldurmalı (checklist B, "ufak nokta ikon = kırmızı"). Yüzünde
# metin olan butonda (fiyat, sayı) ikon vurgudur, anlamı o taşımaz — oraya aynı
# eşiği uygulamak yanlış kırmızı üretir.
static func ikon_doluluk(kok: Node) -> Array:
	var b: Array = []
	for n in _gorunur_kontroller(kok):
		if not (n is Button) or n.icon == null:
			continue
		if n.text.strip_edges() != "":
			continue
		var kutu: Vector2 = n.size
		if kutu.x <= 0.0 or kutu.y <= 0.0:
			continue
		var cizilen := _ikon_cizilen_boyut(n)
		var oran := (cizilen.x * cizilen.y) / (kutu.x * kutu.y)
		if oran < IKON_DOLULUK_MIN:
			b.append({
				"kod": "ikon_doluluk",
				"dugum": _yol(n),
				"mesaj": "ikon butonun %%%d'ini dolduruyor" % int(oran * 100.0),
				"olcum": oran, "esik": IKON_DOLULUK_MIN,
			})
	return b


static func _ikon_cizilen_boyut(btn: Button) -> Vector2:
	var ikon: Vector2 = btn.icon.get_size()
	if ikon.x <= 0.0 or ikon.y <= 0.0:
		return Vector2.ZERO
	var kenar := Vector2.ZERO
	var sb := btn.get_theme_stylebox("normal")
	if sb != null:
		kenar = Vector2(sb.get_margin(SIDE_LEFT) + sb.get_margin(SIDE_RIGHT),
			sb.get_margin(SIDE_TOP) + sb.get_margin(SIDE_BOTTOM))
	var alan: Vector2 = (btn.size - kenar).max(Vector2.ONE)
	# icon_max_width teması ikonu kutudan bağımsız kısıtlar; yok sayılırsa
	# ölçüm çizilenden büyük çıkar.
	var tavan: int = btn.get_theme_constant("icon_max_width")
	if tavan > 0:
		alan.x = minf(alan.x, float(tavan))
	if not btn.expand_icon:
		# expand_icon kapalıyken ikon kendi boyutunda çizilir, kutuya kırpılır.
		var c: Vector2 = ikon.min(alan)
		if tavan > 0 and ikon.x > float(tavan):
			c = ikon * (float(tavan) / ikon.x)
		return c
	var k: float = minf(alan.x / ikon.x, alan.y / ikon.y)
	return ikon * k


# ── 2. Modal içerik / kutu oranı ──────────────────────────────────────────
# Modal kökü elle verilir: hangi panelin "modal" olduğunu ağaç bilmez.
static func modal_doluluk(panel: Control, vp: Vector2) -> Array:
	var b: Array = []
	if panel == null or not panel.visible:
		return b
	var kutu: Vector2 = panel.size
	if kutu.x <= 0.0 or kutu.y <= 0.0:
		return b
	var icerik := _icerik_kutusu(panel)
	if icerik.size.x > 0.0 and icerik.size.y > 0.0:
		for eksen in [["x", icerik.size.x, kutu.x], ["y", icerik.size.y, kutu.y]]:
			var oran: float = float(eksen[2]) / float(eksen[1])
			if oran > MODAL_BOSLUK_MAX:
				b.append({
					"kod": "modal_bosluk",
					"dugum": _yol(panel),
					"mesaj": "kutu içeriğin %.1f katı (%s ekseni)" % [oran, eksen[0]],
					"olcum": oran, "esik": MODAL_BOSLUK_MAX,
				})
	if vp.x > 0.0:
		var en: float = kutu.x / vp.x
		if en < MODAL_EN_MIN or en > MODAL_EN_MAX:
			b.append({
				"kod": "modal_en",
				"dugum": _yol(panel),
				"mesaj": "modal genişliği ekranın %%%d'i" % int(en * 100.0),
				"olcum": en, "esik": MODAL_EN_MIN,
			})
	return b


static func _icerik_kutusu(panel: Control) -> Rect2:
	# Yaprak Control'lerin (Label/TextureRect/Button) birleşimi = gerçek içerik.
	# Container'ların kendi rect'i panelle aynı olur, içeriği temsil etmez.
	var r := Rect2()
	var ilk := true
	for n in _gorunur_kontroller(panel):
		if n == panel:
			continue
		if not (n is Label or n is TextureRect or n is Button or n is RichTextLabel):
			continue
		if n.size.x <= 0.0 or n.size.y <= 0.0:
			continue
		var g := Rect2(n.global_position, n.size)
		r = g if ilk else r.merge(g)
		ilk = false
	return r


# ── 3. Ekran dışı taşma ───────────────────────────────────────────────────
static func ekran_disi(kok: Node, vp: Vector2) -> Array:
	var b: Array = []
	if vp.x <= 0.0 or vp.y <= 0.0:
		return b
	var ekran := Rect2(Vector2.ZERO, vp)
	var suclu: Dictionary = {}
	for n in _gorunur_kontroller(kok):
		if n.size.x <= 0.0 or n.size.y <= 0.0:
			continue
		# Ata zaten taştıysa çocuğunu tekrar raporlama — tek sorun, tek satır.
		if _atada_var(n, suclu):
			suclu[n] = true
			continue
		# ScrollContainer içeriği ekranı aşar, aşması gerekir — kırpılıyor.
		if _kirpan_ata(n):
			continue
		# Kamera altındaki dünya-uzayı Control'leri (harita rozetleri) global_position
		# ile ölçülemez; canvas dönüşümü ekran koordinatını verir.
		var g: Rect2 = n.get_global_transform_with_canvas() * Rect2(Vector2.ZERO, n.size)
		var en_cok: float = maxf(
			maxf(ekran.position.x - g.position.x, ekran.position.y - g.position.y),
			maxf(g.end.x - ekran.end.x, g.end.y - ekran.end.y))
		if en_cok > TASMA_PAY:
			suclu[n] = true
			b.append({
				"kod": "ekran_disi",
				"dugum": _yol(n),
				"mesaj": "ekran dışına %d px taşıyor" % int(en_cok),
				"olcum": en_cok, "esik": TASMA_PAY,
			})
	return b


static func _kirpilip_gizlenmis(n: Control) -> bool:
	var merkez: Vector2 = n.get_global_transform_with_canvas().origin + n.size * 0.5
	var a: Node = n.get_parent()
	while a != null:
		if a is Control and (a is ScrollContainer or a.clip_contents):
			var r: Rect2 = a.get_global_transform_with_canvas() * Rect2(Vector2.ZERO, a.size)
			if not r.has_point(merkez):
				return true
		a = a.get_parent()
	return false


static func _kirpan_ata(n: Node) -> bool:
	var a: Node = n.get_parent()
	while a != null:
		if a is ScrollContainer:
			return true
		if a is Control and a.clip_contents:
			return true
		a = a.get_parent()
	return false


static func _atada_var(n: Node, suclu: Dictionary) -> bool:
	var a: Node = n.get_parent()
	while a != null:
		if suclu.has(a):
			return true
		a = a.get_parent()
	return false


# ── 4. Metin-zemin kontrastı ──────────────────────────────────────────────
# ÇİZİLEN kareden ölçülür, bildirilen renklerden değil.
#
# Önce ağaçtan çıkarmaya çalışıldı (ata/kardeş z-sırası + StyleBoxFlat.bg_color)
# ve İKİ KEZ yanlış ölçtü: Wispward'ın sonuç panosunda bg_color #6B5216 ama
# ekrana basılan piksel #110E13. Bildirilen renk ≠ çizilen piksel. Gözün gördüğü
# tek şey karenin kendisi; ölçüm de oradan alınır.
static func metin_kontrast(kok: Node, kare: Image = null) -> Array:
	var b: Array = []
	for n in _gorunur_kontroller(kok):
		if not (n is Label) or n.text.strip_edges() == "":
			continue
		# Kaydırma alanının dışına çıkmış etiket ÇİZİLMİYOR; kontrastı yoktur.
		if _kirpilip_gizlenmis(n):
			continue
		if kare == null:
			b.append({
				"kod": "kontrast_olculemedi",
				"dugum": _yol(n),
				"mesaj": "çizilen kare verilmedi (metin_kontrast'a Image geçir)",
				"olcum": -1.0, "esik": KONTRAST_MIN,
			})
			continue
		var on: Color = n.get_theme_color("font_color")
		var zemin = _zemin_kareden(n, kare, on)
		if zemin == null:
			# Ölçemediğini sessizce geçme — gözün kaçırdığı tam burası.
			b.append({
				"kod": "kontrast_olculemedi",
				"dugum": _yol(n),
				"mesaj": "etiket alanında zemin pikseli ayırt edilemedi",
				"olcum": -1.0, "esik": KONTRAST_MIN,
			})
			continue
		# Kalın kontur metni zeminden zaten ayırır; gözün gördüğü zemin odur.
		var etkin: Color = zemin
		if n.get_theme_constant("outline_size") >= 3:
			etkin = n.get_theme_color("font_outline_color")
		var oran := kontrast(on, etkin)
		if oran < KONTRAST_MIN:
			b.append({
				"kod": "kontrast",
				"dugum": _yol(n),
				"mesaj": "metin/zemin kontrastı %.2f:1 (zemin #%s)" % [oran, etkin.to_html(false)],
				"olcum": oran, "esik": KONTRAST_MIN,
			})
	return b


static func _zemin_kareden(lbl: Label, kare: Image, _on: Color):
	"""Etiket dikdörtgenindeki EN SIK renk = metnin üstünde durduğu zemin.

	Önce "font rengine yakın pikselleri at" denendi ve tam ölçmesi gereken
	durumda çöktü: metin zemine YAKINSA (düşük kontrast) filtre zemini de
	atıyor, ölçüm "belirlenemedi" diyordu. En sık renk böyle bir varsayım
	yapmaz — glif normal punto/kutu oranında hiçbir zaman çoğunluk değildir.
	"""
	var vp: Vector2 = lbl.get_viewport_rect().size
	if vp.x <= 0.0 or vp.y <= 0.0:
		return null
	# Kare viewport'tan büyük olabilir (retina); ölçeği hesaba kat.
	var olc := Vector2(kare.get_width() / vp.x, kare.get_height() / vp.y)
	var r: Rect2 = lbl.get_global_transform_with_canvas() * Rect2(Vector2.ZERO, lbl.size)
	var x0: int = clampi(int(r.position.x * olc.x), 0, kare.get_width() - 1)
	var y0: int = clampi(int(r.position.y * olc.y), 0, kare.get_height() - 1)
	var x1: int = clampi(int(r.end.x * olc.x), 0, kare.get_width() - 1)
	var y1: int = clampi(int(r.end.y * olc.y), 0, kare.get_height() - 1)
	if x1 <= x0 or y1 <= y0:
		return null
	var adim_x: int = maxi(1, (x1 - x0) / 32)
	var adim_y: int = maxi(1, (y1 - y0) / 16)
	# 5 bit/kanal kova: doku gürültüsü aynı kovaya düşsün, ton farkı düşmesin.
	var sayac: Dictionary = {}
	var toplam: Dictionary = {}
	var n := 0
	for y in range(y0, y1 + 1, adim_y):
		for x in range(x0, x1 + 1, adim_x):
			var c: Color = kare.get_pixel(x, y)
			var kova: int = (int(c.r * 31) << 10) | (int(c.g * 31) << 5) | int(c.b * 31)
			sayac[kova] = int(sayac.get(kova, 0)) + 1
			toplam[kova] = (toplam[kova] + c) if toplam.has(kova) else c
			n += 1
	if n < 4:
		return null
	var en_kova := -1
	var en := 0
	for k in sayac:
		if int(sayac[k]) > en:
			en = int(sayac[k])
			en_kova = k
	if en_kova < 0:
		return null
	var t: Color = toplam[en_kova]
	return Color(t.r / en, t.g / en, t.b / en)


static func kontrast(a: Color, b: Color) -> float:
	var la := _isik(a)
	var lb := _isik(b)
	var ust: float = maxf(la, lb) + 0.05
	var alt: float = minf(la, lb) + 0.05
	return ust / alt


static func _isik(c: Color) -> float:
	return 0.2126 * _kanal(c.r) + 0.7152 * _kanal(c.g) + 0.0722 * _kanal(c.b)


static func _kanal(v: float) -> float:
	return v / 12.92 if v <= 0.04045 else pow((v + 0.055) / 1.055, 2.4)


# ── Yardımcılar ───────────────────────────────────────────────────────────
static func _gorunur_kontroller(kok: Node) -> Array:
	var c: Array = []
	if kok == null:
		return c
	var yigin: Array = [kok]
	while not yigin.is_empty():
		var n: Node = yigin.pop_back()
		if n is Control:
			if not n.is_visible_in_tree():
				continue
			c.append(n)
		if n is CanvasItem and not n.visible:
			continue
		for c2 in n.get_children():
			yigin.append(c2)
	return c


static func _yol(n: Node) -> String:
	var p := n.name
	var a: Node = n.get_parent()
	var d := 0
	while a != null and d < 3:
		p = String(a.name) + "/" + p
		a = a.get_parent()
		d += 1
	return p


static func rapor(bulgular: Array, baslik: String = "") -> int:
	if baslik != "":
		print("── ", baslik)
	if bulgular.is_empty():
		print("  YESIL (%s)" % baslik)
		return 0
	# Aynı kod 120 düğümde tekrarlıyorsa 120 satır sinyal değil gürültüdür:
	# okunmaz olan çıktı okunmayan çıktıya dönüşür. Koda göre topla.
	var grup: Dictionary = {}
	for f in bulgular:
		var k: String = f["kod"]
		if not grup.has(k):
			grup[k] = []
		grup[k].append(f)
	for k in grup:
		var g: Array = grup[k]
		for f in g.slice(0, RAPOR_ORNEK):
			print("  KIRMIZI %s  %s — %s" % [f["kod"], f["dugum"], f["mesaj"]])
		if g.size() > RAPOR_ORNEK:
			print("  KIRMIZI %s  … aynı bulgu %d düğümde daha" % [k, g.size() - RAPOR_ORNEK])
	return bulgular.size()


# ── Öz-test ───────────────────────────────────────────────────────────────
# Sessizce bozulan bir denetçi, hiç denetçi olmamasından kötüdür: her kontrol
# "yeşil" der ve regresyon fark edilmeden geçer. Bu fonksiyon her kontrolün
# bilinen-kötü bir girdide GERÇEKTEN kırmızı verdiğini doğrular.
# Dönüş: hata mesajları listesi (boşsa denetçi sağlam).
static func oz_test(ebeveyn: Node) -> Array:
	var h: Array = []

	# kontrast: bilinen WCAG değerleri
	if absf(kontrast(Color.WHITE, Color.BLACK) - 21.0) > 0.05:
		h.append("kontrast(beyaz,siyah) 21 olmali, %.2f geldi" % kontrast(Color.WHITE, Color.BLACK))
	if absf(kontrast(Color.WHITE, Color.WHITE) - 1.0) > 0.01:
		h.append("kontrast(ayni renk) 1 olmali")

	# Sahne ağacına gerçekten eklenir: ağaç dışı Control'lerde is_visible_in_tree()
	# ve layout hesabı çalışmaz, test sahte yeşile düşer.
	var kok := Control.new()
	ebeveyn.add_child(kok)
	kok.size = Vector2(400, 300)

	# ikon_doluluk: 100x100 butonda 10x10 ikon → %1
	var btn := Button.new()
	btn.size = Vector2(100, 100)
	btn.expand_icon = false
	var img := Image.create(10, 10, false, Image.FORMAT_RGBA8)
	img.fill(Color.RED)
	btn.icon = ImageTexture.create_from_image(img)
	kok.add_child(btn)

	# ekran_disi: ekranın sağına taşan etiket
	var tasan := Label.new()
	tasan.text = "x"
	tasan.position = Vector2(380, 10)
	tasan.size = Vector2(100, 20)
	kok.add_child(tasan)

	for cift in [["ikon_doluluk", ikon_doluluk(kok)],
			["ekran_disi", ekran_disi(kok, Vector2(400, 300))]]:
		var kod: String = cift[0]
		var bulundu := false
		for f in cift[1]:
			if f["kod"] == kod:
				bulundu = true
		if not bulundu:
			h.append("%s: bilinen-kötü girdide kırmızı vermedi" % kod)

	# Metinli buton: ikon vurgudur, aynı eşik uygulanmaz
	var etiketli := Button.new()
	etiketli.size = Vector2(100, 100)
	etiketli.text = "250"
	etiketli.icon = btn.icon
	kok.add_child(etiketli)
	for f in ikon_doluluk(kok):
		if f["dugum"].ends_with(etiketli.name):
			h.append("ikon_doluluk metinli butonu kırmızı yaptı")

	# icon_max_width: tavan varsa çizilen boyut ona uyar
	var tavanli := Button.new()
	tavanli.size = Vector2(100, 100)
	tavanli.expand_icon = true
	var bimg := Image.create(80, 80, false, Image.FORMAT_RGBA8)
	bimg.fill(Color.RED)
	tavanli.icon = ImageTexture.create_from_image(bimg)
	tavanli.add_theme_constant_override("icon_max_width", 10)
	kok.add_child(tavanli)
	if _ikon_cizilen_boyut(tavanli).x > 10.5:
		h.append("icon_max_width yok sayıldı (çizilen %.1f px)" % _ikon_cizilen_boyut(tavanli).x)

	# ScrollContainer içeriği ekranı aşabilir — kırpılıyor, kırmızı değil
	var kaydir := ScrollContainer.new()
	kaydir.size = Vector2(100, 100)
	var uzun := Label.new()
	uzun.text = "u"
	uzun.size = Vector2(2000, 40)
	kaydir.add_child(uzun)
	kok.add_child(kaydir)
	for f in ekran_disi(kok, Vector2(400, 300)):
		if f["dugum"].ends_with(uzun.name):
			h.append("ekran_disi kırpılan ScrollContainer içeriğini kırmızı yaptı")

	# ── Kontrast: ÇİZİLEN kareden ölçülür ──
	var vp: Vector2 = kok.get_viewport_rect().size
	var kare := Image.create(maxi(2, int(vp.x)), maxi(2, int(vp.y)), false, Image.FORMAT_RGBA8)
	kare.fill(Color("101020"))
	var soluk := Label.new()
	soluk.text = "okunmaz"
	soluk.name = "SolukEtiket"
	soluk.position = Vector2(20, 20)
	soluk.size = Vector2(100, 20)
	soluk.add_theme_color_override("font_color", Color("202040"))
	kok.add_child(soluk)
	var net := Label.new()
	net.text = "okunur"
	net.name = "NetEtiket"
	net.position = Vector2(20, 60)
	net.size = Vector2(100, 20)
	net.add_theme_color_override("font_color", Color.WHITE)
	kok.add_child(net)

	var kb: Array = metin_kontrast(kok, kare)
	var soluk_ok := false
	for f in kb:
		if f["dugum"].ends_with("SolukEtiket") and f["kod"] == "kontrast":
			soluk_ok = true
		if f["dugum"].ends_with("NetEtiket"):
			h.append("yüksek kontrastlı etiket kırmızı yapıldı (%s)" % f["kod"])
	if not soluk_ok:
		h.append("düşük kontrast çizilen kareden yakalanmadı")

	# Kare verilmezse sessizce geçmemeli
	var kare_yok := false
	for f in metin_kontrast(kok, null):
		if f["kod"] == "kontrast_olculemedi":
			kare_yok = true
	if not kare_yok:
		h.append("kare verilmeyince kontrast sessizce yeşil geçti")

	# Kalın kontur zemin yerine geçer: açık zeminde beyaz metin konturla kurtulur.
	# (Konturun kendisi yeterli kontrasta sahip olmalı — koyu metne koyu kontur
	# kurtarmaz; bu yüzden test beyaz metin / siyah kontur ile kurulur.)
	var konturlu := Label.new()
	konturlu.text = "konturlu"
	konturlu.name = "KonturluEtiket"
	konturlu.position = Vector2(20, 100)
	konturlu.size = Vector2(100, 20)
	konturlu.add_theme_color_override("font_color", Color.WHITE)
	kok.add_child(konturlu)
	var acik_kare := Image.create(maxi(2, int(vp.x)), maxi(2, int(vp.y)), false, Image.FORMAT_RGBA8)
	acik_kare.fill(Color("F2F2F2"))
	var konturssuz_kirmizi := false
	for f in metin_kontrast(kok, acik_kare):
		if f["dugum"].ends_with("KonturluEtiket") and f["kod"] == "kontrast":
			konturssuz_kirmizi = true
	if not konturssuz_kirmizi:
		h.append("açık zeminde beyaz metin kırmızı verilmedi (kontur öncesi)")
	konturlu.add_theme_color_override("font_outline_color", Color.BLACK)
	konturlu.add_theme_constant_override("outline_size", 6)
	for f in metin_kontrast(kok, acik_kare):
		if f["dugum"].ends_with("KonturluEtiket") and f["kod"] == "kontrast":
			h.append("kalın kontur zemin olarak sayılmadı")

	# modal_doluluk: 400x300 kutuda 20x20 içerik
	var panel := PanelContainer.new()
	panel.size = Vector2(400, 300)
	var ufak := Label.new()
	ufak.text = "."
	ufak.size = Vector2(20, 20)
	panel.add_child(ufak)
	kok.add_child(panel)
	var m := modal_doluluk(panel, Vector2(1920, 1080))
	var kodlar: Array = []
	for f in m:
		kodlar.append(f["kod"])
	if not kodlar.has("modal_bosluk"):
		h.append("modal_bosluk: bilinen-kötü girdide kırmızı vermedi")
	if not kodlar.has("modal_en"):
		h.append("modal_en: bilinen-kötü girdide kırmızı vermedi")

	# Temiz girdi yanlışlıkla kırmızı olmamalı
	var temiz := Control.new()
	ebeveyn.add_child(temiz)
	temiz.size = Vector2(400, 300)
	var iyi := Label.new()
	iyi.text = "ok"
	iyi.position = Vector2(10, 10)
	iyi.size = Vector2(50, 20)
	iyi.add_theme_color_override("font_color", Color.WHITE)
	iyi.add_theme_color_override("font_outline_color", Color.BLACK)
	iyi.add_theme_constant_override("outline_size", 4)
	temiz.add_child(iyi)
	var yanlis := hepsi(temiz, Vector2(400, 300), kare)
	if not yanlis.is_empty():
		h.append("temiz girdide %d yanlış kırmızı: %s" % [yanlis.size(), yanlis[0]["kod"]])

	ebeveyn.remove_child(kok)
	ebeveyn.remove_child(temiz)
	kok.free()
	temiz.free()
	return h
