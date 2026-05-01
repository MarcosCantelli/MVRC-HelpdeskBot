pipeline {

    agent any

    environment {
        DOCKER_IMAGE_API = 'mvrc/helpdesk-api'
        DOCKER_IMAGE_BOT = 'mvrc/helpdesk-bot'

        VM_IP   = '192.168.31.229'
        VM_USER = 'mvrc'
        SSH_KEY = '/var/lib/jenkins/.ssh/ansible_key'
    }

    stages {

        stage('Checkout') {
            steps {
                checkout scm
            }
        }

        stage('Build & Test') {
            steps {
                sh '''
                    set -e

                    python3 -m venv venv || true
                    . venv/bin/activate

                    pip install --upgrade pip
                    pip install -r requirements.txt

                    pip install pytest pytest-cov pytest-asyncio

                    export PYTHONPATH=$(pwd)
                    export TEST_ENV=true

                    pytest --cov=app --cov-report=xml:coverage.xml || true
                '''
            }
        }

        stage('Docker Buildx Setup') {
            steps {
                sh '''
                    set -e

                    echo "🔧 Ativando suporte multi-arch..."
                    docker run --privileged --rm tonistiigi/binfmt --install all || true

                    echo "🔧 Criando builder buildx..."
                    docker buildx create --use --name multiarch_builder || true

                    docker buildx inspect --bootstrap
                '''
            }
        }

        stage('Docker Build & Push (ARM)') {
            steps {
                withCredentials([usernamePassword(
                    credentialsId: 'dockerhub-creds',
                    usernameVariable: 'DOCKER_USER',
                    passwordVariable: 'DOCKER_PASS'
                )]) {

                    sh '''
                        set -e

                        echo "🔐 Login Docker Hub"
                        echo "$DOCKER_PASS" | docker login -u "$DOCKER_USER" --password-stdin

                        echo "📦 Build API (ARMv7)"
                        docker buildx build \
                          --platform linux/arm/v7 \
                          -f Dockerfile.api \
                          -t $DOCKER_IMAGE_API:latest \
                          --push .

                        echo "📦 Build BOT (ARMv7)"
                        docker buildx build \
                          --platform linux/arm/v7 \
                          -f Dockerfile.bot \
                          -t $DOCKER_IMAGE_BOT:latest \
                          --push .
                    '''
                }
            }
        }

        stage('Deploy (Raspberry)') {
            steps {
                withCredentials([
                    string(credentialsId: 'telegram-token-id', variable: 'TELEGRAM_TOKEN')
                ]) {

                    sh '''
                        ssh -i "$SSH_KEY" -o StrictHostKeyChecking=no "$VM_USER@$VM_IP" << EOF

                        set -e

                        echo "🧹 Limpando containers antigos..."
                        docker rm -f helpdesk-api || true
                        docker rm -f helpdesk-bot || true

                        echo "📥 Baixando imagens..."
                        docker pull mvrc/helpdesk-api:latest
                        docker pull mvrc/helpdesk-bot:latest

                        echo "🚀 Subindo API..."
                        docker run -d \
                          --name helpdesk-api \
                          --restart always \
                          -p 5000:5000 \
                          mvrc/helpdesk-api:latest

                        echo "🤖 Subindo BOT..."
                        docker run -d \
                          --name helpdesk-bot \
                          --restart always \
                          -e TELEGRAM_TOKEN="$TELEGRAM_TOKEN" \
                          mvrc/helpdesk-bot:latest

                        echo "✅ Deploy finalizado!"

                        EOF
                    '''
                }
            }
        }

        stage('Healthcheck') {
            steps {
                sh '''
                    echo "⏳ Aguardando API..."
                    sleep 20

                    curl -f http://$VM_IP:5000/ && echo "✅ API OK"
                '''
            }
        }
    }

    post {
        always {
            cleanWs()
        }
    }
}