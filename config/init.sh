#!/bin/bash
chgrp www-data 	-R /var/source
chmod g+s  		-R /var/source

# Force init cluster
chown postgres -R /var/lib/postgresql/data
chmod 0700  	  /var/lib/postgresql/data
chmod g+s  		  /var/lib/postgresql/data

if [ -d "/var/lib/postgresql/data/base" ]
then	
	echo ""
	echo "### Postgres cluster already exists"	
	service postgresql restart
else
	rm -rf /var/lib/postgresql/data;
	echo ""
	echo "### Create postgres cluster"	
	su -c "/usr/lib/postgresql/11/bin/initdb  --pgdata=/var/lib/postgresql/data --encoding=UTF-8 --locale=C --username=postgres" -s /bin/sh postgres
	service postgresql restart
fi

# Check for database update
if [ -f /var/source/create.sql ] 
then
	if [ ! -f /var/lib/postgresql/data/.gitkeep ] 
	then
		echo ""
		echo "### Initialize postgres data"
		psql -U "postgres" -h "localhost" -p 5433 -f /var/source/create.sql
	else
		if [ $(stat /var/source/create.sql --format="%X") -gt $(stat /var/lib/postgresql/data/.gitkeep --format="%X") ] 
		then
			echo ""
			echo "### Update data $(stat /var/lib/postgresql/data/.gitkeep --format="%X") to $(stat /var/www/create.sql --format="%X")"
			psql -U "postgres" -h "localhost" -p 5433 -f /var/source/create.sql
		else
			echo ""
			echo "### Database up-to-date"
		fi
	fi
fi
touch /var/lib/postgresql/data/.gitkeep

# Start postgres bridger
node /etc/postgres_bridger/bootstrap.js & echo "Start Postgresql Bridger"

python3 --version
/var/source/bootstrap.py