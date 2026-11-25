In `/app`, `python3 -m unittest test_cart` fails. The tests describe the intended behaviour; fix the bug in
`cart.py` (do not edit `test_cart.py`).

`total_cents(items, discount_pct)` takes `items` as `(unit_price_cents, quantity)` pairs and an integer
percentage discount, and returns the total in cents. The discount amount is rounded half up to whole cents.
