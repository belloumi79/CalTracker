# CalTracker

CalTracker est une application de suivi nutritionnel privée, construite comme un produit extensible plutôt qu'un simple script. Elle combine un backend FastAPI avec des calculs nutritionnels déterministes, un catalogue d'aliments traçable, une couche IA remplaçable et une interface React responsive en français.

> **Information importante** : CalTracker fournit des informations générales et des estimations à titre informatif. L'application ne pose aucun diagnostic et ne remplace pas un médecin, un diététicien ou tout autre professionnel de santé. En cas de pathologie, d'allergie, de grossesse, de trouble alimentaire ou d'objectif médical, demandez un accompagnement professionnel.

## Fonctionnalités

- création de compte, authentification JWT et profil nutritionnel privé ;
- objectifs, activité, préférences, allergies, intolérances, aliments à éviter, budget et contexte local ;
- saisie d'un repas complet ou d'un aliment unique, modification et suppression ;
- catalogue alimentaire avec portion de référence, source, confiance et valeurs éventuellement inconnues ;
- conversion déterministe uniquement lorsque l'unité est compatible avec la portion déclarée ;
- synthèse quotidienne, tendances sur 7 et 30 jours, macronutriments et hydratation optionnelle ;
- analyse de texte : « deux œufs, 150 g de riz et une pomme » ; les quantités ambiguës sont demandées, jamais inventées silencieusement ;
- recommandations hybrides : règles Python explicables pour les calculs, IA uniquement pour l'explication et la personnalisation ;
- suggestions de repas filtrées par le profil et les exclusions ;
- assistant conversationnel isolé au contexte de l'utilisateur ;
- export JSON et suppression complète du compte ;
- page de confidentialité et avertissements visibles dans l'interface ;
- fournisseur `mock` local par défaut, puis adaptateur OpenAI-compatible optionnel ;
- Docker Compose avec PostgreSQL, API et frontend.

Les aliments présents lors d'un démarrage local sont des **fixtures de développement explicitement marquées `demo_reference`, `estimated` et non vérifiées**. Ils servent à essayer l'interface ; une mise en production doit importer une base citée (par exemple une source alimentaire autorisée) et conserver sa provenance.

## Architecture

```text
CalTracker/
├── backend/
│   ├── app/
│   │   ├── api/             # routes REST et contrôles d'accès
│   │   ├── ai/              # protocole AIProvider, MockAIProvider, adaptateur OpenAI
│   │   ├── core/            # configuration, DB, JWT, hashing, rate limiting
│   │   ├── models/          # modèles SQLAlchemy
│   │   ├── nutrition/       # calculs sans LLM
│   │   ├── schemas/         # contrats Pydantic
│   │   ├── services/        # CRUD, agrégations, recommandations, fixtures
│   │   └── main.py
│   ├── alembic/             # migrations
│   ├── tests/
│   ├── requirements.txt
│   └── .env.example
├── frontend/
│   ├── src/                 # React + TypeScript + CSS responsive
│   ├── package.json
│   └── Dockerfile
├── docker/
│   └── backend.Dockerfile
├── docs/
├── docker-compose.yml
└── Makefile
```

La note d'architecture détaillée se trouve dans [`docs/architecture.md`](docs/architecture.md).

## Démarrage rapide local

Pré-requis : Python 3.11+ (3.12 recommandé), Node.js 20+ et npm. PostgreSQL n'est pas obligatoire en développement : SQLite est utilisé par défaut.

```bash
cp backend/.env.example backend/.env
python -m venv .venv
.venv/bin/pip install -r backend/requirements-dev.txt
cd frontend && npm install && cd ..

# terminal 1
cd backend
PYTHONPATH=. ../.venv/bin/uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

# terminal 2
cd frontend
npm run dev -- --host 0.0.0.0
```

Ouvrir <http://localhost:5173>. La documentation OpenAPI est disponible sur <http://localhost:8000/docs> et l'état de santé sur <http://localhost:8000/health>.

Le frontend utilise des URLs relatives (`/api`) et Vite proxy les appels vers le backend. Il ne dépend donc pas d'un `localhost` codé dans le navigateur lorsqu'il est servi dans Docker.

## Docker Compose

Le lancement suivant démarre PostgreSQL, l'API et le frontend :

```bash
cp backend/.env.example .env       # puis définir au minimum SECRET_KEY en dehors du local
# les variables POSTGRES_* peuvent aussi être précisées dans .env
docker compose up --build
```

- interface : <http://localhost:5173>
- API : <http://localhost:8000>
- PostgreSQL : volume `postgres_data`

Pour la production, remplacer toutes les valeurs de développement, fournir un `SECRET_KEY` aléatoire d'au moins 32 octets via le secret manager, désactiver les fixtures (`SEED_DEMO_FOODS=false`), exécuter `alembic upgrade head` et placer PostgreSQL derrière un chiffrement disque/réseau approprié.

## Configuration

Les secrets ne sont jamais stockés dans le code. Copier le fichier d'exemple et utiliser les variables suivantes :

| Variable | Rôle | Défaut local |
|---|---|---|
| `DATABASE_URL` | SQLite ou `postgresql+psycopg://...` | `sqlite:///./caltracker.db` |
| `SECRET_KEY` | signature des JWT | valeur de démonstration à remplacer |
| `ACCESS_TOKEN_EXPIRE_MINUTES` | durée du token | 1440 |
| `CORS_ORIGINS` | origines séparées par virgule | localhost frontend |
| `AI_PROVIDER` | `mock` ou `openai` | `mock` |
| `OPENAI_API_KEY` | clé uniquement via environnement/secret manager | vide |
| `OPENAI_MODEL` | modèle compatible API Chat Completions | `gpt-4o-mini` |
| `SEED_DEMO_FOODS` | charger les fixtures locales | `true` |

Le mode `mock` ne fait aucun appel externe et est le mode utilisé par les tests. L'adaptateur externe reçoit seulement le contexte nécessaire à la demande (pas le mot de passe et pas les données d'un autre compte).

## API REST principale

Toutes les routes métier sont préfixées par `/api` et documentées automatiquement dans `/docs`.

```text
POST   /api/auth/register
POST   /api/auth/login
GET    /api/users/me
PUT    /api/users/me
GET    /api/users/me/export
DELETE /api/users/me

GET    /api/foods
GET    /api/foods/{id}

POST   /api/meals
GET    /api/meals?start_date=YYYY-MM-DD&end_date=YYYY-MM-DD
GET    /api/meals/{id}
PUT    /api/meals/{id}
DELETE /api/meals/{id}
POST   /api/water

GET    /api/nutrition/daily
GET    /api/nutrition/weekly
GET    /api/nutrition/monthly

POST   /api/ai/analyze-meal
POST   /api/ai/recommendations
POST   /api/ai/meal-suggestions
POST   /api/ai/chat
```

Exemple de repas :

```json
{
  "meal_type": "lunch",
  "items": [
    {"food": "Poulet grillé", "quantity": 150, "unit": "g"}
  ]
}
```

Le raccourci `{ "meal_type": "lunch", "food": "Riz cuit", "quantity": 150, "unit": "g" }` est également accepté. Un aliment absent du catalogue est conservé dans le journal mais marqué `nutrition_known: false`; aucun nutriment n'est créé artificiellement.

## Calculs et limites

- Les agrégations et conversions sont réalisées en Python, jamais confiées à un LLM.
- Chaque aliment déclare une base (`100 g`, `1 piece`, etc.). Une conversion incompatible (par exemple une portion non définie en grammes) reste inconnue.
- Les cibles dérivées utilisent une estimation Mifflin-St Jeor quand âge, taille, poids et activité sont disponibles ; elles sont étiquetées `estimated` et `mifflin_st_jeor_estimate`.
- Une cible explicitement renseignée par l'utilisateur est étiquetée `user_defined`.
- `goal_adherence` est seulement un ratio descriptif interne : proportion de jours connus dans une fenêtre de ±15 % de la cible calorique. Ce n'est pas un score médical ni une validation scientifique.
- Les valeurs du catalogue de démarrage sont des placeholders estimés ; toute importation de données de production doit renseigner `source`, `confidence` et les éventuels micronutriments.

## Tests, qualité et migrations

```bash
# depuis le dossier backend
PYTHONPATH=. ../.venv/bin/pytest -q

# frontend
cd ../frontend && npm run build

# migration (depuis backend, avec DATABASE_URL configurée)
../.venv/bin/alembic upgrade head
```

Les tests couvrent l'inscription, les mots de passe, les permissions inter-utilisateurs, la validation, le CRUD des repas, les conversions, les agrégations, les cas de quantité ambiguë, les recommandations et l'export.

Le démarrage crée les tables automatiquement pour une nouvelle base SQLite afin de rester simple localement. En environnement durable, exécuter les migrations Alembic explicitement avant le démarrage.

## Sécurité et confidentialité

- mots de passe hachés avec scrypt salé ; aucun mot de passe ou token n'est écrit dans les logs ;
- JWT avec expiration et contrôle de compte actif ; chaque requête protégée filtre par `user_id` ;
- validation Pydantic et paramètres SQLAlchemy contre les entrées invalides/injections ;
- CORS explicite, limitation glissante des tentatives d'inscription/connexion (à remplacer par Redis/gateway en multi-instance) ;
- suppression en cascade des repas/hydratations avec le compte et export JSON à la demande ;
- logs réduits à méthode, chemin et statut, sans query string ni corps de requête ;
- les informations nutritionnelles sont traitées comme privées ; la page `/privacy` et la vue dédiée expliquent la collecte ;
- en production : TLS, chiffrement disque PostgreSQL, sauvegardes avec contrôle d'accès, rotation de clé JWT, secret manager, monitoring et politique de rétention doivent être ajoutés à l'infrastructure.
