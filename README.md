
Create the venv
```bash
python -m venv venv
```

Activate the virtual environment and install requirements
```bash
source venv/bin/activate
```
```powershell
.\venv\Scripts\Activate.ps1
```

Install requirements
```python
pip install -r requirements.txt
```

Create the service
```bash
sudo nano /etc/systemd/system/weather.service
```

Paste in this to create the service 

```bash
[Unit]
Description=Weather Display Flask App
After=network.target

[Service]
User=pi
WorkingDirectory=/home/pi/weather-app
ExecStart=/home/pi/venv/bin/python app.py
Restart=always
Environment=FLASK_ENV=production

[Install]
WantedBy=multi-user.target
```