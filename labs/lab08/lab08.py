import secrets
import sys
def xor(a, b):
    if len(a) != len(b):
        raise ValueError('Длины байтовых строк должны совпадать')
    return bytes(x ^ y for x, y in zip(a, b))
p1 = 'КодоваяФраза1'.encode('utf-8')
p2 = 'Безопасность2'.encode('utf-8')
assert len(p1) == len(p2)
key = secrets.token_bytes(len(p1))
c1, c2 = xor(p1, key), xor(p2, key)
print('Архипов Александр Сергеевич | НБИбд-01-24')
print('P1:', p1.decode())
print('P2:', p2.decode())
print('Длина в байтах:', len(p1))
print('C1 (hex):', c1.hex())
print('C2 (hex):', c2.hex())
if len(sys.argv) > 1 and sys.argv[1] == 'attack':
    recovered_key = xor(c1, p1)
    recovered_p2 = xor(xor(c1, c2), p1)
    assert recovered_key == key
    assert recovered_p2 == p2
    print('Восстановленный P2 из C1, C2 и известного P1:', recovered_p2.decode())
    print('Восстановление ключа по известному P1: OK')
else:
    d1, d2 = xor(c1, key), xor(c2, key)
    assert d1 == p1 and d2 == p2
    print('Расшифрованный P1:', d1.decode())
    print('Расшифрованный P2:', d2.decode())
    print('Точное восстановление обоих сообщений: OK')
