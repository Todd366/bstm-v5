# BSTM V5

Production foundation for the BSTM platform.

## Stack

- FastAPI
- SQLAlchemy
- SQLite development database
- PostgreSQL-ready configuration
- Pytest

## Run

```bash
cd bstm_v5

python3 -m venv .venv

source .venv/bin/activate

pip install -r requirements.txt

pytest

uvicorn app.main:app --reload
