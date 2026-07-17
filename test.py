from generator import Generator

gen = Generator(width=30, height=30, min_rooms=12, max_rooms=18, min_floors=2, max_floors=3, seed=42)
floors = gen.generate()

for floor in floors:
    print(f"\n=== Floor {floor.level} ===")
    floor.print_grid()