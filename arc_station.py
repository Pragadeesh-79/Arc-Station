import asyncio

from bleak import (
    BleakClient,
    BleakScanner
)


DEVICE_NAME = "Arc Station"

CHARACTERISTIC_UUID = (
    "12345678-1234-1234-1234-123456789002"
)


async def send_command(command):

    print(
        f"Searching for {DEVICE_NAME}..."
    )

    device = await (
        BleakScanner
        .find_device_by_name(
            DEVICE_NAME
        )
    )

    if device is None:

        print(
            "Arc Station not found."
        )

        return

    print(
        "Found Arc Station"
    )

    async with BleakClient(
        device
    ) as client:

        print(
            "Connected!"
        )

        await client.write_gatt_char(
            CHARACTERISTIC_UUID,
            command.encode()
        )

        print(
            f"Sent: {command}"
        )


asyncio.run(
    send_command("HOME")
)
