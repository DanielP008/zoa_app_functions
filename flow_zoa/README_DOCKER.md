# Instrucciones para levantar el contenedor Docker

## Requisitos previos
1. Asegúrate de que Docker Desktop esté instalado y corriendo
2. Verifica que Docker esté funcionando: `docker ps`

## Opción 1: Usando Docker Compose (Recomendado)

```bash
# Construir la imagen y levantar el contenedor
docker-compose up --build

# O en modo detached (en segundo plano)
docker-compose up -d --build

# Ver los logs
docker-compose logs -f

# Detener el contenedor
docker-compose down
```

## Opción 2: Usando Docker directamente

```bash
# Construir la imagen
docker build -t flow-zoa .

# Ejecutar el contenedor
docker run -d -p 8080:8080 --name flow-zoa-app flow-zoa

# Ver los logs
docker logs -f flow-zoa-app

# Detener el contenedor
docker stop flow-zoa-app

# Eliminar el contenedor
docker rm flow-zoa-app
```

## Verificar que funciona

Una vez levantado, puedes probar el endpoint:

```bash
curl -X POST http://localhost:8080 \
  -H "Content-Type: application/json" \
  -d '{
    "action": "contacts",
    "option": "search",
    "company_id": "test",
    "phone": "123456789"
  }'
```

O abre en tu navegador: http://localhost:8080

## Solución de problemas

Si obtienes errores de permisos:
1. Asegúrate de que Docker Desktop esté corriendo
2. Reinicia Docker Desktop
3. Ejecuta PowerShell como Administrador

Si el puerto 8080 está ocupado, cambia el puerto en `docker-compose.yml`:
```yaml
ports:
  - "3000:8080"  # Cambia 3000 por el puerto que prefieras
```
