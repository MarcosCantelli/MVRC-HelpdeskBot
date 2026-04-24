@Library('shared-lib') _

pipeline {
    agent any

    environment {
        TELEGRAM_TOKEN = credentials('telegram-token-id')
    }

    stages {

        stage('Clone') {
            steps {
                git 'https://github.com/MarcosCantelli/MVRC-HelpdeskBot.git'
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