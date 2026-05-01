@Library('shared-lib') _

pipeline {

    agent any

    options {
        timeout(time: 30, unit: 'MINUTES')
    }

    triggers {
        githubPush()
        pollSCM('H/5 * * * *')
    }

    environment {
        VM_IP   = '192.168.31.229'
        VM_USER = 'mvrc'
        SSH_KEY = '/var/lib/jenkins/.ssh/ansible_key'

        REPO_URL = 'https://github.com/MarcosCantelli/MVRC-HelpdeskBot.git'
        APP_DIR  = 'app'
        BRANCH   = 'main'
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

                    pytest --cov=app --cov-report=xml:coverage.xml
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

        stage('Deploy (Docker Compose)') {
            steps {
                withCredentials([
                    string(credentialsId: 'telegram-token-id', variable: 'TELEGRAM_TOKEN')
                ]) {
                    sh '''
                        ssh -i "$SSH_KEY" -o StrictHostKeyChecking=no "$VM_USER@$VM_IP" << EOF

                        set -e

                        echo "📥 Clonando/Atualizando projeto..."

                        if [ ! -d "$APP_DIR" ]; then
                            git clone -b $BRANCH $REPO_URL $APP_DIR
                        fi

                        cd $APP_DIR
                        git checkout $BRANCH
                        git pull origin $BRANCH

                        echo "📦 Subindo containers com docker-compose..."

                        export TELEGRAM_TOKEN="$TELEGRAM_TOKEN"

                        docker compose down || true
                        docker compose up -d --build

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

                    for i in {1..10}; do
                        if curl -f http://$VM_IP:5000/health; then
                            echo "✅ API OK"
                            exit 0
                        fi
                        echo "⏳ Tentando novamente..."
                        sleep 5
                    done

                    echo "❌ API não respondeu"
                    exit 1
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