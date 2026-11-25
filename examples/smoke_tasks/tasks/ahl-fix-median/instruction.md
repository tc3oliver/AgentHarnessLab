`/app/stats.py` has a buggy `median(values)`. Fix it so that:
- for an even number of values it returns the mean of the two middle values (a float);
- it does not modify the list passed in;
- an empty list raises `ValueError`.

Do not change `mean`. The function must keep working for lists of ints and floats.
