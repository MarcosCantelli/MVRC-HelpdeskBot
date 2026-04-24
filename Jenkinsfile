pipeline {
    agent any

    environment {
        TELEGRAM_TOKEN = credentials('telegram-token-id')
    }

    stages {

        stage('Clone') {
            steps {
                git 'https://github.com/seu-usuario/seu-repo.git'
            }
        }

        stage('Build') {
            steps {
                sh 'docker-compose build'
            }
        }

        stage('Deploy') {
            steps {
                sh 'docker-compose down || true'
                sh 'docker-compose up -d'
            }
        }
    }
}