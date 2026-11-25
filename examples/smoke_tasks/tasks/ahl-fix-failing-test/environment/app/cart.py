def total_cents(items, discount_pct=0):
    subtotal = sum(price * qty for price, qty in items)
    discount = int(subtotal * discount_pct / 100)
    return subtotal - discount
