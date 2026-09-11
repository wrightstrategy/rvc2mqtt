#!/usr/bin/env python3
"""Exercise the built application against an isolated broker on port 2883."""
import configparser
from pathlib import Path
import subprocess
import sys
import tempfile
import time
import uuid

BROKER = "eclipse-mosquitto:2@sha256:6f8d8a947c506f8a2290ec65cd4bd2bc7cb4d43fb5f6271f861cb013e2ef9797"


def docker(*args, check=True):
    return subprocess.run(["docker", *args], text=True, capture_output=True, check=check)


def main(image):
    # Every resource has task-owned identity; cleanup never matches global names.
    network = "rvc-config-test-" + uuid.uuid4().hex
    containers = []
    docker("network", "create", "--internal", network)
    try:
        absent = docker("run", "--rm", "--network", "none", image, check=False)
        assert absent.returncode != 0 and "external INI" in absent.stderr, absent.stderr
        docker("run", "--rm", "--network", "none", image, "python", "-c",
               "from pathlib import Path; assert not Path('/app/rvc2mqtt.ini').exists()")
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            # Docker Desktop must also be able to share the fixture directory.
            root.chmod(0o755)
            (root / "mosquitto.conf").write_text("listener 2883\nallow_anonymous false\npassword_file /mosquitto/config/passwords\n")
            docker("run", "--rm", "--user", "0", "--mount",
                   f"type=bind,src={root},dst=/mosquitto/config", BROKER,
                   "mosquitto_passwd", "-b", "-c", "/mosquitto/config/passwords", "test-user", "test-password")
            (root / "passwords").chmod(0o644)
            broker = docker("run", "-d", "--network", network, "--network-alias", "broker",
                            "--mount", f"type=bind,src={root},dst=/mosquitto/config,readonly", BROKER).stdout.strip()
            containers.append(broker)
            deadline = time.monotonic() + 20
            while docker("exec", broker, "mosquitto_pub", "-h", "127.0.0.1", "-p", "2883",
                         "-u", "test-user", "-P", "test-password", "-t", "test/ready", "-m", "ready", check=False).returncode:
                if time.monotonic() >= deadline:
                    raise AssertionError("Test broker did not become ready")
                time.sleep(0.2)
            config = configparser.ConfigParser(inline_comment_prefixes=";")
            config.read("rvc2mqtt.ini.example")
            config["General"]["debug"] = "1"
            config["MQTT"].update(mqttBroker="broker", mqttPort="2883", mqttUser="test-user", mqttPass="test-password")
            config["CAN"]["CANport"] = "127.0.0.1:3333"
            config["HomeAssistant"]["discovery_enabled"] = "0"
            config["Commands"] = {"enabled": "0"}
            fixture = root / "rvc2mqtt.ini"
            with fixture.open("w") as stream:
                config.write(stream)
            fixture.chmod(0o644)  # Synthetic only; contains no production values.
            app = docker("run", "-d", "--network", network, "--mount",
                         f"type=bind,src={fixture},dst=/app/rvc2mqtt.ini,readonly", image).stdout.strip()
            containers.append(app)
            deadline = time.monotonic() + 25
            while True:
                logs = docker("logs", app).stdout
                if "MQTT Connected with code Success" in logs:
                    break
                if time.monotonic() >= deadline:
                    raise AssertionError("Application did not authenticate on port 2883: " + logs)
                time.sleep(0.2)
            assert "Connecting to MQTT: broker:2883" in logs
            assert "test-password" not in logs
            print("PASS: external INI required; image has no site INI; application authenticated on declared port 2883")
    finally:
        for container in reversed(containers):
            docker("rm", "-f", container, check=False)
        docker("network", "rm", network, check=False)


if __name__ == "__main__":
    main(sys.argv[1])
