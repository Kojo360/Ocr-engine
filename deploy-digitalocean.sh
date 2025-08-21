#!/bin/bash

# DigitalOcean Deployment Script for OCR Engine
# Usage: ./deploy-digitalocean.sh

echo "🚀 DigitalOcean OCR Engine Deployment Script"
echo "============================================="

# Check if required tools are installed
check_requirements() {
    echo "📋 Checking requirements..."
    
    if ! command -v doctl &> /dev/null; then
        echo "❌ doctl CLI not found. Installing..."
        case "$(uname -s)" in
            Linux*)
                snap install doctl
                ;;
            Darwin*)
                brew install doctl
                ;;
            *)
                echo "Please install doctl manually: https://docs.digitalocean.com/reference/doctl/how-to/install/"
                exit 1
                ;;
        esac
    fi
    
    if ! command -v docker &> /dev/null; then
        echo "❌ Docker not found. Please install Docker first."
        exit 1
    fi
    
    echo "✅ Requirements check passed"
}

# Initialize DigitalOcean CLI
init_doctl() {
    echo "🔐 Initializing DigitalOcean CLI..."
    echo "Please enter your DigitalOcean API token:"
    doctl auth init
    
    # Verify authentication
    if ! doctl account get &> /dev/null; then
        echo "❌ Authentication failed. Please check your API token."
        exit 1
    fi
    
    echo "✅ Authentication successful"
}

# Deploy using App Platform
deploy_app_platform() {
    echo "🏗️  Deploying to App Platform..."
    
    # Create app spec
    cat > app.yaml << EOF
name: ocr-engine
services:
- name: api
  source_dir: /
  github:
    repo: Kojo360/Ocr-engine
    branch: main
    run_command: python start_production.py
  environment_slug: python
  instance_count: 1
  instance_size_slug: basic-xxs
    http_port: 8080
  envs:
  - key: HOST
    value: "0.0.0.0"
    - key: PORT
        value: "8080"
  - key: TESSERACT_CMD
    value: "/usr/bin/tesseract"
  - key: POPPLER_PATH
    value: "/usr/bin"
  health_check:
    http_path: /health
databases:
- name: ocr-db
  engine: MYSQL
  version: "8"
  size: db-s-1vcpu-1gb
EOF

    # Deploy the app
    doctl apps create app.yaml
    
    echo "✅ App Platform deployment initiated"
    echo "📱 Check your DigitalOcean dashboard for deployment progress"
}

# Deploy using Droplet
deploy_droplet() {
    echo "💧 Creating Droplet..."
    
    # Create droplet
    DROPLET_NAME="ocr-engine-$(date +%s)"
    
    doctl compute droplet create $DROPLET_NAME \
        --size s-2vcpu-4gb \
        --image ubuntu-22-04-x64 \
        --region nyc1 \
        --ssh-keys $(doctl compute ssh-key list --format ID --no-header | head -1) \
        --wait
    
    # Get droplet IP
    DROPLET_IP=$(doctl compute droplet list --format Name,PublicIPv4 --no-header | grep $DROPLET_NAME | awk '{print $2}')
    
    echo "✅ Droplet created: $DROPLET_NAME ($DROPLET_IP)"
    
    # Wait for droplet to be ready
    echo "⏳ Waiting for droplet to be ready..."
    sleep 60
    
    # Install Docker and deploy
    echo "🐳 Installing Docker and deploying application..."
    
    ssh -o StrictHostKeyChecking=no root@$DROPLET_IP << 'EOF'
        # Install Docker
        curl -fsSL https://get.docker.com -o get-docker.sh
        sh get-docker.sh
        
        # Install Docker Compose
        curl -L "https://github.com/docker/compose/releases/download/v2.20.0/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose
        chmod +x /usr/local/bin/docker-compose
        
        # Clone and deploy application
        git clone https://github.com/Kojo360/Ocr-engine.git
        cd Ocr-engine
        docker-compose up -d
        
        # Configure firewall
        ufw allow 8000
        ufw allow ssh
        ufw --force enable
        
        echo "🎉 Deployment complete!"
EOF
    
    echo "✅ Droplet deployment complete"
    echo "🌐 Your OCR Engine is available at: http://$DROPLET_IP:8000"
    echo "🔍 Health check: http://$DROPLET_IP:8000/health"
}

# Deploy using Container Registry
deploy_container_registry() {
    echo "📦 Deploying with Container Registry..."
    
    # Create container registry
    REGISTRY_NAME="ocr-engine-registry"
    
    echo "Creating container registry..."
    doctl registry create $REGISTRY_NAME
    
    # Configure Docker to use the registry
    doctl registry login
    
    # Build and push image
    echo "🔨 Building Docker image..."
    docker build -t ocr-engine .
    docker tag ocr-engine registry.digitalocean.com/$REGISTRY_NAME/ocr-engine:latest
    
    echo "📤 Pushing to registry..."
    docker push registry.digitalocean.com/$REGISTRY_NAME/ocr-engine:latest
    
    echo "✅ Image pushed to registry"
    echo "📱 Now create an App Platform app using this image:"
    echo "   registry.digitalocean.com/$REGISTRY_NAME/ocr-engine:latest"
}

# Main menu
main_menu() {
    echo ""
    echo "Choose deployment method:"
    echo "1) App Platform (Recommended for teams)"
    echo "2) Droplet with Docker"
    echo "3) Container Registry + Manual App Platform"
    echo "4) Exit"
    echo ""
    read -p "Enter your choice [1-4]: " choice
    
    case $choice in
        1)
            deploy_app_platform
            ;;
        2)
            deploy_droplet
            ;;
        3)
            deploy_container_registry
            ;;
        4)
            echo "👋 Goodbye!"
            exit 0
            ;;
        *)
            echo "❌ Invalid choice. Please try again."
            main_menu
            ;;
    esac
}

# Main execution
main() {
    check_requirements
    init_doctl
    main_menu
}

# Run the script
main
