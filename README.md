# tado-flow-pid
Replaces the tado temperature control algorithm by utilizing flow temperature.

It cannot really change the algorithm, but it controls the flow temperatur in a way that it always keeps the temperatur of the room with the (current) highest heat demand exactly 0.5 °C below the value configured in the app. Other rooms are controlled by tado as usual. This means it works best if there is one main room (e. g. living room) that always requires the most heat.

### Requirements:
* You need a tado premium subscription (aka "AI Assist")
* You need to be able to control the "Flow Temperature" (Vorlauftemperatur/Aanvoertemperatuur). Check the app if you see this in the settings (usually present if tado is connected using OpenTherm).
* Disable "Automated optimization" of the flow temperature in the tado app

## Run on docker
1. Create a `docker-compose.yml` file:
```
services:
  tado-flow-pid:
    image: xiic/tado-flow-pid:latest
    restart: unless-stopped
    environment:
      # Minimum flow temperature:
      FLOW_MIN: 20
      # Maximum flow temperature at -10°C outside temperature; upper limit:
      FLOW_MAX_MINUS10: 70
      # Maximum flow temperature at +20°C outside temperature; *lower* limit for the *maximum* calculated flow:
      FLOW_MAX_PLUS20: 40
      # Integral gain; increase to make the change quicker (when away from the setpoint):
      PARAM_KI: 0.02
      # Proportional-on-measurement gain; increase to make the change *slower* when close to the setpoint:
      PARAM_KPOM: 6.0
    volumes:
      - tado-flow-pid_data:/data

volumes:
  tado-flow-pid_data:
    driver: local
```
2. `docker compose up -d`
3. Check the docker logs to authenticate
4. Done!

## Run manually
```
cp .env.example .env
python -m venv venv
--> now activate the venv
python -m pip install -r ./requirements.txt
python src/app.py
```

# Disclaimer
This library is not affiliated with the tado° GmbH.

# Development

## Publish to Docker Hub
```
docker build -t xiic/tado-flow-pid:0.0.1 -t xiic/tado-flow-pid:latest .
docker push xiic/tado-flow-pid:0.0.1
docker push xiic/tado-flow-pid:latest
```

## HTTP Toolkit (Windows)
Add httptoolkit CA to venv truststore for convenient HTTPS inspection:
```
Get-Content $env:LOCALAPPDATA\httptoolkit\Config\ca.pem | Add-Content .\venv\Lib\site-packages\certifi\cacert.pem
```