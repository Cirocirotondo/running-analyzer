# Running Analyzer

Software per l'analisi della tecnica di corsa a partire da due video su tapis roulant (vista laterale e posteriore). Estrae lo skeleton con keypoint e angoli articolari, dà consigli sulla tecnica e suggerisce scarpe da corsa.

Fase attuale: sviluppo della sola interfaccia web. Produzione su server e app mobile arriveranno dopo.

## Stack proposto (da confermare)

- Frontend: Next.js (React + TypeScript)
- API: FastAPI (Python)
- Elaborazione video: worker asincrono con coda Redis (MediaPipe su CPU in sviluppo, RTMPose su GPU in produzione)
- Database, auth e storage: Supabase (PostgreSQL, Auth, Storage S3-compatibile)
- Sviluppo locale: Windows + WSL2 (Ubuntu) con Docker Compose

## Skill per Claude Code

In `.claude/skills/` ci sono le skill di [Matt Pocock](https://github.com/mattpocock/skills) (licenza MIT, vedi `.claude/skills/LICENSE-mattpocock-skills`). Per esempio `/grill-with-docs` per affinare il progetto e scrivere glossario e ADR.
