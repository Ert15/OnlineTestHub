import os
os.environ.pop('PGPASSFILE', None)
os.environ.pop('PGSERVICEFILE', None)
os.environ.pop('PGSERVICE', None)
os.environ.pop('PGSYSCONFDIR', None)
os.environ.pop('PGHOST', None)
os.environ.pop('PGUSER', None)
os.environ.pop('PGPASSWORD', None)

import psycopg2

print("🔌 Connecting to database...")
conn = psycopg2.connect("host=localhost dbname=postgres user=postgres password=1234")
print("✅ Connected successfully!")
