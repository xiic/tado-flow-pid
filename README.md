# tado-flow-pid
Replace the tado temperature control algorithm by utilizing flow temperature.

## Disclaimer
This library is not affiliated with the tado° GmbH.

## Run on docker
docker-compose.yml
```
services:
  tado-flow-pid:
    image: tado-flow-pid
    container_name: tado-flow-pid
    restart: unless-stopped
```

## Environment variables
* `TADO_USERNAME`
* `TADO_PASSWORD`

## Setup
```
python -m venv venv
--> activate
python -m pip install -r ./requirements.txt
python src/app.py
```

