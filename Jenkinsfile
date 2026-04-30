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

                    echo "🐍 Python version:"
                    python3 --version

                    echo "Criando venv..."
                    python3 -m venv venv || true

                    echo "Ativando venv..."
                    . venv/bin/activate

                    echo "Atualizando pip..."
                    python -m pip install --upgrade pip

                    echo "Instalando dependências..."
                    pip install -r requirements.txt

                    echo "Instalando ferramentas de teste..."
                    pip install pytest pytest-cov pytest-asyncio

                    echo "Rodando testes..."
                    export PYTHONPATH=$(pwd)
                    export TEST_ENV=true

                    pytest --cov=app --cov-report=xml:coverage.xml

                    echo "Verificando coverage..."
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
                        echo "$DOCKER_PASS" | docker login -u "$DOCKER_USER" --password-stdin

                        docker buildx create --use || true

                        docker buildx build \
                          --platform linux/amd64,linux/arm/v7 \
                          -f Dockerfile.api \
                          -t $DOCKER_IMAGE_API:latest \
                          --push .
                        
                        docker buildx build \
                          --platform linux/amd64,linux/arm/v7 \
                          -f Dockerfile.bot \
                          -t $DOCKER_IMAGE_BOT:latest \
                          --push .

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
                    sh """
                        ssh -i ${SSH_KEY} -o StrictHostKeyChecking=no ${VM_USER}@${VM_IP} '

                        docker pull ${DOCKER_IMAGE_API}:latest
                        docker pull ${DOCKER_IMAGE_BOT}:latest

                        docker rm -f helpdesk-api || true
                        docker rm -f helpdesk-bot || true

                        docker run -d --name helpdesk-api -p 5000:5000 ${DOCKER_IMAGE_API}:latest

                        docker run -d --name helpdesk-bot \
                            -e TELEGRAM_TOKEN="${TELEGRAM_TOKEN}" \
                            ${DOCKER_IMAGE_BOT}:latest
                        '
                    """
                }
            }
        }

        stage('Healthcheck') {
            steps {
                sh """
                    echo "Aguardando API subir..."
                    sleep 15

                    curl -f http://${VM_IP}:5000/ && echo "✅ API OK"
                """
            }
        }
    }

    post {
        always {
            cleanWs()
        }
    }
}