# Enmera tasarım kuralları

[English](RULES.md) · `rules.json` dosyasından üretilir; o dosyayı düzenleyip `npm run docs` çalıştırın. **Denetlenir** işaretli kuralları `npx @enmera/ai-design-check` bulur; diğerlerine insanlar ve ajanlar bakar.

## Yazım

### Arayüz metninde yalnız ilk kelime büyük

`sentence-case` · hata · denetlenir

**Kural:** Yalnız ilk kelime ve özel adlar büyük harfle başlar: "Kelime takibi", "Bu hafta yükselen". Otomatik büyük harf dönüştürücü yok; metin nasıl yazıldıysa öyle görünür.

**Neden:** Her kısa etikette her kelimenin büyük yazılması bağırır ve Türkçe yazım kuralı değildir. Microsoft Türkçe stil kılavuzu (4.1.5): yalnız özel adlar ve ilk kelime; TDK'de her kelime büyük yalnız eser, belge ve kurum adlarında.

**Nasıl düzeltilir:** Özel adlar (Google İşletme Profili, Search Console), resmî kategori ve belge adları (Sağlık ve Fitness, Gizlilik Politikası), kısaltmalar (AI, SERP) ve dil kodu rozetleri olduğu gibi kalır. Yol ayracından sonraki ilk kelime büyük: "Site sağlığı › Site denetimi".

### Süs amaçlı büyük harf ve harf aralığı yok

`no-decorative-uppercase` · uyarı · denetlenir

**Kural:** Küçük, büyük harfli ve harf aralıklı etiket yok (başlık üstü etiket, kahraman alanı hap etiketi, "NAVIGATION" gibi bölüm başlığı).

**Neden:** Yapay zekâ üretimi arayüzlerin en bilinen kalıbıdır ve okumayı zorlaştırır: kelimeleri biçiminden tanırız.

**Nasıl düzeltilir:** Etiketi normal yazım ve harf aralığıyla yazın. Kodlar, dil kodu rozeti ve baş harf avatarı büyük kalabilir.

### Etiket yerine sığar

`short-labels` · not · gözden geçirilir

**Kural:** Menüde ya da sekmede kesilen etiket kısaltılır; aynı şey her yerde aynı kelimeyle söylenir (kısa etikette "keyword" = "kelime": "Kelime araştırması").

**Neden:** Kesilen etiket anlamı gizler ve yarım görünür.

**Nasıl düzeltilir:** Etiketi kısaltın; yazıyı küçültmeyin.

### Düğme ve etiketlerde nokta yok

`no-trailing-period-labels` · not · denetlenir

**Kural:** Düğme, sekme, menü öğesi ve kısa etiketler noktasız biter; yardım metnindeki cümleler noktasını korur.

**Neden:** Nokta bir komutu cümleye çevirir ve düğme sırasını düzensiz gösterir.

**Nasıl düzeltilir:** Sondaki noktayı kaldırın.

### Kısa yer tutucular

`short-placeholders` · not · denetlenir

**Kural:** "Her şeyi ara...", "Buraya yazın..." ya da "E-postanızı buraya girin" yok; yer tutucu bir iki kelime ya da örnek değerdir.

**Neden:** Uzun yer tutucu etiketi tekrarlar, yazınca kaybolur ve dolgu gibi okunur.

**Nasıl düzeltilir:** "Ara" ya da "ad@sirket.com" gibi bir örnek.

### Metin kesilmez

`text-not-clipped` · uyarı · denetlenir

**Kural:** Etiket, düğme ve tablo hücreleri 320 px'te metnin tamamını gösterir. Üç noktayla kısaltma yalnız tam metin bir dokunuş uzaktaysa (title, ipucu, ayrıntı) serbesttir.

**Neden:** Kesilen etiket anlamını değiştirebilir ("Tümünü sil…" neyi?) ve çeviriler İngilizceden çoğu zaman %30–40 uzundur.

**Nasıl düzeltilir:** Metni alt satıra geçirin; gerçekten tek satır olmalıysa tam metni title'da ve ayrıntı görünümünde tutun.

## Yazı ölçeği

### Yazı boyutu yalnız ölçekten

`type-scale` · hata · denetlenir

**Kural:** Temadaki ölçek kullanılır: text-2xs (11 px, en küçük), text-xs, text-sm, text-base … Elle text-[10px], text-[13px] yazılmaz.

**Neden:** Tek seferlik boyutlar ekranlar arasında küçük farklar biriktirir. 11 px altı metin okunmaz.

**Nasıl düzeltilir:** Temaya --text-2xs: 0.6875rem (satır yüksekliği 1rem) ekleyin; 9–11 px → text-2xs, 12 px → text-xs, 13 px → text-sm. Tanıtım sitesinin büyük başlık boyutları izin listesine yazılır.

### Dinamik yazı boyutuna uyan metin stilleri

`dynamic-type` · uyarı · denetlenir

**Kural:** SwiftUI'da metni metin stilleriyle (.body, .headline, .caption) ya da relativeTo ile özel yazı tipiyle verin, sabit .system(size:) ile değil. İkonlar sabit boyut kullanabilir.

**Neden:** Sabit boyut, kullanıcının yazı boyutu ayarını yok sayar: büyük yazıya ihtiyacı olan ekranı okuyamaz ve her ekran kendi gelişigüzel boyutlarına sahip olur.

**Nasıl düzeltilir:** Her boyutu en yakın metin stiline eşleyin (11 caption2, 12 caption, 13 footnote, 15 subheadline, 17 body, 20 title3, 22 title2, 28 title, 34 largeTitle) ve kalınlığı .fontWeight ile verin.

### Başlıklar normal ile yarı kalın arası

`no-heavy-headings` · uyarı · denetlenir

**Kural:** Arayüz başlıklarında ve sayılarda font-extrabold ya da font-black (800–900) yok; hiyerarşi boyut ve konumdan gelir.

**Neden:** Üretilmiş ekranlar her başlığı olabildiğince kalın yapar, böylece hiçbiri öne çıkmaz.

**Nasıl düzeltilir:** 400–600 kullanın ve boyutu bir basamak büyütün. Kalın çizilmiş bir gösterim yazı tipi ayarda izinli yapılabilir.

### Vurgu italikle değil, kalınlık ya da renkle

`no-italic-emphasis` · not · denetlenir

**Kural:** Arayüz metni vurgu için italik yazılmaz; alıntı ve eser adı italik olabilir.

**Neden:** İtalik arayüz boyutlarında zor okunur ve yer tutucu gibi görünür.

**Nasıl düzeltilir:** font-medium ya da ikincil metin rengi kullanın.

### Küçük metinde dar harf aralığı yok

`no-tight-small-text` · uyarı · denetlenir

**Kural:** tracking-tight ve eksi harf aralığı büyük gösterim metnine (40 px ve üstü) aittir, text-base ve küçüğüne asla.

**Neden:** Sıkıştırılmış küçük harfler biçimini kaybeder, zor okunur.

**Nasıl düzeltilir:** Küçük metinde harf aralığını 0 bırakın; soluk açıklamada hafif artı olabilir.

### Metin sığsın diye küçültülmez

`no-shrunk-text` · uyarı · denetlenir

**Kural:** Gövde metni ve etiketler telefonda boyutunu korur (12 px altına inmez, masaüstünden küçük olmaz); yalnız büyük başlıklar küçülebilir.

**Neden:** Telefon kol mesafesinde ve güneş altında okunur; yerleşimi sığdırmak için yazıyı küçültmek sorunu okura yükler.

**Nasıl düzeltilir:** Boyutu koruyun, yerleşim esnesin: alta geçirin, üst üste dizin ya da ikincil içeriği aşağı alın.

## Köşe ve yüzey

### Köşe yuvarlaklığı yalnız ölçekten

`radius-scale` · hata · denetlenir

**Kural:** rounded-md … rounded-3xl ve rounded-full kullanılır; tanıtım sitesinin büyük yüzeyleri tek bir ortak değer alır (rounded-panel). Elle köşe yalnız 5 px'e kadar mikro öğelerde ve cihaz/ikon çizimlerinde.

**Neden:** Yan yana 28, 30 ve 32 px'lik köşeler sistem değil gürültü gibi okunur.

**Nasıl düzeltilir:** En yakın ölçek adımını seçin ya da tek bir adlı değer ekleyin.

### Kart içinde kart yok

`no-nested-cards` · uyarı · gözden geçirilir

**Kural:** Kartın içindeki gruplar boşluk, yazı ve ayraçla ayrılır; içe ikinci bir çerçeveli kart konmaz.

**Neden:** İç içe çerçeve anlamı olmayan derinlik ekler.

**Nasıl düzeltilir:** Düzleştirin: ikinci kenarlık ve gölge yerine ayraç ya da hafif zeminli blok.

### İç köşe dış köşeyi izler

`nested-radius` · uyarı · gözden geçirilir

**Kural:** Yuvarlak bir kabın içindeki öğe köşe = dış köşe − iç boşluk kullanır (4 px altına inmez); her öğe tam hap değildir.

**Neden:** İç ve dışta eşit köşe, köşelerde boşluğu düzensiz gösterir; her yerde hap, denetim ile kap arasındaki farkı siler.

**Nasıl düzeltilir:** 8 px boşluklu 16 px kart 8 px köşeli öğe taşır; tam hapı çip ve avatarlara bırakın.

### Kartlar ağır gölgeyle değil yüzey basamağıyla ayrılır

`no-heavy-card-shadow` · uyarı · denetlenir

**Kural:** Sayfa akışındaki kart ve paneller ince kenarlık ya da sayfadan bir basamak açık yüzey kullanır; shadow-lg ve üstü havada duran öğeler içindir (menü, iletişim kutusu, açılır panel).

**Neden:** İncelediğimiz yüksek puanlı panellerin hepsi kartları açık sayfa zemini ve beyaz ya da yükseltilmiş kartla ayırdı, gölge neredeyse yoktu; ağır gölge kart ızgarasını yapıştırma etiketler gibi gösterir.

**Nasıl düzeltilir:** Gölgeyi shadow-sm'e indirin ya da kaldırın, yüzeyi basamaklayın (sayfa gray-50, kart beyaz; koyu: sayfa #0b0d14, kart #11141c).

## Bileşen ve tekrar

### Etkileşimli öğeler ortak bileşenden

`use-shared-components` · uyarı · denetlenir

**Kural:** Sayfalar ortak Button, Input, Select, Textarea ve Checkbox bileşenlerini kullanır; ham <button>, <input>, <select>, <textarea> yazılmaz. Ham öğeler yalnız bileşen klasörünün içinde durur.

**Neden:** Her ham öğe düğmenin yeni bir kopyasıdır: bir yerde yükseklik, odak halkası ya da köşe farklı olur ve bir sonraki düzeltme onu kaçırır.

**Nasıl düzeltilir:** Bileşenle değiştirin; bileşende gereken görünüm yoksa görünümü bileşene ekleyin.

### Rozet, kutu, başlık ve düğme görünümlü bağlantı ortak bileşenden

`use-shared-looks` · uyarı · denetlenir

**Kural:** Rozet gibi biçimlenmiş span, kart gibi biçimlenmiş div, kendi boyut sınıflarını taşıyan başlık ya da düğme gibi biçimlenmiş bağlantı, ortak bileşenin elle yapılmış kopyasıdır. Rozet, kutu, başlık ve bağlantı düğmesi bileşenleri kullanılır; proje adlarını config.looks ile verir.

**Neden:** En hızlı dağılan şey rozet ve kutudur: aynı 'yeni' etiketi beş farklı boşluk ve dört farklı yeşille yazılır. Başlık ölçeği ancak başlıklar boyut yazmak yerine boyut seçtiğinde korunur.

**Nasıl düzeltilir:** Öğeyi bileşenle değiştirip ton ve boyut seçin; uyan yoksa çağrı yerine sınıf değil, bileşene ton ya da boyut ekleyin.

### Ortak bileşene dışarıdan görünüm verilmez

`no-style-overrides` · uyarı · denetlenir

**Kural:** Button, Badge, Input, Card gibi ortak bileşenlere verilen className yalnız yerleştirir (genişlik, kenar boşluğu, hizalama, ızgara konumu). Renk, köşe, iç boşluk, yükseklik, yazı ve kenarlık bileşenin variant/size seçeneklerinden gelir.

**Neden:** Dışarıdan verilen görünüm bileşenin gizli bir kopyasıdır: aynı düğme iki ekranda farklı görünür; tasarım sistemi tam da bunu engellemek için vardır.

**Nasıl düzeltilir:** Görünümü bileşenin adlı bir variant ya da size seçeneğine taşıyın ve onu kullanın.

### Tekrarlanan kalıp bileşen olur

`repeated-markup` · uyarı · denetlenir

**Kural:** Birden çok yerde tekrarlanan aynı uzun sınıf listesi (kart, rozet, gösterge kutusu, bölüm başlığı) tek bir ortak bileşene çıkarılır.

**Neden:** Kopyalar zamanla ayrışır: birine yeni boşluk verilir, diğeri eski köşede kalır. Tek bileşen tek düzeltme ve daha az kod demektir.

**Nasıl düzeltilir:** Öğeyi bir bileşene (ya da var olanın bir görünümüne) çıkarın ve kopyaları onunla değiştirin.

### Az ve sakin rozet

`no-badge-spam` · uyarı · gözden geçirilir

**Kural:** PRO, Yeni ve Beta rozetleri seyrek, yalnız metindir ve bir nedeni vardır; sayaç ve kısayol parlayan hap değil, düz metin ya da tuş görünümüdür.

**Neden:** Her satırdaki rozet anlamını yitirir ve menüye gürültü ekler.

**Nasıl düzeltilir:** Karar değiştiren yerde tek rozet bırakın; gerisini kaldırın.

### Tek durum sistemi

`status-system` · uyarı · gözden geçirilir

**Kural:** Durumlar nokta ve kelimeli küçük, hafif renkli haplardır ve tek bir ortak eşlemeden gelir (başarılı, bekliyor, başarısız, taslak); aynı durum her ekranda aynı renktir.

**Neden:** Durum rengi bir kez öğrenilir; "Bekliyor" bir tabloda turuncu, ötekinde maviyse kullanıcı renge hiç güvenmez.

**Nasıl düzeltilir:** Durum → ton eşlemesiyle tek bir StatusBadge oluşturun, her tablo ve kartta onu kullanın.

## Seçiciler

### Tek seçici dili

`selector-language` · hata · gözden geçirilir

**Kural:** İçerik değiştiren ana seçim (sayfa sekmeleri, konu grupları, ayrı listeler) bölmeli seçicidir. Alt sekmeleri aynı satırda, sağında, ince ayraçtan sonra kutusuz metindir (seçili olan hafif zeminli). Aynı listeyi daraltan süzgeç, listenin içinde hap düğmedir.

**Neden:** Alt alta, benzer ağırlıkta iki seçici sırası hangisinin ana seçim olduğunu gizler. Alt çizgili sekme denendi ve beğenilmedi.

**Nasıl düzeltilir:** Alt alta iki seçici sırası ve alt çizgili sekme yok. Kart içindeki küçük varyant seçimi küçük bölmeli seçicidir.

## Yerleşim

### Geniş tablo tam genişlikte

`full-width-tables` · uyarı · gözden geçirilir

**Kural:** Çok sütunlu veri tablosu tam genişlikte durur; artan genişliği son sütun alır (w-full, hücrede max-w-0 truncate). Az sütunda tarih ile değer birbirinden kopmaz, uzun adlar kesilmez.

**Neden:** Yan sütuna sıkışan tablo adları keser; satır azken altında boş alan bırakır.

**Nasıl düzeltilir:** Yan kartları tablonun altına, iki sütunlu masonry yerleşime alın.

### Yüksekliği farklı kartlar ızgara tabanlı masonry'de

`masonry` · uyarı · denetlenir

**Kural:** Yüksekliği farklı kartlar ızgara tabanlı masonry'ye girer (iki sütun, soldan sağa sıra). CSS columns kullanılmaz; altı boş kalan dar sütun bırakılmaz.

**Neden:** CSS columns Chrome'da gölgeyi sütun başında bölüyor ve kartları sütun sütun diziyor.

**Nasıl düzeltilir:** Her kartı en kısa sütuna yerleştiren ızgara tabanlı masonry bileşeni kullanın.

### Okunur satır uzunluğu ve aralığı

`readable-measure` · uyarı · gözden geçirilir

**Kural:** Akan metin satırda yaklaşık 80 karakteri geçmez (max-w-prose / max-w-3xl), satır aralığı en az 1,3; başlığın üstündeki boşluk altındakinden büyüktür.

**Neden:** Uzun satırda göz bir sonraki satırın başını kaybeder.

**Nasıl düzeltilir:** Kartı değil paragrafı daraltın.

### Boşlukta ritim

`spacing-rhythm` · not · gözden geçirilir

**Kural:** İlgili öğeler sıkı, bölümler arası geniş. Her yerde aynı boşluk ritimsizdir.

**Neden:** Gruplama her şeyden önce boşluktan okunur.

**Nasıl düzeltilir:** İki üç adım kullanın: grup içi, gruplar arası, bölümler arası.

### Boşluklar 4 px ızgarasında

`spacing-scale` · uyarı · denetlenir

**Kural:** Piksel cinsinden keyfi boşluk ve boyutlar (mt-[13px], h-[31px], gap-[7px]) 4 px ızgarasına oturur; tema basamakları tercih edilir.

**Neden:** Izgara dışı değerler modelin tahmin ederken yazdığı değerlerdir; satır ve aralıklar bir iki piksel kayar, ekran düzensiz görünür.

**Nasıl düzeltilir:** En yakın tema basamağına yuvarlayın (mt-3, h-8, gap-2).

### Kahraman alanında tek ana işlem

`hero-one-action` · uyarı · gözden geçirilir

**Kural:** Kahraman alanında bir ana ve en çok bir ikincil işlem olur; üçüncü düğme, düğmelerin altına yığılmış çip ya da avatar sırası yok.

**Neden:** Her ek işlem, ziyaretçinin kalıp kalmayacağına karar verdiği anda dikkati böler.

**Nasıl düzeltilir:** Ana işlemi ve bir alternatifi tutun; gerisini sayfanın aşağısına taşıyın.

### Tek kart başlığı düzeni

`card-header-pattern` · uyarı · gözden geçirilir

**Kural:** Her kart başlığı aynıdır: solda başlık, sağda en çok bir denetim (dönem seçici, "Tümünü gör" ya da ⋯ menüsü), aynı taban çizgisinde.

**Neden:** Kartlarda tek başlık düzenini tekrarlamak yoğun paneli sakin gösteren şeydir; karışık başlıklar her kartı yeni bir okuma işi yapar.

**Nasıl düzeltilir:** Başlık ve isteğe bağlı işlem yuvası olan bir CardHeader bileşeni çıkarıp her yerde kullanın.

### Sayfa başına tek ana işlem

`one-primary-action` · uyarı · gözden geçirilir

**Kural:** Sayfa başlığında tek dolu ana düğme olur (genelde sağ üstte); diğer işlemler ikincil, hayalet ya da menü içindedir.

**Neden:** Yan yana iki dolu düğme, kullanıcıdan sayfanın ne için olduğunu anlamadan seçim yapmasını ister.

**Nasıl düzeltilir:** Sayfanın işini ilerleten işlemi dolu bırakın; gerisini bir basamak indirin.

### Telefonda yana kaydırma yok

`no-horizontal-overflow` · hata · denetlenir

**Kural:** 320 px'te sayfa ekrandan geniş değildir. Geniş içerik (tablo, kod bloğu) sayfa değil kendi kutusu içinde kayar.

**Neden:** Yana kayan sayfa sağ kenarını saklar ve her dikey kaydırmayı yalpalatır.

**Nasıl düzeltilir:** Satırların alta geçmesine izin verin (flex-wrap), uzun kelimeleri bölün (doğru lang ile hyphens: auto, overflow-wrap), geniş tabloyu overflow-x-auto içine alın.

### Telefon aynı içeriği alır

`no-hidden-content-narrow` · not · denetlenir

**Kural:** Masaüstünde görünen metin telefonda gizlenmez (hidden sm:block). Öğeler bir dokunuş uzakta kaldıkça daraltılmış menü sorun değildir.

**Neden:** Küçük yerleşimi çalıştırmak için içerik gizlemek ziyaretçilerin çoğundan bilgiyi saklar.

**Nasıl düzeltilir:** Gösterin, herkes için kısaltın ya da gizlemek yerine sayfada aşağı taşıyın.

## Menü

### Menü işe göre, yer önce kararlaştırılır

`menu-by-job` · uyarı · gözden geçirilir

**Kural:** Özellik yazılmadan önce yeri kararlaştırılır: hangi menü bölümü, ayrı satır mı var olan sayfanın sekmesi mi, hangi adres öneki. Aynı işin sayfaları menüde tek satır, sayfada sekmedir. Bölümler katlanır; içinde bulunulan bölüm açık kalır.

**Neden:** Yoksa menü, birbiriyle ilgili işlerin dört ayrı yere düştüğü elli satırlık düz bir listeye dönüşür.

**Nasıl düzeltilir:** Taşınan adres 301 ile yönlenir (alt yol ve sorgu korunur); dış servislere kayıtlı geri dönüş adresleri taşınmaz. Yardım metinlerindeki "nerede" yolu menüyle aynı yazılır.

## Görsel dil

### Emoji yerine çizgi ikon

`icons-not-emoji` · uyarı · denetlenir

**Kural:** Arayüz işaretleri tek bir setten çizgi ikondur (lucide). Emoji ve ✓ gibi metin işaretleri süs olarak kullanılmaz; içerik olan emoji (sohbet emoji seçici) kalır.

**Neden:** Emoji her platformda farklı çizilir ve üretilmiş gibi okunur.

**Nasıl düzeltilir:** Metin boyutunda karşılık gelen ikonla değiştirin.

### Gradyan metin ve mor gradyan yok

`no-ai-gradients` · hata · denetlenir

**Kural:** Metin düz renktir. Mor, menekşe ya da çivit gradyan ve bölümlerin arkasında süs amaçlı radyal parıltı yok.

**Neden:** Yapay zekâ üretimi arayüzlerin en tanınan izleridir.

**Nasıl düzeltilir:** Marka rengini düz kullanın; renk anlam taşır (durum, seri, seçim).

### Kartın kenarında renkli kalın çizgi yok

`no-side-stripe` · uyarı · denetlenir

**Kural:** Kartın ya da uyarının tek kenarında kalın renkli çizgi yok.

**Neden:** Yapay zekâ üretimi arayüzün en yaygın vurgusudur ve yuvarlak köşeyle çatışır.

**Nasıl düzeltilir:** Durum rozeti, ikon ya da hafif renkli zemin kullanın.

### Parıltı yalnız grafikte

`glow-in-charts-only` · uyarı · denetlenir

**Kural:** Renkli parıltı gölgesi yalnız grafik dilindedir (puan halkası, grafik çizgisi); düğme, kart ve metin parlamaz.

**Neden:** Her yerde parıltı gürültüdür; veride parıltı gözü sayıya çeker.

**Nasıl düzeltilir:** Kaldırın ya da grafik bileşenini izin listesine yazın.

### Okunur kontrast

`legible-contrast` · uyarı · gözden geçirilir

**Kural:** Metin WCAG AA'yı karşılar (4,5:1, büyük metin 3:1); renkli zeminde gri metin yok.

**Neden:** Renkli zeminde gri soluk görünür ve güneş altında okunmaz.

**Nasıl düzeltilir:** Zemin renginin koyu tonunu ya da beyaza yakın rengi kullanın.

### Her başlığın üstünde ikon kutusu yok

`no-icon-tile-stack` · uyarı · gözden geçirilir

**Kural:** Her birinde yuvarlak ikon kutusu, başlık ve iki satır metin olan aynı kartlardan ızgara bir şablondur, yerleşim değildir. İkonu satır içinde kullanın ya da hiç kullanmayın; öne çıkanı değiştirin.

**Neden:** Her üreticinin varsayılan çıktısıdır ve ürün hakkında hiçbir şey söylemez.

**Nasıl düzeltilir:** İkon yerine gerçek içerikle başlayın (bir sayı, bir ekran görüntüsü, bir örnek).

### Başlık üstünde duyuru hapı yok

`no-announcement-pill` · uyarı · denetlenir

**Kural:** Kahraman başlığının üstünde "✨ Introducing X 2.0" hapı yok; gerçek ve yeni bir habere gidiyorsa sade bir metin bağlantısıdır.

**Neden:** En çok kopyalanan kahraman kalıbıdır; göz başlıktan önce ona takılır ve bir şey bulamaz.

**Nasıl düzeltilir:** Kaldırın ya da tarihli düz bir bağlantıya çevirin.

### Yapay zekâ için ışıltı ikonu yok

`no-sparkle-for-ai` · not · denetlenir

**Kural:** Her yapay zekâ özelliği ışıltıyla işaretlenmez; işlemin ne yaptığını söyleyen ikonu (yaz, özetle, çevir) kullanın ya da hiç kullanmayın.

**Neden:** Işıltı her yapay zekâ ürününde var; düğme hakkında kullanıcıya hiçbir şey söylemez.

**Nasıl düzeltilir:** Fiil ikonuyla (PenLine, ListChecks, Languages) ya da yalnız metinle değiştirin.

### İçeriğin arkasında bulanık renk lekesi yok

`no-blur-blobs` · uyarı · denetlenir

**Kural:** Metin ve kartların arkasında süs olarak büyük bulanık şekil (blur-2xl, blur-3xl) ya da radyal renk lekesi yok.

**Neden:** Leke, üretilmiş sayfaların varsayılan arka planıdır; kontrastı düşürür ve ürün hakkında bir şey söylemez.

**Nasıl düzeltilir:** Tek düz yüzey kullanın ya da görsel olarak gerçek bir ürün ekranı koyun.

### Tek vurgu rengi, anlamı olduğu yerde

`one-accent` · uyarı · gözden geçirilir

**Kural:** Vurgu rengi ekranın küçük bir bölümünü kaplar: ana işlem, seçim ve bir önemli sayı. Yüzey, kenarlık ve etiketler nötr kalır.

**Neden:** Her şey vurgulanınca hiçbir şey öne çıkmaz; ekran gözün ineceği tek yeri kaybeder.

**Nasıl düzeltilir:** Ekran görüntüsünde vurguyu sayın; çerçeveden alıp önemli olan tek şeye taşıyın.

### Genel görsel değil, ürünü gösterin

`show-the-product` · uyarı · gözden geçirilir

**Kural:** Ana görsel ürünün kendisi ya da dünyasından somut bir nesnedir; parlak leke, küre, robot, parlayan beyin ya da hazır devre görseli yok.

**Neden:** Genel görsel her ürün sayfasına konabilir; hiçbir şey anlatmaz ve sayfayı şablon gibi gösterir.

**Nasıl düzeltilir:** Gerçek veriyle gerçek bir ekran ya da ürünün ne yaptığını söyleyen bir nesne kullanın.

### Düğmeler düz renk, gradyan dolgu yok

`no-gradient-buttons` · uyarı · denetlenir

**Kural:** Düğme ve düğme görünümlü bağlantılar temadan tek düz renk kullanır; "Yapay zekâya sor" düğmesi dahil gradyan zemin yok.

**Neden:** İncelediğimiz panellerde en güçlü işler düz ana düğme kullandı; gradyan düğme zayıf işlerin yapay zekâ özelliklerinde çıktı ve ana işlem değil süs gibi okundu.

**Nasıl düzeltilir:** Ana rengi düz dolgu olarak kullanın; yapay zekâ işlemini gradyanla değil fiille belirtin.

## Erişilebilirlik

### Odak halkası yerine yenisi konmadan kaldırılmaz

`focus-ring-removed` · hata · denetlenir

**Kural:** outline-none / outline-hidden yalnız aynı öğede görünür bir focus-visible biçimiyle (ring, outline ya da border) birlikte kullanılır.

**Neden:** Klavye kullanan kişi nerede olduğunu kaybeder. WCAG 2.4.7 (görünür odak), 2.4.11 (odak gizlenmez).

**Nasıl düzeltilir:** focus-visible:ring-2 (ya da bileşenin odak biçimini) ekleyin; Tailwind 4'te outline-none yerine outline-hidden kullanın, zorlanmış renk kipinde çerçeve kalsın. Odağı programla alan diyalog ve açılır pencere kapsayıcıları muaftır.

### Yalnız ikonlu düğmenin adı vardır

`icon-button-name` · hata · denetlenir

**Kural:** Yalnız ikon gösteren düğme ya da bağlantı aria-label (ya da title veya görünmeyen metin) taşır.

**Neden:** Ekran okuyucu amacı olmadan yalnız "düğme" der; WCAG 4.1.2 ad, rol, değer.

**Nasıl düzeltilir:** Eylemi söyleyen bir aria-label ekleyin ("Kelimeyi sil").

## Hareket

### Nabız yalnız canlı veride

`pulse-for-live-only` · not · denetlenir

**Kural:** Nabız atan nokta şu an süren bir işi anlatır; süs için atmaz.

**Neden:** Sahte canlılık gerçek uyarıları görmezden gelmeyi öğretir.

**Nasıl düzeltilir:** Animasyonu süren duruma bağlayın; değilse sabit nokta gösterin.

### Kendiliğinden kayan şerit yok

`no-marquee` · uyarı · denetlenir

**Kural:** İçerik kendiliğinden kaymaz.

**Neden:** Dikkat ister ve içeriğinin yarısını hep gizler.

**Nasıl düzeltilir:** Kaydırılabilen sabit bir satır ya da kısa liste.

### Geçiş tüm özelliklere değil, adlı özelliklere

`no-transition-all` · uyarı · denetlenir

**Kural:** transition-all / transition: all yok; transform ve opacity canlandırılır, renk geçişi adıyla verilir.

**Neden:** transition: all kimsenin istemediği yerleşim ve boyut değişimlerini de canlandırır, kare kaybettirir.

**Nasıl düzeltilir:** transition-colors, transition-opacity, transition-transform ya da transition-[width].

### Arayüzde zıplama ve taşma eğrisi yok

`no-bounce-easing` · uyarı · denetlenir

**Kural:** Denetim, panel ve listelerde animate-bounce ve taşan cubic-bezier yok.

**Neden:** Zıplama çalışılan ekranda oyuncak ve eski görünür, tekrarlanan işi yavaşlatır.

**Nasıl düzeltilir:** Girişte ease-out, çıkışta ease-in, 150–300 ms.

### "Hareketi azalt" tercihine uyulur

`reduced-motion` · not · gözden geçirilir

**Kural:** Süs amaçlı ve büyük hareket prefers-reduced-motion altında durur ya da küçülür (motion-safe: / motion-reduce:).

**Neden:** Hareket denge rahatsızlığı tetikler; WCAG 2.3.3.

**Nasıl düzeltilir:** Uzun ya da döngülü animasyonların başına motion-safe: ekleyin.

### Üzerine gelince büyüme yok

`no-hover-scale` · uyarı · denetlenir

**Kural:** Kart ve düğmeler üzerine gelince büyümez; üzerine gelme renk ya da yüzey değiştirir, basınca hafifçe küçülebilir (0,97–0,98).

**Neden:** Büyüyen öğe komşularını görsel olarak iter, yazıyı bulanıklaştırır ve şablon efekti gibi durur.

**Nasıl düzeltilir:** hover:scale-105 yerine zemin ya da kenarlık basamağı; basma geri bildirimi için active:scale-[0.98].

### Konum değil, transform ve opacity canlandırılır

`no-layout-animation` · uyarı · denetlenir

**Kural:** Geçişler top, left, right, bottom, margin ya da padding canlandırmaz; hareket transform ile yapılır. İlerleme çubuğunda genişlik serbesttir.

**Neden:** Konum ve boşluk değişimi her karede yerleşimi yeniden hesaplatır, yavaş cihazda takılır.

**Nasıl düzeltilir:** translate ve opacity kullanın (transition-transform, transition-opacity).

## Veri ve sayılar

### Sayı neye göre olduğunu söyler

`numbers-with-context` · uyarı · gözden geçirilir

**Kural:** Öne çıkan sayı neyle kıyaslandığını söyler ("geçen haftaya göre −1,2"); zamanla değişiyorsa yakın geçmişini gösterir.

**Neden:** Tek başına "Ortalama sıra 13,8" bunun iyi haber olup olmadığını söylemez.

**Nasıl düzeltilir:** Sayının altına değişimi ve dönemini ekleyin.

### Boş veride boş durum

`empty-states` · uyarı · gözden geçirilir

**Kural:** Veri yoksa bir sonraki adımı söyleyen boş durum gösterilir; boş grafik ya da tirelerle dolu tablo değil.

**Neden:** Boş grafik bozuk görünür.

**Nasıl düzeltilir:** Neden boş olduğunu ve neyin dolduracağını söyleyin (bağlayın, çalıştırın, ilk kontrolü bekleyin).

### Tablo ve göstergelerde eşit genişlikte rakam

`tabular-numbers` · not · gözden geçirilir

**Kural:** Kıyaslanan ya da değişen sayılar (tablo sütunları, göstergeler, sayaçlar, süreler) tabular-nums kullanır; tabloda sağa hizalanır.

**Neden:** Orantılı rakamlar sütunları eğri büğrü yapar, değer değişince sayı zıplar.

**Nasıl düzeltilir:** Hücreye ya da tabloya tabular-nums ekleyin; sayısal sütunda text-end.

### İnandırıcı örnek veri

`no-placeholder-data` · uyarı · denetlenir

**Kural:** Ekran, demo ve görüntülerde Lorem ipsum, John Doe, $123,456 ya da [X] yok; örnek veri ürünün dünyasından gerçek veri gibi görünür.

**Neden:** Dolgu veri bitmiş ekranı taslak gibi gösterir ve gerçek uzunlukların ortaya çıkaracağı yerleşim sorunlarını saklar.

**Nasıl düzeltilir:** Gerçekçi adlar, düzensiz basamaklı tutarlar ve gerçek uzunluklar kullanın.

### Gösterge kartı: etiket, değer, değişim

`stat-card-anatomy` · uyarı · gözden geçirilir

**Kural:** Gösterge kartı bu sırayla üç satırdır: kısa soluk etiket, büyük ve sabit genişlikli rakamlarla değer, sonra dönemiyle değişim ("geçen aya göre +%1,5"). Sayıyla yarışan ikon kutusu, mini grafik ya da emoji yok.

**Neden:** İncelediğimiz profesyonel panellerde en tutarlı örüntü buydu: göz tek sütunda aşağı okur ve değişim dönemi olmadan anlamsızdır.

**Nasıl düzeltilir:** Sırayı etiket → değer → değişim yapın; her değişimin yanına dönemi yazın.

### Grafik tek şeyi öne çıkarır

`chart-highlight-one` · uyarı · gözden geçirilir

**Kural:** Çubuk ve seriler nötrdür; vurgu rengi önemli olana gider (bu dönem, seçili nokta) ve değeri grafiğin üstünde yazılıdır. Kategori grafikleri gökkuşağı değil tek rengin basamaklarıdır.

**Neden:** İncelediğimiz profesyonel işler pasif çubukları açık gri tuttu ve birini yaktı; zayıf işler beş altı renk kullandı, bu da grafiği gösterge tablosunda arama işine çevirir.

**Nasıl düzeltilir:** Bir seri dışında hepsini griye çekin; onu doğrudan etiketleyin; küçük kategorileri "Diğer"de toplayın.

### Serileri grafiğin üstünde etiketleyin

`direct-labels` · not · gözden geçirilir

**Kural:** Üç ya da daha az seride ad ya da değer ayrı bir gösterge yerine çizginin sonuna ya da çubuğun üstüne yazılır.

**Neden:** Gösterge okuru renkleri ileri geri eşleştirmeye zorlar; doğrudan etiket bir kez okunur.

**Nasıl düzeltilir:** Gösterge metnini serisinin yanına taşıyın; göstergeyi yalnız çok seri varken tutun.

### Daha az önemli basamakları soldurun

`dim-secondary-digits` · not · gözden geçirilir

**Kural:** Öne çıkan sayıda kuruş, ondalık ya da birim ikincil metin rengindedir (422.525,82 $ içinde ,82 soluk); önemli kısım önce okunur.

**Neden:** İncelediğimiz en güçlü öne çıkan sayılar süs yerine bu tek ayrıntıyı kullandı.

**Nasıl düzeltilir:** Kesirli kısmı ikincil renkli bir span içine alın; boyut aynı kalsın.

## Yerelleştirme

### Büyük-küçük harf dönüşümü dili belirtir

`locale-aware-case` · uyarı · denetlenir

**Kural:** Arayüz metninde toUpperCase()/toLowerCase() yerine toLocaleUpperCase(dil)/toLocaleLowerCase(dil) kullanılır.

**Neden:** Türkçe i/İ ve ı/I: "istanbul".toUpperCase() "ISTANBUL" verir, "İSTANBUL" değil.

**Nasıl düzeltilir:** Arayüz dilini verin; anahtar ve kimlikler için düz yöntem doğrudur (izin listesine yazın).

### Sayı, tarih ve para dil biçimleyicisinden

`locale-number-format` · uyarı · denetlenir

**Kural:** Arayüzdeki sayılar projenin biçimleyicisinden geçer (açık dil verilmiş Intl). toFixed(), dilsiz toLocaleString() ve "$" + değer yok.

**Neden:** 1,255.00 ile 1.255,00: yanlış ayraç değeri bin kat yanlış okutur; sunucu ve tarayıcı farklı metin üretir.

**Nasıl düzeltilir:** Ortak biçim yardımcısını kullanın; düz toFixed() yalnız makine değerleri için.

### Çoğul, çoğul sistemiyle

`no-naive-plural` · uyarı · denetlenir

**Kural:** sayı === 1 ? "öğe" : "öğeler" ve + "s" yok: çoğul, çeviri sisteminin çoğul biçiminden geçer (trans_choice, ICU, Intl.PluralRules).

**Neden:** Dillerde altıya kadar çoğul türü vardır; yalnız İngilizceye göre yazılmış mantık her çeviriyi bozar.

**Nasıl düzeltilir:** Çeviri katmanının çoğul yardımcısını sayıyla kullanın.

### Parçalardan yapıştırılmış cümle yok

`no-concatenated-translation` · uyarı · denetlenir

**Kural:** Bir cümle yer tutuculu tek bir çeviri anahtarıdır; t('a') + değer + t('b') yazılmaz.

**Neden:** Kelime sırası dile göre değişir: Türkçede fiil sondadır.

**Nasıl düzeltilir:** Tek anahtar: t(':count keywords on page one', { count }).

## Etkileşim

### Süzgeç anında tepki verir

`instant-filters` · not · gözden geçirilir

**Kural:** Süzgeç değeri anında yerel durumda değişir; liste yenilenirken soluklaşmaz; sekmeler önden yüklenir.

**Neden:** Denetim sunucuyu beklerken kıpırdamazsa bozuk hissettirir.

**Nasıl düzeltilir:** İyimser yerel değer, ilerleme çubuğu olmadan arka planda yenileme, sekmelerde önden yükleme.

## Metin

### Pazarlama klişesi yok

`no-buzzwords` · uyarı · denetlenir

**Kural:** "Yeni nesil", "devrim niteliğinde", "kusursuz", "sınırları zorlayan", "üst düzey deneyim" yok. Ne yaptığını söyleyin, varsa sayıyla.

**Neden:** Bu kelimeler üretilmiş metnin anında fark edilen izleridir ve ölçülebilir bir şey vaat etmez.

**Nasıl düzeltilir:** İddiayı ölçülmüş bilgiyle değiştirin.

### Düğme ne yaptığını söyler

`specific-action-labels` · uyarı · denetlenir

**Kural:** "Gönder", "Tamam", "Buraya tıklayın", "Evet/Hayır" yok: etiket eylemi ve nesnesini söyler ("Değişiklikleri kaydet", "Kelimeyi sil").

**Neden:** Genel etiket tüm pencereyi okutur ve yıkıcı düğmeye yanlışlıkla basmayı kolaylaştırır.

**Nasıl düzeltilir:** Fiil + nesne, yalnız ilk kelime büyük.

### Hata ne olduğunu ve ne yapılacağını söyler

`error-copy` · uyarı · denetlenir

**Kural:** "Hay aksi", "Bir şeyler ters gitti", "Bir hata oluştu", "Geçersiz giriş" yok: sorunu ve sonraki adımı söyleyin.

**Neden:** Belirsiz hata kişiyi takılı bırakır ve destek talebi doğurur (GOV.UK hata mesajı rehberi).

**Nasıl düzeltilir:** "Geçmiş bir tarih girin", "Dosya 5 MB'tan büyük: daha küçük bir dosya seçin".

### Üç nokta yerine üç nokta karakteri

`ellipsis-character` · not · denetlenir

**Kural:** "Yükleniyor…", "Ara…" tek … karakteriyle yazılır.

**Neden:** Üç ayrı nokta farklı satır kırar ve düzgün yazının yanında yazım hatası gibi durur.

**Nasıl düzeltilir:** Arayüz metinlerinde ... yerine … yazın.

### Arayüz metninde ünlem yok

`no-exclamation-copy` · uyarı · denetlenir

**Kural:** Etiket, sayı, bildirim ve başlıklar düz söyler: "!" ya da "!!" yok, "+12%!!" gibi değişimlerde de.

**Neden:** Ünlem her mesajı aynı derecede acil gösterir ve üretilmiş metnin güçlü bir izidir.

**Nasıl düzeltilir:** İşareti kaldırın; değişime karşılaştırmasını yazın ("geçen aya göre +%12").

### Başlık kullanıcıyı değil sayfayı adlandırır

`no-greeting-headline` · uyarı · denetlenir

**Kural:** Çalışılan ekranın başlığı "Tekrar hoş geldin, Ad" ya da "Günaydın" değildir; başlık sayfanın ne gösterdiğini söyler.

**Neden:** Selamlama ekranın en değerli satırını alır ve yüzüncü ziyarette hiçbir şey söylemez.

**Nasıl düzeltilir:** Başlık olarak sayfayı ya da dönemi yazın ("Genel bakış · bu hafta").

### Kaynağı olan sosyal kanıt

`no-unsourced-proof` · uyarı · denetlenir

**Kural:** "10.000+ ekip güveniyor", beş yıldız sırası ya da kaynaksız avatar yığını yok; müşterileri ya da puan sitesini adıyla yazın ya da çıkarın.

**Neden:** Yuvarlak ve kaynaksız sayılar ziyaretçinin ilk inanmadığı şeydir ve sayfanın geri kalanını da uydurma gösterir.

**Nasıl düzeltilir:** Gerçek sayıyı kaynağıyla ("App Store'da 4,8, 312 puan") ya da adı verilen bir müşteriyi gösterin.
