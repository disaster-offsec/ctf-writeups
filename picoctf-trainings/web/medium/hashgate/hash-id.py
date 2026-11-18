import hashlib

numbers = [i for i in range(3000, 3000 + 100)]
for num in numbers:
    hash_value = hashlib.md5(str(num).encode()).hexdigest()
    print(f"{hash_value}")
