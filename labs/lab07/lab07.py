alphabet = 'абвгдеёжзийклмнопрстуфхцчшщъыьэюя'
indices = {ch: i for i, ch in enumerate(alphabet)}
def transform(text, gamma, sign):
    if not gamma:
        raise ValueError('Гамма не должна быть пустой')
    return ''.join(alphabet[(indices[ch] + sign * indices[gamma[i % len(gamma)]]) % len(alphabet)]
                   for i, ch in enumerate(text))
text = 'архиповалександр'
gamma = 'безопасность'
encrypted = transform(text, gamma, 1)
decrypted = transform(encrypted, gamma, -1)
print('Архипов Александр Сергеевич | НБИбд-01-24')
print('Алфавит:', alphabet, '| N =', len(alphabet), '| номера 0...32')
print('Текст:', text)
print('Гамма:', gamma)
print('Шифротекст:', encrypted)
print('Расшифровка:', decrypted)
assert decrypted == text
assert transform(transform(alphabet, 'я', 1), 'я', -1) == alphabet
print('Проверка восстановления: OK')
