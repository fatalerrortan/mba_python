pipeline {
    agent any

    stages {
        stage('Build Docker Image') {
            steps {
                echo 'Building..'
                checkout scm
                def tag = "tanmba_test:jenkins"
                def customImage = docker.build("${tag}", ".")

                customImage.inside {
                    sh 'uname -a'
                    sh 'ls -al'
                }
            }
        }
        stage('Test Image') {
            steps {
                echo 'Testing..'
            }
        }
        stage('Deploy Image auf Server iuvo132') {
            steps {
                echo 'Deploying....'
            }
        }
    }
}
