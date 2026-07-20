from lunaengine.core import LunaEngine, Scene
from lunaengine.backend import OpenGLRenderer
from lunaengine.ui import *

from typing import Any, Dict, Union, Optional
from argparse import ArgumentParser
import sys
import os
import json
from pathlib import Path
from datetime import datetime
import pygame as pg
import time

from generator import Generator as DungeonGenerator
from generator import ClampSeed

argparser = ArgumentParser()
argparser.add_argument('--debug', action='store_true', default=False, help='Enable debug mode')
argparser.add_argument('--fullscreen', action='store_true', default=False, help='Enable fullscreen mode')

class DungeonSaver:
    def __init__(self, engine: LunaEngine):
        self.engine = engine
        self.filename = self.engine.atlas.get_item('root').path / 'saves.json'
        if not self.filename.exists():
            with open(self.filename, 'w+') as f:
                f.write('{}')
        self.engine.atlas.add_datastore('saves', self.filename)
        self.data: Dict[str, Dict[str, Any]] = {}
        self.current_dungeon: Union[Dict[str, Any], None] = None
        self.load_data()

    def load_data(self):
        with open(self.filename, 'r') as f:
            self.data = json.load(f)

    def save_dungeon(self, dungeon_name: str, dungeon_seed: int):
        data: Dict = self.data
        if f'dungeon_{str(dungeon_name)}' in data.keys():
            data[f'dungeon_{str(dungeon_name)}']['seed'] = dungeon_seed
        else:
            data[f'dungeon_{str(dungeon_name)}'] = {
                'name': dungeon_name,
                'seed': int(dungeon_seed),
                'date': str(datetime.now().strftime('%Y-%m-%d %H:%M:%S'))
            }
        with open(self.filename, 'w') as f:
            json.dump(data, f, indent=4)

    def get_dungeons(self) -> Dict[str, Dict[str, Any]]:
        return self.data

    def get_dungeon(self, dungeon_name: str) -> Union[Dict[str, Any], None]:
        return self.data.get(f'dungeon_{str(dungeon_name)}', None)

    def get_dungeon_by_seed(self, dungeon_seed: int) -> Union[Dict[str, Any], None]:
        for k, v in self.data.items():
            if int(v['seed']) == dungeon_seed:
                return v
        return None


class Menu(Scene):
    def __init__(self, engine: LunaEngine):
        super().__init__(engine)
        self.engine.add_function_to_live_inspector(
            'Create Random Dungeon',
            lambda dungeon_name, seed: DSR.save_dungeon(str(dungeon_name), dungeon_seed=seed),
            [('dungeon_name', str), ('seed', str)],
            'Creates a random dungeon save'
        )
        self.setup_ui()

    def setup_ui(self):
        self.add_ui_element(TextLabel(
            self.engine.width // 2,
            self.engine.ratio.y * 100,
            'Dungeon Generator',
            64 * self.engine.ratio.med,
            font_name='medievalsharp',
            pivot=(0.5, 0)
        ))

        enter_generator_button = Button(
            self.engine.ratio.x * 50,
            self.engine.ratio.y * 200,
            self.engine.ratio.x * 225,
            self.engine.ratio.y * 50,
            'Enter Generator',
            font_size=28 * self.engine.ratio.med,
            font_name='medievalsharp'
        )
        enter_generator_button.set_on_click(self.enter_dungeon)
        self.add_ui_element(enter_generator_button)

        self.scrolling_frame = ScrollingFrame(
            self.engine.ratio.x * 50,
            self.engine.ratio.y * 275,
            self.engine.ratio.x * 275,
            self.engine.ratio.y * 300,
            self.engine.ratio.x * 265,
            self.engine.ratio.y * 700
        )
        self.add_ui_element(self.scrolling_frame)
        self.load_saved_dungeons()

    def on_enter(self, previous_scene: str | None = None) -> None:
        self.load_saved_dungeons()
        DSR.current_dungeon = None

    def load_saved_dungeons(self):
        self.scrolling_frame.clear_children()
        self.scrolling_frame.scroll_y = 0
        dungeons = DSR.get_dungeons()
        if len(dungeons.keys()) == 0:
            self.scrolling_frame.add_child(TextLabel(
                0, 0,
                'No saved dungeons',
                28 * self.engine.ratio.med,
                font_name='medievalsharp',
                pivot=(0, 0)
            ))
        else:
            for i, (k, v) in enumerate(dungeons.items()):
                fr = UiFrame(
                    5 * self.engine.ratio.x,
                    (10 + i * 100) * self.engine.ratio.y,
                    self.engine.ratio.x * 250,
                    self.engine.ratio.y * 100
                )
                fr.add_child(TextLabel(
                    5 * self.engine.ratio.x,
                    5 * self.engine.ratio.y,
                    v['name'],
                    22 * self.engine.ratio.med,
                    font_name='medievalsharp',
                    pivot=(0, 0)
                ))
                fr.add_child(TextLabel(
                    10 * self.engine.ratio.x,
                    30 * self.engine.ratio.y,
                    v['date'],
                    18 * self.engine.ratio.med,
                    font_name='medievalsharp',
                    pivot=(0, 0)
                ))
                fr.add_child(TextLabel(
                    10 * self.engine.ratio.x,
                    50 * self.engine.ratio.y,
                    str(v['seed']),
                    18 * self.engine.ratio.med,
                    font_name='medievalsharp',
                    pivot=(0, 0)
                ))
                fr.add_child(TextLabel(
                    10 * self.engine.ratio.x,
                    70 * self.engine.ratio.y,
                    f'(Id: {k[8:24]})',
                    14 * self.engine.ratio.med,
                    font_name='medievalsharp',
                    pivot=(0, 0)
                ))

                select_button = Button(
                    240 * self.engine.ratio.x,
                    95 * self.engine.ratio.y,
                    50 * self.engine.ratio.x,
                    20 * self.engine.ratio.y,
                    'Select',
                    font_size=16 * self.engine.ratio.med,
                    font_name='medievalsharp',
                    pivot=(1, 1)
                )
                select_button.custom_id = int(v['seed'])
                select_button.set_on_click(lambda id: self.enter_dungeon(seed=int(id)), id=select_button.custom_id)
                fr.add_child(select_button)
                self.scrolling_frame.add_child(fr)

    def enter_dungeon(self, seed: Optional[int] = None):
        if seed:
            DSR.current_dungeon = DSR.get_dungeon_by_seed(seed)
        else:
            DSR.current_dungeon = None
        self.engine.set_scene('generator')

    def render(self, renderer: OpenGLRenderer):
        renderer.fill_screen(ThemeManager.get_color('background'))


class Generator(Scene):
    def __init__(self, engine: LunaEngine):
        super().__init__(engine)
        self.generated_floors = None
        self.current_floor_index = 0
        self.current_seed = None
        self.is_generating = False
        self.generator = None
        self.view_offset_x = 0
        self.view_offset_y = 0
        self.zoom = 1.0
        self.setup_ui()

        @engine.on_event(pg.KEYUP)
        def on_key(event):
            if event.key in (pg.K_ESCAPE, pg.K_TAB):
                self.control_panel.visible = not self.control_panel.visible
                self.subtitle_label.visible = not self.control_panel.visible

        @engine.on_event(pg.MOUSEWHEEL)
        def on_wheel(event):
            if event.y > 0:
                self.zoom = min(2.0, self.zoom + 0.1)
            elif event.y < 0:
                self.zoom = max(0.2, self.zoom - 0.1)

    def setup_ui(self):
        panel_width = 300 * self.engine.ratio.x
        panel_x = 10 * self.engine.ratio.x
        panel_y = self.engine.height // 2
        panel_height = self.engine.height - 20 * self.engine.ratio.y

        self.control_panel = UiFrame(panel_x, panel_y, panel_width, panel_height, pivot=(0, 0.5))
        self.control_panel.bg_color = (30, 30, 50, 200)
        self.add_ui_element(self.control_panel)

        inner = UiFrame(0, 0, panel_width, panel_height)
        self.control_panel.add_child(inner)

        y = 6

        inner.add_child(TextLabel(
            panel_width // 2,
            y * self.engine.ratio.y,
            'Generator',
            32 * self.engine.ratio.med,
            font_name='medievalsharp',
            pivot=(0.5, 0)
        ))
        y += 80

        inner.add_child(TextLabel(
            panel_width // 2,
            y * self.engine.ratio.y,
            'Seed:',
            18 * self.engine.ratio.med,
            font_name='medievalsharp',
            pivot=(0.5, 0)
        ))
        self.seed_box = TextBox(
            panel_width // 2 - 90 * self.engine.ratio.x,
            (y + 20) * self.engine.ratio.y,
            180 * self.engine.ratio.x,
            28 * self.engine.ratio.y,
            font_size=16 * self.engine.ratio.med,
            font_name='medievalsharp'
        )
        self.seed_box.set_text(str(ClampSeed(int(time.time() * 100))))
        inner.add_child(self.seed_box)
        y += 55

        inner.add_child(TextLabel(
            panel_width // 2,
            y * self.engine.ratio.y,
            'Rooms (min-max):',
            18 * self.engine.ratio.med,
            font_name='medievalsharp',
            pivot=(0.5, 0)
        ))
        self.room_box = TextBox(
            panel_width // 2 - 90 * self.engine.ratio.x,
            (y + 20) * self.engine.ratio.y,
            180 * self.engine.ratio.x,
            28 * self.engine.ratio.y,
            font_size=16 * self.engine.ratio.med,
            font_name='medievalsharp'
        )
        self.room_box.set_text('12-18')
        inner.add_child(self.room_box)
        y += 55

        inner.add_child(TextLabel(
            panel_width // 2,
            y * self.engine.ratio.y,
            'Floors (min-max):',
            18 * self.engine.ratio.med,
            font_name='medievalsharp',
            pivot=(0.5, 0)
        ))
        self.floor_box = TextBox(
            panel_width // 2 - 90 * self.engine.ratio.x,
            (y + 20) * self.engine.ratio.y,
            180 * self.engine.ratio.x,
            28 * self.engine.ratio.y,
            font_size=16 * self.engine.ratio.med,
            font_name='medievalsharp'
        )
        self.floor_box.set_text('1-3')
        inner.add_child(self.floor_box)
        y += 55

        self.generate_btn = Button(
            panel_width // 2 - 90 * self.engine.ratio.x,
            y * self.engine.ratio.y,
            180 * self.engine.ratio.x,
            36 * self.engine.ratio.y,
            'Generate Dungeon',
            font_size=20 * self.engine.ratio.med,
            font_name='medievalsharp'
        )
        self.generate_btn.set_on_click(self.generate_dungeon)
        inner.add_child(self.generate_btn)
        y += 45

        self.status_label = TextLabel(
            panel_width // 2,
            y * self.engine.ratio.y,
            'Ready',
            14 * self.engine.ratio.med,
            font_name='medievalsharp',
            color=(200, 200, 200),
            pivot=(0.5, 0)
        )
        inner.add_child(self.status_label)
        y += 30

        self.save_btn = Button(
            panel_width // 2 - 90 * self.engine.ratio.x,
            y * self.engine.ratio.y,
            180 * self.engine.ratio.x,
            30 * self.engine.ratio.y,
            'Save Dungeon',
            font_size=16 * self.engine.ratio.med,
            font_name='medievalsharp'
        )
        self.save_btn.set_on_click(self.save_current_dungeon)
        self.save_btn.enabled = False
        inner.add_child(self.save_btn)
        y += 38

        self.export_btn = Button(
            panel_width // 2 - 90 * self.engine.ratio.x,
            y * self.engine.ratio.y,
            180 * self.engine.ratio.x,
            30 * self.engine.ratio.y,
            'Export JSON',
            font_size=16 * self.engine.ratio.med,
            font_name='medievalsharp'
        )
        self.export_btn.set_on_click(self.export_json)
        self.export_btn.enabled = False
        inner.add_child(self.export_btn)
        y += 38

        self.print_btn = Button(
            panel_width // 2 - 90 * self.engine.ratio.x,
            y * self.engine.ratio.y,
            180 * self.engine.ratio.x,
            30 * self.engine.ratio.y,
            'Print Dungeon',
            font_size=16 * self.engine.ratio.med,
            font_name='medievalsharp'
        )
        self.print_btn.set_on_click(self.print_dungeon)
        self.print_btn.enabled = False
        inner.add_child(self.print_btn)
        y += 38

        self.floor_label = TextLabel(
            panel_width // 2,
            y * self.engine.ratio.y,
            'Floor 0 / 0',
            18 * self.engine.ratio.med,
            font_name='medievalsharp',
            pivot=(0.5, 0)
        )
        inner.add_child(self.floor_label)
        y += 25

        self.prev_btn = Button(
            panel_width // 2 - 80 * self.engine.ratio.x,
            y * self.engine.ratio.y,
            55 * self.engine.ratio.x,
            28 * self.engine.ratio.y,
            '<',
            font_size=18 * self.engine.ratio.med,
            font_name='medievalsharp'
        )
        self.prev_btn.set_on_click(self.prev_floor)
        self.prev_btn.enabled = False
        inner.add_child(self.prev_btn)

        self.next_btn = Button(
            panel_width // 2 + 25 * self.engine.ratio.x,
            y * self.engine.ratio.y,
            55 * self.engine.ratio.x,
            28 * self.engine.ratio.y,
            '>',
            font_size=18 * self.engine.ratio.med,
            font_name='medievalsharp'
        )
        self.next_btn.set_on_click(self.next_floor)
        self.next_btn.enabled = False
        inner.add_child(self.next_btn)
        y += 38

        back_btn = Button(
            panel_width // 2 - 90 * self.engine.ratio.x,
            y * self.engine.ratio.y,
            180 * self.engine.ratio.x,
            30 * self.engine.ratio.y,
            'Back to Menu',
            font_size=16 * self.engine.ratio.med,
            font_name='medievalsharp'
        )
        back_btn.set_on_click(lambda: self.engine.set_scene('menu'))
        inner.add_child(back_btn)

        subtitle_text = (
            "<b>Controls:</b> WASD/Arrows pan\n<b>+/-</b> or scroll zoom \n<b>ESC/TAB</b> toggle panel\n"
        )
        self.subtitle_label = LongTextLabel(
            10 * self.engine.ratio.x,
            self.engine.height - 60 * self.engine.ratio.y,
            subtitle_text,
            width=self.engine.width - 20 * self.engine.ratio.x,
            height=50 * self.engine.ratio.y,
            font_size=14 * self.engine.ratio.med,
            font_name='medievalsharp',
            rich_text=True,
            wrap_width=self.engine.width - 20 * self.engine.ratio.x,
            color=(180, 180, 200),
            pivot=(0, 1)
        )
        self.subtitle_label.visible = False
        self.add_ui_element(self.subtitle_label)

    def generate_dungeon(self):
        if self.is_generating:
            return
        self.is_generating = True
        self.generate_btn.enabled = False
        self.status_label.set_text('Generating...')
        try:
            seed_text = self.seed_box.get_text()
            seed = int(seed_text) if seed_text else ClampSeed(int(time.time() * 100))
            room_range = self.room_box.get_text().split('-')
            min_rooms = int(room_range[0]) if len(room_range) > 0 else 12
            max_rooms = int(room_range[1]) if len(room_range) > 1 else 18
            floor_range = self.floor_box.get_text().split('-')
            min_floors = int(floor_range[0]) if len(floor_range) > 0 else 1
            max_floors = int(floor_range[1]) if len(floor_range) > 1 else 3
            self.generator = DungeonGenerator(
                width=30, height=30,
                min_rooms=min_rooms,
                max_rooms=max_rooms,
                min_floors=min_floors,
                max_floors=max_floors,
                min_room_size=3,
                max_room_size=6,
                seed=seed
            )
            self.generated_floors = self.generator.generate()
            self.current_floor_index = 0
            self.current_seed = str(self.generator.seed)
            self.status_label.set_text(f'Generated {len(self.generated_floors)} floors (Seed: {seed})')
            self.save_btn.enabled = True
            self.export_btn.enabled = True
            self.print_btn.enabled = True
            self.update_navigation()
            self.center_on_room()
        except Exception as e:
            self.status_label.set_text(f'Error: {str(e)}')
        self.is_generating = False
        self.generate_btn.enabled = True

    def center_on_room(self):
        if not self.generated_floors:
            return
        floor = self.generated_floors[self.current_floor_index]
        if self.current_floor_index == 0:
            target = floor.entry
        else:
            target = floor.stair_up
        if target is None:
            target = floor.rooms[0] if floor.rooms else None
        if target is None:
            return
        px, py = target.position
        screen_w = self.engine.width
        screen_h = self.engine.height
        cell_size = min(screen_w / floor.width, screen_h / floor.height) * self.zoom
        total_w = floor.width * cell_size
        total_h = floor.height * cell_size
        desired_x = (screen_w - total_w) / 2 + (px + 0.5) * cell_size - screen_w / 2
        desired_y = (screen_h - total_h) / 2 + (py + 0.5) * cell_size - screen_h / 2
        self.view_offset_x = -desired_x
        self.view_offset_y = -desired_y

    def update_navigation(self):
        if self.generated_floors:
            total = len(self.generated_floors)
            self.floor_label.set_text(f'Floor {self.current_floor_index + 1} / {total}')
            self.prev_btn.enabled = self.current_floor_index > 0
            self.next_btn.enabled = self.current_floor_index < total - 1
        else:
            self.floor_label.set_text('Floor 0 / 0')
            self.prev_btn.enabled = False
            self.next_btn.enabled = False

    def prev_floor(self):
        if self.current_floor_index > 0:
            self.current_floor_index -= 1
            self.update_navigation()
            self.center_on_room()

    def next_floor(self):
        if self.generated_floors and self.current_floor_index < len(self.generated_floors) - 1:
            self.current_floor_index += 1
            self.update_navigation()
            self.center_on_room()

    def save_current_dungeon(self):
        if not self.generated_floors:
            return
        name = f"{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        DSR.save_dungeon(name, self.current_seed)
        self.status_label.set_text(f'Saved as "{name}"')

    def export_json(self):
        if self.generator is None:
            self.status_label.set_text('No dungeon to export')
            return
        try:
            filename = f"dungeon_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
            self.generator.export_json(filename)
            self.status_label.set_text(f'Exported to {filename}')
        except Exception as e:
            self.status_label.set_text(f'Export error: {str(e)}')

    def print_dungeon(self):
        if not self.generated_floors:
            self.status_label.set_text('No dungeon to print')
            return
        try:
            floor = self.generated_floors[self.current_floor_index]
            print(f"=== Floor {floor.level} ===")
            floor.print_grid()
            self.status_label.set_text(f'Printed floor {self.current_floor_index + 1} to console')
        except Exception as e:
            self.status_label.set_text(f'Print error: {str(e)}')

    def on_enter(self, previous_scene: str | None = None) -> None:
        if DSR.current_dungeon:
            seed = DSR.current_dungeon.get('seed')
            print(seed)
            if seed:
                self.seed_box.set_text(str(ClampSeed(seed)))
        else:
            seed = ClampSeed(int(time.time() * 100))
            self.seed_box.set_text(str(seed))
        self.generate_dungeon()

    def update(self, dt):
        keys = self.engine.input_state.get_keys()
        if keys[pg.K_LEFT] or keys[pg.K_a]:
            self.view_offset_x += 5
        if keys[pg.K_RIGHT] or keys[pg.K_d]:
            self.view_offset_x -= 5
        if keys[pg.K_UP] or keys[pg.K_w]:
            self.view_offset_y += 5
        if keys[pg.K_DOWN] or keys[pg.K_s]:
            self.view_offset_y -= 5
        if keys[pg.K_EQUALS] or keys[pg.K_PLUS]:
            self.zoom = min(2.0, self.zoom + 0.02)
        if keys[pg.K_MINUS]:
            self.zoom = max(0.2, self.zoom - 0.02)

    def render(self, renderer: OpenGLRenderer):
        renderer.fill_screen(ThemeManager.get_color('background'))
        if not self.generated_floors:
            return
        floor = self.generated_floors[self.current_floor_index]
        grid = floor.get_grid(carve_corridors=True)
        screen_w = self.engine.width
        screen_h = self.engine.height
        cell_size = min(screen_w / grid.shape[0], screen_h / grid.shape[1]) * self.zoom
        total_w = grid.shape[0] * cell_size
        total_h = grid.shape[1] * cell_size
        offset_x = (screen_w - total_w) / 2 + self.view_offset_x
        offset_y = (screen_h - total_h) / 2 + self.view_offset_y
        colors = {
            '.': (40, 40, 60, 255),
            '#': (80, 80, 120, 255),
            'S': (0, 200, 100, 255),
            'X': (150, 150, 200, 255),
            'B': (200, 50, 50, 255),
            'E': (200, 200, 50, 255),
            'U': (50, 150, 200, 255),
            'D': (200, 100, 50, 255),
        }
        for y in range(grid.shape[1]):
            for x in range(grid.shape[0]):
                ch = grid[x, y]
                color = colors.get(ch, (40, 40, 60, 255))
                rect_x = offset_x + x * cell_size
                rect_y = offset_y + y * cell_size
                if (rect_x + cell_size > 0 and rect_x < screen_w and
                        rect_y + cell_size > 0 and rect_y < screen_h):
                    renderer.draw_rect(
                        rect_x, rect_y, cell_size, cell_size,
                        color=color,
                        border_color=(100, 100, 150) if ch != '.' else None,
                        border_width=1
                    )


def main():
    global DSR
    args = argparser.parse_args(sys.argv[1:])
    engine = LunaEngine('Dungeon Generator', width=800, height=600, debug=args.debug, fullscreen=args.fullscreen)
    engine.atlas.add_folder('root', os.path.abspath(os.path.dirname(__file__)))
    engine.atlas.add_font('medievalsharp', engine.atlas.get_item('root').path / 'MedievalSharp.ttf')
    engine.atlas.add_texture('icon', engine.atlas.get_item('root').path / 'icon.png')
    engine.updateRatio(800, 600)
    engine.set_global_theme(ThemeType.MIDNIGHT)
    DSR = DungeonSaver(engine)
    engine.set_icon(str(engine.atlas.get_item('icon').path))
    engine.add_scene('menu', Menu)
    engine.add_scene('generator', Generator)
    engine.set_scene('menu')
    engine.run()


if __name__ == '__main__':
    main()