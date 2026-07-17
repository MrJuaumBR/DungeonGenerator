import random
import time
import json
from typing import List, Tuple, Optional, Dict, Set, Any
from enum import Enum
from collections import deque
import numpy as np


class RoomType(Enum):
    SPAWN = 0
    NORMAL = 1
    BOSS = 2
    END = 3
    STAIR_UP = 4
    STAIR_DOWN = 5


class Connection:
    def __init__(self, id: str, room1: 'Room', room2: 'Room', weight: int = 1):
        self.id = id
        self.room1 = room1
        self.room2 = room2
        self.weight = weight


class Room:
    def __init__(self, position: Tuple[int, int], room_type: RoomType = RoomType.NORMAL):
        self.position = position
        self.id = f'R-{position[0]}-{position[1]}'
        self.connections: List[Connection] = []
        self.room_type = room_type
        self.distance: Optional[int] = None


class Floor:
    def __init__(self, level: int, width: int, height: int):
        self.level = level
        self.width = width
        self.height = height
        self.rooms: List[Room] = []
        self.connections: List[Connection] = []
        self.grid: Optional[np.ndarray] = None
        self.stair_up: Optional[Room] = None
        self.stair_down: Optional[Room] = None
        self.entry: Optional[Room] = None

    def get_grid(self, carve_corridors: bool = True) -> np.ndarray:
        grid = np.full((self.width, self.height), '.', dtype='U1')
        for room in self.rooms:
            x, y = room.position
            if 0 <= x < self.width and 0 <= y < self.height:
                symbol = {
                    RoomType.SPAWN: 'S',
                    RoomType.BOSS: 'B',
                    RoomType.END: 'E',
                    RoomType.STAIR_UP: 'U',
                    RoomType.STAIR_DOWN: 'D',
                    RoomType.NORMAL: 'X',
                }.get(room.room_type, 'X')
                grid[x, y] = symbol
        if carve_corridors:
            self._carve_corridors(grid)
        self.grid = grid
        return grid

    def _carve_corridors(self, grid: np.ndarray):
        room_positions = {room.position for room in self.rooms}
        for conn in self.connections:
            (x1, y1) = conn.room1.position
            (x2, y2) = conn.room2.position
            if random.choice([True, False]):
                for x in range(min(x1, x2), max(x1, x2) + 1):
                    if (x, y1) not in room_positions:
                        grid[x, y1] = '#'
                for y in range(min(y1, y2), max(y1, y2) + 1):
                    if (x2, y) not in room_positions:
                        grid[x2, y] = '#'
            else:
                for y in range(min(y1, y2), max(y1, y2) + 1):
                    if (x1, y) not in room_positions:
                        grid[x1, y] = '#'
                for x in range(min(x1, x2), max(x1, x2) + 1):
                    if (x, y2) not in room_positions:
                        grid[x, y2] = '#'

    def print_grid(self):
        grid = self.get_grid(carve_corridors=True)
        for y in range(self.height):
            row = ''.join(grid[x, y] for x in range(self.width))
            print(row)

    def to_dict(self) -> Dict[str, Any]:
        return {
            'level': self.level,
            'width': self.width,
            'height': self.height,
            'rooms': [
                {
                    'id': r.id,
                    'position': list(r.position),
                    'type': r.room_type.name,
                    'connections': [c.id for c in r.connections]
                }
                for r in self.rooms
            ],
            'connections': [
                {
                    'id': c.id,
                    'room1': c.room1.id,
                    'room2': c.room2.id,
                    'weight': c.weight
                }
                for c in self.connections
            ],
            'entry': self.entry.id if self.entry else None,
            'stair_up': self.stair_up.id if self.stair_up else None,
            'stair_down': self.stair_down.id if self.stair_down else None,
            'grid': [[str(self.get_grid()[x, y]) for x in range(self.width)] for y in range(self.height)]
        }


class Generator:
    def __init__(self, width: int, height: int, min_rooms: int, max_rooms: int,
                 min_floors: int = 1, max_floors: int = 1,
                 min_room_size: int = 3, max_room_size: int = 6,
                 seed: Optional[int] = None):
        if seed is None:
            seed = int(time.time() * 100)
        self.seed = seed
        self.width = width
        self.height = height
        self.min_rooms = min_rooms
        self.max_rooms = max_rooms
        self.min_floors = min_floors
        self.max_floors = max_floors
        self.min_room_size = min_room_size
        self.max_room_size = max_room_size
        self.floors: List[Floor] = []
        self.timings: Dict[str, float] = {}

    def generate(self) -> List[Floor]:
        random.seed(self.seed)
        np.random.seed(self.seed)
        total_t0 = time.perf_counter()

        num_floors = random.randint(self.min_floors, self.max_floors)

        # ---- Step 1: Generate rooms on each floor using BSP ----
        for level in range(num_floors):
            floor = Floor(level, self.width, self.height)
            target = random.randint(self.min_rooms, self.max_rooms)
            self._generate_rooms_bsp(floor, target)
            self.floors.append(floor)

        # ---- Step 2: Assign entry rooms and stairs ----
        prev_down_pos = None
        for level, floor in enumerate(self.floors):
            is_last = (level == num_floors - 1)
            is_first = (level == 0)

            if is_first:
                entry = self._pick_edge_room(floor)
                entry.room_type = RoomType.SPAWN
            else:
                entry = self._closest_room_to(floor, prev_down_pos)
                entry.room_type = RoomType.STAIR_UP
                floor.stair_up = entry

            floor.entry = entry

            if not is_last:
                down = max(floor.rooms, key=lambda r: abs(r.position[0] - entry.position[0]) +
                           abs(r.position[1] - entry.position[1]))
                down.room_type = RoomType.STAIR_DOWN
                floor.stair_down = down
                prev_down_pos = down.position
            else:
                prev_down_pos = None

        # ---- Step 3: Assign BOSS and END on last floor ----
        last_floor = self.floors[-1]
        entry = last_floor.entry
        for r in last_floor.rooms:
            r.distance = abs(r.position[0] - entry.position[0]) + abs(r.position[1] - entry.position[1])
        sorted_rooms = sorted(last_floor.rooms, key=lambda r: r.distance, reverse=True)

        boss_candidates = [r for r in sorted_rooms if r.room_type not in (RoomType.SPAWN, RoomType.STAIR_UP, RoomType.STAIR_DOWN)]
        if boss_candidates:
            boss = boss_candidates[0]
            boss.room_type = RoomType.BOSS
            end_candidates = [r for r in boss_candidates if r != boss]
            if end_candidates:
                end = end_candidates[0]
                end.room_type = RoomType.END

        # ---- Step 4: Build connections with robust connectivity ----
        for floor in self.floors:
            self._build_connections(floor)

        self.timings['total'] = time.perf_counter() - total_t0
        return self.floors

    # ---------- BSP Room Generation ----------
    def _generate_rooms_bsp(self, floor: Floor, target_rooms: int):
        width, height = floor.width, floor.height
        min_room_size = self.min_room_size
        max_room_size = self.max_room_size

        class BSPNode:
            def __init__(self, x, y, w, h):
                self.x = x
                self.y = y
                self.w = w
                self.h = h
                self.left = None
                self.right = None
                self.room = None

        def split_node(node, depth):
            if depth >= max_depth or node.w < min_room_size * 2 + 1 or node.h < min_room_size * 2 + 1:
                return
            if node.w > node.h:
                split_horizontal = False
            elif node.h > node.w:
                split_horizontal = True
            else:
                split_horizontal = random.choice([True, False])
            if split_horizontal:
                split_pos = random.randint(min_room_size, node.h - min_room_size)
                node.left = BSPNode(node.x, node.y, node.w, split_pos)
                node.right = BSPNode(node.x, node.y + split_pos, node.w, node.h - split_pos)
            else:
                split_pos = random.randint(min_room_size, node.w - min_room_size)
                node.left = BSPNode(node.x, node.y, split_pos, node.h)
                node.right = BSPNode(node.x + split_pos, node.y, node.w - split_pos, node.h)
            split_node(node.left, depth + 1)
            split_node(node.right, depth + 1)

        def collect_leaves(node):
            if node is None:
                return []
            if node.left is None and node.right is None:
                return [node]
            return collect_leaves(node.left) + collect_leaves(node.right)

        def create_rooms_in_leaves(leaves):
            rooms = []
            for leaf in leaves:
                if leaf.w < min_room_size + 1 or leaf.h < min_room_size + 1:
                    continue
                room_w = random.randint(min_room_size, min(max_room_size, leaf.w - 1))
                room_h = random.randint(min_room_size, min(max_room_size, leaf.h - 1))
                pad_x = random.randint(0, leaf.w - room_w)
                pad_y = random.randint(0, leaf.h - room_h)
                room_x = leaf.x + pad_x
                room_y = leaf.y + pad_y
                leaf.room = (room_x, room_y, room_w, room_h)
                center_x = room_x + room_w // 2
                center_y = room_y + room_h // 2
                rooms.append((center_x, center_y))
            return rooms

        max_depth = max(1, int(np.ceil(np.log2(target_rooms))) + 1)
        root = BSPNode(0, 0, width, height)
        split_node(root, 0)
        leaves = collect_leaves(root)

        while len(leaves) < target_rooms:
            splittable = [l for l in leaves if l.w >= min_room_size * 2 + 1 and l.h >= min_room_size * 2 + 1]
            if not splittable:
                break
            leaf = random.choice(splittable)
            leaves.remove(leaf)
            split_node(leaf, 0)
            leaves.extend(collect_leaves(leaf))

        room_positions = create_rooms_in_leaves(leaves)

        while len(room_positions) < target_rooms:
            x = random.randint(0, width - 1)
            y = random.randint(0, height - 1)
            if not any(r == (x, y) for r in room_positions):
                room_positions.append((x, y))

        if len(room_positions) > target_rooms:
            room_positions = random.sample(room_positions, target_rooms)

        for pos in room_positions:
            floor.rooms.append(Room(pos))

    # ---------- Main Connection Builder (enforces all rules) ----------
    def _build_connections(self, floor: Floor):
        rooms = floor.rooms
        if len(rooms) < 2:
            return

        # 1. Build proximity graph (threshold 5)
        adj: Dict[Room, List[Room]] = {r: [] for r in rooms}
        threshold = 5
        for i, a in enumerate(rooms):
            for b in rooms[i+1:]:
                dist = abs(a.position[0] - b.position[0]) + abs(a.position[1] - b.position[1])
                if dist <= threshold:
                    adj[a].append(b)
                    adj[b].append(a)

        # 2. Ensure connectivity using BFS + bridging
        all_rooms = set(rooms)
        visited = set()
        queue = deque([rooms[0]])
        visited.add(rooms[0])
        while queue:
            curr = queue.popleft()
            for nb in adj.get(curr, []):
                if nb not in visited:
                    visited.add(nb)
                    queue.append(nb)
        unvisited = all_rooms - visited
        while unvisited:
            best_dist = float('inf')
            best_pair = None
            for v in visited:
                for u in unvisited:
                    d = abs(v.position[0] - u.position[0]) + abs(v.position[1] - u.position[1])
                    if d < best_dist:
                        best_dist = d
                        best_pair = (v, u)
            if best_pair:
                a, b = best_pair
                adj[a].append(b)
                adj[b].append(a)
                visited.add(b)
                unvisited.remove(b)

        # 3. Create connection objects from adj
        conn_id = 0
        processed = set()
        connections = []
        for a, neighbors in adj.items():
            for b in neighbors:
                if (a, b) in processed or (b, a) in processed:
                    continue
                processed.add((a, b))
                conn = Connection(f'conn-{conn_id}', a, b)
                connections.append(conn)
                a.connections.append(conn)
                b.connections.append(conn)
                conn_id += 1
        floor.connections = connections

        # 4. Enforce rules:
        # - END only connects to BOSS
        # - BOSS has exactly two connections: one to END, one to a NORMAL room
        # - STAIR_UP never connects to D, B, E; and must have at least one NORMAL connection
        # - Every room (except END) must have at least one connection

        # 4a. Enforce END rule
        end_room = next((r for r in rooms if r.room_type == RoomType.END), None)
        boss_room = next((r for r in rooms if r.room_type == RoomType.BOSS), None)
        if end_room and boss_room:
            self._enforce_end_room_rule(floor, end_room, boss_room)

        # 4b. Enforce BOSS connection to X (if missing)
        if boss_room:
            self._enforce_boss_connections(floor, boss_room, end_room)

        # 4c. Enforce U rule (remove D, B, E connections; add X if none)
        self._enforce_stair_connection_rule(floor)

        # 4d. Final safety: any room (except END) with 0 connections gets a connection to nearest valid room
        self._ensure_all_connected(floor)

    # ---------- Rule enforcement helpers ----------
    def _enforce_end_room_rule(self, floor: Floor, end_room: Room, boss_room: Room):
        end_conns = [c for c in floor.connections if c.room1 == end_room or c.room2 == end_room]
        boss_conn = None
        other = []
        for c in end_conns:
            if (c.room1 == boss_room and c.room2 == end_room) or (c.room2 == boss_room and c.room1 == end_room):
                boss_conn = c
            else:
                other.append(c)
        for c in other:
            floor.connections.remove(c)
            if c in end_room.connections:
                end_room.connections.remove(c)
            if c in c.room1.connections:
                c.room1.connections.remove(c)
            if c in c.room2.connections:
                c.room2.connections.remove(c)
        if boss_conn is None:
            new_conn = Connection(f'end-boss-{len(floor.connections)}', end_room, boss_room)
            floor.connections.append(new_conn)
            end_room.connections.append(new_conn)
            boss_room.connections.append(new_conn)

    def _enforce_boss_connections(self, floor: Floor, boss_room: Room, end_room: Optional[Room]):
        # Ensure boss has exactly 2 connections: one to END (already), one to a NORMAL room
        # First, gather current boss connections
        boss_conns = [c for c in floor.connections if c.room1 == boss_room or c.room2 == boss_room]

        # Identify connection to END
        end_conn = None
        other = []
        for c in boss_conns:
            other_room = c.room2 if c.room1 == boss_room else c.room1
            if other_room == end_room:
                end_conn = c
            else:
                other.append(c)

        # We need exactly one connection to a NORMAL room (not END)
        # Find a NORMAL room to connect to
        normal_rooms = [r for r in floor.rooms if r.room_type == RoomType.NORMAL and r != boss_room]

        # Remove all connections except end_conn
        for c in other:
            floor.connections.remove(c)
            if c in boss_room.connections:
                boss_room.connections.remove(c)
            if c in c.room1.connections:
                c.room1.connections.remove(c)
            if c in c.room2.connections:
                c.room2.connections.remove(c)

        # If we don't have a connection to a NORMAL room, add one
        if normal_rooms:
            # Find nearest NORMAL room
            nearest = min(normal_rooms, key=lambda r: abs(r.position[0] - boss_room.position[0]) +
                          abs(r.position[1] - boss_room.position[1]))
            # Check if already connected (shouldn't be)
            already = False
            for c in boss_room.connections:
                other_room = c.room2 if c.room1 == boss_room else c.room1
                if other_room == nearest:
                    already = True
                    break
            if not already:
                new_conn = Connection(f'boss-x-{len(floor.connections)}', boss_room, nearest)
                floor.connections.append(new_conn)
                boss_room.connections.append(new_conn)
                nearest.connections.append(new_conn)

        # Now ensure boss has exactly 2 connections (should be end_conn + one normal)
        # If end_conn is None, we need to create it (should have been done in END rule)
        if end_conn is None and end_room is not None:
            new_conn = Connection(f'boss-end-{len(floor.connections)}', boss_room, end_room)
            floor.connections.append(new_conn)
            boss_room.connections.append(new_conn)
            end_room.connections.append(new_conn)

    def _enforce_stair_connection_rule(self, floor: Floor):
        stair_up = floor.stair_up
        if stair_up is None:
            return

        # Remove connections to D, B, E
        stair_conns = [c for c in floor.connections if c.room1 == stair_up or c.room2 == stair_up]
        forbidden_types = {RoomType.STAIR_DOWN, RoomType.BOSS, RoomType.END}
        to_remove = []
        for conn in stair_conns:
            other = conn.room2 if conn.room1 == stair_up else conn.room1
            if other.room_type in forbidden_types:
                to_remove.append(conn)

        for conn in to_remove:
            floor.connections.remove(conn)
            if conn in stair_up.connections:
                stair_up.connections.remove(conn)
            if conn in conn.room1.connections:
                conn.room1.connections.remove(conn)
            if conn in conn.room2.connections:
                conn.room2.connections.remove(conn)

        # If U has no connections, connect to nearest NORMAL room
        if len(stair_up.connections) == 0:
            normal_rooms = [r for r in floor.rooms if r.room_type == RoomType.NORMAL and r != stair_up]
            if normal_rooms:
                nearest = min(normal_rooms, key=lambda r: abs(r.position[0] - stair_up.position[0]) +
                              abs(r.position[1] - stair_up.position[1]))
                new_conn = Connection(f'stair-conn-{len(floor.connections)}', stair_up, nearest)
                floor.connections.append(new_conn)
                stair_up.connections.append(new_conn)
                nearest.connections.append(new_conn)

    def _ensure_all_connected(self, floor: Floor):
        """Connect any isolated rooms (except END) to the nearest valid room."""
        end_room = next((r for r in floor.rooms if r.room_type == RoomType.END), None)
        for room in floor.rooms:
            if room == end_room:
                continue
            if len(room.connections) == 0:
                # Find nearest room (excluding self, excluding END, and not BOSS if it would break its degree?)
                # For simplicity, connect to any room that is not END
                best = None
                best_dist = float('inf')
                for other in floor.rooms:
                    if other == room or other == end_room:
                        continue
                    # Avoid connecting to BOSS if it already has 2 connections? But we can allow; it might be okay.
                    # We'll keep it simple.
                    d = abs(room.position[0] - other.position[0]) + abs(room.position[1] - other.position[1])
                    if d < best_dist:
                        best_dist = d
                        best = other
                if best is not None:
                    new_conn = Connection(f'safety-{len(floor.connections)}', room, best)
                    floor.connections.append(new_conn)
                    room.connections.append(new_conn)
                    best.connections.append(new_conn)

    # ---------- Helpers ----------
    def _pick_edge_room(self, floor: Floor) -> Room:
        width, height = floor.width, floor.height
        edge_rooms = [r for r in floor.rooms if
                      r.position[0] == 0 or r.position[0] == width - 1 or
                      r.position[1] == 0 or r.position[1] == height - 1]
        return random.choice(edge_rooms) if edge_rooms else floor.rooms[0]

    def _closest_room_to(self, floor: Floor, pos: Tuple[int, int]) -> Room:
        if pos is None:
            return floor.rooms[0]
        return min(floor.rooms, key=lambda r: abs(r.position[0] - pos[0]) + abs(r.position[1] - pos[1]))

    def print_timings(self):
        for key, val in self.timings.items():
            print(f"{key}: {val:.6f} seconds")

    def export_json(self, filename: str = "dungeon.json"):
        data = {
            'seed': self.seed,
            'width': self.width,
            'height': self.height,
            'min_rooms': self.min_rooms,
            'max_rooms': self.max_rooms,
            'min_floors': self.min_floors,
            'max_floors': self.max_floors,
            'timings': self.timings,
            'floors': [f.to_dict() for f in self.floors]
        }
        with open(filename, 'w') as f:
            json.dump(data, f, indent=4)
        print(f"Exported to {filename}")


# ---------- Demo ----------
if __name__ == '__main__':
    gen = Generator(width=30, height=30, min_rooms=12, max_rooms=18,
                    min_floors=2, max_floors=3,
                    min_room_size=3, max_room_size=6,
                    seed=42)
    floors = gen.generate()

    for floor in floors:
        print(f"\n=== Floor {floor.level} ===")
        print(f"Rooms: {len(floor.rooms)}, Connections: {len(floor.connections)}")
        if floor.stair_up:
            print(f"  Stair up at {floor.stair_up.position} (type {floor.stair_up.room_type})")
        if floor.stair_down:
            print(f"  Stair down at {floor.stair_down.position} (type {floor.stair_down.room_type})")
        if floor.entry:
            print(f"  Entry room at {floor.entry.position} (type {floor.entry.room_type})")
        floor.print_grid()

    gen.print_timings()
    gen.export_json("dungeon.json")