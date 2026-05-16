from catalogs import build_all_catalogs

catalogs = build_all_catalogs()

print("Suppliers count:", len(catalogs["suppliers"]))
print("Categories count:", len(catalogs["categories"]))
print("Brands count:", len(catalogs["brands"]))
print("Client groups count:", len(catalogs["client_groups"]))

print("\nFirst 10 suppliers:")
for item in catalogs["suppliers"][:10]:
    print("-", item)

print("\nFirst 10 categories:")
for item in catalogs["categories"][:10]:
    print("-", item)

print("\nFirst 10 brands:")
for item in catalogs["brands"][:10]:
    print("-", item)

print("\nClient groups:")
for item in catalogs["client_groups"]:
    print("-", item)