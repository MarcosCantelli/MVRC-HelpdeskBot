@Library('shared-lib') _

pipeline {
    agent any

    options {
        timeout(time: 20, unit: 'MINUTES')
    }

    triggers {
        githubPush()
        pollSCM('H/5 * * * *')
    }

    environment {
        VM_IP        = '192.168.31.229'
        VM_USER      = 'mvrc'
        SSH_KEY      = '/var/lib/jenkins/.ssh/ansible_key'

        DOCKER_IMAGE_API = 'mrhightech/helpdesk-api'
        DOCKER_IMAGE_BOT = 'mrhightech/helpdesk-bot'
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

                    echo "🐍 Criando ambiente..."
                    python3 -m venv venv || true
                    . venv/bin/activate

                    echo "📦 Instalando dependências..."
                    pip install --upgrade pip
                    pip install -r requirements.txt

                    echo "🧪 Instalando ferramentas de teste..."
                    pip install pytest pytest-cov pytest-asyncio

                    echo "🚀 Rodando testes..."
                    export PYTHONPATH=$(pwd)
                    export TEST_ENV=true

                    pytest --cov=app --cov-report=xml:coverage.xml

                    echo "✅ Coverage gerado"
                    ls -la coverage.xml
                '''
            }
        }

        stage('Code Analysis') {
            steps {
                script {
                    devopsPipeline.sonarAnalysis()
                }
            }
        }

        stage('Quality Gate') {
            steps {
                script {
                    devopsPipeline.qualityGate()
                }
            }
        }

        stage('Build & Push Docker') {
            steps {
                withCredentials([usernamePassword(
                    credentialsId: 'dockerhub-creds',
                    usernameVariable: 'DOCKER_USER',
                    passwordVariable: 'DOCKER_PASS'
                )]) {
                    sh '''
                        set -e

                        echo "🔐 Login DockerHub..."
                        echo "$DOCKER_PASS" | docker login -u "$DOCKER_USER" --password-stdin

                        echo "🚀 Build API"
                        docker build -f Dockerfile.api -t $DOCKER_IMAGE_API:latest .
                        docker push $DOCKER_IMAGE_API:latest

                        echo "🚀 Build BOT"
                        docker build -f Dockerfile.bot -t $DOCKER_IMAGE_BOT:latest .
                        docker push $DOCKER_IMAGE_BOT:latest
                    '''
                }
            }
        }

        stage('Deploy') {
            steps {
                withCredentials([
                    string(credentialsId: 'telegram-token-id', variable: 'TELEGRAM_TOKEN')
                ]) {
                    sh '''
                        ssh -i "$SSH_KEY" -o StrictHostKeyChecking=no "$VM_USER@$VM_IP" << EOF

                        set -e

                        echo "📥 Pull das imagens..."
                        docker pull $DOCKER_IMAGE_API:latest
                        docker pull $DOCKER_IMAGE_BOT:latest

                        echo "🧹 Removendo containers antigos..."
                        docker rm -f helpdesk-api || true
                        docker rm -f helpdesk-bot || true

                        echo "🚀 Subindo API..."
                        docker run -d \
                          --name helpdesk-api \
                          --restart always \
                          -p 5000:5000 \
                          $DOCKER_IMAGE_API:latest

                        echo "🤖 Subindo BOT..."
                        docker run -d \
                          --name helpdesk-bot \
                          --restart always \
                          -e TELEGRAM_TOKEN="$TELEGRAM_TOKEN" \
                          $DOCKER_IMAGE_BOT:latest

                        echo "✅ Deploy finalizado!"

                        EOF
                    '''
                }
            }
        }

        stage('Healthcheck') {
            steps {
                sh '''
                    echo "⏳ Aguardando API subir..."
                    sleep 15

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