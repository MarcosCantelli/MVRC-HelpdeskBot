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

        stage('Detect Project Type') {
            steps {
                script {
                    devopsPipeline.detectProjectType()
                }
            }
        }

        stage('Build & Test') {
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

        stage('Build & Push Docker') {
            steps {
                withCredentials([usernamePassword(
                    credentialsId: 'dockerhub-creds',
                    usernameVariable: 'DOCKER_USER',
                    passwordVariable: 'DOCKER_PASS'
                )]) {
                    sh '''
                        echo "$DOCKER_PASS" | docker login -u "$DOCKER_USER" --password-stdin

                        docker build -f Dockerfile.api -t $DOCKER_IMAGE_API:latest .
                        docker push $DOCKER_IMAGE_API:latest

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
                    sleep 15
                    curl -f http://${VM_IP}:5000/ && echo "API OK"
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