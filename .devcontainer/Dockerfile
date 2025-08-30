# Usa una imagen base de Python que sea adecuada para construir la aplicación.
FROM python:3.12-slim

# Instala las dependencias del sistema necesarias.
RUN apt-get update && apt-get install -y \
    gcc \
    libffi-dev \
    libssl-dev \
    libpq-dev \
    default-libmysqlclient-dev \
    pkg-config \
    git \
    unzip \
    && rm -rf /var/lib/apt/lists/*

# Copia los archivos de dependencia de Python.
# La ruta aquí es 'requirements.txt' porque el contexto de construcción
# se establecerá en el directorio padre de este Dockerfile.
COPY ../requirements.txt ./

# Instala las dependencias de Python.
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# Copia el resto del código del proyecto.
# Esto copia la carpeta 'app', 'tests', 'main.py', etc.
COPY . .

# Exponer el puerto en el que la aplicación se ejecutará.
EXPOSE 8000

# Comando para ejecutar la aplicación cuando el contenedor se inicie.
# La ruta al archivo principal ahora es 'app.main'
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]

# Crear usuario no-root para seguridad
RUN useradd --create-home --shell /bin/bash app && \
    chown -R app:app /app
USER app