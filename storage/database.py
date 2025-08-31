# Importa las clases y módulos necesarios para la base de datos y la codificación/decodificación Base64.
from database.db import Database
from database.levels_db_access import LevelsDBAccessLayer # Importación corregida
from base64 import b64decode, b64encode
import re
from typing import Optional

# Define la clase StorageProviderDatabase, que gestiona las operaciones con la base de datos.
class StorageProviderDatabase:
    """
    Gestiona el almacenamiento de niveles en la base de datos.
    """
    def __init__(self, base_url: str, database: Database):
        """Inicializa el proveedor de almacenamiento de la base de datos."""
        
        # La URL base se configura a partir del motor de la base de datos.
        # Si es un motor SQLite, extrae el nombre del archivo, de lo contrario, usa la URL base proporcionada.
        if database.engine.name == 'sqlite':
            match = re.search(r'[^/]+\.db$', database.engine.url.database)
            self.base_url = match.group(0) if match else str(database.engine.url.database)
        else:
            self.base_url = base_url
        
        # Guarda la instancia de la base de datos para usarla en otros métodos.
        self.db = database
        # Define el tipo de proveedor de almacenamiento como "database".
        self.type = "database"

    async def upload_file(self, level_data: str, level_id: str) -> None:
        """Sube los datos de un nivel a la base de datos."""
        async with self.db.async_session() as session:
            async with session.begin():
                dal = LevelsDBAccessLayer(session) # Uso de la clase corregida
                # Decodifica los datos del nivel de Base64.
                decoded_level_data = b64decode(level_data[:-40].encode()).decode()
                # Extrae el checksum (los últimos 40 caracteres).
                level_checksum = level_data[-40:]
                await dal.add_level_data(
                    level_id=level_id,
                    level_data=decoded_level_data,
                    level_checksum=level_checksum
                )
                await dal.commit()

    def generate_url(self, level_id: str) -> str:
        """Genera una URL para un archivo de nivel."""
        return f'{self.base_url}stage/{level_id}/file'

    def generate_download_url(self, level_id: str) -> str:
        """Un método de conveniencia que llama a generate_url."""
        return self.generate_url(level_id)

    async def delete_level(self, level_id: str) -> None:
        """Elimina un nivel de la base de datos."""
        async with self.db.async_session() as session:
            async with session.begin():
                dal = LevelsDBAccessLayer(session) # Uso de la clase corregida
                await dal.delete_level_data(level_id=level_id)
                await dal.commit()
                print(f"Deleted level {level_id} from database")

    async def dump_level_data(self, level_id: str) -> Optional[str]:
        """Recupera los datos de un nivel de la base de datos."""
        async with self.db.async_session() as session:
            async with session.begin():
                dal = LevelsDBAccessLayer(session) # Uso de la clase corregida
                level = await dal.dump_level_data(level_id=level_id)
                if level and level.level_data:
                    # Convierte los datos del nivel a bytes si no lo son
                    level_data_bytes = level.level_data.encode() if isinstance(level.level_data, str) else level.level_data
                    # Codifica los datos a Base64 y los combina con el checksum.
                    return f'{b64encode(level_data_bytes).decode()}{level.level_checksum}'
                else:
                    return None