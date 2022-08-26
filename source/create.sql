DROP DATABASE IF EXISTS test;
CREATE DATABASE test;

DROP OWNED BY app;

-- For use pgadmin from out of container
DROP USER IF EXISTS app;
CREATE USER app WITH PASSWORD 'password';
GRANT ALL PRIVILEGES ON DATABASE test to app;
\c test;
SET search_path TO public;

GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA public TO postgres;
ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT ALL PRIVILEGES ON TABLES TO postgres;
GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA public TO app;
ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT ALL PRIVILEGES ON TABLES TO app;

DROP FUNCTION IF EXISTS now_utc();
CREATE FUNCTION now_utc() RETURNS timestamp AS $$
    DECLARE
		result timestamp;
    BEGIN
        SELECT DATE_TRUNC('second', (now() AT TIME ZONE 'UTC'))::timestamp into result;
        RETURN result;
    END;
$$ LANGUAGE PLPGSQL;

DROP TABLE IF EXISTS "user" CASCADE;

CREATE TABLE "user"(
    userid          INTEGER NOT NULL,
    login           character varying(64) NULL default NULL,
    password        character varying(64) NULL default NULL,
    firstname       character varying(128) NULL default NULL,
    lastname        character varying(128) NULL default NULL,
    email           character varying(256) NOT NULL,
    enabled         BOOLEAN default true,
    createdat       timestamp,
    updatedat       timestamp,
    PRIMARY KEY(userid)
);

CREATE FUNCTION user_before_insert() RETURNS trigger AS $$
    DECLARE
        uniquelogin BOOLEAN;
        uniqueemail BOOLEAN;
        has_majority    BOOLEAN;
    BEGIN
        SELECT COUNT(userid)=0 into uniquelogin FROM "user" WHERE login=NEW.login;
        IF not uniquelogin THEN
            RAISE EXCEPTION 'bdd.user.insert.login.alreadyused';
        END IF;
        SELECT COUNT(userid)=0 into uniqueemail FROM "user" WHERE email=NEW.email;
        IF not uniqueemail THEN
            RAISE EXCEPTION 'bdd.user.insert.email.alreadyused';
        END IF;
        SELECT CASE WHEN NEW.firstname IS NULL THEN NULL ELSE INITCAP(NEW.firstname::text) END into NEW.firstname;
        SELECT CASE WHEN NEW.lastname  IS NULL THEN NULL ELSE UPPER(NEW.lastname::text)    END into NEW.lastname;
        SELECT CASE WHEN MAX(userid) IS NULL THEN 1 ELSE MAX(userid)+1 END into NEW.userid FROM "user";
        NEW.createdat  := now_utc();
        NEW.updatedat := now_utc();
        RETURN NEW;
    END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER user_before_insert BEFORE INSERT ON "user" FOR EACH ROW EXECUTE PROCEDURE user_before_insert();

CREATE FUNCTION user_before_update() RETURNS trigger AS $$
    BEGIN
        NEW.updatedat := now_utc();
        RETURN NEW;
    END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER user_before_update BEFORE UPDATE ON "user" FOR EACH ROW EXECUTE PROCEDURE user_before_update();

INSERT INTO "user"(login, password, firstname, lastname, email, enabled) VALUES 
('admin'  , '35d1df1f97cfd72c2988ec26a6fdf688763c8b38', 'Billy' , 'Maurice', 'bmaurice@gmail.com', true),
('rartena', '705174cf51135982bfbe26734723a49c893612e3', 'Roger' , 'Artena' , 'rartena@gmail.com' , true),
('pdavid' , '705174cf51135982bfbe26734723a49c893612e3', 'Pierre', 'David'  , 'pdavid@gmail.com'  , true);
