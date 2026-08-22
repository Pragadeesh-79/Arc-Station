import asyncio
from bleak import BleakScanner


async def main():

    print("Scanning for Arc Station...\n")

    devices = await BleakScanner.discover()

    for device in devices:

        if device.name:

            print(
                device.name,
                device.address
            )


asyncio.run(main())
