import os
import pyodbc

def get_conn():
    driver = os.getenv("DB_DRIVER", "ODBC Driver 18 for SQL Server")
    server = os.getenv("DB_SERVER", "WIN-MBL7F6P8T1B")
    database = os.getenv("DB_NAME", "rolmark")

    trusted = (os.getenv("DB_TRUSTED_CONNECTION", "").lower() in ("1", "true", "yes"))

    if trusted:
        conn_str = (
            f"DRIVER={{{driver}}};"
            f"SERVER={server};"
            f"DATABASE={database};"
            "Trusted_Connection=yes;"
            "TrustServerCertificate=yes;"
        )
    else:
        user = os.getenv("DB_USER", "")
        pwd = os.getenv("DB_PASSWORD", "")
        conn_str = (
            f"DRIVER={{{driver}}};"
            f"SERVER={server};"
            f"DATABASE={database};"
            f"UID={user};"
            f"PWD={pwd};"
            "TrustServerCertificate=yes;"
        )

    return pyodbc.connect(conn_str, timeout=5)
