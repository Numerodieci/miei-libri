# Pubblicare "I Miei Libri" su HTTPS e provarla su telefono

Questa guida serve per mettere online l'app e verificare l'installazione su un
Android e un iPhone reali. Il progetto è un sito statico: **non serve compilare
nulla**, si pubblica la cartella così com'è.

> Nota importante: il vecchio indirizzo `numerodieci.github.io/miei-libri` oggi
> risponde **404 Not Found**. Il link nel QR code della home è stato reso
> dinamico, quindi si aggiorna da solo qualunque sia il nuovo indirizzo: non
> dovrai modificare il codice quando cambi dominio.

---

## 1. Scegli dove pubblicare

Tutte e tre le opzioni danno **HTTPS automatico e gratuito**.

### Opzione A — GitHub Pages (repository già pronto in questa cartella)

Questa cartella è già un repository Git con il primo commit completo, quindi
non serve caricare i file uno per uno dal sito di GitHub: bastano tre passaggi.

**1. Crea il repository vuoto su GitHub**

1. Accedi a <https://github.com> → **+** in alto a destra → **New repository**.
2. Nome consigliato: `miei-libri`.
3. Visibilità: **Public** (con il piano gratuito GitHub Pages pubblica solo
   repository pubblici).
4. **Non** aggiungere README, licenza o `.gitignore`: devono restare vuoti,
   altrimenti il primo `push` viene rifiutato.
5. Premi **Create repository** e copia l'indirizzo che compare, del tipo
   `https://github.com/<tuo-utente>/miei-libri.git`.

**2. Collega e carica (Git Bash, nella cartella del sito)**

```bash
cd "C:/Users/PC01/Desktop/miei-libri-main"
git remote add origin https://github.com/<tuo-utente>/miei-libri.git
git push -u origin main
```

Se il `push` chiede le credenziali, usa il tuo nome utente GitHub e come password
un **Personal Access Token** (GitHub → *Settings → Developer settings → Personal
access tokens → Tokens (classic) → Generate new token*, spunta lo scope `repo`).
La password normale dell'account non è più accettata da GitHub.

Al primo `push` Git potrebbe chiedere chi sei. Per firmare i commit con il tuo
nome (facoltativo, si può fare anche dopo):

```bash
git config user.name "Nome Cognome"
git config user.email "la-tua-email@example.com"
```

**3. Attiva GitHub Pages**

1. Nel repository: **Settings → Pages**.
2. In *Build and deployment* scegli **Deploy from a branch**.
3. Branch `main`, cartella `/ (root)`, poi **Save**.
4. Attendi 1–2 minuti: il sito sarà su
   `https://<tuo-utente>.github.io/miei-libri/`.
5. Se il repository si chiama `<tuo-utente>.github.io`, l'indirizzo sarà invece
   `https://<tuo-utente>.github.io/`.

Il file `.nojekyll` presente nella cartella dice a GitHub di pubblicare i file
così come sono, senza rielaborarli: è già committato e non va toccato.

Tutti i percorsi interni sono relativi (`icons/…`, `splash/…`, `./index.html`,
`scope: "./"`), quindi il sito funziona anche nella sottocartella del repository.

Aggiornamenti successivi: dopo aver modificato i file, esegui

```bash
git add -A
git commit -m "Descrizione della modifica"
git push
```

GitHub ripubblica da solo in un minuto o due. Ricordati di alzare `CACHE_NAME`
in `sw.js` quando cambi contenuti, come spiegato al punto 5.

### Opzione B — Netlify Drop (la più veloce, trascini la cartella)

1. Apri <https://app.netlify.com/drop> e accedi.
2. Trascina l'intera cartella `miei-libri-main` nella pagina.
3. Ottieni subito un indirizzo `https://<nome>.netlify.app` con HTTPS.
4. In *Site configuration → Change site name* puoi scegliere un nome più bello
   (per esempio `mieilibri`).
5. Le regole di cache sono già nel file `netlify.toml`.

Aggiornamenti: trascina di nuovo la cartella nella sezione *Deploys*.

### Opzione C — Cloudflare Pages

1. Apri <https://dash.cloudflare.com> → **Workers & Pages → Create → Pages →
   Upload assets**.
2. Carica la cartella del progetto e pubblica.
3. L'indirizzo sarà `https://<progetto>.pages.dev`.
4. Le regole di cache sono nel file `_headers`.

### Dominio personalizzato (facoltativo ma consigliato)

1. Registra un dominio (per esempio `imieilibri.it`) presso un registrar.
2. Nel pannello dell'hosting aggiungi il dominio personalizzato e segui le
   istruzioni (record `CNAME` verso l'indirizzo fornito).
3. Attendi la propagazione DNS (da pochi minuti a qualche ora): il certificato
   HTTPS viene emesso automaticamente.

Un dominio proprio serve anche in futuro per Google Play: la verifica del sito
(`/.well-known/assetlinks.json`) richiede di poter pubblicare un file nella
radice del dominio.

---

## 2. Checklist di prova su Android (Chrome)

Da fare con un telefono vero, non con l'emulatore.

- [ ] Apri l'indirizzo in Chrome e attendi qualche secondo (la prima visita
      salva i file per l'uso offline).
- [ ] Menu `⋮` → dovrebbe comparire **Installa app** (o *Aggiungi a Home*).
      In alternativa usa il pulsante **📲 Installa l'app** nella home.
- [ ] L'icona appare nella schermata Home con il nome "I Miei Libri".
- [ ] Aprendola dall'icona non si vede la barra degli indirizzi.
- [ ] Attiva la **modalità aereo** e riapri l'app: la home deve caricarsi.
- [ ] Apri una materia, torna indietro, apri il quiz e completa una partita.
- [ ] Chiudi e riapri l'app: i punteggi del quiz sono ancora presenti.
- [ ] Ruota il telefono: il layout resta leggibile.
- [ ] Menu `⋮` → **Condividi l'app** nella home: il QR code e il link mostrano
      l'indirizzo reale del sito.

## 3. Checklist di prova su iPhone (Safari)

- [ ] Apri l'indirizzo in **Safari** (non in Chrome: su iOS l'installazione
      funziona solo da Safari).
- [ ] Tocca **Condividi** → **Aggiungi a Home** → *Aggiungi*.
- [ ] L'icona appare nella schermata Home.
- [ ] Aprendola dall'icona l'app occupa tutto lo schermo, senza barra di Safari.
- [ ] Attiva la **modalità aereo** e riapri l'app: deve funzionare offline.
- [ ] Prova il quiz e verifica che i punteggi restino dopo la chiusura.

> Su iOS, se l'app non viene aperta per molte settimane, il sistema può liberare
> lo spazio della cache offline. In quel caso basta riaprire l'app con una
> connessione attiva: i file vengono salvati di nuovo.

## 4. Controlli tecnici facoltativi

- **Chrome su desktop**: apri l'indirizzo → `F12` → *Application* →
  *Manifest* (deve risultare installabile) e *Service Workers*
  (deve essere `activated and is running`).
- **Lighthouse**: `F12` → *Lighthouse* → sezione *PWA*.
- **PageSpeed Insights**: <https://pagespeed.web.dev> con il tuo indirizzo.

## 5. Quando aggiorni l'app

1. Modifica i file.
2. In `sw.js` cambia `CACHE_NAME` (per esempio da `miei-libri-v13` a
   `miei-libri-v14`). Serve a far scaricare subito la nuova versione anche a chi
   ha già installato l'app.
3. Ricarica i file sull'hosting.

## 5bis. Strumenti di manutenzione

Nella cartella `tools/` ci sono gli script che hanno generato gli asset. Servono
solo quando cambi qualcosa (per esempio aggiungi una materia o un font nuovo):

| Comando | Cosa fa |
| --- | --- |
| `python tools/check-pwa.py` | Verifica manifest, icone, precache, font esterni e link rotti. Esce con 0 se va tutto bene. |
| `node tools/verify-offline.mjs` | Prova reale offline con Chrome: avvia il server, installa il service worker, spegne il server e verifica che pagine, viewer e font continuino a funzionare. |
| `python tools/localize-fonts.py` | Scarica i font richiesti dalle pagine e rigenera `fonts.css`. |
| `python tools/build-icons.py` | Rigenera icone e splash a partire da `icons/icon-512.png`. |
| `python tools/sync-precache.py` | Riscrive l'elenco dei file da salvare offline dentro `sw.js`. |

Dopo aver aggiunto o rinominato file, esegui `sync-precache.py` e poi
`check-pwa.py`.

## 6. Prossimo passo per gli store

- **Microsoft Store (Windows)**: il pacchetto si crea con PWABuilder a partire
  dall'indirizzo HTTPS, senza modificare il codice.
- **Google Play (Android)**: serve la verifica del dominio tramite
  `/.well-known/assetlinks.json` con l'impronta SHA-256 della chiave di firma
  dell'app. Va preparata solo quando avrai l'account Play e la chiave.
