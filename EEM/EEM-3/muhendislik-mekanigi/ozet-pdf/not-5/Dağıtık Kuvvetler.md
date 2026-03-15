# Dağıtık Kuvvetler

## İçindekiler
- [Genel Özet](#genel-özet)
- [Temel Terimler ve Kavramlar](#temel-terimler-ve-kavramlar)
- [Ana Gövde: Kronolojik veya Tematik Kayıt](#ana-gövde-kronolojik-veya-tematik-kayıt)
  - [Ağırlık Merkezi, Kütle Merkezi ve Geometrik Merkez (Centroid)](#ağırlık-merkezi-kütle-merkezi-ve-geometrik-merkez-centroid)
  - [Kirişlerde Dış ve İç Etkiler](#kirişlerde-dış-ve-iç-etkiler)
  - [Bileşik Teknikler](#bileşik-teknikler)
- [Temel Formüller ve Hızlı Bilgiler](#temel-formüller-ve-hızlı-bilgiler)
- [Kaynaklar](#kaynaklar)

---

## Genel Özet

Dağıtık kuvvetler, mühendislik mekaniğinde kuvvetin tek bir noktaya değil, bir **çizgi**, **alan** veya **hacim** boyunca yayıldığı durumları inceler. Bu kavram, **ağırlık merkezi**, **kütle merkezi** ve **centroid** (geometrik merkez) gibi temel noktaların belirlenmesini sağlar. Bu noktalar, bir cismin dengesi, kirişlerde gerilme analizi ve yapısal tasarım gibi pek çok mühendislik uygulaması için hayati öneme sahiptir.

Belgelerde yer alan içerik, **Meriam ve Kraige**’nin klasik mühendislik mekaniği yaklaşımını temel alarak, **entegrasyon** ve **bileşik alan/hacim** yöntemleriyle centroid ve kütle merkezi hesaplamalarını adım adım açıklamaktadır. Ayrıca **kiriş** analizinde **kesme kuvveti** (shear) ve **eğilme momenti** (bending moment) diyagramlarının çizimi, dağıtık yüklerin eşdeğer tekil kuvvetlere dönüştürülmesi gibi konular detaylı örneklerle işlenmiştir. Tüm bu konular, **statik dengenin sağlanması** ve **yapısal bütünlüğün analizi** açısından temel bilgiler sunar.

---

## Temel Terimler ve Kavramlar

- **Ağırlık Merkezi**: Bir cismin ağırlığının toplandığı nokta; yerçekimi alanının etkisiyle tanımlanır.
- **Kütle Merkezi**: Bir cismin kütlesinin dengede olduğu nokta; yerçekimi ivmesinin sabit kabul edildiği durumlarda ağırlık merkeziyle çakışıktır.
- **Centroid**: Bir geometrik şeklin yalnızca **geometrisine** bağlı olarak belirlenen merkezidir; yoğunluk veya kütle dağılımı dikkate alınmaz.
- **Dağıtık Yük**: Kuvvetin bir alana, çizgiye veya hacme yayılması; örnek: su basıncı, kablo ağırlığı.
- **Kesme Kuvveti (V)**: Kirişin enine kesitinde oluşan, parçaları birbiri üzerinden kaydırmaya çalışan iç kuvvet.
- **Eğilme Momenti (M)**: Kirişi eğilmeye zorlayan iç moment; diyagramda maksimum değeri genellikle kesme kuvvetinin sıfır olduğu noktada görülür.
- **Bileşik Teknik**: Karmaşık şekillerin, basit geometrik parçalara bölünerek centroid veya kütle merkezinin hesaplanması yöntemi.
- **Eşdeğer Tekil Kuvvet**: Dağıtık bir yükün toplam etkisini temsil eden, alanın **centroid**’ında etkiyen tek bir kuvvet.

---

## Ana Gövde: Kronolojik veya Tematik Kayıt

### Ağırlık Merkezi, Kütle Merkezi ve Geometrik Merkez (Centroid)

#### Ağırlık Merkezi
Bir cismin ağırlık merkezi koordinatları aşağıdaki gibi hesaplanır:

```math
\bar{x} = \frac{\int x \, dW}{W}, \quad \bar{y} = \frac{\int y \, dW}{W}, \quad \bar{z} = \frac{\int z \, dW}{W}
```

Burada \( dW \) ağırlığın sonsuz küçük bir parçası, \( W = \int dW \) ise toplam ağırlıktır.

#### Kütle Merkezi
Yerçekimi ivmesi \( g \) sabit ise:

```math
\bar{x} = \frac{\int x \, dm}{m}, \quad \bar{y} = \frac{\int y \, dm}{m}, \quad \bar{z} = \frac{\int z \, dm}{m}
```

#### Centroid
Yoğunluk sabit olduğunda, centroid yalnızca geometriye bağlıdır:

- **Hacim için:**
  ```math
  \bar{x} = \frac{\int x \, dV}{V}, \quad \bar{y} = \frac{\int y \, dV}{V}, \quad \bar{z} = \frac{\int z \, dV}{V}
  ```
- **Alan için:**
  ```math
  \bar{x} = \frac{\int x \, dA}{A}, \quad \bar{y} = \frac{\int y \, dA}{A}
  ```
- **Çizgi için:**
  ```math
  \bar{x} = \frac{\int x \, dL}{L}, \quad \bar{y} = \frac{\int y \, dL}{L}
  ```

>[!infobox] 
>![img-12.jpeg](img-12.jpeg|300)  
>Yarım alüminyum, yarım çelik disk örneğinde **centroid** geometrik merkezdeyken, **kütle merkezi** çelik tarafına kayar.

#### İntegrasyon İpuçları
1. Düşük mertebeden elemanlar tercih edin (tek katlı integral yeterliyse).
2. Eleman seçimi, sürekli tek integralle çözüm sağlayacak şekilde olmalı.
3. İntegraldeki \( x, y \) terimleri, seçilen elemanın **kendi centroid koordinatlarıdır** → \( x_c, y_c \).

**Örnek**:  
\( y = 3x^2 \) eğrisi altında \( 0 \leq x \leq 4 \) aralığındaki alanın centroidu:

```math
\bar{y} = \frac{\int y_c \, dA}{\int dA} = \frac{\int_0^4 \frac{y}{2} \cdot y \, dx}{\int_0^4 y \, dx} = \frac{72}{5}, \quad \bar{x} = \frac{\int_0^4 x \cdot y \, dx}{\int_0^4 y \, dx} = 3
```

---

### Bileşik Teknikler

Karmaşık şekiller, bilinen basit geometrik parçalara ayrılır. "Delikler" **negatif alan/hacim** olarak kabul edilir.

**Örnek**: Gövdedeki delikli alanın centroidu:

| Parça | A (in²) | x (in) | y (in) | xA (in³) | yA (in³) |
|-------|--------|--------|--------|----------|----------|
| 1     | 120    | 6      | 5      | 720      | 600      |
| 2     | 30     | 14     | 10/3   | 420      | 100      |
| 3     | -14.14 | 6      | 1.273  | -84.8    | -18      |
| 4     | -8     | 12     | 4      | -96      | -32      |
| **Toplam** | **127.9** |        |        | **959**  | **650**  |

```math
\bar{X} = \frac{959}{127.9} = 7.50 \text{ in}, \quad \bar{Y} = \frac{650}{127.9} = 5.08 \text{ in}
```

---

### Kirişlerde Dış ve İç Etkiler

#### Dış Etkiler
Dağıtık yükün **eşdeğer tekil kuvveti**:
- **Büyüklük** = Yük eğrisi altındaki **alan**.
- **Konum** = Bu alanın **centroid**’ı.

**Örnek**: Dikdörtgen + üçgen yük dağılımı → \( R_1 = 1200 \text{ lb}, R_2 = 480 \text{ lb} \).  
Mesnet tepkileri:
```math
R_A = 696 \text{ lb}, \quad R_B = 984 \text{ lb}
```

#### İç Etkiler: Kesme Kuvveti ve Eğilme Momenti

**Temel İlişkiler**:
```math
w = -\frac{dV}{dx}, \quad V = \frac{dM}{dx}, \quad \frac{d^2M}{dx^2} = -w
```

**İşaret Kabulleri**:
- **Pozitif kesme**: Elemanı **saat yönünde** döndürür.
- **Pozitif moment**: Kirişi **çukur yukarı** (su tutar) şekilde eğer.

**Örnek**: 4-kN tekil yük etkisindeki basit mesnetli kiriş:
- \( 0 < x < 6 \): \( V = 1.6 \text{ kN}, M = 1.6x \)
- \( 6 < x < 10 \): \( V = -2.4 \text{ kN}, M = 2.4(10 - x) \)

>[!note]
>Maksimum eğilme momenti, **kesme kuvvetinin sıfır olduğu noktada** oluşur.

---

## Temel Formüller ve Hızlı Bilgiler

### Centroid Formülleri (Temel Şekiller)
| Şekil | Alan/Hacim | \( \bar{x} \) | \( \bar{y} \) |
|-------|------------|---------------|---------------|
| **Üçgen** | \( \frac{1}{2}bh \) | \( \frac{b}{3} \) | \( \frac{h}{3} \) |
| **Yarım Daire** | \( \frac{1}{2}\pi r^2 \) | 0 | \( \frac{4r}{3\pi} \) |
| **Çeyrek Elips** | \( \frac{1}{4}\pi ab \) | \( \frac{4a}{3\pi} \) | \( \frac{4b}{3\pi} \) |
| **Parabolik Segment** | \( \frac{2}{3}bh \) | \( \frac{3}{8}b \) | \( \frac{2}{5}h \) |

### Kiriş Analizi Kuralları
- Dağıtık yükün eşdeğeri → **alan** ve **centroid**.
- Kesme diyagramı eğimi → **–yük şiddeti**.
- Moment diyagramı eğimi → **kesme kuvveti**.
- Moment diyagramı altındaki alan → **kesme kuvveti değişimini vermez**; tersi geçerlidir.

### Bileşik Alan/Hacim Hesabı
```math
\bar{X} = \frac{\sum A_i x_i}{\sum A_i}, \quad \bar{Y} = \frac{\sum A_i y_i}{\sum A_i}
```
> Delikler için \( A_i \) **negatif** alınır.

---

## Kaynaklar

Kaynak bulunamadı.