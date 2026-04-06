def calculate_total(price, tax_rate):
    tax = price * tax_rate
    total = price + tax
    return "Total is: " + str(total)

print(calculate_total(100, 0.05))