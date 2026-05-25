"""
Matematik Bilgi Tabanı
=======================

AI'ya enjekte edilecek matematik konularındaki uzman bilgileri.
Her modül, AI'nın o konuda doğru soru üretmesi için kritik bilgileri içerir.
"""


# ═══════════════════════════════════════════
# KALKÜLÜS 1
# ═══════════════════════════════════════════

KALKULUS_1 = """
═══ KALKÜLÜS 1 — UZMAN NOTLARI ═══

▸ TEMEL KAVRAMLAR:
- Limit: lim(x→a) f(x) = L. Sağ ve sol limitlerin eşit olması gerekir.
- Süreklilik: f(a) tanımlı, lim(x→a) f(x) var ve f(a) = lim(x→a) f(x)
- Türev: f'(x) = lim(h→0) [f(x+h) - f(x)] / h

▸ TÜREV KURALLARI (en sık kullanılan):
- Çarpım: (fg)' = f'g + fg'
- Bölüm: (f/g)' = (f'g - fg') / g²
- Zincir: (f∘g)'(x) = f'(g(x)) · g'(x)
- İmplicit (kapalı): y'yi de değişken kabul et, türev al, y' için çöz

▸ ÖNEMLİ TÜREVLER:
- d/dx[sin x] = cos x,  d/dx[cos x] = -sin x
- d/dx[tan x] = sec²x = 1/cos²x
- d/dx[ln x] = 1/x,  d/dx[eˣ] = eˣ
- d/dx[arctan x] = 1/(1+x²)
- d/dx[arcsin x] = 1/√(1-x²)

▸ L'HÔPITAL KURALI:
- 0/0 veya ∞/∞ belirsizliklerinde kullanılır
- lim f(x)/g(x) = lim f'(x)/g'(x) — eğer ikinci limit varsa
- ÖNEMLİ HATA: l'Hôpital'i bölüm kuralıyla karıştırma!

▸ ÖĞRENCİLERİN TİPİK HATALARI:
1. Zincir kuralında iç fonksiyonun türevini unutmak
2. (sin x)² ile sin(x²) karıştırmak
3. ln'in tabanını e değil 10 sanmak (Türk kitaplarında log = log₁₀)
4. Mutlak değer fonksiyonunun türevinde işareti unutmak

▸ KRİTİK ÖZEL DEĞERLER (hata yapmamak için):
- sin(0)=0, sin(π/6)=1/2, sin(π/4)=√2/2, sin(π/3)=√3/2, sin(π/2)=1
- cos(0)=1, cos(π/6)=√3/2, cos(π/4)=√2/2, cos(π/3)=1/2, cos(π/2)=0
- tan(0)=0, tan(π/4)=1, tan(π/3)=√3
- tan(π/2) tanımsız!

▸ EKSTREMUM ANALİZİ:
- Yerel ekstremum: f'(x)=0 olan noktalarda (kritik noktalar)
- Birinci türev testi: f' işareti değişiyorsa ekstremum
- İkinci türev testi: f''>0 ise minimum, f''<0 ise maksimum, f''=0 ise belirsiz
- Mutlak ekstremum: [a,b] aralığında uç noktaları da kontrol et

▸ ASİMPTOTLAR:
- Düşey: lim(x→a) f(x) = ±∞ olduğu noktalar
- Yatay: lim(x→±∞) f(x) = L sabit
- Eğik: y = mx+n şeklinde, m = lim(x→∞) f(x)/x, n = lim(x→∞) [f(x)-mx]
"""


# ═══════════════════════════════════════════
# KALKÜLÜS 2
# ═══════════════════════════════════════════

KALKULUS_2 = """
═══ KALKÜLÜS 2 — UZMAN NOTLARI ═══

▸ İNTEGRAL TEKNİKLERİ:

1. DEĞİŞKEN DEĞİŞTİRME (u-substitution):
   u = g(x), du = g'(x)dx
   ∫f(g(x))g'(x)dx = ∫f(u)du

2. KISMİ İNTEGRAL:
   ∫u dv = uv - ∫v du
   LIATE kuralı: Logaritmik, İnvers, Algebraik, Trigonometrik, Üstel
   (u olarak öndekini seç)

3. TRİGONOMETRİK İNTEGRALLER:
   • ∫sin²x dx = (x - sin(2x)/2)/2 + C
   • ∫cos²x dx = (x + sin(2x)/2)/2 + C
   • ∫sin(mx)cos(nx)dx → çarpım-toplam formülü
   • ∫tan x dx = -ln|cos x| + C = ln|sec x| + C

4. TRİGONOMETRİK İKAME:
   • √(a²-x²) için x = a·sin(θ)
   • √(a²+x²) için x = a·tan(θ)
   • √(x²-a²) için x = a·sec(θ)

5. KISMI KESİRLER:
   Rasyonel fonksiyonların integralinde kullanılır
   P(x)/Q(x) → A/(x-a) + B/(x-b) + ... şeklinde ayrış

▸ ÖNEMLİ İNTEGRALLER:
- ∫1/x dx = ln|x| + C
- ∫eˣ dx = eˣ + C
- ∫1/(1+x²) dx = arctan(x) + C
- ∫1/√(1-x²) dx = arcsin(x) + C
- ∫sec(x) dx = ln|sec(x) + tan(x)| + C

▸ BELİRLİ İNTEGRAL UYGULAMALARI:
- Alan: ∫[a,b] f(x)dx (f≥0 için)
- İki eğri arası alan: ∫[a,b] (f(x) - g(x))dx
- Hacim (disk metodu): V = π∫[a,b] [f(x)]²dx
- Hacim (silindirik kabuk): V = 2π∫[a,b] x·f(x)dx
- Yay uzunluğu: L = ∫[a,b] √(1+[f'(x)]²)dx

▸ SERİLER VE DİZİLER:

YAKINSAKLIK TESTLERİ (sıra önemli!):
1. n-inci terim testi: lim aₙ ≠ 0 ise IRAKSAR
2. Geometrik seri: ∑arⁿ, |r|<1 ise yakınsak (toplam a/(1-r))
3. p-serisi: ∑1/nᵖ, p>1 ise yakınsak
4. Karşılaştırma testi
5. Limit karşılaştırma testi
6. İntegral testi (azalan, pozitif fonksiyon için)
7. Oran testi: lim |aₙ₊₁/aₙ| = L. L<1 yakınsak, L>1 ıraksak, L=1 belirsiz
8. Kök testi: lim ⁿ√|aₙ| = L
9. Leibniz testi (alterne seriler için)

▸ TAYLOR SERİLERİ:
f(x) = ∑ f⁽ⁿ⁾(a)/n! · (x-a)ⁿ

Önemli açılımlar (a=0, Maclaurin):
- eˣ = 1 + x + x²/2! + x³/3! + ...
- sin(x) = x - x³/3! + x⁵/5! - ...
- cos(x) = 1 - x²/2! + x⁴/4! - ...
- ln(1+x) = x - x²/2 + x³/3 - ... (|x|<1)
- 1/(1-x) = 1 + x + x² + x³ + ... (|x|<1)

▸ TİPİK HATALAR:
1. Belirsiz integralde +C unutmak
2. Kısmi integralde u ve dv seçimini yanlış yapmak
3. Trigonometrik ikamede sınır değiştirmeyi unutmak
4. p-serisi testinde p≤1 ile p>1 karıştırmak
5. Oran testinde limit alırken işaret hatası
"""


# ═══════════════════════════════════════════
# KALKÜLÜS 3
# ═══════════════════════════════════════════

KALKULUS_3 = """
═══ KALKÜLÜS 3 — UZMAN NOTLARI ═══

▸ KISMİ TÜREVLER:
- ∂f/∂x: y'yi sabit tut, x'e göre türev al
- ∂f/∂y: x'i sabit tut, y'ye göre türev al
- Karışık türev: ∂²f/∂x∂y = ∂²f/∂y∂x (Clairaut teoremi)

▸ GRADIENT, DIVERGENS, ROTASYONEL:
- Gradient: ∇f = (∂f/∂x, ∂f/∂y, ∂f/∂z) — VEKTÖR sonucu
- Divergens: ∇·F = ∂F₁/∂x + ∂F₂/∂y + ∂F₃/∂z — SKALER sonucu
- Rotasyonel: ∇×F = |i j k; ∂x ∂y ∂z; F₁ F₂ F₃| — VEKTÖR sonucu

▸ YÖNLÜ TÜREV:
D_û f = ∇f · û (û birim vektör olmalı!)
En büyük artış yönü: ∇f yönünde
En büyük değer: |∇f|

▸ ÇOK DEĞİŞKENLİ EKSTREMUM:
1. Kritik noktalar: ∇f = 0
2. İkinci türev testi: D = fₓₓ·f_yy - (fₓy)²
   • D>0 ve fₓₓ>0: yerel minimum
   • D>0 ve fₓₓ<0: yerel maksimum
   • D<0: eyer noktası
   • D=0: test başarısız

▸ LAGRANGE ÇARPANLARI:
g(x,y)=k kısıtı altında f(x,y) ekstremumları için:
∇f = λ·∇g denklemini çöz

▸ ÇİFT KATLI İNTEGRAL:
- Dikdörtgen bölge: ∫∫ f(x,y) dA = ∫[c,d]∫[a,b] f(x,y)dx dy
- Genel bölge tip 1 (y için sınır): ∫[a,b]∫[g₁(x),g₂(x)] f dy dx
- Genel bölge tip 2 (x için sınır): ∫[c,d]∫[h₁(y),h₂(y)] f dx dy

▸ KUTUPSAL KOORDİNATLAR (ÇOK ÖNEMLİ!):
- x = r·cos(θ), y = r·sin(θ)
- dA = r·dr·dθ — JACOBİ ÇARPANI 'r'Yİ ASLA UNUTMA!
- x² + y² = r²
- Daire x²+y²≤a²: 0≤r≤a, 0≤θ≤2π

▸ ÜÇLÜ KATLI İNTEGRAL:
- Silindirik: (r, θ, z), dV = r·dr·dθ·dz
- Küresel: (ρ, φ, θ), dV = ρ²·sin(φ)·dρ·dφ·dθ
   - φ: yukarıdan açı (0 ≤ φ ≤ π)
   - θ: yatay açı (0 ≤ θ ≤ 2π)

▸ JACOBİ DETERMİNANTI:
Değişken değiştirmede: dA = |J|·du·dv
J = |∂(x,y)/∂(u,v)| determinant

▸ ÇİZGİ İNTEGRALLERİ:
- Skaler: ∫_C f ds = ∫[a,b] f(r(t))·|r'(t)|dt
- Vektörel: ∫_C F·dr = ∫[a,b] F(r(t))·r'(t)dt

▸ TEMEL TEOREMLER (KARIŞTIRMAMAK İÇİN):

1. GREEN TEOREMİ (2D):
   ∮_C (P dx + Q dy) = ∫∫_D (∂Q/∂x - ∂P/∂y) dA
   Kapalı eğri etrafındaki integrali alana çevirir.

2. STOKES TEOREMİ (3D):
   ∮_C F·dr = ∫∫_S (∇×F)·dS
   Kapalı eğri integralini yüzey integraline çevirir.

3. DİVERGENS TEOREMİ (3D):
   ∯_S F·dS = ∭_V (∇·F) dV
   Kapalı yüzey integralini hacim integraline çevirir.

▸ TİPİK HATALAR:
1. Kutupsal/silindirik integrde 'r' (Jacobi) çarpanını unutmak — ÇOK YAYGIN!
2. Küresel integralinde sin(φ) çarpanını unutmak
3. İntegrasyon sınırlarını ters yazmak
4. Stokes ve Divergens teoremlerini karıştırmak
5. Yön (orientation) belirtmemek - kapalı eğrilerde yön önemli
"""


# ═══════════════════════════════════════════
# LİNEER CEBİR
# ═══════════════════════════════════════════

LINEER_CEBIR = """
═══ LİNEER CEBİR — UZMAN NOTLARI ═══

▸ MATRİSLER:
- Toplama: aynı boyutlu matrisler, eleman-eleman
- Çarpma: A(m×n) · B(n×p) = C(m×p). İç boyutlar eşleşmeli!
- AB ≠ BA genelde (komütatif değil)
- Transpoze: (AB)ᵀ = BᵀAᵀ (sıra DEĞİŞİR)
- İnvers: (AB)⁻¹ = B⁻¹A⁻¹ (sıra DEĞİŞİR)

▸ DETERMİNANT HESAPLAMA:
- 2x2: ad - bc
- 3x3: Sarrus kuralı veya kofaktör açılımı
- n×n: Kofaktör açılımı, satır/sütun seçilebilir
- Özellikler:
  - det(AB) = det(A)·det(B)
  - det(Aᵀ) = det(A)
  - det(A⁻¹) = 1/det(A)
  - Bir satır 0 ise det = 0
  - İki satır eşitse det = 0

▸ İNVERS HESAPLAMA:
- 2x2 için: A⁻¹ = (1/det) · [[d,-b],[-c,a]]
- Genel: A⁻¹ = (1/det) · adj(A)
- Gauss-Jordan: [A|I] → [I|A⁻¹]

▸ LİNEER DENKLEM SİSTEMLERİ:
- Ax = b formunda
- det(A) ≠ 0 ise tek çözüm (Cramer kuralı)
- Gauss eliminasyonu: satır işlemleri ile üst üçgen forma getir
- Echelon form (basamak formu)

▸ ÖZDEĞER VE ÖZVEKTÖRLER:
- Av = λv (v ≠ 0)
- Karakteristik denklem: det(A - λI) = 0
- Özvektör: (A - λI)v = 0 denklemini çöz
- n×n matrisin (kompleks dahil) n özdeğeri vardır
- İz (trace) = özdeğerlerin toplamı
- det = özdeğerlerin çarpımı

▸ KÖŞEGENLEŞTİRME:
A = PDP⁻¹
P: özvektör matrisi (sütunlar)
D: köşegen üzerinde özdeğerler

▸ VEKTÖR UZAYLARI:
Aksiyomlar (kapalılık, birim, ters, vs.)
- Lineer bağımsızlık: c₁v₁+...+cₙvₙ = 0 sadece cᵢ=0 için
- Taban: lineer bağımsız ve üretici küme
- Boyut: tabandaki vektör sayısı
- Rank: lineer bağımsız satır/sütun sayısı
- Nullity: Av=0 çözüm uzayının boyutu
- Rank-Nullity teoremi: rank(A) + nullity(A) = n (sütun sayısı)

▸ İÇ ÇARPIM UZAYI:
- ⟨u,v⟩ = u·v = u₁v₁ + u₂v₂ + ... 
- ||v|| = √⟨v,v⟩
- Cosθ = ⟨u,v⟩/(||u||·||v||)
- Ortogonal: ⟨u,v⟩ = 0
- Gram-Schmidt: ortogonal taban inşası

▸ TİPİK HATALAR:
1. Matris çarpımında boyut uyumsuzluğu
2. Determinant hesabında işaret hataları (kofaktör açılımı)
3. Özdeğer bulurken karakteristik polinom yanlış yazmak
4. Köşegenleştirme için P matrisini özvektörlerden yanlış kurmak
5. Transpoze ve invers'i sıraya dikkat etmemek
"""


# ═══════════════════════════════════════════
# DİFERANSİYEL DENKLEMLER
# ═══════════════════════════════════════════

DIFERANSIYEL_DENKLEMLER = """
═══ DİFERANSİYEL DENKLEMLER — UZMAN NOTLARI ═══

▸ BİRİNCİ DERECEDEN ODE'LER:

1. AYRIK DEĞİŞKENLİ:
   dy/dx = f(x)g(y) → dy/g(y) = f(x)dx
   Her iki tarafı integralle.

2. LİNEER 1. DERECE:
   y' + P(x)y = Q(x)
   İntegral çarpanı: μ(x) = e^(∫P(x)dx)
   Çözüm: y = (1/μ)·∫μQ dx

3. TAM (EXACT) DİFERANSİYEL:
   M(x,y)dx + N(x,y)dy = 0
   ∂M/∂y = ∂N/∂x ise tamdır
   Çözüm: F(x,y) = c (F'in kısmi türevleri M ve N)

4. BERNOULLI:
   y' + P(x)y = Q(x)yⁿ
   v = y^(1-n) dönüşümü ile lineerleştir

▸ İKİNCİ DERECEDEN LİNEER ODE'LER:

ay'' + by' + cy = f(x)

KARAKTERİSTİK DENKLEM: ar² + br + c = 0

3 DURUM:
- Δ = b²-4ac > 0 (iki farklı reel kök r₁, r₂):
  y_h = C₁e^(r₁x) + C₂e^(r₂x)

- Δ = 0 (çift kök r):
  y_h = (C₁ + C₂x)e^(rx)

- Δ < 0 (karmaşık kökler α ± βi):
  y_h = e^(αx)(C₁cos(βx) + C₂sin(βx))

▸ ÖZEL ÇÖZÜM (Belirsiz Katsayılar Yöntemi):
Eğer f(x) =
- Polinom → y_p = polinom (aynı dereceden)
- e^(kx) → y_p = Ae^(kx)
- sin/cos → y_p = A·sin + B·cos
- Çakışma varsa x ile çarp

GENEL ÇÖZÜM: y = y_h + y_p

▸ LAPLACE DÖNÜŞÜMÜ:

L{f(t)} = F(s) = ∫₀^∞ f(t)e^(-st) dt

ÖNEMLİ DÖNÜŞÜMLER:
- L{1} = 1/s
- L{tⁿ} = n!/s^(n+1)
- L{e^(at)} = 1/(s-a)
- L{sin(at)} = a/(s²+a²)
- L{cos(at)} = s/(s²+a²)
- L{f'(t)} = sF(s) - f(0)
- L{f''(t)} = s²F(s) - sf(0) - f'(0)

KULLANIM: Başlangıç değer problemlerinde
1. ODE'in Laplace dönüşümünü al
2. Y(s) için çöz
3. Ters Laplace ile y(t) bul

▸ WRONSKIAN:
İki çözümün lineer bağımsızlığını kontrol için:
W(y₁,y₂) = |y₁ y₂; y₁' y₂'| = y₁y₂' - y₂y₁'
W ≠ 0 ise lineer bağımsız

▸ TİPİK HATALAR:
1. İntegral çarpanı bulurken işaret hatası
2. Özel çözümde y_h ile çakışma kontrolünü unutmak
3. Karmaşık köklerde α (reel) ve β (imajiner) kısmını karıştırmak
4. Laplace'te başlangıç koşullarını yerleştirmeyi unutmak
5. Tam diferansiyel testinde kısmi türevleri ters almak
"""


# ═══════════════════════════════════════════
# OLASILIK VE İSTATİSTİK
# ═══════════════════════════════════════════

OLASILIK_ISTATISTIK = """
═══ OLASILIK VE İSTATİSTİK — UZMAN NOTLARI ═══

▸ TEMEL KAVRAMLAR:
- Örnek uzay (S): tüm olası sonuçlar
- Olay (A): örnek uzayın alt kümesi
- P(A) = |A|/|S| (eşit olasılıklı sonuçlar)
- 0 ≤ P(A) ≤ 1

▸ TEMEL FORMÜLLER:
- P(A∪B) = P(A) + P(B) - P(A∩B)
- P(A^c) = 1 - P(A)
- Bağımsız olaylar: P(A∩B) = P(A)·P(B)
- Koşullu: P(A|B) = P(A∩B)/P(B)

▸ BAYES TEOREMİ (ÇOK ÖNEMLİ):
P(A|B) = P(B|A)·P(A) / P(B)

Toplam olasılık: P(B) = Σ P(B|Aᵢ)·P(Aᵢ)

▸ PERMÜTASYON VE KOMBİNASYON:
- Permütasyon: P(n,r) = n!/(n-r)!  (sıralı seçim)
- Kombinasyon: C(n,r) = n!/[r!(n-r)!]  (sırasız seçim)
- Tekrarlı permütasyon: n^r
- n! = n·(n-1)·...·1, 0! = 1

▸ KESİKLİ DAĞILIMLAR:

1. BERNOULLI: X = {0, 1}
   P(X=1) = p, P(X=0) = 1-p
   E(X) = p, Var(X) = p(1-p)

2. BİNOM: n bağımsız Bernoulli denemesi
   P(X=k) = C(n,k)·p^k·(1-p)^(n-k)
   E(X) = np, Var(X) = np(1-p)

3. POISSON: nadir olaylar
   P(X=k) = (λ^k · e^(-λ)) / k!
   E(X) = λ, Var(X) = λ

4. GEOMETRİK: ilk başarıya kadar
   P(X=k) = (1-p)^(k-1)·p
   E(X) = 1/p, Var(X) = (1-p)/p²

▸ SÜREKLİ DAĞILIMLAR:

1. ÜNİFORM [a,b]:
   f(x) = 1/(b-a)
   E(X) = (a+b)/2, Var(X) = (b-a)²/12

2. NORMAL (GAUSS) N(μ, σ²):
   f(x) = (1/√(2πσ²))·exp(-(x-μ)²/(2σ²))
   E(X) = μ, Var(X) = σ²
   Standardizasyon: Z = (X-μ)/σ ~ N(0,1)

3. ÜSTEL: Exp(λ)
   f(x) = λ·e^(-λx), x ≥ 0
   E(X) = 1/λ, Var(X) = 1/λ²
   Hafızasızlık özelliği

▸ BEKLENTI VE VARYANS:
- E(aX + b) = a·E(X) + b
- Var(aX + b) = a²·Var(X)
- Var(X) = E(X²) - [E(X)]²
- Bağımsız X, Y için: Var(X+Y) = Var(X) + Var(Y)
- Cov(X,Y) = E(XY) - E(X)·E(Y)

▸ MERKEZİ LİMİT TEOREMİ:
n büyük olduğunda, X̄ = (X₁+...+Xₙ)/n yaklaşık N(μ, σ²/n) dağılır
(orijinal dağılım ne olursa olsun!)

▸ HİPOTEZ TESTİ:
- H₀ (sıfır hipotezi) vs H₁ (alternatif)
- Tip 1 hata (α): H₀ doğru iken reddetmek
- Tip 2 hata (β): H₀ yanlış iken kabul etmek
- p-değeri: H₀ altında gözlenen veya daha aşırı sonucun olasılığı
- p < α ise H₀ reddedilir

▸ GÜVEN ARALIĞI:
%(1-α) güven aralığı: X̄ ± z_(α/2) · σ/√n

▸ TİPİK HATALAR:
1. P(A|B) ile P(B|A) karıştırmak (Bayes)
2. Bağımsız vs ayrık olayları karıştırmak
3. Permütasyon ve kombinasyon karışıklığı
4. Var(X+Y) için bağımsızlığı kontrol etmemek
5. p-değerini yanlış yorumlamak (H₀'ın olasılığı DEĞİL!)
"""