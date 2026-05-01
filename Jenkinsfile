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

                    echo "🐍 Criando ambiente Python"
                    python3 -m venv venv
                    . venv/bin/activate

                    echo "📦 Instalando dependências"
                    pip install --upgrade pip
                    pip install -r requirements.txt

                    echo "🧪 Instalando libs de teste"
                    pip install pytest pytest-cov pytest-asyncio

                    export PYTHONPATH=$(pwd)
                    export TEST_ENV=true

                    echo "🚀 Rodando testes"
                    pytest --cov=app --cov-report=xml:coverage.xml
                '''
            }
        }

        stage('Docker Buildx Setup') {
            steps {
                sh '''
                    set -e

                    echo "🔧 Ativando multi-arch (binfmt)"
                    docker run --privileged --rm tonistiigi/binfmt --install all

                    echo "🔧 Criando builder buildx"
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

                        echo "🔐 Login Docker Hub"
                        echo "$DOCKER_PASS" | docker login -u "$DOCKER_USER" --password-stdin

                        echo "📦 Build & Push API (ARMv7)"
                        docker buildx build \
                          --platform linux/arm/v7 \
                          -f Dockerfile.api \
                          -t mrhightech/helpdesk-api:latest \
                          --push .

                        echo "📦 Build & Push BOT (ARMv7)"
                        docker buildx build \
                          --platform linux/arm/v7 \
                          -f Dockerfile.bot \
                          -t mrhightech/helpdesk-bot:latest \
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

                    sh """
                        set -e

                        ssh -i ${SSH_KEY} -o StrictHostKeyChecking=no ${VM_USER}@${VM_IP} '
                            set -e

                            echo "🧹 Removendo containers antigos"
                            docker rm -f helpdesk-api || true
                            docker rm -f helpdesk-bot || true

                            echo "📥 Pull imagens atualizadas"
                            docker pull mrhightech/helpdesk-api:latest
                            docker pull mrhightech/helpdesk-bot:latest

                            echo "🚀 Subindo API"
                            docker run -d \
                              --name helpdesk-api \
                              --restart always \
                              -p 5000:5000 \
                              mrhightech/helpdesk-api:latest

                            echo "🤖 Subindo BOT"
                            docker run -d \
                              --name helpdesk-bot \
                              --restart always \
                              -e TELEGRAM_TOKEN=${TELEGRAM_TOKEN} \
                              mrhightech/helpdesk-bot:latest

                            echo "✅ Deploy concluído"
                        '
                    """
                }
            }
        }

        stage('Healthcheck') {
            steps {
                sh '''
                    set -e

                    echo "⏳ Aguardando API subir..."
                    sleep 20

                    curl -f http://$VM_IP:5000/ || exit 1

                    echo "✅ API OK"
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