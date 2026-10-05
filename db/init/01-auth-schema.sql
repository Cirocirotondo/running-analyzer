-- Role and schema used by Supabase Auth (GoTrue). It runs its own migrations in `auth`.
-- Runs once, when the database volume is created (psql with ON_ERROR_STOP, as $POSTGRES_USER).
\set auth_pw `echo "$AUTH_DB_PASSWORD"`
\set dbname `echo "$POSTGRES_DB"`
\set dbuser `echo "$POSTGRES_USER"`
CREATE ROLE supabase_auth_admin LOGIN PASSWORD :'auth_pw' NOINHERIT CREATEROLE;
CREATE SCHEMA auth AUTHORIZATION supabase_auth_admin;
-- GoTrue's migrations grant to the roles of a Supabase deployment; they only need to exist.
CREATE ROLE postgres NOLOGIN;
CREATE ROLE anon NOLOGIN;
CREATE ROLE authenticated NOLOGIN;
CREATE ROLE service_role NOLOGIN;
GRANT CREATE ON DATABASE :"dbname" TO supabase_auth_admin;
-- The application reads auth.users (ids and emails) but never writes to it.
GRANT USAGE ON SCHEMA auth TO :"dbuser";
ALTER DEFAULT PRIVILEGES FOR ROLE supabase_auth_admin IN SCHEMA auth GRANT SELECT ON TABLES TO :"dbuser";
