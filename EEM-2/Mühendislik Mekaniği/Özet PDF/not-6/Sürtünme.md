# Engineering Mechanics – Friction Study Guide  
**Based on: Meriam & Kraige, 6th Edition**  
*Compiled by Dr. Yusuf YILMAZ – Mechanical Engineering Department, Konya, Türkiye*

---

## İçindekiler (Table of Contents)

- [Genel Özet](#genel-özet)
- [Temel Terimler ve Kavramlar](#temel-terimler-ve-kavramlar)
- [Ana Gövde: Kronolojik Kayıt](#ana-gövde-kronolojik-kayıt)
  - [Kuru (Coulomb) Sürtünme](#kuru-coulomb-sürtünme)
    - [Statik ve Kinetik Sürtünme](#statik-ve-kinetik-sürtünme)
    - [Örnek 1: Eğik Düzlemde Blok](#örnek-1-eğik-düzlemde-blok)
    - [Örnek 2: Silindir ve Moment](#örnek-2-silindir-ve-moment)
  - [Kayış Sürtünmesi (Belt Friction)](#kayış-sürtünmesi-belt-friction)
    - [Euler-Eytelwein Denklemi](#euler-eytelwein-denklemi)
    - [Örnek: Silindirin Yükseltilmesi ve İndirilmesi](#örnek-silindirin-yükseltilmesi-ve-indirilmesi)
- [Temel Formüller ve Hızlı Bilgiler](#temel-formüller-ve-hızlı-bilgiler)
- [Kaynaklar](#kaynaklar)

---

## Genel Özet

Bu ders notu, **mühendislik mekaniğinin sürtünme** (friction) konusunu detaylı şekilde ele alır. İki ana başlık altında incelenir:  
1. **Kuru (Coulomb) Sürtünme**: Sürtünme kuvvetinin statik ve kinetik davranışları, sürtünme katsayıları ve denge/sürtünme denklemleri.  
2. **Kayış Sürtünmesi**: Esnek kayışların sabit silindir etrafında sarılması durumunda oluşan gerilme farkı ve Euler-Eytelwein formülü.

Öğrencilerin en sık yaptığı hata, sürtünme kuvvetini her zaman maksimum değeriyle (µ<sub>s</sub>N) almasıdır. Oysa sürtünme kuvveti, denge durumunda **0 ile F<sub>max</sub> arasında herhangi bir değer** alabilir. Analiz üç kategoriye ayrılır:
- Kayma başlangıcı (impending motion): **F = µ<sub>s</sub>N**
- Kayma yok (statik denge): **F < µ<sub>s</sub>N** → F denge eşitliklerinden bulunur.
- Kayma var (kinetik): **F = µ<sub>k</sub>N**

---

## Temel Terimler ve Kavramlar

- **Kuru Sürtünme **(Dry Friction): İki katı yüzey arasında, göreceli harekete karşı direnç oluşturan teğetsel kuvvet.
- **Statik Sürtünme Katsayısı **(µ<sub>s</sub>): Hareket başlamadan hemen önceki maksimum sürtünme kuvvetini belirleyen boyutsuz sabit.
- **Kinetik Sürtünme Katsayısı **(µ<sub>k</sub>): Hareket sırasında etkin olan sürtünme katsayısı; genellikle µ<sub>s</sub>’den küçüktür.
- **Maksimum Sürtünme Kuvveti **(F<sub>max</sub>): F<sub>max</sub> = µ<sub>s</sub>N; bu değerin aşılması durumunda kayma başlar.
- **Kayış Sürtünmesi**: Esnek bir kordonun sabit bir tambur etrafında sarılmasıyla, iki uç geriliminin farklılaşması.
- **Sarım Açısı **(β): Kayışın tambur ile temas ettiği toplam açı (radyan cinsinden).
- **Euler-Eytelwein Denklemi**: T<sub>2</sub>/T<sub>1</sub> = e<sup>µβ</sup>, burada T<sub>2</sub> > T<sub>1</sub>.

---

## Ana Gövde: Kronolojik Kayıt

### Kuru (Coulomb) Sürtünme

Gerçek yüzeyler arasında, harekete karşı direnç oluşturan **sürtünme kuvveti **(F) doğar. Bu kuvvet, yüzeye dik olan **normal kuvvet **(N) ile orantılıdır.

#### Statik ve Kinetik Sürtünme

- **Statik Sürtünme**: Hareket yokken F, uygulanan kuvvete eşit ve zıt yönlüdür:  
  \[
  \sum F_x = 0 \Rightarrow P - F = 0 \Rightarrow F = P
  \]
  Ancak F, **F<sub>max</sub> = µ<sub>s</sub>N** değerini aşamaz.

- **Hareket Başlangıcı **(Impending Motion):  
  F = F<sub>max</sub> olduğunda hareket başlar.

- **Kinetik Sürtünme**: Hareket başladıktan sonra:  
  \[
  F_k = \mu_k N \quad (\mu_k < \mu_s)
  \]

> [!note]  
> Sürtünme analizinde üç durum vardır:
> 1. **Hareket başlangıcı biliniyorsa**: F = µ<sub>s</sub>N  
> 2. **Durum bilinmiyorsa**: F bilinmeyen olarak alınır; sonra F<sub>max</sub> ile karşılaştırılır.  
> 3. **Kayma varsa**: F = µ<sub>k</sub>N

#### Örnek 1: Eğik Düzlemde Blok

**Verilenler**:
- Kütle: 100 kg → Ağırlık = 981 N  
- µ<sub>s</sub> = 0.20, µ<sub>k</sub> = 0.17  
- Eğim açısı: 20°  
- (a) P = 500 N, (b) P = 100 N

##### (a) P = 500 N

Denge denklemleri:
\[
\begin{aligned}
\sum F_x &= 0: & 500 \cos 20^\circ + F - 981 \sin 20^\circ &= 0 \\
\sum F_y &= 0: & N - 500 \sin 20^\circ - 981 \cos 20^\circ &= 0
\end{aligned}
\]

**Çözüm**:
- F = -134.3 N → **134.3 N aşağı yönlü**  
- N = 1093 N  
- F<sub>max</sub> = 0.20 × 1093 = **219 N**

> [!success]  
> |F| = 134.3 N < F<sub>max</sub> → **Denge sağlanır**.  
> Cevap: **134.3 N, eğim aşağı**

##### (b) P = 100 N

Denge denklemleri:
\[
\begin{aligned}
\sum F_x &= 0: & 100 \cos 20^\circ + F - 981 \sin 20^\circ &= 0 \\
\sum F_y &= 0: & N - 100 \sin 20^\circ - 981 \cos 20^\circ &= 0
\end{aligned}
\]

**Çözüm**:
- F = **+242 N** (yukarı yönlü, varsayılan yön doğru)  
- N = 956 N  
- F<sub>max</sub> = 0.20 × 956 = **191.2 N**

> [!warning]  
> F = 242 N > F<sub>max</sub> → **Denge bozulur, blok kayar**.  
> Gerçek sürtünme: F = µ<sub>k</sub>N = 0.17 × 956 = **162.5 N**  
> Cevap: **162.5 N, eğim yukarı** (kayma aşağı yönlü olduğundan sürtünme buna karşı)

#### Örnek 2: Silindir ve Moment

**Verilenler**:
- Kütle = 30 kg → Ağırlık = 294 N  
- Çap = 400 mm → Yarıçap = 0.2 m  
- µ<sub>s</sub> = 0.25 (tüm yüzeylerde)  
- Amaç: Kaymaya neden olan **M momentini** bulmak

**Serbest Cisim Diyagramı **(FBD):
- A noktasında: N<sub>A</sub>, F<sub>A</sub> = 0.25 N<sub>A</sub>  
- B noktasında: N<sub>B</sub>, F<sub>B</sub> = 0.25 N<sub>B</sub>  
- Açı: 30°

**Denge Denklemleri**:
\[
\begin{aligned}
\sum F_x &= 0: & N_B \sin 30^\circ + 0.25 N_B \cos 30^\circ - N_A &= 0 \\
\sum F_y &= 0: & N_B \cos 30^\circ - 0.25 N_B \sin 30^\circ + 0.25 N_A - 294 &= 0 \\
\sum M_G &= 0: & -M + 0.25 N_B (0.2) + 0.25 N_A (0.2) &= 0
\end{aligned}
\]

**Çözüm**:
- N<sub>A</sub> = 191.6 N  
- N<sub>B</sub> = 268 N  
- M = 0.25 × 0.2 × (268 + 191.6) = **22.9 N·m**

> [!example]+  
> Kayma, her iki yüzeyde eşzamanlı olarak başlar. Bu nedenle F = µ<sub>s</sub>N kullanılır.

---

### Kayış Sürtünmesi (Belt Friction)

Esnek bir kordonun sabit bir tambur etrafında sarılması durumunda, iki uçtaki gerilmeler farklı olabilir.

#### Euler-Eytelwein Denklemi

Tambur etrafında dθ’lik bir eleman için:
- Teğetsel denge: µ dN = dT  
- Normal denge: dN = T dθ  

Bu iki denklem birleştirilirse:
\[
\frac{dT}{T} = \mu \, d\theta
\]

İntegral alınır (T<sub>1</sub> → T<sub>2</sub>, θ = 0 → β):
\[
\int_{T_1}^{T_2} \frac{dT}{T} = \int_0^\beta \mu \, d\theta \Rightarrow \ln \left( \frac{T_2}{T_1} \right) = \mu \beta
\]

Sonuç:
\[
\boxed{ \frac{T_2}{T_1} = e^{\mu \beta} }
\]
- T<sub>2</sub>: **Büyük gerilme** (çekilen taraf)  
- T<sub>1</sub>: Küçük gerilme  
- β: **Radyan cinsinden** sarım açısı

#### Örnek: Silindirin Yükseltilmesi ve İndirilmesi

**Verilenler**:
- Kütle = 100 kg → Ağırlık = 981 N  
- µ = 0.30  
- Tambur yarım daire → β = π rad

##### (a) Silindir **yükseltilir** (hareket yukarı)

- T<sub>2</sub> = P (çekme kuvveti)  
- T<sub>1</sub> = 981 N  
\[
\frac{P}{981} = e^{0.3 \pi} \approx e^{0.942} \approx 2.566 \Rightarrow P = 981 \times 2.566 \approx \boxed{2520\ \text{N}}
\]

##### (b) Silindir **indirilir** (hareket aşağı)

- T<sub>2</sub> = 981 N  
- T<sub>1</sub> = P  
\[
\frac{981}{P} = e^{0.3 \pi} \Rightarrow P = \frac{981}{2.566} \approx \boxed{382.3\ \text{N}}
\]

> [!infobox]  
> ![[img-56.jpeg|400]]  
> *Kayış sürtünmesi uygulaması: Tambur çevresinde kordon*

---

## Temel Formüller ve Hızlı Bilgiler

> [!example]+ Sürtünme Formülleri
> - **Maksimum statik sürtünme**:  
>   \[
>   F_{\text{max}} = \mu_s N
>   \]
> - **Kinetik sürtünme**:  
>   \[
>   F_k = \mu_k N
>   \]
> - **Kayış sürtünmesi**:  
>   \[
>   \frac{T_2}{T_1} = e^{\mu \beta}, \quad \beta \text{ (radyan)}
>   \]

> [!note]  
> - µ<sub>k</sub> ≈ 0.75–0.90 µ<sub>s</sub>  
> - Sürtünme kuvveti **her zaman harekete zıt yönlüdür**.  
> - Eğik düzlemde:  
>   \[
>   \text{Ağırlık bileşenleri: } W \sin\theta \text{ (eğim aşağı)},\ W \cos\theta \text{ (normal)}
>   \]

---

## Kaynaklar

- Meriam, J. L., & Kraige, L. G. (2007). *Engineering Mechanics: Statics* (6th Edition). Wiley.  
- Ders Notları – Dr. Yusuf YILMAZ, Mechanical Engineering Department, Konya, Türkiye.