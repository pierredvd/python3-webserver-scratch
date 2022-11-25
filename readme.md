Pour la petite histoire, l'idée était d'estimer a partir de rien s'il etait possible d'établir une stack complete webserveur + framework en python3.
Sur le principe cela semble effectivement envisageable, mais la facheuse tendance de python3 a rendre difficile la libération mémoires lors du maintien de thread en deamon, donne au final un résultat assez recevant. Pour le coup, en langage de haut niveau, NodeJs semble bien plus adapté pour ce genre de petit challenge.

Actulement en cours de développement, sans recherche véritable de produit fini.
Configurée pour répondre sur le localhost en http et https, et laisse la possibilités de consulter le contenu de la base de données Postgresql avec un pgadmin sur le port 5432.

[2022-11-25] Grosse réécriture du code, dispersion et mise au propre des packages, 
- env: update dockerfile (postgres minor version), patch init.sh
- server: prise en charge du protocol websocket 13
- app: habillage des erreurs, corrections du developpeurMode qui ne forcait pas convenablement le rechargement des modules
- app: les configurations sont rechargée live a chaque appel, (1 update par seconde max), avec verifications des mtimes des fichiers
- app: prise en charge fichier de langues
- app: logs (applicatifs seulement)
- app: le comportement controller et model sont derenavent integré par heritable
- perf: reduction de l'usage memoire et des propabilités de suites (sans grand succès)
- todo: cache, tests autmatisés, doc, pre-queue les requetes par applicatif, penser a comment scalarisée la charge par applicatif

P.S: Pour les amis de chromes et de https, le serveur est configuré par defaut avec un certificat autosignés, donc pour que chrome ne hurle pas pour un self-signed sur localhost:
chrome://flags/#allow-insecure-localhost
"Allow invalid certificates for resources loaded from localhost." > Enabled (voila voila !)

## _Environnement de developpement Python / Postgres11 / Node 10 / Portgres bridger sous docker_

## Contruire le contener
```bash
[Windows] docker build -t dev-python:1.00 .
[Linux] sudo docker build -t dev-python:1.00 .
 ```

 ## Lancer le conteneur
```bash 
[Windows] docker run -it --rm -m 1g --name "dev-python_1.00" -p 80:80 -p 443:443 -p 5432:5432 -v "%cd%/source":/var/source -v "%cd%/persistant_data":/var/lib/postgresql/data dev-python:1.00
[Linux] sudo docker run -it --rm -m 1g --name "dev-python_1.00" -p 80:80 -p 443:443 -p 5432:5432 -v "`pwd`/source":/var/source -v "`pwd`/persistant_data":/var/lib/postgresql/data dev-python:1.00
```