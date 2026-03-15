### Soru 1 (Sayfa 1)

> Matlab Simulink ortamında bir sinyalin zamana göre değişimini gözlemlemek istersek hangi bloğu kullanmalıyız?
>
> Lütfen birini seçin:

* a. Time Analyzer
* b. Logic Analyzer
* **c. Scope**
* d. Radar
* e. Logic Probe

-----

### Soru 2 (Sayfa 2)

> Matlab'de $p(x)=x^{2}+x$ polinomunun 1'den 3'e kadar x değerleri için çözümü aşağıdakilerden hangisi ile bulunabilir?
>
> Lütfen birini seçin:

* a. `a=1-3; polyval([1 0 1 0],a);`
* b. `x=1-3; polyval([1 0 1 0],x)`
* c. `polyval([1 1 0],1:3)` (Tahmin: 1.3 yerine 1:3)
* d. `polyval(x,1:3); x=[1 0 1 0]`
* e. `polyval([1 0 1 0],1:3)` (Tahmin: 1.3 yerine 1:3)

-----

### Soru 3 (Sayfa 3)

> MATLAB' de $V=[5 \ 6 \ 7 \ 8 \ 9 \ 10]$ vektörünü oluşturmak için aşağıda[kilerden hangisi kullanılamaz?] (Tahmin: Soru kökü eksik)
>
> Lütfen birini seçin:

* a. `V=[5,6,7,8,9,10]`
* b. `V=[5:1:10]`
* c. `v=linspace(5,10,6)`
* d. `V=[5 6 7 8 9 10]`
* e. `V=['5:10']`

-----

### Soru 4 (Sayfa 4)

> $A=[\begin{matrix}2&-7&9\\ 7&4&8\\ 5&6&-3\end{matrix}]$
>
> Yukarıda verilen A matrisinin Matlab'de "A" değişkeni ile [tanımlandığı biliniyor. (Soru ifadesi eksik. Tahmin: Sayfa 17'deki gibi A(1, :) \* A(:, 2) )] ifadesinin üreteceği sonuç aşağıdakilerden hangisidir?
>
> Lütfen birini seçin:

* a. [14 28 40]
* b. 82
* c. 58
* d. 12
* e. [14 -28 72]

*(Not: Sayfa 5'te `>> A(2:3,1:2)'` komutu ve sonucu `ans = 7 5 4 6` görünmektedir, ancak bu Sayfa 4'teki seçeneklerle eşleşmemektedir.)*

-----

### Soru 5 (Sayfa 6)

> $p(x)=2x^{4}-4x^{2}+10x-3$ polinomunu ifade etmek için Matlab'de aşağıdaki de[ğişkenlerden hangisi kullanılabilir?]
>
> Lütfen birini seçin:

* a. `p1=[2 -4 10 -3];`
* b. `p1=[4 -2 10 -1];`
* c. `p2=[2 0 -4 10 -3];`
* d. `p2=[1 0 -1 2 -3];`
* e. `p1=[8 0 -8 10 0];`

-----

### Soru 6 (Sayfa 7)

> İki polinom fonksiyonu p1 $=[2 \ 4 \ 5]$ ve $p2=[3 \ -5 \ 7]$ olarak tanım[lanmıştır. Bu iki polinomun çarpımını bulmak için hangi kod kullanılır?]
>
> Lütfen birini seçin:

* a. `p1*p2`
* b. hiçbiri
* c. `deconv(p1,p2)`
* d. `p1.*p2`
* e. `conv(p1,p2)`

-----

### Soru 7 (Sayfa 8)

> Matlab'de A=[1 2; 2 5] ve B=[-1 3; 4 2] olarak tanımlanmıştır. $B.^{*}(A^{\prime})$ işleminin sonucu aşağıdakilerden hangisi ile [aynıdır?]
>
> Lütfen birini seçin:

*(Seçenekler okunamayacak kadar bozuk.)*

-----

### Soru 8 (Sayfa 9)

> MATLAB'de blok diyagramlar kullanarak bir sistemi modellemek istersek aşağıdakilerden hangisini yapmalıyız?
>
> Lütfen birini seçin:

* a. Simulink butonu tıklanmalıdır.
* b. Komut penceresine "Model Block Diagram" komutu yazılmalıdır.
* c. Model butonu tıklanmalıdır.
* d. Komut penceresine "Simulink Block Diagram" komutu yazılmalıdır.
* e. Komut penceresine "Start Block Diagram" komutu yazılmalıdır.

-----

### Soru 9 (Sayfa 10)

> MATLAB komut satırına `>> 1e3 + 3` yazıldığında çıktı ne olur?
>
> Lütfen birini seçin:

* a. 1000000
* b. 4
* c. 1
* d. 3+3
* e. 1003

-----

### Soru 10 (Sayfa 12)

> Yukarıdaki gibi 2 farklı grafiği üst üste tek pencerede çizdirebilmek için ihtiyaç duyula[n komut hangisidir?]
>
> Lütfen birini seçin:

* a. subfigure
* b. plot(6)
* c. subplot
* d. figure(6)
* e. hold on

-----

### Soru 11 (Sayfa 13)

> MATLAB' de ekrana "Merhaba" yazdırmak için aşağıdakilerden hangisini kullanabi[liriz?]
>
> Lütfen birini seçin:

* a. `show('Merhaba')`
* b. `printf('Merhaba')`
* c. `scanf('Merhaba')`
* d. `disp('Merhaba')`
* e. `output('Merhaba')`

-----

### Soru 12 (Sayfa 14)

> $B=[\begin{matrix}2&5&11\\ 0&7&8\\ -4&3&-5\end{matrix}]$
>
> Yukarıda verilen B matrisi Matlab'de tanımlandıktan sonra komut satırından $B(2,3)$, $B(2:5)$, $B(7)$, $B(2,:)$ değerleri hesaplanıyor.
>
> Hangisi bu işlemler sonucunda elde edilen sonuçlardan biri değildir?
>
> Lütfen birini seçin:

* a. [0 7 8]
* b. 11
* c. -4
* d. 8
* e. [0 -4 5 7] (Tahmin: `B(2:5)`'in çıktısı `[0; -4; 5; 7]` vektörüdür)

-----

### Soru 13 (Sayfa 15)

> $6+5i$ karmaşık ifadesi Matlab de aşağıdakilerden hangisi ile tanımlanamaz?
>
> Lütfen birini seçin:

* a. `6-(-5)^2`
* b. `6+i*5`
* c. `6+j*5`
* d. `6+5i`
* e. `6-(-5)i`

-----

### Soru 14 (Sayfa 16)

> $A=[\begin{matrix}2&-7&9\\ 7&4&8\\ 5&6&-3\end{matrix}]$
>
> $B=[\begin{matrix}7&5\\ 4&6\end{matrix}]$
>
> Yukarıda verilen A matrisinin Matlab'de "A" değişkeni ile tanımlandığı biliniyor. A matrisini kullanarak B matrisini elde etm[ek için hangi komut] kullanılabilir?
>
> Lütfen birini seçin:

* a. `B=A(1:2,2:3)`
* b. `B=A(2:3,1:2)'`
* c. `B=A(1:2,2:3)'`
* d. `B=inv(A(1:2,2:3))`
* e. `B=A'(1:2,2:3)`

-----

### Soru 15 (Sayfa 17)

> $A=[\begin{matrix}2&-7&9\\ 7&4&8\\ 5&6&-3\end{matrix}]$
>
> Yukarıda verilen A matrisinin Matlab'de "A" değişkeni ile tanımlandığı biliniyor.
>
> Buna göre komut satırına yazılan `A(1,:) * A(:,2)` (Tahmin: Metin okunamıyor, Sayfa 4'ten çıkarım) ifadesinin üreteceği sonuç aşağıdakilerden hangisidir?
>
> Lütfen birini seçin:

* a. 58
* b. [14 -28 72]
* c. 12
* d. [14 28 40]
* e. 82

-----

### Soru 16 (Sayfa 18)

> MATLAB' de değişkenlerin içeriğinin gösterildiği pencere aşağıda[kilerden hangisidir?]
>
> Lütfen birini seçin:

* a. Simulink
* b. Matlab Writer
* c. Workspace
* d. Code Writer
* e. Editor

-----

### Soru 17 (Sayfa 19)

> (GNO ve S/H tablosu)
>
> Yukarıda bir sınıftaki öğrencilerin haftalık ortalama çalışma saatlerine karşılık genel not ortalamaları verilmiştir.
>
> Bu iki veri baz alınarak 6.5 saat çalışmaya karşılık gelen not ortalamasını Matlab ile bulmak için kullanılabilecek interpolasyon yöntemleri arasında aşağıdakilerden hangisi yoktur?
>
> Lütfen birini seçin:

* a. Cubic
* b. Linear
* c. Nearest
* d. Spline
* e. interp1

-----

### Soru 18 (Sayfa 20)

> Resimdeki grafiğin (polar grafik) çizdirilebilmesi için verilen program parçasındaki noktalarla gösterilen yerde hangi komut kullanılmalıdı[r]?
>
> `t=[0: 0.01: 2*pi]`
>
> `y=cos(t)`
>
> [...]
>
> Lütfen birini seçin:

* a. polar
* b. graph
* c. `draw(t,y)`
* d. `graph(t,y)`
* e. `polar(t,y)` (Tahmin: `polar(ty)` yerine)

-----

### Soru 19 (Sayfa 21)

> MATLAB komut satırına `>> 3e2 + 2` yazıldığında çıktı ne olur?
>
> Lütfen birini seçin:

* a. 302
* b. 81
* c. 11
* d. 2,03
* e. $\sqrt{}+2$ (Okunamıyor)

-----

### Soru 20 (Sayfa 22)

> Matlab' de gerçekleştirilen `(2+3^2-sqrt(81)/2)*4+2^2+3` (Tahmin: Soru Sayfa 39 ile aynı) işleminin [sonucunun asal çarpanlarının bulunması için...] (Tahmin)
>
> Lütfen birini seçin:

* a. `primes(11)`
* b. `factor(33)`
* c. `factor(39)`
* d. `primes(33)`
* e. `factor(11)`

-----

### Soru 21 (Sayfa 23)

> MATLAB' de aşağıdaki komutlar sıra[sıyla çalıştırıldığında çıktı nasıl olur?]
>
> `>> x=6`
>
> `>> 6+2`
>
> Lütfen birini seçin:

* a. boşluk
* b. `x=8`
* c. error
* d. 8
* **e. `ans=8`**

-----

### Soru 22 (Sayfa 24)

> Aşağıdakilerden hangisi MATLAB'e uygun bir değişken ismidir?
>
> Lütfen birini seçin:

* a. `deger 1`
* b. `1deger` (Tahmin: `Ideger`)
* c. (Eksik) `debur 1` (Tahmin: 'd' şıkkı 'c' olmalı)
* d. `debur 1`
* e. `deger1`

-----

### Soru 23 (Sayfa 25)

> $ln(x) + arctan(x)$ matematiksel işleminin Matlab dilindeki karşılığı nedir?
>
> Lütfen birini seçin:

* a. `ln(x) + atan(x)`
* b. `ln(x) - atan(x)`
* c. `log(x) + arctan(x)`
* d. `log(x) + atan(x)`
* e. `ln(x) + arc tan(x)`

-----

### Soru 24 (Sayfa 26)

> $log_5(17)$ (Tahmin: log 17) matematiksel işleminin Matlab ile hesaplanabilmesi için kom[ut satırına ne yazılmalıdır?]
>
> Lütfen birini seçin:

* a. `log(5)/log(17)`
* b. `ln(17)/ln(5)`
* c. `log10(17)/log2(5)`
* d. `log10(5)/log10(17)`
* e. `log10(17)/log10(5)`

-----

### Soru 25 (Sayfa 27)

> Aşağıdakilerden hangisi M[ATLAB'de bir çizim komutu değildir?] (Tahmin)
>
> Lütfen birini seçin:

* a. fplot
* b. plot
* c. fbar
* d. pie
* e. bar

-----

### Soru 26 (Sayfa 28)

> MATLAB'de blok diyagramlar kullanarak bir sistemi modellemek istersek aşağıdakilerden hangisini yapmalıyız?
>
> Lütfen birini seçin:

* a. Model butonu tıklanmalıdır.
* b. Simulink butonu tıklanmalıdır.
* c. Komut penceresine "Start Block Diagram" komutu yazılmalıdır.
* d. Komut penceresine "Model Block Diagram" komutu yazılmalıdır.
* e. Komut penceresine "Simulink Block Diagram" komutu yazılmalıdır.

-----

### Soru 27 (Sayfa 29)

> Simulink'te kurulmuş olan devrede (Resimdeki R-C devresi) numaralandırılmış bloklardan hangisi çıkartılsa da sistem düzgün çalışmaya devam eder?
> (1: Constant, 2: Simulink-PS Converter, 3: Solver Configuration, 4: Converter (PS-Simulink) )
>
> Lütfen birini seçin:

* a. 1
* b. 2
* c. 4
* d. 3
* (Seçenek 'e' eksik)

-----

### Soru 28 (Sayfa 30)

> Simulink'te simülasyon belirli bir süre gerçekleşip simülasyon sonlanmaktadır. Bunun yerine simülasyonun sürekli çalışmaya devam etmesi için aşağıdakilerden hangisi yapılmalıdır?
>
> Lütfen birini seçin:

* a. Bitiş zamanına "inf" yazılmalıdır.
* b. Tasarım alanına "Never Stop" bloğu eklenmelidir.
* c. Tasarım alanına "Continuous" bloğu eklenmelidir.
* d. "Never stop" kutusu işaretlenmelidir.
* e. "Continuous" kutusu işaretlenmelidir.

-----

### Soru 29 (Sayfa 31)

> Şekilde Simulink'te sıklıkla kullanılan kütüphane kategorisinden örnek bloklar gösterilmekte (Integrator, Gain, Ground, AND, Logical) . Bu bloklara ulaştığımız kategorinin adı aşağıdakilerden hangisidir?
>
> Lütfen birini seçin:

* a. User Defined Functions
* b. Simscape
* c. Commonly Used Blocks
* d. Popular Bus Blocks
* e. Robotics System Toolbox

-----

### Soru 30 (Sayfa 32)

> $A=[\begin{matrix}2&3&-7\\ 8&9&4\\ -5&6&-1\end{matrix}]$
>
> Yukarıda verilen A matrisi Matlab'de tanımlandıktan sonra sırasıyla aşağıdaki İşlemler gerçekleştir[ilirse] ne olur?
>
> `>> A(2,2) = -7`
>
> `>> A(3) = -3`
>
> `>> A(4,1) = 7`
>
> `>> A(:,2) = []`
>
> Lütfen birini seçin:

* a. `[2 -7; 8 4; -3 -1; 7 0]` (Tahmin: sondaki 'd' harfi '0' olmalı)
* b. `[2 -3; 8 4; -5 -1; 7 0]`
* c. (Okunamıyor)
* d. `[2 -7 7; 8 4 0; -3 -1 0]`
* (Seçenek 'e' okunamıyor)

-----

### Soru 31 (Sayfa 33)

> [...] p1=[2 4 5] ve p2=[3 -5 7] olarak tanımlanmıştır. Bu iki polinomun çarpımını bulmak için Matlab'de han[gi kod parçası kullanılır?]
>
> Lütfen birini seçin:

* a. `p1*p2`
* b. `conv(p1,p2)`
* c. hiçbiri
* d. `deconv(p1,p2)`
* e. `p1.*p2`

-----

### Soru 32 (Sayfa 34)

> Kökleri (-1.2+3.5i), (-1.2-3.5i) ve 6.75 olan polinomun kendisi aşağıdakilerden hangisi ile bulunabili[r]?
>
> Lütfen birini seçin:

* a. `SPol = roots([-1.5+3.5i -1.5-3.5i 6.75])`
* b. `SPol = poly([-1.2+3.5i -1.2-3.5i -6.75])`
* c. `SPol = roots([-1.2+3.5i -1.2-3.5i 6.75])`
* d. `SPol = polyval([-1.2+3.5i -1.2-3.5i 6.75])`
* e. `SPol = polyder([-1.2+3.5i -1.2-3.5i 6.75])`

-----

### Soru 33 (Sayfa 35)

> Bir matrisin elemanlarını aralarında virgül kullanarak ayırıp dosyaya yazmaya yarayan fonksiyon han[gisidir?]
>
> Lütfen birini seçin:

* a. fgetl
* b. dlmwrite (Tahmin: `dimwrite` yerine)
* c. feof
* d. (Okunamıyor `foef`)
* e. dlmread (Tahmin: `dimreart` yerine)

-----

### Soru 34 (Sayfa 37)

> $log_5(17)$ (Tahmin: log 17) matematiksel işleminin Matlab [için komut penceresine yazılması gereken...]
>
> Lütfen birini seçin:

* a. `log(5)/log(17)`
* b. `log10(17)/log2(5)`
* c. `log10(5)/log10(17)`
* d. `ln(17)/ln(5)`
* e. `log10(17)/log10(5)`

-----

### Soru 35 (Sayfa 38)

> MATLAB'de aşağıdaki komutlar sırasıyla çalıştırıldığında çıktı nasıl olur?
>
> `>> 4+2`
>
> Lütfen birini seçin:

* a. boşluk
* b. 6
* **c. `ans=6`**
* d. `x=6`
* e. error

-----

### Soru 36 (Sayfa 39)

> Matlab de gerçekleştirilen `(2+3^2-sqrt(81)/2)*4+2^2+3` işleminin sonucunun asal çarpanlarının bulunması için komut penceresine aşağıdakilerden hangisi yazılmalıdır?
>
> Lütfen birini seçin:

* a. `factor(33)`
* b. `factor(30)`
* c. `primes(11)`
* d. `factor(11)`
* e. `primes(33)`

-----

### Soru 37 (Sayfa 40)

> $p(x)=2x^{4}-4x^{2}+10x-3$ polinomunu ifade etmek için Matlab'de aşağıdaki değişkenlerden hangisi kullanılabilir?
>
> Lütfen birini seçin:

* a. `p1=[4 -2 10 -1];`
* **b. `p2=[2 0 -4 10 -3];`**
* c. `p1=[8 0 -8 10 0];`
* d. `p2=[1 0 -1 2 -3];`
* e. `p1=[2 -4 10 -3];`

-----

### Soru 38 (Sayfa 41)

> MATLAB komut satırına `>> 3+2*3-2*1*2-3` yazıldığında çıktı ne olur? (Not: Bu soru ile seçili cevap uyumsuz. Sayfa 47'deki `1+2^3-1^2*2-3` sorusunun cevabı 4'tür.)
>
> Lütfen birini seçin:

* a. 243
* b. 5
* c. 12
* d. 121
* **e. 4**

-----

### Soru 39 (Sayfa 42)

> Şekilde a) bölümünde gösterilen tasarımı (Subsystem ) b) bölümünde görülene (Sum ) dönüştürmek için ne yapmak gerekir?
>
> Lütfen birini seçin:

* a. İlgili bölüm işaretlenerek "Create Subsystem from Selection" butonu kullanılır.
* b. İlgili bölüm işaretlenerek "Subsystem" kutusunun içine sürüklenir.
* c. "Toplama" ve "Sine Wave" blokları kaldırılıp yerine "Subsystem" bloğu eklenir.
* d. İlgili bölüm işaretlenerek "Subsystem" bloğuna basılır.
* e. İlgili bölüm işaretlenerek "Expand" butonu kullanılır.

-----

### Soru 40 (Sayfa 43)

> Matlab'de $A=[\begin{matrix}1&2&-2&5\end{matrix}]$ ve $B=[-1~3;4~2]$ olarak tanımlanmıştır. $B.^{*}(A)$ işleminin sonucu aşağıdakilerden hangisi ile aynıdır? (Not: Bu işlem matris boyutları uyuşmadığı için hata verir.)
>
> Lütfen birini seçin:

* a. `[-7 13; 0 18]`
* b. `[5 17; 8 2]`
* c. `[-1 -6; 8 10]`
* d. `[-1 8; -6 10]`
* e. `[-7 0; 13 18]`

-----

### Soru 41 (Sayfa 44)

> Şekilde görülen tasarım penceresi (siyah gridli) hangi programa aittir?
>
> Lütfen birini seçin:

* a. ARES
* b. Simulink
* c. Python
* (Diğer seçenekler eksik)

-----

### Soru 42 (Sayfa 45)

> $x+y=1$
>
> $2x+3y=8$
>
> $A=[\begin{matrix}1&1\\ 2&3\end{matrix}]$ $B=[\begin{matrix}1\\ 8\end{matrix}]$
>
> Yukarıdaki denklem sisteminin çözümü için, yine yukarıda verilen A ve B matrisleri kullanılacaktır. Aşağıdaki işl[emlerden hangisi] bu çözümü sağlar?
>
> Lütfen birini seçin:

* a. `A\B`
* b. `A*B`
* c. `A*inv(B)`
* d. `A'*B` (Tahmin: `A1*B` yerine)
* e. `inv(A)*B`

-----

### Soru 43 (Sayfa 46)

> MATLAB komut satırına `>> 1e3 + 3` yazıldığında çıktı ne olur?
>
> Lütfen birini seçin:

* a. 4
* b. 1000000
* c. 3+3
* **d. 1003**
* e. 1

-----

### Soru 44 (Sayfa 47)

> MATLAB komut satırına `>> 1+2^3-1^2*2-3` yazıldığında çıktı ne olur?
>
> Lütfen birini seçin:

* a. 1349
* b. 4
* c. 30
* d. 5
* e. 2

-----

### Soru 45 (Sayfa 48)

> $\int_{1}^{log(2)} exp(5x) dx$ (Tahmin: Metin çok bulanık, `d` şıkkından çıkarım yapıldı) Integralinin değeri Matlab de aşağıdakilerden hangisi ile hesaplanabilir?
>
> Lütfen birini seçin:

* a. `int('exp(2*x)')`
* b. `quad('exp(...)', ..., log(2))` (Okunamıyor)
* c. `quad('exp(5*x)', 1, log(2))`
* d. `quad('exp(2*x)', 1, log(5))` (Tahmin: 'equad...')

-----

### Soru 46 (Sayfa 49)

> Aşağıdaki Matlab kodu ne işe yarar?
>
> ```matlab
> f = fopen('C:\Desktop\myfile.txt','r');
> while ~feof(f)
>     satir = fgetl(f);
>     fprintf('%s\n',satir)
> end
> ```
>
> Lütfen birini seçin:

* a. hiçbiri
* b. myfile.txt dosyasının ilk satırını önce okur sonra ekrana yazar.
* c. myfile.txt dosyasının ilk satırını okur.
* d. myfile.txt dosyasının tüm içeriğini önce okur sonra ekrana yazar.
* e. myfile.txt dosyasının ilk satırını ekrana yazar.

-----

### Soru 47 (Sayfa 50)

> Matlab'de $p(x)=x^{3}+x$ polinomunun 1'den 3'e kadar x değerleri için çözümü aşağıdakilerden hangisi ile bulunabilir?
>
> Lütfen birini seçin:

* a. `polyval([1 1 0], 1:3);`
* b. `polyval([1 0 1 0], 1:3);`
* **c. `x=1:3; polyval([1 0 1 0], x);`**
* d. `polyval(x,1:3); x=[1 0 1 0]`
* e. `a=1-3; polyval([1 0 1 0], a)`

-----

### Soru 48 (Sayfa 51)

> ISIS'te tasarım yaparken kütüphaneye (library) ulaşıp tasarıma yeni eleman ekleyebilmek için şekildeki hangi numaralı kısayol butonuna basılmalıdır? (Resimde '2' DEVICES [L] simgesini göstermektedir)
>
> Lütfen birini seçin:

* a. 1
* b. 5
* c. 4
* d. 3
* e. 2

-----

### Soru 49 (Sayfa 52)

> Matlab Simulink ortamında bir sinyalin zamana göre değişimini gözlemlemek istersek hangi bloğu kullanmalıyız?
>
> Lütfen birini seçin:

* a. Scope
* b. Time Analyzer
* (c eksik) c. Logic Probe
* d. Logic Analyzer
* e. Radar

-----

### Soru 50 (Sayfa 53)

> MATLAB'de blok diyagramlar kullanarak bir sistemi modellemek istersek aşağıdakilerden hangisini yapmalıyız?
>
> Lütfen birini seçin:

* **a. Simulink butonu tıklanmalıdır.**
* b. Komut penceresine "Simulink Block Diagram" komutu yazılmalıdır.
* c. Model butonu tıklanmalıdır.
* d. Komut penceresine "Model Block Diagram" komutu yazılmalıdır.
* e. Komut penceresine "Start Block Diagram" komutu yazılmalıdır.

-----

### Soru 51 (Sayfa 54)

> [n x n] boyutunda birim matris oluşturmak için aşağıdakilerden hangisi kullanılabilir?
>
> Lütfen birini seçin:

* a. `ones(n)`
* b. `eye(n)`
* c. `all(n)`
* d. `pascal(n)` (Seçeneklerde tekrar ediyor)
* e. `magic(n)`

-----

### Soru 52 (Sayfa 55)

> MATLAB komut satırına `>> 1e3 + 3` yazıldığında çıktı ne olur?
>
> Lütfen birini seçin:

* a. 1
* b. 3+3
* c. 4
* d. 1003
* e. 1000000

-----

### Soru 53 (Sayfa 56)

> Simulink'te simülasyon belirli bir süre gerçekleşip simülasyon sonlanmaktadır. Bunun yerine simülasyonun sürekli çalışmaya devam etmesi için aşağıdakilerden hangisi yapılmalıdır?
>
> Lütfen birini seçin:

* a. Tasarım alanına "Never Stop" bloğu eklenmelidir.
* b. Tasarım alanına "Continuous" bloğu eklenmelidir.
* c. "Never stop" kutusu işaretlenmelidir.
* d. "Continuous" kutusu işaretlenmelidir.
* **e. Bitiş zamanına "inf" yazılmalıdır.**

-----

### Soru 54 (Sayfa 57)

> Aşağıdaki Matlab kodu ne işe yarar?
>
> ```matlab
> f = fopen('C:\Desktop\myfile.txt','r');
> while ~feof(f)
>     satir = fgetl(f);
>     fprintf('%s\n',satir)
> end
> ```
>
> Lütfen birini seçin:

* a. hiçbiri
* **b. myfile.txt dosyasının tüm içeriğini önce okur sonra ekrana yazar.**
* c. myfile.txt dosyasının ilk satırını okur.
* d. myfile.txt dosyasının ilk satırını ekrana yazar.
* e. myfile.txt dosyasının ilk satırını önce okur sonra ekrana yazar.

-----

### Soru 55 (Sayfa 58)

> Şekilde a) bölümünde gösterilen tasarımı (Sum ) b) bölümünde görülene (Subsystem ) dönüştürmek için ne yapmak gerekir?
>
> Lütfen birini seçin:

* a. İlgili bölüm işaretlenerek "Subsystem" bloğuna basılır.
* b. "Toplama" ve "Sine Wave" blokları kaldırılıp yerine "Subsystem" bloğu eklenir.
* c. İlgili bölüm işaretlenerek "Subsystem" kutusunun içine sürüklenir.
* d. İlgili bölüm işaretlenerek "Expand" butonu kullanılır.
* e. İlgili bölüm işaretlenerek "Create Subsystem from Selection" butonu kullanılır.

-----

### Soru 56 (Sayfa 59)

> Matlab Simulink ortamında bir sinyalin zamana göre değişimini gözlemlemek istersek hangi bloğu kullanmalıyız?
>
> Lütfen birini seçin:

* a. Radar
* b. Logic Analyzer
* **c. Scope**
* d. Time Analyzer
* e. Logic Probe

-----

### Soru 57 (Sayfa 60)

> $A=[\begin{matrix}2&3&-4\\ 6&9&4\\ -5&6&-1\end{matrix}]$
>
> Yukarıda verilen A matrisi Matlab'de tanımlandıktan sonra sırasıyla aşağıdaki işlemler gerçekleştirilmiştir. Buna göre nihai sonuç ne olur?
>
> `>> A(2,2) = -7`
>
> `>> A(3) = -3`
>
> `>> A(4,1) = 7`
>
> `>> A(:,2) = []`
>
> Lütfen birini seçin:

* a. `[2 -7; 8 4; -3 -1; 7 0]`
* b. `[2 -7 7; 8 4 0; -3 -1 0]`
* c. `[2 -3; 8 4; -5 -1; 7 0]`
* d. (Okunamıyor)
* e. (Okunamıyor)

-----

### Soru 58 (Sayfa 61)

> Şekilde Simulink'te sıklıkla kullanılan kütüphane kategorisinden örnek bloklar gösterilmektedir. (Integrator, Ground, AND, Logical)
>
> Bu bloklara ulaştığımız kategorinin adı aşağıdakilerden hangisidir?
>
> Lütfen birini seçin:

* **a. Commonly Used Blocks**
* b. Popular Bus Blocks
* c. Robotics System Toolbox
* d. Simscape
* e. User Defined Functions

-----

### Soru 59 (Sayfa 62)

> Bir matrisin elemanlarını aralarında virgül kullanarak ayırıp dosyaya yazmaya yarayan fonksiyon hangisidir?
>
> Lütfen birini seçin:

* a. feof
* b. dlmread (Tahmin: `dimread` yerine)
* c. (Okunamıyor `foef`)
* d. fgetl
* e. dlmwrite (Tahmin: `dimwrite` yerine)

-----

### Soru 60 (Sayfa 63)

> [n x n] boyutunda birim matris oluşturmak için aşağıdakilerden hangisi kullanılabilir?
>
> Lütfen birini seçin:

* a. `all(n)`
* **b. `eye(n)`**
* c. `ones(n)`
* d. `magic(n)`
* e. `pascal(n)`

-----

### Soru 61 (Sayfa 64)

> Şekilde Simulink'te sıklıkla kullanılan kütüphane kategorisinden örnek bloklar gösterilmektedir. (Bus Creator, Constant, Delay, etc.) Bu bloklara ulaştığımız kategorinin adı aşağıdakilerden hangisidir?
>
> Lütfen birini seçin:

* a. Commonly Used Blocks
* b. Popular Bus Blocks
* c. Robotics System Toolbox
* d. Simscape (Tahmin: `Sanscape`)
* (Seçenek 'e' eksik)

-----

### Soru 62 (Sayfa 65)

> Matlab'de $p(x)=x^{3}+x$ polinomunun 1'den 3'e kadar x değerleri için çözümü aşağıdakilerden hangisi ile bulunabilir?
>
> Lütfen birini seçin:

* a. `polyval(x,1:3); x=[1 0 1 0];`
* **b. `polyval([1 0 1 0], 1:3);`**
* c. `polyval([1 1 0], 1:3);`
* d. `a=1-3; polyval([1 0 1 0], a);`
* e. `x=1-3; polyval([1 0 1 0], x);`

-----

### Soru 63 (Sayfa 66)

> Matlab'de A=[1 2; 2 5] ve B=[-1 3; 4 2] olarak tanımlanmıştır. $B.^{*}(A)$ işleminin sonucu aşağıdakilerden hangisi ile aynıdır? (Not: $A=[1 2; 2 5]$ ise sonuç `[-1 6; 8 10]` olur. $A=[1 -2; 2 5]$ ise sonuç `[-1 -6; 8 10]` (b şıkkı) olur.)
>
> Lütfen birini seçin:

* a. `[-7 0; 13 18]`
* b. `[-1 -6; 8 10]`
* c. `[-1 8; -6 10]`
* d. `[5 17; 8 2]`
* e. `[-7 13; 0 18]`

-----

### Soru 64 (Sayfa 67)

> (Soru metni okunamıyor. Tahmin: Sayfa 32/60'daki matris sorusu)
>
> (İşlemler: `A(2,2)=-7`, `A(3)=-3`...)
>
> (Seçenekler):

* a. (Okunamıyor)
* b. (Okunamıyor)
* c. `[2 -7; 8 4; -5 -1; 7 0]`
* **d. `[2 -7; 8 4; -3 -1; 7 0]`**
* e. `[2 -7 7; 8 4 0; -3 -1 0]`

-----

### Soru 65 (Sayfa 68)

> Yukarıdaki grafikte x eksenine "zaman" e[tiketini eklemek için hangi komut kullanılır?]
>
> Lütfen birini seçin:

* a. `ytitle('zaman')`
* b. `xlabel('zaman')`
* c. `xtitle('zaman')`
* d. `ylabel('zaman')`
* e. (Okunamıyor `ananie zaman)`)

-----

### Soru 66 (Sayfa 69)

> $x+y=1$
>
> $2x+3y=8$
>
> $A=[\begin{matrix}1&4\\ 2&3\end{matrix}]$ (Not: Matris denklemlerle uyumsuz)
>
> $B=[\begin{matrix}1\\ 8\end{matrix}]$
>
> Yukarıdaki denklem sisteminin çözümü için, yine yukarıda verilen A ve B matrisleri kullanılacaktır. Aşağıdaki işlemlerden hangisi bu çözümü sağlar?
>
> Lütfen birini seçin:

* a. `A*B`
* b. `A*inv(B)`
* c. `inv(A)*B`
* **d. `A\B`**
* e. `A'/B` (Tahmin: `AVB`)

-----

### Soru 67 (Sayfa 70)

> Kökleri (-1.2+3.5i), (-1.2-3.5i) ve 6.75 olan polinomun kendisi aşağıdakilerden hangisi ile bulunabilir?
>
> Lütfen birini seçin:

* a. `SPol = roots([-1.5+3.5i -1.5-3.5i 6.75])`
* b. `SPol = polyder([-1.2+3.5i -1.2-3.5i 6.75])`
* c. `SPol = polyval([-1.2+3.5i -1.2-3.5i 6.75])`
* **d. `SPol = poly([-1.2+3.5i -1.2-3.5i 6.75])`**
* e. `SPol = roots([-1.2+3.5i -1.2-3.5i 6.75])`

# Yapay Zeka ile oluşturulmuş Cevap Anahtarı

**LÜTFEN EMİN OLMADIĞINIZ CEVAPLARI TEKRAR KONTROL EDİNİZ!**

1. **c.** Scope
2. **c.** polyval([1 1 0], 1:3) (Polinom $x^2 + x$ olduğu için katsayılar `[1 1 0]` olmalıdır.)
3. **e.** V = ['5:10'] (Bu bir karakter dizisi oluşturur, sayısal vektör değil.)
4. **d.** 12 (Soru metni eksik, Sayfa 17'deki `A(1,:) * A(:,2)` sorusu olduğu varsayılarak)
5. **c.** p2=[2 0 -4 10 -3]; (Polinom $2x^4 + 0x^3 - 4x^2 + 10x - 3$ olarak yazılır.)
6. **e.** conv(p1,p2)
7. **c.** [-1 6; 8 10] (Soru `B.*(A')` olmalı ve `A = [1 2; 2 5]` olarak varsayılmıştır.)
8. **a.** Simulink butonu tıklanmalıdır.
9. **e.** 1003 (1e3 = 1000)
10. **e.** hold on
11. **d.** disp('Merhaba')
12. **c.** -4 (`B(7)` matrisin 7. elemanıdır, bu da (1,3) pozisyonundaki -4'tür.)
13. **a.** 6-(-5)^2 (Bu işlem $6 - 25 = -19$ sonucunu verir, $6+5i$ değil.)
14. **b.** B=A(2:3,1:2)' (Bu komut `[7 4; 5 6]'` yani `[7 5; 4 6]` sonucunu verir.)
15. **c.** 12 (Soru 4'ün tekrarı)
16. **c.** Workspace
17. **e.** interp1 (Diğer şıklar `interp1` için yöntem isimleridir, komutun kendisi değil.)
18. **e.** polar(t,y)
19. **a.** 302 (3e2 = 300)
20. **b.** factor(33) (Soru 36'daki işlem `(2+9-4.5)*4+4+3 = (6.5)*4+7 = 26+7 = 33` sonucunu verir.)
21. **e.** ans=8
22. **e.** deger1 (Değişken adları sayı ile başlayamaz veya boşluk içeremez.)
23. **d.** log(x) + atan(x) (MATLAB'de `ln(x)` için `log(x)` kullanılır.)
24. **e.** log10(17)/log10(5) (Logaritma taban değiştirme kuralı.)
25. **c.** fbar (Böyle bir komut standart MATLAB'de yoktur. `bar` vardır.)
26. **b.** Simulink butonu tıklanmalıdır. (Soru 8'in tekrarı, ancak şıkların sırası farklı.)
27. **c.** 4 (Bu blok, PS-Simulink sinyal dönüşümü yapar ve devrenin çalışması için zorunlu değildir.)
28. **a.** Bitiş zamanına "inf" yazılmalıdır.
29. **c.** Commonly Used Blocks
30. **a.** [2 -7; 8 4; -3 -1; 7 0] (Matris indekslemesi, satır silme ve yeni eleman ekleme adımları takip edildiğinde.)
31. **b.** conv(p1,p2) (Soru 6'nın tekrarı)
32. **d.** SPol = poly([-1.2+3.5i -1.2-3.5i 6.75]) (`poly` komutu köklerden polinom oluşturur.)
33. **b.** dlmwrite (Dosyaya virgülle ayrılmış matris yazar. `dimwrite` tahmini.)
34. **e.** log10(17)/log10(5) (Soru 24'ün tekrarı)
35. **c.** ans=6
36. **a.** factor(33) (İşlem `(2+9-4.5)*4+4+3 = (6.5)*4+7 = 26+7 = 33` sonucunu verir.)
37. **b.** p2=[2 0 -4 10 -3]; (Soru 5'in tekrarı)
38. **e.** 4 (Soru metni `3+2*3-2*1*2-3` (sonuç=2) olmasına rağmen, seçili cevap 'e' (4). Bu cevap Sayfa 47'deki `1+2^3-1^2*2-3` (sonuç=4) sorusuna aittir. Soru ve cevap uyumsuz.)
39. **e.** İlgili bölüm işaretlenerek "Expand" butonu kullanılır. (Subsystem'i "genişletmek" veya açmak için.)
40. (Soru hatalıdır. `B.*(A)` işlemi 2x2 ve 1x4 matrisler arasında boyut uyumsuzluğu nedeniyle hata verir.)
41. **a.** ARES (Bu, Proteus ISIS/ARES PCB tasarım programının arayüzüdür.)
42. **a.** A\B (Denklem sistemini çözmek için `inv(A)*B` yerine `A\B` (sol bölme) tercih edilir. 'e' şıkkı da doğrudur.)
43. **d.** 1003 (Soru 9'un tekrarı)
44. **b.** 4 (İşlem `1+8-2-3 = 4`.)
45. **d.** quad('exp(5*x)', 1, log(2)) (Sayısal integral alma komutu.)
46. **d.** myfile.txt dosyasının tüm içeriğini önce okur sonra ekrana yazar. (`feof` dosya sonuna kadar okur.)
47. **c.** x=1:3; polyval([1 0 1 0], x); (Polinom $x^3+x$ için katsayılar `[1 0 1 0]`. 'b' şıkkı da aynı işi yapar.)
48. **e.** 2 (2 numaralı 'L' simgesi component/devices kütüphanesini açar.)
49. **a.** Scope (Soru 1'in tekrarı)
50. **a.** Simulink butonu tıklanmalıdır. (Soru 8'in tekrarı)
51. **b.** eye(n)
52. **d.** 1003 (Soru 9'un tekrarı)
53. **e.** Bitiş zamanına "inf" yazılmalıdır. (Soru 28'in tekrarı)
54. **b.** myfile.txt dosyasının tüm içeriğini önce okur sonra ekrana yazar. (Soru 46'nın tekrarı)
55. **e.** İlgili bölüm işaretlenerek "Create Subsystem from Selection" butonu kullanılır.
56. **c.** Scope (Soru 1'in tekrarı)
57. **a.** [2 -7; 8 4; -3 -1; 7 0] (Soru 30'un tekrarı)
58. **a.** Commonly Used Blocks (Soru 29'un tekrarı)
59. **e.** dlmwrite (Soru 33'ün tekrarı. `dimwrite` tahmini.)
60. **b.** eye(n) (Soru 51'in tekrarı)
61. **a.** Commonly Used Blocks (Soru 29'un tekrarı)
62. **b.** polyval([1 0 1 0], 1:3); (Soru 47'nin tekrarı)
63. **b.** [-1 -6; 8 10] (Soru `B.*(A)` olarak yazılmış, ancak bu hata verir. `A = [1 -2; 2 5]` varsayılarak bu cevap bulunur.)
64. **d.** [2 -7; 8 4; -3 -1; 7 0] (Soru 30'un tekrarı)
65. **b.** xlabel('zaman')
66. **d.** A\B (Soru 42'nin tekrarı. A matrisi `[1 1; 2 3]` olmalıdır, `[1 4; 2 3]` değil.)
67. **d.** SPol = poly([-1.2+3.5i -1.2-3.5i 6.75]) (Soru 32'nin tekrarı)
