# Architecture technique

## Flux d'une saisie

1. Le frontend envoie un texte ou un repas structuré à `/api` avec le JWT.
2. Pydantic valide taille, valeurs et unités autorisées.
3. Le service de repas résout éventuellement un aliment du catalogue privé/public, calcule les nutriments compatibles et prend un snapshot au moment de la saisie.
4. Les agrégations quotidiennes lisent les snapshots : une mise à jour future du catalogue ne réécrit pas l'historique.
5. Le moteur de règles compare les données connues aux repères du profil.
6. Le `AIProvider` reçoit uniquement ce contexte minimal pour formuler une explication ou une suggestion. Il ne calcule pas les totaux critiques.

## Découpage

- `core` : configuration typée, session DB, scrypt, JWT, dépendances d'authentification et limiteur local.
- `models` : `User`, `Food`, `Meal`, `MealItem`, `WaterIntake`.
- `schemas` : frontière HTTP, validation stricte et contrats OpenAPI.
- `nutrition/calculations.py` : conversions avec base explicite, cibles et répartitions.
- `services/analytics.py` : agrégations par utilisateur, périodes et tendances.
- `services/recommendations.py` : règles déterministes, filtrage d'exclusions et orchestration IA.
- `ai/providers.py` : `AIProvider` structurel, fournisseur hors-ligne déterministe et adaptateur OpenAI-compatible.
- `api` : routes fines ; l'autorisation est imposée par `get_current_user` et les services reçoivent l'utilisateur courant.

## Évolution prévue

- remplacer le limiteur mémoire par Redis ou une politique d'API gateway ;
- ajouter une table de versions/sources de données alimentaires et un job d'import idempotent ;
- séparer un service de jobs asynchrones pour les imports et appels IA longs ;
- ajouter rotation/révocation de sessions et audit des accès sensibles ;
- brancher un fournisseur local en implémentant les quatre méthodes du protocole `AIProvider` ;
- faire évoluer les agrégations en requêtes SQL matérialisées si le volume le justifie ;
- chiffrer les colonnes sensibles avec une stratégie de gestion de clés adaptée au déploiement.

## Données et confidentialité

Le mot de passe est stocké uniquement sous forme de hash. Les données de repas sont toujours liées à un `user_id`, les endpoints protégés obtiennent l'utilisateur depuis le JWT et ne prennent jamais un identifiant d'utilisateur fourni par le navigateur. Les données envoyées à un modèle externe sont construites par `public_profile()` et excluent les identifiants de connexion.
