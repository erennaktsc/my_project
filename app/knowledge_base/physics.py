"""
Fizik Bilgi Tabanı
==================

AI'ya enjekte edilecek fizik konularındaki uzman bilgileri.
"""


# ═══════════════════════════════════════════
# KLASİK MEKANİK
# ═══════════════════════════════════════════

KLASIK_MEKANIK = """
═══ KLASİK MEKANİK — UZMAN NOTLARI ═══

▸ NEWTON'UN HAREKET YASALARI:
1. Eylemsizlik: Kuvvet uygulanmadıkça hareket değişmez (F=0 ⟹ a=0)
2. F = m·a (Vektörel denklem!)
3. Etki-tepki: F_AB = -F_BA

▸ KUVVETLER:
- Yerçekimi: W = mg (g ≈ 9.81 m/s² yerde)
- Normal kuvvet: yüzeye dik
- Sürtünme: f_k = μ_k·N (kinetik), f_s ≤ μ_s·N (statik)
- Yay kuvveti: F = -kx (Hooke yasası)
- Merkezi kuvvet: F = -mv²/r (merkeze doğru)

▸ KİNEMATİK FORMÜLLERİ (sabit ivme):
- v = v₀ + at
- x = x₀ + v₀t + ½at²
- v² = v₀² + 2a(x-x₀)
- x = x₀ + ½(v+v₀)t

▸ ENERJİ:
- Kinetik: KE = ½mv²
- Potansiyel (yerçekimi): PE = mgh
- Yay potansiyeli: PE = ½kx²
- İş-enerji teoremi: W = ΔKE
- Korunum: KE₁ + PE₁ = KE₂ + PE₂ (korunumlu kuvvet)

▸ MOMENTUM:
- p = mv (vektörel)
- İmpuls: J = F·Δt = Δp
- Korunum: dış kuvvet yoksa p_toplam sabit

▸ ÇARPIŞMALAR:
- Elastik: KE ve p korunur
- Esnek olmayan: sadece p korunur
- Tam esnek olmayan: birlikte hareket ederler

▸ DAİRESEL HAREKET:
- Açısal hız: ω = v/r
- Merkezcil ivme: a_c = v²/r = ω²r
- Periyot: T = 2π/ω = 2πr/v
- Frekans: f = 1/T

▸ DÖNME HAREKETİ:
- Tork: τ = r × F = r·F·sin(θ)
- Açısal momentum: L = Iω
- Eylemsizlik momenti (cisim cinsi):
  - Nokta: I = mr²
  - Çubuk (ortadan): I = (1/12)mL²
  - Disk: I = (1/2)mr²
  - Küre: I = (2/5)mr²
- Dönme kinetik enerjisi: KE = ½Iω²

▸ EĞİK DÜZLEM:
Açı θ olan düzlemde:
- Yerçekimi bileşenleri: paralel mg·sin(θ), dik mg·cos(θ)
- Normal: N = mg·cos(θ)
- Sürtünme: f = μ·mg·cos(θ)

▸ TİPİK HATALAR:
1. F = ma'da yön bilgisini unutmak (skaler değil vektörel!)
2. Sürtünme katsayısında kinetik ve statik karıştırmak
3. Korunum kanunlarını dış kuvvet varken uygulamak
4. Dairesel harekette merkezcil ivmeyi unutmak
5. Tork yön belirsizliğinde sağ el kuralını ihmal etmek
"""


# ═══════════════════════════════════════════
# ELEKTROMANYETİZMA
# ═══════════════════════════════════════════

ELEKTROMANYETIZMA = """
═══ ELEKTROMANYETİZMA — UZMAN NOTLARI ═══

▸ ELEKTRİK YÜK VE KUVVET:
- Coulomb yasası: F = k·q₁·q₂/r²
- k = 1/(4πε₀) ≈ 9·10⁹ N·m²/C²
- Aynı işaret: itme, zıt işaret: çekme
- Yük kuantize: q = n·e, e = 1.6·10⁻¹⁹ C

▸ ELEKTRİK ALAN:
- E = F/q (q test yükü)
- Nokta yük için: E = k·Q/r²
- Birim: N/C veya V/m
- Düzgün yüklü plakanın alanı: E = σ/ε₀

▸ ELEKTRİK POTANSİYEL:
- V = U/q (potansiyel enerji / yük)
- Nokta yük: V = k·Q/r
- Potansiyel farkı: ΔV = -∫E·dr
- E = -∇V (gradient ilişkisi)
- Birim: Volt (J/C)

▸ GAUSS YASASI:
∮E·dA = Q_içeride/ε₀

Simetrik durumlar için çok güçlü:
- Küresel simetri (nokta yük, küre)
- Silindirik simetri (uzun tel)
- Düzlemsel simetri (düzgün plaka)

▸ KAPASİTÖR:
- C = Q/V
- Düzlem plakalı: C = ε₀A/d
- Dielektrik içinde: C = κ·ε₀A/d (κ > 1)
- Seri: 1/C_eş = 1/C₁ + 1/C₂ + ...
- Paralel: C_eş = C₁ + C₂ + ...
- Enerji: U = (1/2)CV² = Q²/(2C)

▸ AKIM VE DİRENÇ:
- I = dQ/dt (A = Amper = C/s)
- Ohm yasası: V = IR
- Direnç: R = ρL/A (ρ özdirenç)
- Güç: P = VI = I²R = V²/R

▸ KIRCHHOFF YASALARI:
1. Düğüm: ΣI_giren = ΣI_çıkan (yük korunumu)
2. Halka: ΣV = 0 (enerji korunumu)

▸ DİRENÇ KOMBİNASYONLARI:
- Seri: R_eş = R₁ + R₂ + ...
- Paralel: 1/R_eş = 1/R₁ + 1/R₂ + ...

▸ MANYETIK ALAN:
- Manyetik kuvvet: F = qv × B (Lorentz kuvveti)
- Doğru tel: F = IL × B
- Sağ el kuralı yön için
- Birim: Tesla (T) veya Gauss

▸ MANYETIK ALAN KAYNAKLARI:
- Düz tel: B = μ₀I/(2πr)
- Solenoid: B = μ₀nI (n birim uzunluktaki sarım)
- Halka merkezi: B = μ₀I/(2R)
- Biot-Savart: dB = (μ₀/4π)·(IdL × r̂)/r²

▸ FARADAY İNDÜKSİYON:
ε = -dΦ/dt
Φ = ∫B·dA (manyetik akı)
- Lenz yasası: indüklenen akım, akı değişimine karşı koyar

▸ MAXWELL DENKLEMLERİ (integral):
1. Gauss elektrik: ∮E·dA = Q/ε₀
2. Gauss manyetik: ∮B·dA = 0
3. Faraday: ∮E·dL = -dΦ_B/dt
4. Ampere-Maxwell: ∮B·dL = μ₀(I + ε₀·dΦ_E/dt)

▸ TİPİK HATALAR:
1. F = qE'de işaret unutmak (negatif yük için ters yön)
2. Gauss yasası uygularken simetri tipini yanlış seçmek
3. Kapasitör seri/paralel formüllerini karıştırmak
4. Sağ el kuralında yönü ters almak (v × B)
5. Faraday'da Lenz yasasını ihmal etmek (eksi işareti)
"""


# ═══════════════════════════════════════════
# TERMODİNAMİK
# ═══════════════════════════════════════════

TERMODINAMIK = """
═══ TERMODİNAMİK — UZMAN NOTLARI ═══

▸ TEMEL KAVRAMLAR:
- Sıcaklık: maddenin ortalama kinetik enerjisinin ölçüsü
- Isı (Q): enerji transferi (J)
- İş (W): enerji transferi (J)
- İç enerji (U): sistemdeki toplam enerji

▸ SICAKLIK DÖNÜŞÜMLERİ:
- Kelvin: T(K) = T(°C) + 273.15
- Fahrenheit: T(°F) = (9/5)T(°C) + 32

▸ ISI VE FAZ DEĞİŞİMLERİ:
- Q = mcΔT (sıcaklık değişimi, c: özgül ısı)
- Q = mL (faz değişimi, L: gizli ısı)
- Erime/donma: L_f (gizli erime ısısı)
- Buharlaşma/yoğunlaşma: L_v

▸ İDEAL GAZ:
- PV = nRT (R = 8.314 J/(mol·K))
- PV = NkT (k = R/N_A, Boltzmann)
- Avogadro: N_A ≈ 6.022·10²³
- Maxwell-Boltzmann: v_rms = √(3kT/m)

▸ KİNETİK TEORİ:
- Ortalama KE = (3/2)kT
- İç enerji (ideal gaz, monatomik): U = (3/2)nRT
- İç enerji (diatomik): U = (5/2)nRT

▸ TERMODİNAMİĞİN BİRİNCİ YASASI:
ΔU = Q - W
(Sistem için Q girer, sistem W yapar)
DİKKAT: bazı kitaplarda W = -PΔV (sistemin yaptığı iş)

▸ TERMODİNAMİK SÜREÇLER:

1. İZOTERMAL (T sabit):
   • PV = sabit
   • ΔU = 0 (ideal gaz için)
   • Q = W = nRT·ln(V₂/V₁)

2. İZOBARİK (P sabit):
   • V/T = sabit (Charles)
   • W = PΔV
   • Q = nC_pΔT
   • ΔU = nC_vΔT

3. İZOKORİK (V sabit):
   • P/T = sabit (Gay-Lussac)
   • W = 0
   • Q = ΔU = nC_vΔT

4. ADYABATİK (Q = 0):
   • PV^γ = sabit
   • TV^(γ-1) = sabit
   • γ = C_p/C_v (1.4 hava için)
   • W = -ΔU = -nC_vΔT

▸ ISI KAPASİTELERİ:
- C_v: sabit hacimde
- C_p: sabit basınçta
- İdeal gaz: C_p - C_v = R
- Monatomik: C_v = (3/2)R, C_p = (5/2)R
- Diatomik: C_v = (5/2)R, C_p = (7/2)R

▸ İKİNCİ YASA VE ENTROPİ:
- Entropi: ΔS = Q_rev/T
- İzole sistem için ΔS ≥ 0
- Tersinir süreç: ΔS = 0
- Tersinmez süreç: ΔS > 0

▸ ISI MAKİNESİ:
- Verim: η = W/Q_h = 1 - Q_c/Q_h
- Carnot (ideal): η_carnot = 1 - T_c/T_h
- Carnot verimi maksimum verimdir

▸ TERSİNMİŞ ÇEVRİMLER (soğutucu/pompası):
- Soğutma performansı: COP = Q_c/W
- Carnot soğutucu: COP = T_c/(T_h - T_c)

▸ TİPİK HATALAR:
1. Sıcaklık birimini K yerine °C kullanmak (PV=nRT'de hata!)
2. Adyabatikte PV=sabit (yanlış!) yerine PV^γ=sabit
3. İş yönü işareti (sistem yapıyor mu, dışarı mı?)
4. Faz değişiminde T sabit, sadece Q = mL kullan
5. Carnot verimini % yerine ondalık kullanmak (gerekirse)
"""