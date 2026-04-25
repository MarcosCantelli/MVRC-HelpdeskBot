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

        DOCKER_IMAGE_API = 'mrhightech/helpdesk-api'
        DOCKER_IMAGE_BOT = 'mrhightech/helpdesk-bot'
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

        // 🚀 MULTI-ARCH BUILD + PUSH
        stage('Build & Push Multi-Arch') {
            steps {
                withCredentials([usernamePassword(
                    credentialsId: 'dockerhub-creds',
                    usernameVariable: 'DOCKER_USER',
                    passwordVariable: 'DOCKER_PASS'
                )]) {
                    sh """
                        docker buildx create --use || true
                        docker buildx inspect --bootstrap

                        echo \$DOCKER_PASS | docker login -u \$DOCKER_USER

                        docker buildx build \
                            --platform linux/amd64,linux/arm64 \
                            -f Dockerfile.api \
                            -t \$DOCKER_USER/helpdesk-api:latest \
                            --push .

                        docker buildx build \
                            --platform linux/amd64,linux/arm64 \
                            -f Dockerfile.bot \
                            -t \$DOCKER_USER/helpdesk-bot:latest \
                            --push .
                    """
                }
            }
        }

        // 🚀 DEPLOY REMOTO (PULL)
        stage('Deploy na VM') {
            steps {
                withCredentials([
                    string(credentialsId: 'telegram-token-id', variable: 'TELEGRAM_TOKEN')
                ]) {
                    sh """
                        ssh -i ${SSH_KEY} -o StrictHostKeyChecking=no ${VM_USER}@${VM_IP} '

                            docker network create helpdesk-net 2>/dev/null || true

                            docker pull ${DOCKER_IMAGE_API}:latest
                            docker pull ${DOCKER_IMAGE_BOT}:latest

                            docker stop helpdesk-api 2>/dev/null || true
                            docker rm helpdesk-api 2>/dev/null || true

                            docker stop helpdesk-bot 2>/dev/null || true
                            docker rm helpdesk-bot 2>/dev/null || true

                            docker run -d \
                                --name helpdesk-api \
                                --network helpdesk-net \
                                -p 5000:5000 \
                                -e DB_HOST=helpdesk-db \
                                -e DB_PORT=5432 \
                                -e DB_NAME=helpdesk \
                                -e DB_USER=helpdesk_user \
                                -e DB_PASSWORD=strongpassword \
                                --restart unless-stopped \
                                ${DOCKER_IMAGE_API}:latest

                            docker run -d \
                                --name helpdesk-bot \
                                --network helpdesk-net \
                                -e TELEGRAM_TOKEN="${TELEGRAM_TOKEN}" \
                                --restart unless-stopped \
                                ${DOCKER_IMAGE_BOT}:latest

                            docker image prune -f
                        '
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