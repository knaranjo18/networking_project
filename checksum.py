def gen_checksum16(data: bytes) -> bytes:
    """Generates a 16 bit XOR based checksum for a byte array"""

    # Make sure we are evenly divisible by 16 bits (2 bytes)
    if len(data) % 2 != 0:
        data += bytes([0x00])

    # Number of 16 bit chunks to iterate over
    num16_chunk = int(len(data) / 2)

    checksum = 0
    for i in range(0, num16_chunk):
        chunk = int.from_bytes(data[2 * i : 2 * (i + 1)], "big")

        # Running XOR
        checksum ^= chunk

    return checksum


def check_checksum16(data: bytes, checksum: int) -> bool:
    """Verifies that data has no error by comparing checksum. If no errors then returns true."""
    # Locally calculate checksum of data
    calc_checksum = gen_checksum16(data)

    # Compare to a given checksum
    output = calc_checksum ^ checksum

    return output == 0
