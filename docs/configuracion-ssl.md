# Configuracion SSL con Let's Encrypt

Este documento describe la configuracion de SSL/HTTPS para el sistema de Reserva de Espacios, incluyendo la configuracion de DNS en Namecheap, Security Groups en AWS y certificados SSL con Let's Encrypt.

## Arquitectura General

```
                    Internet
                        |
                        v
              +-------------------+
              |   Namecheap DNS   |
              | (Resolucion DNS)  |
              +-------------------+
                        |
                        v
              +-------------------+
              | AWS Security Group|
              |  (Puertos 80/443) |
              +-------------------+
                        |
                        v
              +-------------------+
              |     EC2 Instance  |
              |  56.125.216.219   |
              +-------------------+
                        |
                        v
              +-------------------+
              |      Docker       |
              +-------------------+
               /        |        \
              v         v         v
         +-------+  +-------+  +--------+
         | Nginx |  |Keycloak| | Backend|
         | :443  |  | :8080  | | :5001  |
         +-------+  +-------+  +--------+
              |
              v
         +----------+
         | Certbot  |
         | (SSL)    |
         +----------+
```

## 1. Configuracion DNS en Namecheap

### Registros DNS Configurados

En el panel de Namecheap (Domain List > Manage > Advanced DNS), se configuraron los siguientes registros A apuntando al IP del EC2:

| Tipo | Host | Valor | TTL |
|------|------|-------|-----|
| A | @ | 56.125.216.219 | Automatic |
| A | www | 56.125.216.219 | Automatic |
| A | api | 56.125.216.219 | Automatic |
| A | auth | 56.125.216.219 | Automatic |

### Dominios Resultantes

- `reserva-espacios-um.space` - Frontend (aplicacion web)
- `www.reserva-espacios-um.space` - Frontend (alias)
- `api.reserva-espacios-um.space` - Backend API (Flask)
- `auth.reserva-espacios-um.space` - Keycloak (autenticacion)

### Verificacion DNS

Para verificar que los registros DNS estan propagados:

```bash
nslookup reserva-espacios-um.space
nslookup api.reserva-espacios-um.space
nslookup auth.reserva-espacios-um.space
```

## 2. Configuracion AWS Security Group

### Reglas de Entrada (Inbound Rules)

El Security Group de la instancia EC2 debe tener las siguientes reglas:

| Tipo | Protocolo | Puerto | Origen | Descripcion |
|------|-----------|--------|--------|-------------|
| HTTP | TCP | 80 | 0.0.0.0/0 | Trafico HTTP y ACME challenges |
| HTTPS | TCP | 443 | 0.0.0.0/0 | Trafico HTTPS |
| SSH | TCP | 22 | Tu IP | Acceso administrativo |

### Notas Importantes

- El puerto 80 debe permanecer abierto para:
  - Redireccion automatica a HTTPS
  - Renovacion de certificados Let's Encrypt (ACME challenge)
- El puerto 443 es para todo el trafico HTTPS de produccion

## 3. Configuracion de Certificados SSL con Let's Encrypt

### Estructura de Directorios

```
reserva-espacios-backend/
├── certbot/
│   ├── conf/           # Certificados y configuracion de Let's Encrypt
│   │   ├── live/
│   │   │   └── reserva-espacios-um.space/
│   │   │       ├── fullchain.pem    # Certificado completo
│   │   │       └── privkey.pem      # Clave privada
│   │   ├── archive/    # Historial de certificados
│   │   └── renewal/    # Configuracion de renovacion
│   └── www/            # Archivos ACME challenge
└── nginx/
    └── nginx.conf      # Configuracion con SSL
```

### Docker Compose - Servicios

#### Servicio Nginx (Reverse Proxy)

```yaml
nginx:
  image: nginx:alpine
  container_name: nginx-proxy
  ports:
    - "80:80"
    - "443:443"
  volumes:
    - ./nginx/nginx.conf:/etc/nginx/nginx.conf:ro
    - ./nginx/frontend:/usr/share/nginx/html:ro
    - ./certbot/conf:/etc/letsencrypt:ro
    - ./certbot/www:/var/www/certbot:ro
  depends_on:
    - backend-app
    - keycloak
  restart: unless-stopped
```

#### Servicio Certbot (Renovacion Automatica)

```yaml
certbot:
  image: certbot/certbot
  container_name: certbot
  volumes:
    - ./certbot/conf:/etc/letsencrypt
    - ./certbot/www:/var/www/certbot
  entrypoint: "/bin/sh -c 'trap exit TERM; while :; do certbot renew; sleep 12h & wait $${!}; done;'"
  restart: unless-stopped
```

### Obtencion Inicial de Certificados

El proceso para obtener los certificados por primera vez:

1. **Levantar Nginx con configuracion HTTP** (sin SSL, solo para ACME challenge)

2. **Ejecutar Certbot para obtener certificados:**

```bash
docker run --rm \
  -v $(pwd)/certbot/conf:/etc/letsencrypt \
  -v $(pwd)/certbot/www:/var/www/certbot \
  certbot/certbot certonly --webroot \
  --webroot-path=/var/www/certbot \
  -d reserva-espacios-um.space \
  -d www.reserva-espacios-um.space \
  -d api.reserva-espacios-um.space \
  -d auth.reserva-espacios-um.space \
  --email mibanez@correo.um.edu.uy \
  --agree-tos \
  --no-eff-email
```

3. **Activar configuracion SSL en Nginx y reiniciar**

### Renovacion de Certificados

Los certificados Let's Encrypt expiran cada 90 dias. La renovacion es automatica gracias al servicio Certbot que:

- Ejecuta `certbot renew` cada 12 horas
- Solo renueva si el certificado expira en menos de 30 dias

Para forzar una renovacion manual:

```bash
docker compose run --rm --entrypoint "" certbot certbot renew --force-renewal
docker compose restart nginx
```

### Verificacion de Certificados

```bash
# Ver fecha de expiracion
docker compose run --rm --entrypoint "" certbot certbot certificates

# Verificar HTTPS desde el servidor
curl -I https://auth.reserva-espacios-um.space
curl -I https://api.reserva-espacios-um.space
curl -I https://reserva-espacios-um.space
```

## 4. Configuracion Nginx con SSL

### Caracteristicas de Seguridad

- **Protocolos:** TLS 1.2 y TLS 1.3 (versiones seguras)
- **Ciphers:** Solo algoritmos modernos y seguros (ECDHE, AES-GCM)
- **OCSP Stapling:** Habilitado para mejor rendimiento
- **Redireccion HTTP a HTTPS:** Todo el trafico HTTP se redirige automaticamente

### Flujo de Trafico

1. Cliente hace request a `auth.reserva-espacios-um.space`
2. DNS de Namecheap resuelve a `56.125.216.219`
3. Request llega al puerto 80/443 del EC2
4. Nginx recibe el request:
   - Si es HTTP (80): redirige a HTTPS
   - Si es HTTPS (443): termina SSL y hace proxy a Keycloak (HTTP interno)
5. Keycloak responde a Nginx
6. Nginx envia respuesta cifrada al cliente

### Configuracion de Keycloak para Proxy

Keycloak esta configurado para funcionar detras de un reverse proxy:

```yaml
environment:
  KC_HOSTNAME: auth.reserva-espacios-um.space
  KC_PROXY_HEADERS: xforwarded
  KC_HTTP_ENABLED: "true"
```

- `KC_HOSTNAME`: Dominio publico de Keycloak
- `KC_PROXY_HEADERS`: Acepta headers X-Forwarded-* del proxy
- `KC_HTTP_ENABLED`: Permite conexiones HTTP internas (desde Nginx)

## 5. Comandos Utiles

### Gestion de Servicios

```bash
# Ver estado de todos los servicios
docker compose ps

# Ver logs de nginx
docker compose logs -f nginx

# Ver logs de keycloak
docker compose logs -f keycloak

# Reiniciar nginx (despues de cambiar config)
docker compose restart nginx

# Reiniciar todo
docker compose down && docker compose up -d
```

### Troubleshooting SSL

```bash
# Verificar que nginx puede leer los certificados
docker compose exec nginx ls -la /etc/letsencrypt/live/reserva-espacios-um.space/

# Probar configuracion de nginx
docker compose exec nginx nginx -t

# Ver certificado desde afuera
openssl s_client -connect auth.reserva-espacios-um.space:443 -servername auth.reserva-espacios-um.space
```

## 6. Informacion del Certificado

- **Autoridad Certificadora:** Let's Encrypt
- **Tipo:** Certificado multidominio (SAN)
- **Dominios cubiertos:**
  - reserva-espacios-um.space
  - www.reserva-espacios-um.space
  - api.reserva-espacios-um.space
  - auth.reserva-espacios-um.space
- **Validez:** 90 dias (renovacion automatica)
- **Fecha de emision:** 15 de enero de 2026
- **Fecha de expiracion:** 15 de abril de 2026

## 7. Consideraciones de Seguridad

1. **Certificados:** Los archivos en `certbot/conf/` contienen claves privadas. No deben subirse a repositorios publicos (incluido en `.gitignore`).

2. **Renovacion:** Verificar periodicamente que la renovacion automatica funciona correctamente.

3. **Backups:** Considerar hacer backup de `certbot/conf/` antes de cambios mayores.

4. **Rate Limits:** Let's Encrypt tiene limites:
   - 5 certificados por dominio por semana
   - 5 errores de validacion por hora
   - Usar `--staging` para pruebas
