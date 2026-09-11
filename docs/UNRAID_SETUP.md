# RVC2MQTT Unraid Setup Guide

Quick guide for installing rvc2mqtt on Unraid using the Docker template.

## Quick Install (Recommended)

### Method 1: Using the Unraid Template

1. **Add Template Repository**
   - In Unraid: Go to Docker tab
   - Click "Add Container" button at bottom
   - Click "Template repositories" at top
   - Add: `https://raw.githubusercontent.com/wrightstrategy/rvc2mqtt/main/unraid-template.xml`

2. **Select Template**
   - Under "Template", search for: `rvc2mqtt`
   - Click on the rvc2mqtt template

3. **Prepare Configuration Files**
   ```bash
   # SSH into your Unraid server
   ssh root@<unraid-ip>

   # Create appdata directory
   mkdir -p /mnt/user/appdata/rvc2mqtt/{logs,audit,mappings}

   # Clone repo to get config files
   cd /tmp
   git clone https://github.com/wrightstrategy/rvc2mqtt.git

   # Copy config files to appdata
   cp /tmp/rvc2mqtt/rvc2mqtt.ini.example /mnt/user/appdata/rvc2mqtt/rvc2mqtt.ini
   cp /tmp/rvc2mqtt/rvc-spec.yml /mnt/user/appdata/rvc2mqtt/
   cp -r /tmp/rvc2mqtt/mappings/* /mnt/user/appdata/rvc2mqtt/mappings/

   # Clean up
   rm -rf /tmp/rvc2mqtt
   ```

4. **Edit Configuration**
   ```bash
   # Edit config file
   nano /mnt/user/appdata/rvc2mqtt/rvc2mqtt.ini

   # Update these settings:
   # [MQTT]
   # mqttBroker = <your-mqtt-broker-ip>
   # mqttUser = <your-mqtt-username>
   # mqttPass = <your-mqtt-password>
   #
   # [CAN]
   # CANport = <your-esp32-ip>:3333
   ```

5. **Configure Template in Unraid GUI**
   - **Configuration File**: `/mnt/user/appdata/rvc2mqtt/rvc2mqtt.ini`
   - **Mappings Directory**: `/mnt/user/appdata/rvc2mqtt/mappings`
   - **RVC Spec File**: `/mnt/user/appdata/rvc2mqtt/rvc-spec.yml`
   - **Logs Directory**: `/mnt/user/appdata/rvc2mqtt/logs`
   - **Audit Directory**: `/mnt/user/appdata/rvc2mqtt/audit`
   - **Timezone**: Your timezone (e.g., `America/New_York`)
   - MQTT settings are configured only in the mounted INI.

6. **Apply and Start**
   - Click "Apply"
   - Unraid will download the Docker image from GitHub
   - Container will start automatically

7. **Verify Operation**
   - Click on the rvc2mqtt container icon
   - Select "Logs"
   - Look for successful connection messages
   - Check Home Assistant for auto-discovered entities

### Method 2: Manual Docker Installation

If you prefer not to use the template:

```bash
# SSH into Unraid
ssh root@<unraid-ip>

# Prepare directories
mkdir -p /mnt/user/appdata/rvc2mqtt/{logs,audit,mappings}
cd /mnt/user/appdata/rvc2mqtt

# Get config files
git clone https://github.com/wrightstrategy/rvc2mqtt.git temp
cp temp/rvc2mqtt.ini.example rvc2mqtt.ini
cp temp/rvc-spec.yml .
cp -r temp/mappings/* mappings/
cp temp/docker-compose.yml .
rm -rf temp

# Edit configuration
nano rvc2mqtt.ini
# Update MQTT and CAN settings

# Start with docker-compose
docker-compose up -d

# View logs
docker-compose logs -f
```

## Configuration

### Required Settings

Edit `/mnt/user/appdata/rvc2mqtt/rvc2mqtt.ini`:

```ini
[MQTT]
mqttBroker = 192.168.1.100    ; Your MQTT broker IP
mqttUser = hassio              ; Your MQTT username
mqttPass = your-password       ; Your MQTT password

[CAN]
CANport = 192.168.1.200:3333   ; Your ESP32 SLCAN IP:port
```

### Optional Settings

Configure broker host/port, credentials, CAN interface, and debug level in the mounted
INI. The template's timezone is the only supported environment setting. MQTT, CAN, and
debug environment overrides are not implemented.

## Updating

### Update to Latest Version

1. **Via Unraid GUI** (Easiest)
   - Docker tab → Click "Check for Updates"
   - If update available, click "Update"
   - Container will pull latest image and restart

2. **Via Command Line**
   ```bash
   docker pull ghcr.io/wrightstrategy/rvc2mqtt:latest
   docker stop rvc2mqtt
   docker rm rvc2mqtt
   # Then recreate via Unraid GUI or docker-compose up -d
   ```

3. **Via docker-compose**
   ```bash
   cd /mnt/user/appdata/rvc2mqtt
   docker-compose pull
   docker-compose up -d
   ```

## Troubleshooting

### Container Won't Start

1. **Check logs**
   ```bash
   docker logs rvc2mqtt
   ```

2. **Verify config file exists**
   ```bash
   ls -la /mnt/user/appdata/rvc2mqtt/
   cat /mnt/user/appdata/rvc2mqtt/rvc2mqtt.ini
   ```

3. **Check permissions**
   ```bash
   chown -R nobody:users /mnt/user/appdata/rvc2mqtt/
   chmod -R 755 /mnt/user/appdata/rvc2mqtt/
   ```

### Cannot Connect to SLCAN

1. **Test ESP32 connectivity**
   ```bash
   ping <esp32-ip>
   nc -zv <esp32-ip> 3333
   ```

2. **Verify config**
   ```bash
   grep CANport /mnt/user/appdata/rvc2mqtt/rvc2mqtt.ini
   ```

### Cannot Connect to MQTT

1. **Test MQTT broker**
   ```bash
   ping <mqtt-broker-ip>
   ```

2. **Check MQTT credentials**
   - Verify username/password in config file
   - Check MQTT broker allows remote connections
   - Check Home Assistant Mosquitto add-on settings

### No Entities in Home Assistant

1. **Check discovery is enabled**
   ```bash
   grep discovery_enabled /mnt/user/appdata/rvc2mqtt/rvc2mqtt.ini
   # Should show: discovery_enabled = 1
   ```

2. **Check MQTT topics**
   - In HA: Developer Tools → MQTT
   - Listen to: `homeassistant/#`
   - Should see discovery messages

3. **Restart Home Assistant**
   - Sometimes needed to refresh MQTT integration
   - Settings → System → Restart

## Advanced

### View Real-time Logs
```bash
docker logs -f rvc2mqtt
# Or via docker-compose:
cd /mnt/user/appdata/rvc2mqtt
docker-compose logs -f
```

### Access Container Shell
```bash
docker exec -it rvc2mqtt sh
```

### Backup Configuration
```bash
tar -czf rvc2mqtt-backup-$(date +%Y%m%d).tar.gz \
  /mnt/user/appdata/rvc2mqtt/
```

### Restore Configuration
```bash
tar -xzf rvc2mqtt-backup-YYYYMMDD.tar.gz -C /
```

## Support

- **GitHub Issues**: https://github.com/wrightstrategy/rvc2mqtt/issues
- **Documentation**: https://github.com/wrightstrategy/rvc2mqtt/tree/main/docs
- **Unraid Forums**: Community support (coming soon)

## Architecture

```
┌─────────────────────────────────────────┐
│          Unraid Server                   │
│                                          │
│  ┌────────────────────────────────────┐ │
│  │ rvc2mqtt Docker Container          │ │
│  │ (ghcr.io/wrightstrategy/rvc2mqtt:latest) │ │
│  │                                    │ │
│  │ Connects to:                       │ │
│  │ • ESP32 SLCAN (192.168.x.x:3333)  │ │
│  │ • MQTT Broker (on HA Yellow)      │ │
│  └────────────────────────────────────┘ │
│                                          │
│  Volumes:                                │
│  • /mnt/user/appdata/rvc2mqtt/          │
│    ├── rvc2mqtt.ini                     │
│    ├── rvc-spec.yml                     │
│    ├── mappings/                        │
│    ├── logs/                            │
│    └── audit/                           │
└─────────────────────────────────────────┘
           │                    │
           ▼                    ▼
      ESP32 SLCAN          HA Yellow
      (CAN Bus)            (MQTT Broker)
```

## Next Steps

After successful installation:
1. Verify all RV sensors appear in Home Assistant
2. Test control commands (lights, HVAC, etc.)
3. Monitor logs for any errors
4. Customize entity names in mappings file if needed
5. Set up Home Assistant dashboards

---

**Installation Time**: ~15 minutes
**Difficulty**: Beginner (with template) / Intermediate (manual)
**Version**: Phase 2.5
**Last Updated**: December 2025
