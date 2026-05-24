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

        // =========================
        // DOCKER
        // =========================
        DOCKER_IMAGE_API = 'mrhightech/helpdesk-api'
        DOCKER_IMAGE_BOT = 'mrhightech/helpdesk-bot'

        // =========================
        // VM
        // =========================
        VM_IP   = '192.168.31.229'
        VM_USER = 'mvrc'
        SSH_KEY = '/var/lib/jenkins/.ssh/ansible_key'

        // =========================
        // GIT
        // =========================
        REPO_URL = 'https://github.com/MarcosCantelli/MVRC-HelpdeskBot.git'
        APP_DIR  = 'app'
        BRANCH   = 'main'

        // =========================
        // SONAR
        // =========================
        PROJECT_TYPE = 'python'
        SONAR_PROJECT_KEY = 'helpdesk-bot'
        SONAR_HOST_URL = 'http://192.168.31.232:9000'
    }

    stages {

        // =========================
        // CHECKOUT
        // =========================
        stage('Checkout') {
            steps {
                checkout scm
            }
        }

        // =========================
        // BUILD + TEST
        // =========================
        stage('Build & Test') {
            steps {

                sh '''
                    set -e

                    echo "========================="
                    echo "CRIANDO VENV"
                    echo "========================="

                    python3 -m venv venv

                    . venv/bin/activate

                    echo "========================="
                    echo "ATUALIZANDO PIP"
                    echo "========================="

                    pip install --upgrade pip

                    echo "========================="
                    echo "INSTALANDO DEPENDÊNCIAS"
                    echo "========================="

                    pip install -r requirements.txt

                    echo "========================="
                    echo "INSTALANDO DEPENDÊNCIAS TESTE"
                    echo "========================="

                    pip install pytest pytest-cov pytest-asyncio

                    echo "========================="
                    echo "CONFIGURANDO AMBIENTE TESTE"
                    echo "========================="

                    export PYTHONPATH=$(pwd)
                    export TEST_ENV=true

                    echo "========================="
                    echo "RODANDO TESTES"
                    echo "========================="

                    pytest --cov=app --cov-report=xml:coverage.xml

                    echo "========================="
                    echo "TESTES FINALIZADOS"
                    echo "========================="
                '''
            }
        }

        // =========================
        // SONARQUBE
        // =========================
        stage('Code Analysis (SonarQube)') {

            steps {

                withSonarQubeEnv('SonarQube') {

                    script {

                        def scannerHome = tool 'SonarScanner'

                        sh """
                            set -e

                            . venv/bin/activate

                            export PYTHONPATH=\$(pwd)
                            export TEST_ENV=true

                            echo "========================="
                            echo "SONAR ANALYSIS"
                            echo "========================="

                            ${scannerHome}/bin/sonar-scanner \\
                              -Dsonar.projectKey=${SONAR_PROJECT_KEY} \\
                              -Dsonar.sources=. \\
                              -Dsonar.python.version=3 \\
                              -Dsonar.host.url=$SONAR_HOST_URL \\
                              -Dsonar.login=$SONAR_AUTH_TOKEN \\
                              -Dsonar.python.coverage.reportPaths=coverage.xml \\
                              -Dsonar.coverage.exclusions=tests/**,__pycache__/**,.pytest_cache/**,venv/**

                            echo "========================="
                            echo "SONAR FINALIZADO"
                            echo "========================="
                        """
                    }
                }
            }
        }

        // =========================
        // QUALITY GATE
        // =========================
        stage('Quality Gate') {

            steps {

                timeout(time: 10, unit: 'MINUTES') {

                    waitForQualityGate abortPipeline: true
                }
            }
        }

        // =========================
        // DOCKER BUILDX
        // =========================
        stage('Docker Buildx Setup') {

            steps {

                sh '''
                    set -e

                    echo "========================="
                    echo "CONFIGURANDO BUILDX"
                    echo "========================="

                    docker run --privileged --rm tonistiigi/binfmt --install all

                    docker buildx create --name multiarch_builder --use || true

                    docker buildx inspect --bootstrap
                '''
            }
        }

        // =========================
        // DOCKER BUILD + PUSH
        // =========================
        stage('Docker Build & Push (ARM)') {

            steps {

                withCredentials([
                    usernamePassword(
                        credentialsId: 'dockerhub-creds',
                        usernameVariable: 'DOCKER_USER',
                        passwordVariable: 'DOCKER_PASS'
                    )
                ]) {

                    sh '''
                        set -e

                        echo "========================="
                        echo "DOCKER LOGIN"
                        echo "========================="

                        echo "$DOCKER_PASS" | docker login -u "$DOCKER_USER" --password-stdin

                        echo "========================="
                        echo "BUILD API"
                        echo "========================="

                        docker buildx build \
                          --platform linux/arm/v7 \
                          -f Dockerfile.api \
                          -t $DOCKER_IMAGE_API:latest \
                          --push .

                        echo "========================="
                        echo "BUILD BOT"
                        echo "========================="

                        docker buildx build \
                          --platform linux/arm/v7 \
                          -f Dockerfile.bot \
                          -t $DOCKER_IMAGE_BOT:latest \
                          --push .

                        echo "========================="
                        echo "PUSH FINALIZADO"
                        echo "========================="
                    '''
                }
            }
        }

        // =========================
        // DEPLOY
        // =========================
        stage('Deploy (Raspberry - Docker Compose)') {

            steps {

                withCredentials([

                    string(
                        credentialsId: 'telegram-token-id',
                        variable: 'TELEGRAM_TOKEN'
                    ),

                    string(
                        credentialsId: 'telegram-admin-id',
                        variable: 'ADMIN_CHAT_ID'
                    ),

                    string(
                        credentialsId: 'supabase-db-url',
                        variable: 'DATABASE_URL'
                    )

                ]) {

                    sh '''
                        set -e

                        echo "========================="
                        echo "INICIANDO DEPLOY"
                        echo "========================="

                        ssh -i "$SSH_KEY" \
                            -o StrictHostKeyChecking=no \
                            "$VM_USER@$VM_IP" << EOF

set -e

echo "========================="
echo "ATUALIZANDO REPOSITÓRIO"
echo "========================="

if [ ! -d "$APP_DIR" ]; then
    git clone -b $BRANCH $REPO_URL $APP_DIR
fi

cd $APP_DIR

git checkout $BRANCH
git pull origin $BRANCH

echo "========================="
echo "CRIANDO .ENV"
echo "========================="

cat > .env <<EOL
TELEGRAM_TOKEN=$TELEGRAM_TOKEN
TELEGRAM_CHAT_ID=$ADMIN_CHAT_ID
DATABASE_URL=$DATABASE_URL
EOL

echo "========================="
echo "DOCKER PULL"
echo "========================="

docker pull $DOCKER_IMAGE_API:latest
docker pull $DOCKER_IMAGE_BOT:latest

echo "========================="
echo "RECRIANDO STACK"
echo "========================="

docker compose down --remove-orphans || true

docker compose pull

docker compose up -d --force-recreate

echo "========================="
echo "DEPLOY FINALIZADO"
echo "========================="

EOF
                    '''
                }
            }
        }
    }

    // =========================
    // POST
    // =========================
    post {

        always {

            echo "========================="
            echo "LIMPANDO WORKSPACE"
            echo "========================="

            cleanWs()
        }

        success {

            echo "✅ PIPELINE EXECUTADO COM SUCESSO"
        }

        failure {

            echo "❌ PIPELINE FALHOU"
        }
    }
}