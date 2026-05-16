from margin_logic import calculate_margin_result

supplier = input("Supplier: ")
category = input("Category: ")
brand = input("Brand: ")
client_group = input("Client group: ")
cost = float(input("Cost: "))

result = calculate_margin_result(
    supplier=supplier,
    category=category,
    brand=brand,
    client_group=client_group,
    cost=cost
)

print("\n=== RESULT ===")
print(result)