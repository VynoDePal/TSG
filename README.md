# TSG - API de Gestion de Centre de Jeux

Ce projet est une API RESTful développée avec Django REST framework pour la gestion d'un centre de jeux. Elle permet d'automatiser le suivi des sessions de jeu, la facturation et la génération de rapports financiers pour améliorer la transparence et l'efficacité opérationnelle.

## Fonctionnalités

- **Authentification sécurisée** : Système d'authentification basé sur JSON Web Tokens (JWT)
- **Gestion des utilisateurs** : Support pour différents rôles (joueur, personnel, administrateur)
- **Gestion des stations** : Suivi des stations de jeu (PC, consoles) avec leur statut et leurs sessions actives
- **Suivi des sessions** : Enregistrement des sessions de jeu avec horodatage et calcul automatique des coûts
- **Tarification personnalisable** : Définition de tarifs horaires différents selon le type de station (PC, Console)
- **Facturation automatique** : Calcul des coûts en FCFA basé sur la durée et le tarif horaire applicable
- **Documentation API** : Interface Swagger pour explorer et tester l'API
- **Échanges de données** : Communication en format JSON
- **Contrôle d'accès** : Permissions basées sur les rôles utilisateur

## Technologies utilisées

- Django 5.2.1
- Django REST Framework 3.15.2
- PostgreSQL (base de données relationnelle)
- JWT pour l'authentification
- Swagger pour la documentation d'API

## Prérequis

- Python 3.13 ou supérieur
- PostgreSQL
- pip (gestionnaire de paquets Python)
- virtualenv (environnement virtuel Python)

## Installation

1. **Cloner le dépôt**
   ```bash
   git clone <URL_DU_REPO>
   cd TSG
   ```

2. **Créer et activer un environnement virtuel**
   ```bash
   python -m venv .venv
   source .venv/bin/activate  # Sous Linux/Mac
   # ou
   .venv\Scripts\activate  # Sous Windows
   ```

3. **Installer les dépendances**
   ```bash
   pip install -r requirements.txt
   ```

4. **Configurer la base de données PostgreSQL**
   - Créer une base de données PostgreSQL nommée `game_center_db`
   - Adapter les informations de connexion dans `TSG/settings.py` si nécessaire

5. **Appliquer les migrations**
   ```bash
   python manage.py makemigrations
   python manage.py migrate
   ```

6. **Créer un superutilisateur**
   ```bash
   python manage.py createsuperuser
   ```

7. **Lancer le serveur de développement**
   ```bash
   python manage.py runserver
   ```

## API Endpoints

### Authentification

- `POST /api/auth/register/` : Inscription d'un nouvel utilisateur
- `POST /api/auth/login/` : Connexion et obtention d'un token JWT

### Gestion des stations

- `GET /api/stations/` : Liste de toutes les stations avec leur statut
- `POST /api/stations/` : Création d'une nouvelle station (Admin/Staff uniquement)
- `GET /api/stations/{id}/` : Détails d'une station spécifique
- `PUT /api/stations/{id}/` : Mise à jour des informations d'une station (Admin/Staff uniquement)
- `DELETE /api/stations/{id}/` : Suppression d'une station (Admin uniquement)

### Gestion des sessions

- `POST /api/sessions/` : Démarre une nouvelle session en assignant un joueur à une station (Admin/Staff uniquement)
- `GET /api/sessions/` : Liste les sessions avec filtres optionnels (joueur, date)
- `GET /api/sessions/{id}/` : Récupère les détails d'une session spécifique
- `PUT /api/sessions/{id}/end/` : Termine une session, calcule la durée et le coût (Admin/Staff uniquement)

### Gestion des tarifs

- `GET /api/rates/` : Liste tous les paramètres tarifaires actifs
- `POST /api/rates/` : Crée un nouveau paramètre tarifaire (Admin/Staff uniquement)
- `GET /api/rates/{id}/` : Récupère les détails d'un paramètre tarifaire spécifique
- `PUT /api/rates/{id}/` : Met à jour un paramètre tarifaire (Admin/Staff uniquement)
- `DELETE /api/rates/{id}/` : Désactive un paramètre tarifaire (Admin uniquement)
- `GET /api/rates/current/` : Récupère les tarifs actuels pour chaque type de station

### Rapports financiers

- `GET /api/reports/revenue/?start_date=yyyy-mm-dd&end_date=yyyy-mm-dd` : Génère un rapport des revenus pour une période donnée (Admin/Staff uniquement)
- `GET /api/reports/usage/?start_date=yyyy-mm-dd&end_date=yyyy-mm-dd` : Fournit des statistiques d'utilisation pour une période donnée (Admin/Staff uniquement)

### Interface d'administration

- `GET /api/users/` : Liste tous les utilisateurs (Admin uniquement)
- `GET /api/users/{id}/` : Récupère les détails d'un utilisateur (Admin ou l'utilisateur lui-même)
- `PUT /api/users/{id}/` : Met à jour un utilisateur (Admin ou l'utilisateur lui-même)
- `DELETE /api/users/{id}/` : Supprime un utilisateur (Admin uniquement)

## Modèles de données

### Utilisateurs

Le système prend en charge trois types d'utilisateurs :
- **Joueurs** : Clients du centre de jeux
- **Personnel** : Employés autorisés à gérer les stations et les sessions
- **Administrateurs** : Accès complet à toutes les fonctionnalités

### Stations

Les stations représentent les appareils de jeu et possèdent les attributs suivants :
- **Nom** : Identifiant lisible de la station
- **Type** : PC ou Console
- **Statut** : Disponible, En utilisation, En maintenance
- **Session active** : Référence à la session en cours sur cette station (si applicable)

### Sessions

Les sessions enregistrent l'utilisation des stations par les joueurs :
- **Joueur** : Utilisateur associé à la session
- **Station** : Station utilisée pour la session
- **Heure de début** : Moment où la session a commencé
- **Heure de fin** : Moment où la session s'est terminée (null si active)
- **Durée** : Temps de jeu calculé automatiquement en minutes
- **Coût** : Montant calculé en FCFA selon le tarif horaire applicable
- **Statut** : Active ou terminée

### Paramètres tarifaires

Les paramètres tarifaires définissent les tarifs horaires pour chaque type de station :
- **Tarif horaire** : Montant en FCFA par heure de jeu
- **Type de station** : PC, Console ou tous les types
- **Description** : Description optionnelle du tarif
- **Créé par** : Utilisateur qui a créé ou modifié le tarif
- **Statut** : Actif ou inactif

## Documentation API

Une documentation interactive de l'API est disponible aux endpoints suivants :

- Documentation Swagger : `/swagger/`
- Documentation ReDoc : `/redoc/`

## Tests

Pour exécuter les tests du projet :

```bash
python manage.py test
