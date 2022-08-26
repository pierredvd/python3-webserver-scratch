Pour la petite histoire, l'idée était d'estimer a partir de rien s'il etait possible d'établir une stack complete webserveur + framework en python3.
Sur le principe cela semble effectivement envisageable, mais la facheuse tendance de python3 a rendre difficile la libération mémoires lors du maintien de thread en deamon, donne au final un résultat assez recevant. Pour le coup, en langage de haut niveau, NodeJs semble bien plus adapté pour ce genre de petit challenge.

Actulement en cours de développement, sans recherche véritable de produit fini.
Configurée pour répondre sur le localhost en http et https, et laisse la possibilités de consulter le contenu de la base de données Postgresql avec un pgadmin sur le port 5432.

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