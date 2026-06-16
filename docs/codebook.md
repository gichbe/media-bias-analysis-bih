# Kodbook za anotaciju političke pristrasnosti
**Verzija 1.0** — referentni dokument za ručnu anotaciju i LLM evaluaciju

---

## 1. Svrha dokumenta

Ovaj kodbook definira **četiri dimenzije** političke pristrasnosti koje se mjere u svakom članku. Svaka dimenzija se ocjenjuje **nezavisno**. Cilj je da dva nezavisna anotatora, koristeći samo ovaj dokument, dođu do što sličnijih ocjena (inter-annotator agreement).

Isti kodbook se koristi i kao osnova za prompt LLM modela, čime se osigurava poredivost.

---

## 2. Jedinica analize

**Jedan članak = jedna jedinica analize.**

Anotira se cjelokupan sadržaj članka uključujući:
- naslov (title)
- podnaslov / lead
- glavno tijelo teksta
- citate i izvore navedene u članku

Ne anotira se: komentari čitalaca, povezani članci, reklamni sadržaj.

---

## 3. Dimenzije pristrasnosti

### 3.1. Dimenzija: TON (sentiment prema subjektu)

**Pitanje:** Kakav je opći ton članka prema dominantnom političkom akteru/grupi u tekstu?

**Skala:** Cjelobrojna, od **−2 do +2**

| Vrijednost | Oznaka | Opis |
|---|---|---|
| −2 | Vrlo negativan | Otvoreno neprijateljski, koristi pejorativne izraze, optužujući ton, dominantno kritika bez konteksta |
| −1 | Negativan | Kritičan, naglašava slabosti, propuste ili greške, ali bez otvorenog napada |
| 0 | Neutralan | Informativan, faktografski, bez emocionalno obojenih opisa |
| +1 | Pozitivan | Pohvalan, naglašava uspjehe ili dobre strane, ali bez pretjerivanja |
| +2 | Vrlo pozitivan | Otvoreno hvali, koristi superlative, idealizuje aktera |

**Identifikacija dominantnog subjekta:**
- Ako se u članku spominje više aktera, dominantan je onaj kojem je posvećeno **najviše prostora** (broj rečenica/paragrafa)
- Ako su dva aktera podjednako zastupljena, anotira se ton prema akteru spomenutom u naslovu
- Ako je nemoguće odrediti dominantnog aktera, ostavi polje prazno i označi članak kao "neaplikabilan za ton"

**Primjeri:**
- *"Premijer X je nesposobno odgovorio na krizu i ponovo razočarao građane."* → **−2**
- *"Premijer X nije uspio osigurati većinu u parlamentu."* → **−1**
- *"Premijer X je danas održao konferenciju za medije."* → **0**
- *"Premijer X je predstavio plan koji su ekonomisti ocijenili pozitivno."* → **+1**
- *"Premijer X je još jednom dokazao da je vizionarski lider."* → **+2**

---

### 3.2. Dimenzija: FRAMING (način uokvirivanja)

**Pitanje:** Iz koje perspektive je događaj predstavljen?

**Skala:** Kategorička

| Kategorija | Opis |
|---|---|
| `konflikt` | Naglasak na sukobu, podjelama, "mi vs. oni" narativ |
| `odgovornost` | Naglasak na tome ko je odgovoran/kriv za situaciju |
| `ekonomski` | Posljedice se predstavljaju primarno kroz ekonomsku prizmu |
| `ljudski_interes` | Fokus na pojedinačnim sudbinama, emocijama, ličnim pričama |
| `moralni` | Pitanje se postavlja kao moralna/etička dilema |
| `proceduralni` | Fokus na proceduri, zakonima, institucionalnom procesu |
| `nacionalni` | Naglasak na etničkom/nacionalnom identitetu ili interesu |
| `neutralan` | Bez izraženog uokvirivanja, čisto informativno |

**Pravilo:** Ako se više framing-a pojavljuje, biraj **dominantan** (onaj koji zauzima više prostora ili je u naslovu).

**Primjeri:**
- Naslov *"Bošnjaci i Srbi se ponovo ne mogu dogovoriti oko zakona"* → `konflikt` ili `nacionalni`
- Naslov *"Cijene struje rastu, građani u nevolji"* → `ekonomski` ili `ljudski_interes`
- Naslov *"Ustavni sud potvrdio proceduralnu ispravnost zakona"* → `proceduralni`

---

### 3.3. Dimenzija: BALANSIRANOST (multi-perspectivity)

**Pitanje:** Da li članak predstavlja različite strane priče?

**Skala:** Cjelobrojna, od **0 do 2**

| Vrijednost | Opis |
|---|---|
| 0 | Jednostrano — predstavljena samo jedna strana (jedan izvor, jedna pozicija) |
| 1 | Djelimično balansirano — spominju se i druge strane, ali površno |
| 2 | Balansirano — više strana dobija približno jednak prostor i argumente |

**Kako prepoznati:**
- Broj različitih izvora citiranih u članku
- Da li su navedeni i suprotstavljeni stavovi
- Da li autor sam donosi zaključke ili pušta činjenice/izvore da govore

---

### 3.4. Dimenzija: PRISTRASNOST PREMA POLITIČKOJ OPCIJI

**Pitanje:** Da li članak favorizuje neku političku stranu/blok?

**Skala:** Kategorička

| Kategorija | Opis |
|---|---|
| `pro_vlast` | Naklonjen vladajućim strukturama (na nivou na kojem se događaj odvija) |
| `pro_opozicija` | Naklonjen opozicionim strujama |
| `pro_bosnjacka_opcija` | Naklonjen bošnjačkim političkim akterima/interesima |
| `pro_srpska_opcija` | Naklonjen srpskim političkim akterima/interesima (RS, SNSD itd.) |
| `pro_hrvatska_opcija` | Naklonjen hrvatskim političkim akterima/interesima (HDZ BiH itd.) |
| `pro_gradjanska_opcija` | Naklonjen građanskim/multietničkim opcijama |
| `nejasno` | Ne može se utvrditi jasna preferencija |
| `neutralan` | Bez naklonosti, jasno faktografski |

---

## 4. Procedura anotacije

1. Pročitaj cijeli članak jednom bez ocjenjivanja
2. Pročitaj članak drugi put i popuni dimenzije ovim redoslijedom:
   - Balansiranost (lakša, brojanje izvora)
   - Framing (na osnovu naslova i lead-a)
   - Ton (na osnovu pridjeva, glagola, opisa subjekta)
   - Pristrasnost prema političkoj opciji
3. Ako si u nedoumici između dvije vrijednosti, biraj **manje ekstremnu** (npr. −1 umjesto −2)
4. Vrijeme po članku: oko **3–5 minuta**

---

## 5. Inter-annotator agreement

- Svaki članak nezavisno anotiraju **3 (ili 4) anotatora**
- Same anotacije se obavljaju **potpuno nezavisno** — nijedan anotator ne vidi tuđe ocjene dok ne završi sve članke

### 5.1. Statističke mjere slaganja

Pošto su anotatora više od 2, ne primjenjuje se klasična Cohen's Kappa. Umjesto toga:

- **Fleiss' kappa (κ_F)** — za kategoričke dimenzije (framing, political_lean). Direktno proširenje Cohen's Kappa na više anotatora.
- **Krippendorff's alpha (α)** — za ordinalne dimenzije (ton, balansiranost). Podržava ordinalne težine, što znači da se veće razlike u ocjeni (npr. anotator A: +2, anotator B: −2) penaliziraju više od manjih (A: +1, B: 0).

Dopunska analiza:

- **Pairwise Cohen's Kappa** između svih parova anotatora — identifikuje da li neki anotator sistemski odstupa od ostalih (signal da nije pravilno razumio kodbook ili da je pristrasan)

### 5.2. Interpretacija vrijednosti

| Vrijednost (κ_F ili α) | Interpretacija |
|---|---|
| < 0.40 | slabo slaganje — kodbook treba reviziju |
| 0.40 – 0.60 | umjereno slaganje |
| 0.60 – 0.80 | znatno slaganje (**ciljni opseg**) |
| > 0.80 | gotovo savršeno slaganje |

### 5.3. Konstrukcija "gold standard" anotacije

Za poređenje sa LLM modelima koristi se **konsenzus anotacija** dobijena agregacijom svih anotatora:

- **Kategoričke dimenzije** (framing, political_lean): većinsko glasanje (mode). U slučaju izjednačenja, anotatori naknadno diskutuju i postižu konsenzus.
- **Ordinalne dimenzije** (ton, balansiranost): medijan ocjena, sa zaokruživanjem prema neutralnoj vrijednosti (0) u slučaju neslaganja.

---

## 6. Anti-pravila (česte greške)

- ❌ **Ne anotirati prema vlastitom političkom stavu** — anotira se ŠTA je u tekstu, ne šta se misli o akteru
- ❌ **Ne pretpostavljati šira znanja** — anotira se samo na osnovu informacija u članku
- ❌ **Ne anotirati naslov odvojeno od teksta** — jedinica je cijeli članak, ali naslov ima posebnu težinu
- ❌ **Ne miješati ton i pristrasnost** — članak može biti negativan prema X, a ne biti pristrasan prema političkoj opciji X

---

## 7. Format izlaza (CSV)

Svaki anotirani članak ima sljedeća polja:

| Polje | Tip | Opis |
|---|---|---|
| `article_id` | string | Jedinstveni ID članka |
| `portal` | string | Naziv portala |
| `url` | string | URL članka |
| `title` | string | Naslov |
| `date_published` | date | Datum objave |
| `annotator_id` | string | ID anotatora (A1, A2, LLM_GPT4, LLM_CLAUDE...) |
| `tone` | int | −2 do +2 |
| `framing` | string | Jedna od kategorija |
| `balance` | int | 0, 1, 2 |
| `political_lean` | string | Jedna od kategorija |
| `dominant_actor` | string | Ime dominantnog aktera/grupe |
| `confidence` | int | 1–5, koliko je anotator siguran |
| `notes` | string | Dodatne napomene (opciono) |
