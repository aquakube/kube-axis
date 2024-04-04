import re

def is_valid_axis_serial_number(serial_number: str) -> bool:
    """
    Each Axis product has a unique serial number that can be used in the installation process or for identification of individual devices in large installations.  
    Serial numbers for Axis network video, print and document servers generally start with either 00408c or accc8e followed by another 6 hexadecimal characters.
    The serial number is identical to the product's hardware address (MAC address) and can be written in the format 00408c1a2b3c, accc8e1a2b3c, 00:40:8c:1a:2b:3c or acc:cc:8e:1a:2b:3c.
    """
    regex = "^(00408c|accc8e)[0-9a-fA-F]{6}$|^(00408c|accc8e)([0-9a-fA-F]{2}:){5}[0-9a-fA-F]{2}$"
    pattern = re.compile(regex, re.IGNORECASE)

    # Remove colons if present and convert to lowercase
    serial_number = serial_number.replace(':', '').lower()

    if pattern.match(serial_number):
        return True
    else:
        return False
