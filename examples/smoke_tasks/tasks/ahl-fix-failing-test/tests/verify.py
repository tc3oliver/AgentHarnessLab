import sys
sys.path.insert(0, "/app")
from cart import total_cents

assert total_cents([(250, 2), (100, 1)]) == 600
assert total_cents([(1050, 1)], 15) == 892
assert total_cents([], 20) == 0
assert total_cents([(1, 1)], 50) == 0      # 0.5 rounds up to 1 cent off
assert total_cents([(1, 1)], 49) == 1      # 0.49 rounds to 0
assert total_cents([(999, 3)], 10) == 2697  # 299.7 -> 300
assert total_cents([(5, 1)], 10) == 4       # 0.5 -> 1
assert total_cents([(333, 3)], 33) == 999 - 330  # 329.67 -> 330
assert total_cents([(100, 0)], 10) == 0
print("ok")
