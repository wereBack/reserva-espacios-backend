#!/bin/bash

#===============================================================================
# Script de Instalacion - Reserva Espacios
# 
# Este script configura una VM Amazon Linux nueva con todo lo necesario:
# - Docker y Docker Compose
# - Node.js para build del frontend
# - Clonado de repositorios (backend y frontend)
# - Build del frontend React/Vite
# - Certificados SSL con Let's Encrypt
# - Levantamiento de todos los servicios
#
# Uso:
#   ./setup.sh
#   ./setup.sh --skip-ssl
#   ./setup.sh --skip-frontend
#   ./setup.sh --domain otro-dominio.com
#
# Prerequisitos:
#   1. VM Amazon Linux con acceso SSH
#   2. DNS configurado apuntando al IP de la VM
#   3. Security Group con puertos 80, 443 y 22 abiertos
#   4. Archivo .env copiado a /home/ec2-user/.env
#===============================================================================

set -e  # Salir si hay error

# Colores para output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configuracion por defecto
DOMAIN="reserva-espacios-um.space"
REPO_URL="https://github.com/wereBack/reserva-espacios-backend.git"
FRONTEND_REPO_URL="https://github.com/wereBack/reserva-espacios-frontend.git"
BRANCH="despliegue"
FRONTEND_BRANCH="main"
INSTALL_DIR="/home/ec2-user/reserva-espacios-backend"
FRONTEND_DIR="/home/ec2-user/reserva-espacios-frontend"
EMAIL="mibanez@correo.um.edu.uy"
SKIP_SSL=false
SKIP_FRONTEND=false

#-------------------------------------------------------------------------------
# Funciones de utilidad
#-------------------------------------------------------------------------------

log_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

log_success() {
    echo -e "${GREEN}[OK]${NC} $1"
}

log_warning() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

print_banner() {
    echo ""
    echo "========================================"
    echo "  Reserva Espacios - Setup Script"
    echo "========================================"
    echo ""
}

print_usage() {
    echo "Uso: $0 --email EMAIL [opciones]"
    echo ""
    echo "Opciones:"
    echo "  --email EMAIL      Email para Let's Encrypt (requerido)"
    echo "  --domain DOMAIN    Dominio base (default: reserva-espacios-um.space)"
    echo "  --skip-ssl         Omitir obtencion de certificados SSL"
    echo "  --skip-frontend    Omitir build del frontend"
    echo "  --help             Mostrar esta ayuda"
    echo ""
    echo "Ejemplo:"
    echo "  $0 --email admin@ejemplo.com"
    echo ""
}

#-------------------------------------------------------------------------------
# Parseo de argumentos
#-------------------------------------------------------------------------------

parse_args() {
    while [[ $# -gt 0 ]]; do
        case $1 in
            --email)
                EMAIL="$2"
                shift 2
                ;;
            --domain)
                DOMAIN="$2"
                shift 2
                ;;
            --skip-ssl)
                SKIP_SSL=true
                shift
                ;;
            --skip-frontend)
                SKIP_FRONTEND=true
                shift
                ;;
            --help)
                print_usage
                exit 0
                ;;
            *)
                log_error "Argumento desconocido: $1"
                print_usage
                exit 1
                ;;
        esac
    done

    # Validar email requerido (solo si no se salta SSL)
    if [[ "$SKIP_SSL" == false && -z "$EMAIL" ]]; then
        log_error "El parametro --email es requerido"
        print_usage
        exit 1
    fi
}

#-------------------------------------------------------------------------------
# Instalacion de Docker
#-------------------------------------------------------------------------------

install_docker() {
    log_info "Verificando Docker..."
    
    if command -v docker &> /dev/null; then
        log_success "Docker ya esta instalado"
        docker --version
        return
    fi

    log_info "Instalando Docker..."
    
    # Actualizar sistema
    sudo yum update -y
    
    # Instalar Docker
    sudo yum install -y docker
    
    # Iniciar servicio
    sudo systemctl start docker
    sudo systemctl enable docker
    
    # Agregar usuario al grupo docker
    sudo usermod -aG docker $USER
    
    log_success "Docker instalado correctamente"
    docker --version
}

install_docker_compose() {
    log_info "Verificando Docker Compose..."
    
    if docker compose version &> /dev/null; then
        log_success "Docker Compose ya esta instalado"
        docker compose version
        return
    fi

    log_info "Instalando Docker Compose plugin..."
    
    # Crear directorio para plugins
    mkdir -p ~/.docker/cli-plugins/
    
    # Descargar Docker Compose
    COMPOSE_VERSION=$(curl -s https://api.github.com/repos/docker/compose/releases/latest | grep '"tag_name"' | cut -d'"' -f4)
    curl -SL "https://github.com/docker/compose/releases/download/${COMPOSE_VERSION}/docker-compose-linux-$(uname -m)" -o ~/.docker/cli-plugins/docker-compose
    
    # Dar permisos de ejecucion
    chmod +x ~/.docker/cli-plugins/docker-compose
    
    log_success "Docker Compose instalado correctamente"
    docker compose version
}

install_nodejs() {
    log_info "Verificando Node.js..."
    
    if command -v node &> /dev/null; then
        log_success "Node.js ya esta instalado"
        node --version
        return
    fi

    log_info "Instalando Node.js 20.x..."
    
    # Instalar Node.js usando NodeSource
    curl -fsSL https://rpm.nodesource.com/setup_20.x | sudo bash -
    sudo yum install -y nodejs
    
    log_success "Node.js instalado correctamente"
    node --version
    npm --version
}

#-------------------------------------------------------------------------------
# Build del Frontend
#-------------------------------------------------------------------------------

build_frontend() {
    if [[ "$SKIP_FRONTEND" == true ]]; then
        log_warning "Omitiendo build del frontend (--skip-frontend)"
        return
    fi

    log_info "Preparando build del frontend..."
    
    # Clonar o actualizar frontend
    if [[ -d "$FRONTEND_DIR" ]]; then
        log_info "Actualizando repositorio frontend..."
        cd "$FRONTEND_DIR"
        git fetch origin
        git checkout "$FRONTEND_BRANCH"
        git pull origin "$FRONTEND_BRANCH"
    else
        log_info "Clonando repositorio frontend..."
        git clone -b "$FRONTEND_BRANCH" "$FRONTEND_REPO_URL" "$FRONTEND_DIR"
    fi
    
    cd "$FRONTEND_DIR"
    
    # Crear archivo .env.production con las URLs de produccion
    log_info "Configurando variables de entorno para produccion..."
    cat > .env.production << EOF
VITE_API_BASE=https://api.$DOMAIN
VITE_KEYCLOAK_URL=https://auth.$DOMAIN
VITE_KEYCLOAK_REALM=reserva-espacios
VITE_KEYCLOAK_CLIENT_ID=front-admin
EOF
    
    log_success "Variables de entorno configuradas"
    
    # Instalar dependencias
    log_info "Instalando dependencias del frontend..."
    npm ci --production=false
    
    # Build
    log_info "Ejecutando build del frontend..."
    npm run build
    
    # Verificar que el build fue exitoso
    if [[ -d "dist" ]]; then
        log_success "Build del frontend completado"
        
        # Copiar al directorio de nginx
        log_info "Copiando frontend a nginx..."
        rm -rf "$INSTALL_DIR/nginx/frontend"/*
        cp -r dist/* "$INSTALL_DIR/nginx/frontend/"
        
        log_success "Frontend desplegado en nginx/frontend"
    else
        log_error "El build del frontend fallo - no se encontro el directorio dist"
        exit 1
    fi
    
    cd "$INSTALL_DIR"
}

#-------------------------------------------------------------------------------
# Clonado del repositorio
#-------------------------------------------------------------------------------

clone_repository() {
    log_info "Verificando repositorio..."
    
    if [[ -d "$INSTALL_DIR" ]]; then
        log_warning "El directorio $INSTALL_DIR ya existe"
        log_info "Actualizando repositorio..."
        cd "$INSTALL_DIR"
        git fetch origin
        git checkout "$BRANCH"
        git pull origin "$BRANCH"
        log_success "Repositorio actualizado"
    else
        log_info "Clonando repositorio desde $REPO_URL..."
        git clone -b "$BRANCH" "$REPO_URL" "$INSTALL_DIR"
        log_success "Repositorio clonado en $INSTALL_DIR"
    fi
    
    cd "$INSTALL_DIR"
}

#-------------------------------------------------------------------------------
# Verificacion de .env
#-------------------------------------------------------------------------------

check_env_file() {
    log_info "Verificando archivo .env..."
    
    # Verificar si .env existe en el directorio de instalacion
    if [[ -f "$INSTALL_DIR/.env" ]]; then
        log_success "Archivo .env encontrado en $INSTALL_DIR"
        return
    fi
    
    # Verificar si existe en home del usuario
    if [[ -f "/home/ec2-user/.env" ]]; then
        log_info "Copiando .env desde /home/ec2-user/.env"
        cp /home/ec2-user/.env "$INSTALL_DIR/.env"
        log_success "Archivo .env copiado"
        return
    fi
    
    log_error "No se encontro archivo .env"
    echo ""
    echo "Debes copiar el archivo .env antes de ejecutar este script:"
    echo "  scp -i ~/.ssh/tu-key.pem .env ec2-user@IP:/home/ec2-user/.env"
    echo ""
    exit 1
}

#-------------------------------------------------------------------------------
# Configuracion de directorios
#-------------------------------------------------------------------------------

setup_directories() {
    log_info "Creando directorios necesarios..."
    
    cd "$INSTALL_DIR"
    
    # Crear directorios para certbot
    mkdir -p certbot/conf certbot/www
    
    # Crear directorio para frontend si no existe
    mkdir -p nginx/frontend
    
    # Crear index.html placeholder si no existe
    if [[ ! -f "nginx/frontend/index.html" ]]; then
        echo "<html><body><h1>Reserva Espacios</h1><p>Frontend en construccion</p></body></html>" > nginx/frontend/index.html
    fi
    
    log_success "Directorios creados"
}

#-------------------------------------------------------------------------------
# Obtencion de certificados SSL
#-------------------------------------------------------------------------------

obtain_ssl_certificates() {
    if [[ "$SKIP_SSL" == true ]]; then
        log_warning "Omitiendo obtencion de certificados SSL (--skip-ssl)"
        return
    fi

    log_info "Iniciando obtencion de certificados SSL..."
    
    cd "$INSTALL_DIR"
    
    # Usar configuracion inicial de nginx (sin SSL)
    log_info "Configurando nginx para ACME challenge..."
    cp nginx/nginx.conf nginx/nginx-ssl-backup.conf
    cp nginx/nginx-initial.conf nginx/nginx.conf
    
    # Detener contenedores existentes
    docker compose down 2>/dev/null || true
    
    # Levantar nginx temporalmente
    log_info "Levantando nginx para verificacion ACME..."
    docker compose up -d nginx
    
    # Esperar a que nginx este listo
    sleep 5
    
    # Verificar que nginx esta corriendo
    if ! docker compose ps nginx | grep -q "Up"; then
        log_error "Nginx no pudo iniciar. Revisar logs con: docker compose logs nginx"
        exit 1
    fi
    
    log_info "Obteniendo certificados de Let's Encrypt..."
    
    # Ejecutar certbot
    docker run --rm \
        -v "$(pwd)/certbot/conf:/etc/letsencrypt" \
        -v "$(pwd)/certbot/www:/var/www/certbot" \
        certbot/certbot certonly --webroot \
        --webroot-path=/var/www/certbot \
        -d "$DOMAIN" \
        -d "www.$DOMAIN" \
        -d "api.$DOMAIN" \
        -d "auth.$DOMAIN" \
        --email "$EMAIL" \
        --agree-tos \
        --no-eff-email \
        --non-interactive
    
    # Verificar que se obtuvieron los certificados
    # Nota: Let's Encrypt usa symlinks, verificamos el directorio en lugar del archivo
    if [[ -d "certbot/conf/live/$DOMAIN" ]] || [[ -d "certbot/conf/archive/$DOMAIN" ]]; then
        log_success "Certificados SSL obtenidos correctamente"
    else
        log_error "No se pudieron obtener los certificados SSL"
        log_error "Verificar:"
        log_error "  1. DNS configurado correctamente (nslookup $DOMAIN)"
        log_error "  2. Puertos 80 y 443 abiertos en Security Group"
        log_error "  3. Nginx respondiendo en puerto 80"
        
        # Restaurar configuracion original
        cp nginx/nginx-ssl-backup.conf nginx/nginx.conf
        exit 1
    fi
    
    # Restaurar configuracion SSL de nginx
    log_info "Restaurando configuracion SSL de nginx..."
    cp nginx/nginx-ssl-backup.conf nginx/nginx.conf
    rm nginx/nginx-ssl-backup.conf
    
    log_success "Configuracion SSL completada"
}

#-------------------------------------------------------------------------------
# Levantamiento de servicios
#-------------------------------------------------------------------------------

start_services() {
    log_info "Levantando todos los servicios..."
    
    cd "$INSTALL_DIR"
    
    # Detener contenedores existentes
    docker compose down 2>/dev/null || true
    
    # Pull de las imagenes desde GHCR
    log_info "Descargando imagenes desde GitHub Container Registry..."
    docker compose pull
    
    # Levantar servicios
    docker compose up -d
    
    # Esperar a que los servicios esten listos
    log_info "Esperando a que los servicios inicien..."
    sleep 10
    
    # Ejecutar migraciones de base de datos
    log_info "Ejecutando migraciones de base de datos..."
    docker compose exec -T backend-app alembic upgrade head || log_warning "No se pudieron ejecutar las migraciones (puede ser que ya esten aplicadas)"
    
    # Verificar estado
    log_info "Estado de los servicios:"
    docker compose ps
    
    log_success "Servicios levantados"
}

#-------------------------------------------------------------------------------
# Verificacion final
#-------------------------------------------------------------------------------

verify_installation() {
    log_info "Verificando instalacion..."
    
    echo ""
    
    # Verificar HTTP
    log_info "Probando respuesta HTTP..."
    if curl -s -o /dev/null -w "%{http_code}" "http://$DOMAIN" | grep -q "301\|200"; then
        log_success "HTTP respondiendo correctamente"
    else
        log_warning "HTTP no responde (puede estar bien si solo usas HTTPS)"
    fi
    
    # Verificar HTTPS (solo si no se salto SSL)
    if [[ "$SKIP_SSL" == false ]]; then
        log_info "Probando respuesta HTTPS..."
        
        if curl -s -o /dev/null -w "%{http_code}" "https://$DOMAIN" 2>/dev/null | grep -q "200"; then
            log_success "Frontend HTTPS OK: https://$DOMAIN"
        else
            log_warning "Frontend HTTPS no responde"
        fi
        
        if curl -s -o /dev/null -w "%{http_code}" "https://api.$DOMAIN/health" 2>/dev/null | grep -q "200"; then
            log_success "API HTTPS OK: https://api.$DOMAIN"
        else
            log_warning "API HTTPS no responde (puede necesitar endpoint /health)"
        fi
        
        if curl -s -o /dev/null -w "%{http_code}" "https://auth.$DOMAIN" 2>/dev/null | grep -q "200\|302"; then
            log_success "Keycloak HTTPS OK: https://auth.$DOMAIN"
        else
            log_warning "Keycloak HTTPS no responde (puede tardar en iniciar)"
        fi
    fi
    
    echo ""
}

#-------------------------------------------------------------------------------
# Resumen final
#-------------------------------------------------------------------------------

print_summary() {
    echo ""
    echo "========================================"
    echo "  Instalacion Completada"
    echo "========================================"
    echo ""
    echo "Servicios disponibles:"
    echo "  - Frontend:  https://$DOMAIN"
    echo "  - API:       https://api.$DOMAIN"
    echo "  - Keycloak:  https://auth.$DOMAIN"
    echo ""
    echo "Comandos utiles:"
    echo "  cd $INSTALL_DIR"
    echo "  docker compose ps          # Ver estado"
    echo "  docker compose logs -f     # Ver logs"
    echo "  docker compose restart     # Reiniciar"
    echo "  docker compose down        # Detener"
    echo ""
    echo "Renovacion SSL (automatica via certbot container):"
    echo "  docker compose up -d certbot"
    echo ""
    
    if [[ "$SKIP_SSL" == true ]]; then
        echo "NOTA: SSL fue omitido. Para obtener certificados:"
        echo "  ./setup.sh --email tu-email@ejemplo.com"
        echo ""
    fi
    
    if [[ "$SKIP_FRONTEND" == true ]]; then
        echo "NOTA: Frontend fue omitido. Para buildear el frontend:"
        echo "  ./setup.sh --skip-ssl"
        echo ""
    fi
    
    echo "Para actualizar solo el frontend:"
    echo "  cd $FRONTEND_DIR && git pull && npm ci && npm run build"
    echo "  cp -r dist/* $INSTALL_DIR/nginx/frontend/"
    echo "  docker compose restart nginx"
    echo ""
}

#===============================================================================
# Main
#===============================================================================

main() {
    print_banner
    parse_args "$@"
    
    log_info "Dominio: $DOMAIN"
    log_info "Email: ${EMAIL:-'(no especificado)'}"
    log_info "Skip SSL: $SKIP_SSL"
    log_info "Skip Frontend: $SKIP_FRONTEND"
    echo ""
    
    install_docker
    install_docker_compose
    install_nodejs
    
    # Recargar grupo docker (necesario para usar docker sin sudo)
    # Nota: esto solo funciona si se ejecuta en una nueva sesion
    if ! groups | grep -q docker; then
        log_warning "Necesitas cerrar sesion y volver a entrar para usar docker sin sudo"
        log_warning "O ejecuta: newgrp docker"
    fi
    
    clone_repository
    check_env_file
    setup_directories
    build_frontend
    obtain_ssl_certificates
    start_services
    verify_installation
    print_summary
}

# Ejecutar
main "$@"