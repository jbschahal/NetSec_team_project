import os


key_dir = os.path.expanduser("~/netsec/keys/")
my_key_path = key_dir + "my.key"
cli_key_path = key_dir + "client.key"
server_key_path = key_dir + "server.key"
flag2_key_path = key_dir + "flag2.key" # 20174.1.11.2
flag3_key_path = key_dir + "flag3.key" # 20174.1.11.2
cert_dir = os.path.expanduser("~/netsec/certs/")
root_cert_path = cert_dir + "root.crt" # 20174.1
my_cert_path = cert_dir + "my.crt" # 20174.1.11
cli_cert_path = cert_dir + "client.crt" # 20174.1.11.1
server_cert_path = cert_dir + "server.crt" # 20174.1.11.2
flag2_cert_path = cert_dir + "flag2.crt" # 20174.1.11.2
flag3_cert_path = cert_dir + "flag3.crt" # 20174.1.11.2
flag3a_cert_path = cert_dir + "flag3a.crt" # 20174.1.11.2
flag3b_cert_path = cert_dir + "flag3b.crt" # 20174.1.11.2

cert_dict = {
    "20174.1":root_cert_path,
    "20174.1.11":my_cert_path,
    "20174.1.11.1":cli_cert_path,
    "20174.1.11.2":server_cert_path,
    "20174.1.22.1":flag2_cert_path,
    "20174.1.1337.4":flag3_cert_path,
    "20174.1.1337.4.1":flag3a_cert_path,
    "20174.1.1337.4.2":flag3b_cert_path,
}

key_dict = {
    "20174.1.11":my_key_path,
    "20174.1.11.1":cli_key_path,
    "20174.1.11.2":server_key_path,
    "20174.1.22.1":flag2_key_path,
    "20174.1.1337.4":flag3_cert_path,
}


def getPrivateKeyForAddr(addr):
    if addr == "20174.1.1337.4":
        return None
    addr = key_dict[addr]
    with open(addr) as fp:
        private_key_user = fp.read()
    return private_key_user.encode()

def getCertsForAddr(addr):
    if addr == "20174.1.1337.4":
        addr1 = cert_dict[addr]
        addr2 = cert_dict["20174.1.1337.4.1"]
        addr3 = cert_dict["20174.1.1337.4.2"]
        with open(addr1) as fp:
            certs_user1 = fp.read()
        with open(addr2) as fp:
            certs_user2 = fp.read()
        with open(addr3) as fp:
            certs_user3 = fp.read()
        return [certs_user1.encode(), certs_user2.encode(), certs_user3.encode()]

    addr1 = cert_dict[addr]
    addr2 = cert_dict["20174.1.11"]
    with open(addr1) as fp:
        certs_user1 = fp.read()
    with open(addr2) as fp:
        certs_user2 = fp.read()
    return [certs_user1.encode(), certs_user2.encode()]

def getRootCert(addr):
    addr = cert_dict[addr]
    with open(addr) as fp:
        root_cert_user = fp.read()
    return root_cert_user.encode()
