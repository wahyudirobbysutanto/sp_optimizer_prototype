import pyodbc
import os
from dotenv import load_dotenv

load_dotenv(override=True)

server = os.getenv("SQL_SERVER")
database = os.getenv("SQL_DATABASE")
use_windows_auth = os.getenv("USE_WINDOWS_AUTH", "false").lower() == "true"

if use_windows_auth:
    conn_str = f"DRIVER={{ODBC Driver 17 for SQL Server}};SERVER={server};DATABASE={database};Trusted_Connection=yes;"
else:
    user = os.getenv("SQL_USER")
    password = os.getenv("SQL_PASSWORD")
    conn_str = f"DRIVER={{ODBC Driver 17 for SQL Server}};SERVER={server};DATABASE={database};UID={user};PWD={password};"

connection = pyodbc.connect(conn_str)
