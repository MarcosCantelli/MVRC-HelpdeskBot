pipeline {

    agent any

    environment {
        DOCKER_IMAGE_API = 'mrhightech/helpdesk-api'
        DOCKER_IMAGE_BOT = 'mrhightech/helpdesk-bot'

        VM_IP   = '192.168.31.229'
        VM_USER = 'mvrc'
        SSH_KEY = '/var/lib/jenkins/.ssh/ansible_key'
    }

    options {
        timestamps()
        timeout(time: 30, unit: 'MINUTES')
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

                    python3 -m venv venv
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

                    docker run --privileged --rm tonistiigi/binfmt --install all

                    docker buildx create --name multiarch_builder --use || true
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

                        echo "$DOCKER_PASS" | docker login -u "$DOCKER_USER" --password-stdin

                        docker buildx build \
                          --platform linux/arm/v7 \
                          -f Dockerfile.api \
                          -t $DOCKER_IMAGE_API:latest \
                          --push .

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
                        set -e

                        echo "🚀 Deploy no Raspberry..."

                        ssh -i "$SSH_KEY" -o StrictHostKeyChecking=no "$VM_USER@$VM_IP" << EOF
                            set -e

                            echo "🧹 Limpando ambiente"
                            docker rm -f helpdesk-api || true
                            docker rm -f helpdesk-bot || true

                            echo "🌐 Criando network"
                            docker network create helpdesk-net || true

                            echo "📥 Pull imagens"
                            docker pull '"$DOCKER_IMAGE_API"':latest
                            docker pull '"$DOCKER_IMAGE_BOT"':latest

                            echo "🚀 Subindo API"
                            docker run -d \
                              --name helpdesk-api \
                              --network helpdesk-net \
                              --restart always \
                              -p 5000:5000 \
                              '"$DOCKER_IMAGE_API"':latest

                            echo "🤖 Subindo BOT"
                            docker run -d \
                              --name helpdesk-bot \
                              --network helpdesk-net \
                              --restart always \
                              -e TELEGRAM_TOKEN='"$TELEGRAM_TOKEN"' \
                              -e API_URL=http://helpdesk-api:5000 \
                              '"$DOCKER_IMAGE_BOT"':latest

                            echo "✅ Deploy finalizado"
EOF
                    '''
                }
            }
        }

        stage('Healthcheck') {
            steps {
                sh '''
                    set -e

                    echo "🔎 Validando deploy no Raspberry..."

                    ssh -i "$SSH_KEY" -o StrictHostKeyChecking=no "$VM_USER@$VM_IP" << 'EOF'
                        set -e

                        echo "📦 Containers ativos:"
                        docker ps | grep helpdesk || (echo "❌ Containers não estão rodando" && exit 1)

                        echo "🌐 Testando API internamente..."
                        docker exec helpdesk-api curl -f http://localhost:5000/ || (echo "❌ API não respondeu" && exit 1)

                        echo "🤖 Logs do BOT:"
                        docker logs helpdesk-bot --tail 20 || true

                        echo "✅ Deploy saudável"
EOF
                '''
            }
        }
    }

    post {
        always {
            cleanWs()
        }

        success {
            echo "✅ Pipeline executado com sucesso"
        }

        failure {
            echo "❌ Pipeline falhou - verifique logs acima"
        }
    }
}