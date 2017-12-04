# ws17_oos_sp
Semesterprojekt OOS - Wintersemester 2017 - Beuth Hochschule Berlin

## web_django

### Architecture

local:
- django
- postgres
- mailhog


production:
- django
- postgres
- redis

### Development

```
cd web_django
docker-compose -f local.yml up -d
```

localhost:8000

mailhog:
localhost:1025


### Production

### build environment for ci:
```
cd web_django
docker-compose -f production.yml up -d
docker-compose -f production.yml run django python manage.py migrate
```

#### persistence has a docker volume under:
```
volumes:
  - postgres_data:/var/lib/postgresql/data
  - postgres_backup:/backups
```

#### pls inspect mountpoint with:
```
docker volume inspect --format '{{ .Mountpoint }}' postgres_data
docker volume inspect --format '{{ .Mountpoint }}' postgres_backup
```

#### to build completely from scratch (remove volumnes and rebuild all containers)
```
docker-compose -f production.yml down -v
docker-compose -f production.yml up -d
docker-compose -f production.yml run django python manage.py migrate
```
