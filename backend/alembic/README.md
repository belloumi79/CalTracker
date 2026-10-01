Run migrations from `backend/` with:

```bash
alembic upgrade head
```

The API also creates tables automatically for a fresh SQLite development
instance. Production deployments should run migrations explicitly.
