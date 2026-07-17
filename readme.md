# Dungeon Generator

## Generator
### 1. Room Placement
For create the room placement system was used [BSP(Binary Space Partitioning)](#what-is-bsp)
#### What it does? (BSP)
Recursively splits the map into rectangular sub‑sections until each leaf is small enough to hold a single room.
Then, inside each leaf, we place a room (with random size and position). This guarantees that rooms never overlap and are spread across the whole map in a hierarchical way.

#### Steps
**Steps for the generation:**

- Start with the whole map as one rectangle.

- At each step, choose a random axis (horizontal or vertical) and split the rectangle at a random position (within constraints).

- Repeat until we have at least as many leaves as the target number of rooms, or until the rectangles become too small.

- Place one room inside each leaf (choose a random position and size within the leaf).

#### Why BSP?
It produces a natural dungeon with rooms that are well‑distributed, often forming corridors and distinct "wings". It’s the classic algorithm from the [RogueBasin article](https://www.roguebasin.com/index.php/Basic_BSP_Dungeon_generation).

### 2. Building Connections - Graph Approach
After rooms are placed, we treat them as nodes in a graph.

#### Proximity threshold
We create an edge between any two rooms whose Manhattan distance ≤ ``5`` (you can adjust this). This gives a dense but local network.

> Manhattan distance = |x₁-x₂| + |y₁‑y₂|, the distance measured along grid lines (like a taxi moving in a city).

#### Connectivity guarantee
We run a [BFS](#what-is-bfs) starting from the first room. If any room is unreachable, we connect the nearest disconnected room to the main component (even if distance > 5). This ensures the entire floor is a single connected graph.

#### Connection objects
Each edge becomes a Connection object, stored in both rooms and the floor. Later, ``corridors`` are carved between connected rooms (L‑shaped paths).

### 3. Rule Enforcement (Post‑Processing)
After building the initial connected graph, we apply your custom rules as fix‑up passes (in this order):

1. **END rule:** The END room (E) must have exactly one connection, and that must be to the BOSS room (B).
    Implementation: Remove all other connections from E, and if it’s not connected to B, add that connection.

2. **BOSS rule:** The BOSS room (B) must have exactly two connections: one to END (already ensured) and one to a NORMAL (X) room.
    Implementation: Remove any extra connections from B (beyond the one to E), then find the nearest X room and add a connection to it.

3. **STAIR_UP rule:** The STAIR_UP room (U) cannot connect directly to D, B, or E. It must connect to at least one NORMAL (X) room.
    Implementation: Remove any forbidden connections from U; if U becomes isolated, connect it to the nearest X room.

4. **Final safety pass:** Every room except END must have at least one connection.
    Implementation: For any room (S, X, D, U, B) with zero connections, connect it to the nearest room that is not END (and not problematic for B’s degree – but we already fixed B).

This order ensures that all rules are satisfied while keeping the graph connected.

#### Room Type Summary
| Room | Symbol | What it represents | Connection Rules |
| ---- | ------ | ------------------ | ---------------- |
| Spawn | S | Starting point of the Dungeon | Must have at least 1 connection (typically to an X room). |
| NORMAL |	X |	Standard room |	Must have at least 1 connection (can connect to any type except END). |
| STAIR_DOWN |	D |	Exit to next floor |	Must have at least 1 connection (typically to an X room). |
| STAIR_UP |	U |	Entrance from previous floor |	Must have at least 1 connection; cannot connect to D, B, or E. |
| BOSS |	B |	Final boss room |	Exactly 2 connections: one to END (E) and one to a NORMAL (X) room. |
| END |	E |	Reward room after boss |	Exactly 1 connection: only to BOSS (B). |

> All rooms (except END) must have at least one connection – this is enforced by the final safety pass.

### 4. Parameters of Generator
| Parameter     |	Type |	Default |	What it controls |
| ---------     | ---    | ---------| -------------- |
| width         | int	 | required | Total horizontal size of the dungeon grid (number of cells). |
| height        | int	 | required | Total vertical size of the dungeon grid. |
| min_rooms     | int	 | required | Minimum number of rooms (including special ones) per floor. |
| max_rooms     | int	 | required | Maximum number of rooms per floor. The actual number is randomly chosen between min_rooms and max_rooms. |
| min_floors    | int	 | 1        | Minimum number of dungeon levels (floors) to generate. |
| max_floors    | int	 | 1        | Maximum number of floors. The actual number is random within this range. |
| min_room_size | int	 | 3        | Minimum size (width or height) of a room in cells. Must be at least 2. |
| max_room_size | int	 | 6        | Maximum size of a room. Rooms are randomly sized between min_room_size and max_room_size. |
| seed          | int	 | random   | Seed for the random number generator; using the same seed produces the same dungeon layout (for debugging).|

#### How room count affects layout:

- With ``min_rooms`` = 12 and ``max_rooms`` = 18, you’ll get a fairly dense dungeon.

- Larger maps (e.g., 30×30) allow the BSP to create more varied room sizes and corridors.

- The connection threshold (currently fixed at 5) can be adjusted in the code if you want rooms to connect only when very close (value = 2) or farther (value = 8).

### BFS - Breadth‑First Search {#what-is-bfs}
#### What it is:
BFS is an algorithm for exploring or traversing a graph (a network of nodes connected by edges).
It starts at a chosen "root" node and explores **all its immediate neighbours first**, then moves on to their neighbours, then their neighbours, and so on. It works like a ripple in water: a circular wave spreading outward from the starting point.

#### How it works (step‑by‑step):

- Start at a room (e.g., the first room). Mark it as "visited".

- Add it to a queue (a waiting list).

- While the queue is not empty, take the front room out.

- For each room connected to it, if that room hasn’t been visited, mark it as visited and add it to the queue.

- Repeat until the queue is empty.

#### Why it is used in this generator:
After the initial connections are made (rooms that are within a distance of 5), we don’t know if every room is reachable. BFS tells us exactly which rooms are in the main connected group.
If some rooms are never visited by BFS, we know they are disconnected (isolated). The generator then builds a bridge to connect the nearest isolated room back to the main group.
This guarantee that the entire dungeon is one single, walkable component - no room is cut off behind a wall of empty space.

### BSP – Binary Space Partitioning {#what-is-bsp}
#### What it is:
BSP is a method for recursively subdividing a space (like a 2D rectangle) into smaller, non‑overlapping rectangular regions by making straight cuts (splits).
It’s a classic technique used in 3D gaming (for render order) and in dungeon generation to place rooms in a structured, tree‑like pattern.

#### How it works (step‑by‑step):

- Start with the whole dungeon map – one big rectangle.

- Choose a random axis (vertical or horizontal).

- Pick a random position along that axis (but respecting a minimum size).

- Split the rectangle into two smaller rectangles along that line.

- Repeat this splitting process on each child rectangle, over and over, until each rectangle is “small enough” to hold a single room.

- Finally, inside each smallest rectangle (leaf), place a room with a random size and position, ensuring it fits fully inside that leaf.

#### Why it is used in the generator:

- Rooms never overlap – because each leaf is independent and we check fit.

- Rooms are naturally spread across the whole map – you don’t get all rooms clumped in one corner.

- The layout has a “hierarchical” feel – rooms often line up along the splits, which creates natural corridors between them. This gives the dungeon a structured, hand‑crafted appearance rather than a chaotic random scatter.

#### How it splits:
```txt
+-------+-------+
|       |       |
|   A   |   B   |
|       |       |
+-------+---+---+
|       |   |   |
|   C   +---+   |
|       |   D   |
+-------+-------+
```

## Summary of the Generation Pipeline

1. Place rooms using BSP → ensure no overlap, good spread.

2. Identify special rooms:

   - Floor 0: SPAWN on the edge; STAIR_DOWN farthest from spawn.

   - Subsequent floors: STAIR_UP at the spot closest to previous floor’s STAIR_DOWN; STAIR_DOWN farthest from that entry.

   - Last floor: assign BOSS and END based on distance from entry.

3. Build initial connections using proximity + BFS connectivity.

4. Enforce rules in order: END → BOSS → STAIR_UP → final safety.

5. Carve corridors on the grid for visualization (L‑shaped paths between connected rooms).

The result is a fully connected, multi‑floor dungeon with predictable relationships between all room types, and with a visual grid you can print or export.

## Getting Started
To get started, import the ``Generator`` class:, and based on that you can generate all the floors.

Import from [Generator.py](./generator.py)
```py
from generator import Generator

gen = Generator(width=30, height=30, min_rooms=12, max_rooms=18, min_floors=2, max_floors=3, seed=42)
floors = gen.generate()
```

Also, if you want to get a debug ``json`` file, so you could analyze it more precisely, you can try using:
```py
gen.export_json()
```

And each ``floor`` as a function called ``print_grid()`` which will print a visual grid to you see what you generated:
```py
for floor in floors:
    print(f"\n=== Floor {floor.level} ===")
    floor.print_grid()
```
Returns:
```txt
=== Floor 0 ===
..............................
..............................
..............................
..............................
............X#######..........
....S########......######X....
............#......X.....#....
............#............#....
............X............#....
............#............#....
............#............#....
............#............#....
............#............#....
............#............#....
............#............#....
............#............#....
.......#####X............##X..
.......#....#.................
.......X....#.................
.......#....#.................
.......#....##X##.............
.......#........#.............
.......#........#.............
.......#........X########.....
.......#................#.....
.......#................#.....
.......#................#.....
.......#................D.....
...X####......................
..............................

=== Floor 1 ===
..............................
..............................
..............########X.......
...B######....#.......#.......
....#....#####X.......#.......
....#....#............#.....X.
....#....#............#.....#.
....#....X##..........#.....#.
....#......#..........X######.
....#......#..........#.......
....E......#..........#.......
...........#..........#.......
...........#..........X##.....
...........#............#.....
...........X###.........#.....
..............X.........#.....
..............#.........#.....
..............#.........X#....
..X...........#..........#....
..#..........#X..........#....
..#..........#...........#....
..#..........#...........#....
..#..........#...........#....
..#..........#....X......#....
..#..........#....#......#....
..#......X###X#####......#....
..#......#...............#....
..##X#####...............#....
.........................U....
..............................
```

## Limitations
- Rooms are represented as single cells (the BSP creates larger rooms, but we only use their centers for connectivity).
- Corridor carving uses simple L‑shaped paths; no support for winding or multi‑tile corridors.
- The connection threshold (distance ≤ 5) is hard‑coded; adjusting it requires modifying the source code.

## Dependencies
- Python 3.7+
- [NumPy](https://numpy.org/) (for grid operations)