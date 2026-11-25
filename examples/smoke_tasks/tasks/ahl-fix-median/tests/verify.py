import sys
sys.path.insert(0, "/app")
import stats

assert stats.median([3, 1, 2]) == 2
assert stats.median([4, 1, 3, 2]) == 2.5
assert stats.median([10, 20]) == 15
assert stats.median([5]) == 5
assert stats.median([2.5, 0.5, 9.0, 1.0, 7.0]) == 2.5
assert stats.median([-5, -1, -3, -2]) == -2.5
data = [9, 1, 5, 3]
before = list(data)
stats.median(data)
assert data == before, "input was modified"
try:
    stats.median([])
except ValueError:
    pass
else:
    raise AssertionError("empty list must raise ValueError")
assert stats.mean([1, 2, 3, 4]) == 2.5
print("ok")
