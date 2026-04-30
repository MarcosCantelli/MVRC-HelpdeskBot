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

        VM_IP        = '192.168.31.229'

        VM_USER      = 'mvrc'

        SSH_KEY      = '/var/lib/jenkins/.ssh/ansible_key'



        REPO_URL     = 'https://github.com/MarcosCantelli/MVRC-HelpdeskBot.git' // 🔥 ALTERAR

        APP_DIR      = 'app'

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



                    echo "✅ Coverage OK"

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



        stage('Deploy (Build no Raspberry)') {

            steps {

                withCredentials([

                    string(credentialsId: 'telegram-token-id', variable: 'TELEGRAM_TOKEN')

                ]) {

                    sh '''

                        ssh -i "$SSH_KEY" -o StrictHostKeyChecking=no "$VM_USER@$VM_IP" << EOF



                        set -e



                        echo "📥 Clonando/Atualizando projeto..."

                        if [ ! -d "$APP_DIR" ]; then

                            git clone $REPO_URL $APP_DIR

                        fi



                        cd $APP_DIR

                        git pull



                        echo "🧹 Removendo containers antigos..."

                        docker rm -f helpdesk-api || true

                        docker rm -f helpdesk-bot || true



                        echo "🚀 Build API (ARM nativo)"

                        docker build -f Dockerfile.api -t helpdesk-api:latest .



                        echo "🚀 Build BOT (ARM nativo)"

                        docker build -f Dockerfile.bot -t helpdesk-bot:latest .



                        echo "🚀 Subindo API..."

                        docker run -d \

                          --name helpdesk-api \

                          --restart always \

                          -p 5000:5000 \

                          helpdesk-api:latest



                        echo "🤖 Subindo BOT..."

                        docker run -d \

                          --name helpdesk-bot \

                          --restart always \

                          -e TELEGRAM_TOKEN="$TELEGRAM_TOKEN" \

                          helpdesk-bot:latest



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