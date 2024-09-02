# Dockerfile for fortio load generator
FROM golang:alpine3.17

WORKDIR /app

RUN go install fortio.org/fortio@latest

ENV PATH=$PATH:/root/go/bin

ENTRYPOINT sleep 10000000
