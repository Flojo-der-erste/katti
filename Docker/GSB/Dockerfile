FROM golang:1.20-rc-bullseye

RUN git clone https://github.com/google/safebrowsing.git
WORKDIR ./safebrowsing
RUN go mod download
RUN go mod vendor
WORKDIR ./cmd/sbserver
ENTRYPOINT ["go", "run", "main.go"]
