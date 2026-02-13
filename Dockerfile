# Usar imagen base de Python
FROM python:3.11-slim

# Set timezone to Spain
ENV TZ=Europe/Madrid
RUN ln -snf /usr/share/zoneinfo/$TZ /etc/localtime && echo $TZ > /etc/timezone

# Establecer directorio de trabajo
WORKDIR /app

# Copiar requirements y instalar dependencias
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copiar el código de la aplicación
COPY . .

# Exponer el puerto que usa functions-framework (por defecto 8080)
EXPOSE 8080

# Comando para ejecutar la función
CMD ["functions-framework", "--target=main", "--port=8080", "--host=0.0.0.0"]
