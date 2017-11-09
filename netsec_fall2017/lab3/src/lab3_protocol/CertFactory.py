# TODO: modify so addr is not filename but a.b.c.d address


def getPrivateKeyForAddr(addr):
    with open(addr) as fp:
        private_key_user = fp.read()
    return private_key_user

def getCertsForAddr(addr):
    with open(addr) as fp:
        certs_user = fp.read()
    return certs_user

def getRootCert(addr):
    with open(addr) as fp:
        root_cert_user = fp.read()
    return root_cert_user
