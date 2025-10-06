from checksum import check_checksum16, gen_checksum16

data = bytes([0x40, 0xDF, 0x52, 0x66])
bad_data = bytes([0x41, 0xDF, 0x51, 0x61])

checksum = gen_checksum16(data)

full_good = data + checksum

full_bad = bad_data + checksum

if check_checksum16(full_good[0:-2], full_good[-2:]):
    print("[Pass] Checksum matched for good data")
else:
    print("[Fail] Checksum did not match for bad data")

if check_checksum16(full_bad[0:-2], full_bad[-2:]):
    print("[Fail] Checksum matched for bad data")
else:
    print("[Pass] Checksum did not match for bad data")
