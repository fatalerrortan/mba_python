pipeline {
    agent any

    stages {
        stage('Build Docker Image') {
            steps {
                echo 'Docker-Image von Fabman wird aufgebaut...'
                script {
                    checkout scm
                    def tag = "tanmba_test:jenkins"
                    def customImage = docker.build("${tag}", "-f Dockerfile .")

                    customImage.inside {
                        sh 'uname -a'
                        sh 'ls -al'
                    }
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
                script {
                    def remote = [:]
                    remote.name = 'resberry'
                    remote.host = '192.168.178.51'
                    remote.user = 'pi'
                    remote.password = '900804'
                    remote.allowAnyHosts = true
                    
                    sshCommand remote: remote, command: "ls -al"
                    sshCommand remote: remote, command: "pwd"
                    sshCommand remote: remote, command: "uname -a"
                }
            }
        }
    }
}
