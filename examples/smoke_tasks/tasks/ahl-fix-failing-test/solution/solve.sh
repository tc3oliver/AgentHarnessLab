#!/bin/bash
set -e
cat > /app/cart.py <<'AHL_EOF'
def total_cents(items, discount_pct=0):
    subtotal = sum(price * qty for price, qty in items)
    discount = (subtotal * discount_pct * 2 + 100) // 200
    return subtotal - discount
AHL_EOF
