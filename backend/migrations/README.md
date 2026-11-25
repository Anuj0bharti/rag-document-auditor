# Database migrations

The application creates its schema at startup for zero-friction local development. Docker runs the committed Alembic baseline before serving traffic. Apply it manually with `alembic upgrade head`; `migrations/env.py` reads `DATABASE_URL` through `app.config`.
