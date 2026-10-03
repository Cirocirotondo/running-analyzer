# Handover: contesto del progetto Running Analyzer

Documento di passaggio di consegne per una sessione di Claude Code aperta in locale (WSL), scritto il 2026-10-03. Riassume tutto ciò che è stato discusso e deciso nelle sessioni cloud del progetto "Run biokynematic analysis". Leggilo per intero prima di lavorare; dopo, le fonti di verità restano il codice, `GLOSSARY.md` e `docs/adr/`.

## 1. Chi e cosa

- **Proprietario:** Simone (GitHub `Cirocirotondo`). Scrive in italiano, a volte in inglese: rispondi nella lingua del suo ultimo messaggio (di default italiano, vedi `CLAUDE.md`).
- **Obiettivo:** un software che analizza la tecnica di corsa di una persona a partire da video su tapis roulant (vista laterale e posteriore), estrae lo skeleton con keypoint e angoli articolari, dà consigli sulla tecnica e, in una fase successiva, suggerimenti sulle scarpe da corsa.
- **Rilascio previsto:** prima solo interfaccia web durante lo sviluppo. Quando il software funziona bene: deploy di produzione su server e app mobile (iOS/Android) che usano lo stesso backend.

## 2. Stato attuale del repository

- Repo: https://github.com/Cirocirotondo/running-analyzer, branch `main`.
- Clone locale: `/home/simone/projects/running-analyzer` dentro WSL (Ubuntu 24.04).
- Contenuto: solo il commit iniziale, **nessun codice applicativo ancora**.
  - `README.md` con obiettivo e stack proposto.
  - `CLAUDE.md` con le convenzioni (rispondere in italiano, glossario in `GLOSSARY.md`, ADR in `docs/adr/`, skill da non modificare a mano).
  - `.gitignore` per Python, Node, `.env`, `data/` e file video (`*.mp4`, `*.mov`, `*.avi`).
  - `.claude/skills/`: le 27 skill di Matt Pocock (cartelle `engineering/` e `productivity/` di `mattpocock/skills`, commit d81f3a1, licenza MIT), tra cui `grill-with-docs`, `grilling`, `domain-modeling`, `tdd`, `prototype`, `to-spec`, `to-tickets`, `handoff`.
- `GLOSSARY.md` e `docs/adr/` **non esistono ancora**: vanno creati al primo termine risolto e alla prima decisione da registrare.
- Non è ancora stato lanciato `/setup-matt-pocock-skills` (configura issue tracker, label di triage e layout dei documenti di dominio). È il primo passo consigliato, da fare una volta sola.

## 3. Ambiente di sviluppo (deciso)

- PC Windows con **WSL2 + Ubuntu 24.04**. Simone ha scelto Windows invece della partizione Ubuntu nativa del PC perché ci tiene altri programmi in parallelo; la partizione Ubuntu resta piano B (per esempio se la GPU in WSL desse problemi).
- Codice e video **dentro il filesystem di WSL**, mai su `C:\` (lì Docker e Python sono molto più lenti).
- Docker Desktop con backend WSL2; VS Code con l'estensione WSL.
- Il PC ha una **GPU NVIDIA**: CUDA funziona dentro WSL2 con il solo driver Windows aggiornato, senza driver in Ubuntu.
- Suggerito di limitare RAM e CPU di WSL in `%UserProfile%\.wslconfig` (per esempio `memory=16GB`).
- Nota: l'app desktop Claude su Windows non accetta cartelle WSL (`\\wsl.localhost\...`) per il controllo remoto, perché le considera cartelle di rete. Per questo si lavora con Claude Code avviato direttamente dentro WSL.

## 4. Stack consigliato (proposto, non ancora confermato formalmente)

- **Frontend:** Next.js (React + TypeScript). Video con skeleton sovrapposto su canvas, grafici degli angoli.
- **API:** FastAPI in Python, perché pose estimation e analisi (RTMPose/MediaPipe, NumPy, SciPy) sono in Python. Le future app mobile useranno la stessa API.
- **Upload:** il browser carica i video direttamente sullo storage con URL firmati, senza passare dall'API.
- **Elaborazione asincrona:** l'API crea un job su una coda (Redis + Celery o RQ), un worker separato esegue la pose estimation. In sviluppo CPU con MediaPipe (o GPU locale); in produzione GPU serverless (Modal o RunPod) con RTMPose.
- **Storage:** S3-compatibile (Supabase Storage o Cloudflare R2): video e keypoint grezzi in Parquet.
- **Database:** PostgreSQL (incluso in Supabase): utenti, sessioni, job, metriche riassuntive, catalogo scarpe.
- **Auth:** Supabase Auth (email, Google, Apple); FastAPI verifica il JWT, così web e app usano lo stesso sistema.
- **Locale:** tutto con Docker Compose.
- **Produzione:** frontend su Vercel; API e coda su Fly.io/Railway o VPS (es. Hetzner); worker GPU serverless. App mobile più avanti con React Native + Expo.
- **Privacy (da decidere subito):** i video sono dati personali, quindi server in UE e cancellazione automatica dei video dopo l'analisi.

## 5. Risultati della ricerca bibliografica (utili per il software)

Report completo: https://claude.ai/artifact/LDwJXWHuiFLcA1Qggd9krb ("Corsa al microscopio", settembre 2026, 18 fonti). Alcuni numeri vengono dagli abstract, non dal testo completo: prima di fissare soglie nel codice va letto lo studio originale.

### Principi generali
- **Non esiste una "tecnica migliore" universale.** Le revisioni sistematiche trovano legami deboli e incoerenti tra singole variabili e infortuni (Ceyssens 2019). Le singole variabili spiegano solo il 4–12% delle differenze di economia di corsa (Van Hooren 2024).
- Il report va presentato come "fuori dal range tipico, secondo lo studio X", **mai come diagnosi**: le soglie in letteratura sono medie di gruppo, non cut-off validati sul singolo.
- Riferimento clinico per l'analisi video 2D: protocollo di Souza (2016). L'affidabilità test-retest delle misure 2D è buona per gli angoli sagittali e la caduta del bacino.

### Metriche misurabili da video 2D

| Metrica | Vista | Come si calcola | Evidenza |
|---|---|---|---|
| Cadenza | Laterale | passi/min dal ciclo dei piedi | moderata: +5–10% riduce i carichi su anca e ginocchio (Heiderscheit 2011); cadenza alta associata a minor costo energetico |
| Overstride | Laterale | distanza orizzontale tallone–bacino o angolo tibia al contatto | limitata |
| Flessione ginocchio al contatto | Laterale | angolo coscia–gamba al primo contatto | limitata: ginocchio più esteso negli infortunati (Bramah 2018) |
| Angolo tibia e caviglia al contatto | Laterale | inclinazione tibia, dorsiflessione | limitata |
| Tipo di appoggio | Laterale | angolo piede–suolo al contatto | molto bassa: cambiarlo sposta il carico, non lo elimina |
| Oscillazione verticale | Laterale | escursione verticale del bacino | moderata (economia) |
| Inclinazione del tronco | Laterale | angolo spalla–anca a metà appoggio | limitata |
| Caduta del bacino (pelvic drop) | Posteriore | inclinazione della linea tra le anche a metà appoggio | moderata: predittore più forte in Bramah 2018 (+80% di probabilità per grado) |
| Adduzione d'anca | Posteriore | angolo coscia rispetto al bacino | limitata (dolore femoro-rotuleo e bandelletta nelle donne) |
| Pronazione / eversione retropiede | Posteriore | angolo tallone–gamba | incoerente; nessun modello standard ha un keypoint sul calcagno |
| Loading rate | — | serve pedana o IMU, non stimabile da video | incoerente |

Tempo di contatto, tempo di volo e lunghezza del passo non mostrano associazioni con l'economia: riportarli come descrittori, non come giudizi.

### Scarpe
- **Non si scelgono in base alla pronazione:** in scarpa neutra i piedi pronati non si infortunano di più (Nielsen 2014). Eccezione: le motion control riducono gli infortuni nei piedi pronati (Malisoux 2016/2021).
- Cochrane 2022: prove insufficienti per prescrivere un tipo di scarpa.
- **Il criterio più difeso è il comfort** ("comfort filter" e "preferred movement path", Nigg 2015).
- Quindi il software dovrebbe proporre **una rosa di scarpe da provare** per caratteristiche (drop, ammortizzazione, stabilità), non "la scarpa giusta". La funzione più solida è il **confronto A/B dello stesso runner con scarpe diverse** sul tapis roulant, insieme a un questionario di comfort.

### Pose estimation
- Sul piano sagittale è affidabile: errori di circa 4–7° su anca e ginocchio in corsa rispetto al motion capture con marker.
  - RTMPose (MMPose, keypoint del piede con Halpe26/RTMW): ~5,6°, il migliore nel confronto arXiv 2505.04713.
  - MediaPipe BlazePose (33 punti, con tallone e punta): ~6°.
  - Sports2D: open source, angoli articolari da una sola vista, usa RTMPose. Buon punto di partenza: https://github.com/davidpagnon/Sports2D
  - Pose2Sim (3D multi-camera) ~4,1°; OpenCap (2+ smartphone) anca/ginocchio ~6°, caviglia ~7,3°.
- **Punti deboli:** caviglia (sempre il giunto meno accurato), vista posteriore, occlusioni (corrimano del tapis roulant), velocità alte.
- Tapis roulant e strada hanno cinematica in gran parte comparabile.

### Pipeline suggerita
1. **Acquisizione:** due camere fisse perpendicolari al tapis roulant, all'altezza del bacino, 120–240 fps, 30–60 s dopo il riscaldamento, a velocità nota.
2. **Pose 2D:** RTMPose o MediaPipe su ogni vista, con keypoint dei piedi; filtro temporale (es. Butterworth) sulle traiettorie.
3. **Eventi del passo:** contatto iniziale e distacco dal moto di tallone e punta.
4. **Metriche:** cadenza, overstride, angoli di ginocchio, tibia e tronco (laterale); caduta del bacino e adduzione d'anca (posteriore); media su 10+ cicli.
5. **Report:** valori con range di riferimento e fonte; consigli limitati a ciò che la letteratura supporta (soprattutto la cadenza).

Raccomandazioni: partire dalla vista laterale; trattare la pronazione come obiettivo di ricerca, non funzione di base; validare il pipeline su qualche soggetto contro un riferimento (Kinovea con marcatori adesivi o un laboratorio) prima di dare consigli.

## 6. Sessione grill-with-docs: dove riprendere

Simone ha avviato `/grill-with-docs` per definire interfaccia e funzionalità. È stato posto **solo il primo round di domande e Simone non ha ancora risposto**. Nessuna decisione presa, nessun file scritto. Riprendi da qui: ripresenta queste domande (Simone può rispondere con il numero e "ok" dove accetta la proposta), poi prosegui con i round successivi, scrivendo `GLOSSARY.md` e gli ADR man mano.

1. **Chi usa il software:** (a) il runner da solo; (b) un operatore (allenatore, fisioterapista, negozio di scarpe) con i suoi clienti; (c) entrambi. Proposta: (a) per la prima versione; (b) cambia molto l'interfaccia (lista clienti, report da consegnare).
2. **Quali video servono:** sempre entrambe le viste o ne basta una? Proposta: laterale obbligatoria, posteriore facoltativa.
3. **Come arrivano i video:** (a) caricamento di file registrati col telefono; (b) registrazione dal vivo nel browser. Proposta: (a), che si estende bene all'app mobile.
4. **Cosa restituisce la prima versione:** (a) video con skeleton e metriche; (b) come (a) più consigli testuali sulla tecnica; (c) come (b) più consiglio scarpe. Proposta: (b); il consiglio scarpe in una fase successiva, per caratteristiche e non per modello.
5. **Account e storico:** login con storico delle analisi o analisi usa e getta? Proposta: login con storico, per confrontare la tecnica nel tempo.
6. **Dati inseriti a mano:** proposta di rendere obbligatorie velocità e pendenza del tapis roulant e altezza del runner (servono per lunghezza del passo e confronto tra sessioni); facoltativi peso, scarpe indossate, infortuni passati.

Rami ancora da esplorare dopo questo round (indicativi): schermate e flusso utente, elenco delle metriche della v1 e range di riferimento, formato del report, istruzioni di ripresa per l'utente (posizione camera, fps), gestione privacy e retention dei video, conferma dello stack e prime ADR (per esempio Supabase, coda Redis, pose estimation lato server).

## 7. Prossimi passi consigliati

1. `/setup-matt-pocock-skills` (una volta sola).
2. Riprendere `/grill-with-docs` dal round della sezione 6.
3. Registrare le decisioni chiave come ADR (stack, privacy/UE, scelta del modello di pose).
4. Primo prototipo: pipeline della sola vista laterale (MediaPipe o RTMPose via Sports2D) che da un video produce skeleton sovrapposto, cadenza e angoli principali, prima ancora della parte web.
