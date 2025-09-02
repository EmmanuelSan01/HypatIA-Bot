# Usa una imagen base de Python que sea compatible con tus dependencias.
# Las dependencias de FastAPI y HTTPX requieren Python >=3.11.
FROM python:3.11-slim

# Establece el directorio de trabajo en una ruta estándar.
WORKDIR /usr/src/app

# Instala las dependencias del sistema necesarias para las librerías de Python.
RUN apt-get update && apt-get install -y \
    gcc \
    libffi-dev \
    libssl-dev \
    libpq-dev \
    default-libmysqlclient-dev \
    pkg-config \
    git \
    unzip \
    ca-certificates \
    && rm -rf /var/lib/apt/lists/*

# Copia los archivos de dependencia de Python.
COPY requirements.txt ./

# Instala las dependencias de Python.
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# Copia el resto del código del proyecto.
COPY . .

# Expone el puerto en el que la aplicación se ejecutará.
EXPOSE 8000

# Comando para ejecutar la aplicación cuando el contenedor se inicie.
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
