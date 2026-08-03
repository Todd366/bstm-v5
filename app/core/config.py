import os


APP_NAME = os.getenv(
    "BSTM_APP_NAME",
    "BSTM Platform"
)

APP_VERSION = os.getenv(
    "BSTM_APP_VERSION",
    "5.0.0"
)

ENVIRONMENT = os.getenv(
    "BSTM_ENVIRONMENT",
    "development"
)

DATABASE_PATH = os.getenv(
    "BSTM_DATABASE",
    "bstm.db"
)
