import sqlite3

# 1. Conéctate a la base de datos
conn = sqlite3.connect('database.db')

# 2. Habilita el modo WAL
conn.execute("PRAGMA journal_mode = WAL")

# 3. Guarda los cambios
conn.commit()

# Ahora la conexión está en modo WAL.
# Puedes usar 'conn' para tus operaciones.
# ...