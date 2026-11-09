# Database migrations (Alembic)

Schema changes are version-controlled here.

```powershell
# Create a new migration after changing models:
alembic revision --autogenerate -m "describe change"

# Apply migrations to the database in DATABASE_URL:
alembic upgrade head

# Roll back one step:
alembic downgrade -1
```

The DB URL and model metadata are injected from app settings in `env.py`;
`alembic.ini` deliberately leaves `sqlalchemy.url` blank.
