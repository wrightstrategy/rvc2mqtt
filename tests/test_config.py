"""The external INI is required; MQTT port selection preserves legacy defaults."""
from pathlib import Path
import tempfile
import unittest

from rvc_config import ConfigurationError, load_configuration


class ConfigurationTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.path = Path(self.tmp.name) / "rvc2mqtt.ini"
        self.example = Path("rvc2mqtt.ini.example").read_text()

    def load(self, text):
        self.path.write_text(text)
        return load_configuration(self.path)

    def test_external_file_is_required(self):
        with self.assertRaisesRegex(ConfigurationError, "external INI"):
            load_configuration(self.path)

    def test_declared_port_is_used_and_omitted_port_defaults_to_1883(self):
        for port in (1, 2883, 65535):
            config = self.load(self.example.replace("mqttPort = 1883", f"mqttPort = {port}"))
            self.assertEqual(config.getint("MQTT", "mqttPort", fallback=1883), port)
        text = "\n".join(line for line in self.example.splitlines() if not line.startswith("mqttPort"))
        self.assertEqual(self.load(text).getint("MQTT", "mqttPort", fallback=1883), 1883)

    def test_invalid_ports_fail_without_echoing_values(self):
        for port in ("0", "65536", "-1", "", "not-a-port"):
            with self.assertRaisesRegex(ConfigurationError, "mqttPort"):
                self.load(self.example.replace("mqttPort = 1883", f"mqttPort = {port}"))

    def test_parse_errors_never_include_config_contents(self):
        secret = "synthetic-secret-marker"
        for text in (self.example + f"\n{secret}\n", self.example.replace("mqttPass = password", f"mqttPass = %{secret}")):
            with self.assertRaises(ConfigurationError) as caught:
                self.load(text)
            self.assertNotIn(secret, str(caught.exception))

    def test_required_fields_are_validated_before_startup(self):
        for before, after in (("debug = 0", "debug = invalid"), ("mqttBroker =", "wrongName =")):
            with self.assertRaises(ConfigurationError):
                self.load(self.example.replace(before, after))

    def test_existing_comment_and_percent_dialect_is_preserved(self):
        config = self.load(self.example.replace("mqttPass = password", "mqttPass = literal%%value"))
        self.assertEqual(config.get("MQTT", "mqttPass"), "literal%value")
        self.assertEqual(config.get("CAN", "CANport"), "192.168.1.200:3333")


if __name__ == "__main__":
    unittest.main()
