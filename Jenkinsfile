@Library('shared-lib') _

pipeline {
    agent any

    triggers {
        githubPush()
        pollSCM('H/2 * * * *')
    }

    environment {
        VM_IP        = '192.168.31.229'
        VM_USER      = 'mvrc'
        SSH_KEY      = '/var/lib/jenkins/.ssh/ansible_key'

        IMAGE_API    = 'helpdesk-api'
        IMAGE_BOT    = 'helpdesk-bot'
    }

    stages {

        stage('Checkout') {
            steps {
                checkout scm
                script {
                    def branchName = env.GIT_BRANCH ?: sh(script: 'git rev-parse --abbrev-ref HEAD', returnStdout: true).trim()
                    def commitId = env.GIT_COMMIT ?: sh(script: 'git rev-parse HEAD', returnStdout: true).trim()
                    echo "Branch: ${branchName}"
                    echo "Commit: ${commitId}"
                }
            }
        }

        stage('Detect Project Type') {
            steps {
                script {
                    devopsPipeline.detectProjectType()
                }
            }
        }

        stage('Build') {
            steps {
                script {
                    devopsPipeline.buildProject()
                }
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

        // 🔥 Build separado (API + BOT)
        stage('Build Docker Images') {
            steps {
                sh """
                    docker build -f Dockerfile.api -t ${IMAGE_API}:${BUILD_NUMBER} -t ${IMAGE_API}:latest .
                    docker build -f Dockerfile.bot -t ${IMAGE_BOT}:${BUILD_NUMBER} -t ${IMAGE_BOT}:latest .
                """
                echo "Imagens criadas: API e BOT"
            }
        }

        // 📦 Empacotar imagens
        stage('Package Images') {
            steps {
                sh """
                    docker save ${IMAGE_API}:latest | gzip > /tmp/${IMAGE_API}.tar.gz
                    docker save ${IMAGE_BOT}:latest | gzip > /tmp/${IMAGE_BOT}.tar.gz
                """
            }
        }

        // 🚀 Deploy remoto
        stage('Deploy na VM') {
            steps {
                withCredentials([
                    string(credentialsId: 'telegram-token-id', variable: 'TELEGRAM_TOKEN')
                ]) {
                    sh """
                        scp -i ${SSH_KEY} -o StrictHostKeyChecking=no /tmp/${IMAGE_API}.tar.gz ${VM_USER}@${VM_IP}:/tmp/
                        scp -i ${SSH_KEY} -o StrictHostKeyChecking=no /tmp/${IMAGE_BOT}.tar.gz ${VM_USER}@${VM_IP}:/tmp/

                        ssh -i ${SSH_KEY} -o StrictHostKeyChecking=no ${VM_USER}@${VM_IP} '
                            
                            docker load < /tmp/${IMAGE_API}.tar.gz
                            docker load < /tmp/${IMAGE_BOT}.tar.gz

                            docker network create helpdesk-net 2>/dev/null || true

                            docker stop helpdesk-api 2>/dev/null || true
                            docker rm helpdesk-api 2>/dev/null || true

                            docker stop helpdesk-bot 2>/dev/null || true
                            docker rm helpdesk-bot 2>/dev/null || true

                            docker run -d \
                                --name helpdesk-api \
                                --network helpdesk-net \
                                -p 5000:5000 \
                                --restart unless-stopped \
                                ${IMAGE_API}:latest

                            docker run -d \
                                --name helpdesk-bot \
                                --network helpdesk-net \
                                -e TELEGRAM_TOKEN="${TELEGRAM_TOKEN}" \
                                --restart unless-stopped \
                                ${IMAGE_BOT}:latest

                            docker image prune -f

                            rm -f /tmp/${IMAGE_API}.tar.gz
                            rm -f /tmp/${IMAGE_BOT}.tar.gz
                        '

                        rm -f /tmp/${IMAGE_API}.tar.gz
                        rm -f /tmp/${IMAGE_BOT}.tar.gz
                    """
                }
            }
        }

        // 🧪 Healthcheck
        stage('Verificar API') {
            steps {
                sh """
                    echo "Aguardando API subir..."
                    sleep 15

                    curl -sf http://${VM_IP}:5000/ticket \
                        && echo "API OK" \
                        || echo "API não respondeu"
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