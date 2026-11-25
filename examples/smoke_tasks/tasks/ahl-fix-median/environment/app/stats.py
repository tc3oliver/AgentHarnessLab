def mean(values):
    return sum(values) / len(values)


def median(values):
    values.sort()
    n = len(values)
    return values[n // 2]
