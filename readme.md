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