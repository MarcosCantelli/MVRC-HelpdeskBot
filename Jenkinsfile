@Library('shared-lib') _

pipeline {

    agent any

    options {
        timeout(time: 30, unit: 'MINUTES')
        timestamps()
    }

    triggers {
        githubPush()
        pollSCM('H/5 * * * *')
    }

    environment {
        DOCKER_IMAGE_API = 'mrhightech/helpdesk-api'
        DOCKER_IMAGE_BOT = 'mrhightech/helpdesk-bot'

        VM_IP   = '192.168.31.229'
        VM_USER = 'mvrc'
        SSH_KEY = '/var/lib/jenkins/.ssh/ansible_key'

        REPO_URL = 'https://github.com/MarcosCantelli/MVRC-HelpdeskBot.git'
        APP_DIR  = 'app'
        BRANCH   = 'main'

        PROJECT_TYPE = 'python'
        SONAR_PROJECT_KEY = 'helpdesk-bot'
        SONAR_HOST_URL = 'http://192.168.31.233:9000'
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

                    pytest --cov=app --cov-report=xml:coverage.xml
                '''
            }
        }

        stage('Code Analysis (SonarQube)') {
            steps {
                script {
                    def sonarUrl = env.SONAR_HOST_URL ?: 'http://192.168.31.233:9000'
                    def status = sh(script: "python3 -c 'import urllib.request; urllib.request.urlopen(\\\"${sonarUrl}\\\", timeout=5)'", returnStatus: true)
                    if (status != 0) {
                        error "SonarQube server unreachable at ${sonarUrl}. Verifique a rede ou o endereço de host."
                    }
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

        stage('Deploy (Raspberry - Docker Compose)') {
            steps {
                withCredentials([
                    string(credentialsId: 'telegram-token-id', variable: 'TELEGRAM_TOKEN'),
                    string(credentialsId: 'telegram-admin-id', variable: 'ADMIN_CHAT_ID'),
                    string(credentialsId: 'supabase-db-url', variable: 'DATABASE_URL')
                ]) {
                    sh '''
                        set -e

                        ssh -i "$SSH_KEY" -o StrictHostKeyChecking=no "$VM_USER@$VM_IP" << EOF
set -e

# Clone ou atualiza repo
if [ ! -d "$APP_DIR" ]; then
    git clone -b $BRANCH $REPO_URL $APP_DIR
fi

cd $APP_DIR
git checkout $BRANCH
git pull origin $BRANCH

# 🔥 CRIA .env AUTOMATICAMENTE
cat > .env <<EOL
TELEGRAM_TOKEN=$TELEGRAM_TOKEN
ADMIN_CHAT_ID=$ADMIN_CHAT_ID
DATABASE_URL=$DATABASE_URL
EOL

# Pull imagens
docker pull $DOCKER_IMAGE_API:latest
docker pull $DOCKER_IMAGE_BOT:latest

# Restart stack
docker compose down || true
docker compose up -d

EOF
                    '''
                }
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
            echo "❌ Pipeline falhou"
        }
    }
}