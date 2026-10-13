# Mastodon RSS

## Obiettivo del progetto

Creare un feed RSS tramite **Cloudflare Workers**, scritto in Python, che raccolga i post pubblicati su Mastodon con un determinato hashtag e li filtri in base alla lingua.

Il progetto non prevede un'interfaccia web: l'obiettivo è ottenere un feed RSS utilizzabile direttamente da un lettore di feed.

## 1. Ambiente di sviluppo

- Sistema operativo: Fedora Linux 44.
- Linguaggio: Python.
- Gestione di Python e delle dipendenze: `uv`.
- Esecuzione degli strumenti di sviluppo: `uvx` e PyWrangler.
- Ambiente di destinazione: Cloudflare Workers con runtime Python.

Durante la configurazione abbiamo installato Python 3.12 e l'interprete WebAssembly richiesto da PyWrangler per eseguire il progetto nell'ambiente Workers.

## 2. Inizializzazione del progetto

Abbiamo creato il progetto nella directory:

`/home/paolo/bin/python/mastodon-rss`

I principali file sono:

- `src/entry.py`: contiene la logica principale del Worker.
- `src/submodule.py`: file aggiuntivo generato durante l'inizializzazione.
- `wrangler.jsonc`: configurazione di Cloudflare Workers.
- `pyproject.toml`: metadati del progetto e dipendenze di sviluppo.
- `.python-version`: versione Python scelta per il progetto.

Il server di sviluppo viene avviato con `uv run pywrangler dev`.

## 3. Collegamento alle API di Mastodon

Abbiamo scelto come istanza di riferimento:

`https://mastodon.social`

Il Worker interroga l'API pubblica delle timeline per hashtag, senza richiedere autenticazione per l'accesso ai post pubblici disponibili.

Abbiamo verificato con `curl` che l'API restituisce i post e le relative informazioni, tra cui data di pubblicazione, lingua e URL.

L'istanza può includere post provenienti da altri server federati, nei limiti dei contenuti che conosce.

## 4. Generazione del feed RSS

Il Worker genera dinamicamente un documento RSS 2.0 a partire dai post ricevuti da Mastodon.

Per ciascun post vengono utilizzati, quando disponibili:

- titolo identificativo dell'autore;
- collegamento al post originale;
- identificativo univoco;
- contenuto;
- data di pubblicazione.

La risposta viene restituita con il tipo di contenuto `application/rss+xml`.

## 5. Filtri e parametri

L'indirizzo del feed accetta due parametri:

- `tag`: hashtag da cercare, senza obbligo di inserire `#`;
- `lang`: lingua dei post da includere.

Se i parametri non vengono specificati, vengono utilizzati i valori predefiniti:

- Hashtag: `linux`
- Lingua: `it`

Esempi di utilizzo in locale:

- `/feed.xml?tag=linux&lang=it`
- `/feed.xml?tag=photography&lang=en`

Sono presenti controlli di validazione sui parametri per rifiutare hashtag o codici lingua non validi.

## 6. Filtraggio e paginazione

L'API di Mastodon consente di richiedere al massimo 40 post per singola richiesta.

Abbiamo quindi previsto una paginazione tramite il parametro `max_id`, che permette di recuperare post meno recenti.

La versione attuale della funzione di recupero:

- richiede fino a 40 post per pagina;
- mantiene soltanto quelli nella lingua richiesta;
- evita duplicati usando l'identificativo del post;
- ordina i risultati dal più recente al meno recente;
- restituisce al massimo 30 post;
- esegue al massimo 5 richieste API per generare il feed.

In questo modo può esaminare fino a 200 post per trovare i 30 risultati desiderati. Se non ne trova abbastanza, restituisce quelli disponibili.

## 7. Stato attuale

**Funzionalità implementate e verificate:**

- progetto Python Workers inizializzato;
- accesso all'API pubblica di Mastodon;
- filtraggio dei post per lingua;
- selezione dell'hashtag tramite parametro URL;
- generazione del feed RSS;
- paginazione per superare il limite di 40 post per richiesta;
- limite massimo di 30 elementi nel feed;
- validazione dei parametri e gestione degli errori.

Il feed è attualmente generato a ogni richiesta, interrogando Mastodon in tempo reale.

## 8. Funzionalità ancora da valutare

- **Cache e persistenza:** evitare di interrogare Mastodon a ogni richiesta e valutare come conservare i post tra un aggiornamento e l'altro.
- **Aggiornamento automatico:** configurare un aggiornamento periodico, ad esempio ogni 30 minuti, se necessario.
- **Pubblicazione:** distribuire il Worker su Cloudflare e verificare il feed attraverso l'indirizzo pubblico.
- **Test del feed:** verificare il comportamento con hashtag poco attivi, lingue diverse e risposte API vuote o non valide.

## 9. Note tecniche

- `uv` gestisce interpreti, ambienti virtuali e dipendenze.
- `uvx` (abbreviazione di "uv tool run") esegue strumenti Python senza richiedere necessariamente un'installazione permanente nel progetto.
- Il runtime Python di Workers utilizza un ambiente WebAssembly: alcuni moduli specifici di Workers non possono essere importati ed eseguiti direttamente con il normale interprete Python locale.
- La configurazione locale di sviluppo è distinta dalla pubblicazione effettiva su Cloudflare.

Per creare il progetto python:
`uvx --from workers-py pywrangler init`

Per provare il worker
`uv run pywrangler dev`

Per installare nell'ambiente del progetto python
`uv python install 3.12`

```
paolo@fedora:~/bin/python/mastodon-rss$ uv python list
cpython-3.14.7-linux-x86_64-gnu          /usr/bin/python3.14
cpython-3.14.7-linux-x86_64-gnu          /usr/bin/python3 -> python3.14
cpython-3.14.7-linux-x86_64-gnu          /usr/bin/python -> ./python3
pyodide-3.14.2-emscripten-wasm32-musl    /home/paolo/.local/share/uv/python/pyodide-3.14.2-emscripten-wasm32-musl/python
cpython-3.12.14-linux-x86_64-gnu         /home/paolo/.local/bin/python3.12 -> /home/paolo/.local/share/uv/python/cpython-3.12-linux-x86_64-gnu/bin/python3.12
cpython-3.12.14-linux-x86_64-gnu         /home/paolo/.local/share/uv/python/cpython-3.12-linux-x86_64-gnu/bin/python3.12
```

Documentazione sui python worker
https://developers.cloudflare.com/workers/languages/python/

# Ruolo di nodejs

Sì, ma con una distinzione importante: Node.js fa parte degli strumenti che possono essere coinvolti nello sviluppo, ma il nostro codice applicativo è Python e viene eseguito nel runtime Python di Cloudflare Workers.

Vediamo come sono collegati i componenti del progetto.

## Come funziona il nostro ambiente

Il tuo ambiente Fedora

Terminale e strumenti di sviluppo

### uv / uvx

Gestiscono Python, ambienti virtuali e strumenti.

### Node.js

Può fornire l'ambiente JavaScript necessario ad alcuni strumenti dell'ecosistema Cloudflare.

### PyWrangler

Strumento di sviluppo e gestione del Worker Python

Python Workers Runtime

Esegue il nostro codice Python, compreso l'accesso all'API di Mastodon e la generazione RSS.

## Quindi, a cosa serve Node.js?

Node.js è un ambiente di esecuzione JavaScript. Nell'ecosistema Cloudflare, diversi strumenti di sviluppo e pacchetti possono utilizzarlo o dipendere da strumenti JavaScript.

Nel nostro progetto, però:

- Il codice applicativo è Python: il file `src/entry.py` contiene tutta la logica del feed RSS.
- PyWrangler è lo strumento di sviluppo: serve a eseguire e gestire il Worker durante lo sviluppo e la pubblicazione.
- Il runtime Python di Workers è l'ambiente di esecuzione: è qui che gira il codice Python, non nel normale interprete Python di Fedora e nemmeno in Node.js.
- Node.js non è un componente del nostro feed: non abbiamo scritto codice JavaScript né realizzato un'applicazione Node.js.

Una precisazione: dal solo codice del progetto non possiamo concludere se la versione di Node.js installata venga effettivamente invocata da PyWrangler o da una sua dipendenza durante ogni operazione. Per verificarlo dovremmo esaminare gli strumenti e le dipendenze installati.

In sintesi: Python è il linguaggio del progetto, Workers è la piattaforma di destinazione e PyWrangler è lo strumento di sviluppo. Node.js può essere una dipendenza dell'infrastruttura di sviluppo, ma non è necessario trasformare il nostro progetto in un'applicazione Node.js.

## Workers
PyWrangler mette a disposizione i comandi di Wrangler per gestire Workers KV, ovviamente occorre **autenticarsi su Cloudflare**

```
paolo@fedora:~/bin/python/mastodon-rss$ uv run pywrangler whoami
INFO     Passing command to npx wrangler: npx --yes wrangler whoami                                                                                           

 ⛅️ wrangler 4.149.0
────────────────────
Getting User settings...
You are not authenticated. Please run `wrangler login`.
To deploy without logging in, run a command like `wrangler deploy --temporary` to use a temporary preview account.
```

### Dopo l'autenticazione

Passiamo alla creazione del namespace KV.

## Passo 3 — Crea il namespace

Esegui questo comando:

```
uv run pywrangler kv namespace create FEED_CACHE
```

Cloudflare creerà un archivio KV chiamato `FEED_CACHE` e dovrebbe restituire un identificativo simile a:

```
id = "xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx"
```

L'ID sarà necessario per collegare l'archivio al Worker tramite `wrangler.jsonc`.

### Deploy su cloudflare
paolo@fedora:~/bin/python/mastodon-rss$ uv run pywrangler deploy
INFO     Passing command to npx wrangler: npx --yes wrangler deploy                                                                                           

 ⛅️ wrangler 4.149.0
────────────────────
Attaching additional modules:
┌────────────────────┬────────┬────────────┐
│ Name               │ Type   │ Size       │
├────────────────────┼────────┼────────────┤
│ submodule.py       │ python │ 0.05 KiB   │
├────────────────────┼────────┼────────────┤
│ Vendored Modules   │        │ 107.52 KiB │
├────────────────────┼────────┼────────────┤
│ Total (31 modules) │        │ 107.57 KiB │
└────────────────────┴────────┴────────────┘
Total Upload: 113.47 KiB / gzip: 32.12 KiB
Worker Startup Time: 767 ms
Your Worker has access to the following bindings:
Binding                                                Resource          
env.FEED_CACHE (f15821b555704e19b52ca9afbb39ecfa)      KV Namespace      

Uploaded mastodon-rss (7.95 sec)
Deployed mastodon-rss triggers (1.99 sec)
  https://mastodon-rss.macchia.workers.dev
Current Version ID: 517c8a92-4e2e-4995-aa94-9509a2f9f025


# Una nota importante:
In sintesi: un Worker, un namespace KV, tante chiavi di cache quante sono le combinazioni di hashtag e lingua richieste. E puoi aggiungere nuovi hashtag semplicemente usando URL diversi, senza modificare il codice o creare altri Worker. 
Quindi il worker è multihashtag pur essendo un singolo worker e con un solo namespace, il segreto sta nell'inizializzare diverse chiavi di cache:
`cache_key = f"feed:{hashtag.lower()}:{language}"`

Tra l'altro la cache del namespace si può vedere sulla console di Cloudflare nella sezione 
Storage & databases -> Workers KV


