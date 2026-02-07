def validate_ip(ip: str) -> bool:
    """Validate IPv4, excluding loopback, link-local, multicast, and experimental ranges."""
    octets = ip.split('.')

    # Must have exactly 4 octets
    if len(octets) != 4:
        return False

    # Validate and convert each octet
    try:
        nums = []
        for octet in octets:
            # Reject empty or leading zeros (except "0" itself)
            if not octet or (octet[0] == '0' and len(octet) > 1):
                return False
            # Must be digits only
            if not octet.isdigit():
                return False
            num = int(octet)
            # Must be 0-255
            if num > 255:
                return False
            nums.append(num)
    except ValueError:
        return False

    # Check excluded ranges
    a, b, c, d = nums

    # Loopback: 127.0.0.0/8
    if a == 127:
        return False

    # Link-local: 169.254.0.0/16
    if a == 169 and b == 254:
        return False

    # Multicast: 224.0.0.0/4 (224-239)
    if 224 <= a <= 239:
        return False

    # Experimental/Reserved: 240.0.0.0/4 (240-255)
    if a >= 240:
        return False

    return True

if __name__ == "__main__":
    print(validate_ip("192.168.0.1"))
    print(validate_ip("1.1.1.1"))
    print(validate_ip("1.1.1a.1"))
    print(validate_ip("1.1.1."))
    print(validate_ip("1.1.1"))
    print(validate_ip(".1.1.1"))
    print(validate_ip("127.0.0.5"))
    print(validate_ip("169.0.0.1"))
    print(validate_ip("255.255.255.255"))
    print(validate_ip("224.0.0.1"))
    print(validate_ip("239.100.0.1"))
