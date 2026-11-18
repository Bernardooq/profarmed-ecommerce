FROM postgres:15-alpine

# Inicialización del esquema maestro en instalaciones nuevas
COPY schema/01_init.sql /docker-entrypoint-initdb.d/01-init.sql
