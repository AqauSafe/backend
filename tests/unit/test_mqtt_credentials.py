from __future__ import annotations

from django.core.management import call_command

from apps.devices.models import Device
from integrations.mqtt.crypto import encrypt_secret


def test_sync_mqtt_credentials_writes_device_acl(tmp_path, db, farm, pond):
    device = Device.objects.create(
        farm=farm,
        pond=pond,
        device_id="esp32-acl",
        name="ACL Device",
        secret_encrypted=encrypt_secret("broker-password"),
    )
    acl_file = tmp_path / "acl.generated"

    call_command(
        "sync_mqtt_credentials",
        "--skip-passwords",
        f"--acl-file={acl_file}",
    )

    content = acl_file.read_text()
    assert "user aquasafe-backend" in content
    assert "user esp32-acl" in content
    assert f"aquasafe/v1/devices/{device.device_id}/telemetry" in content
    assert f"aquasafe/v1/devices/{device.device_id}/commands" in content
