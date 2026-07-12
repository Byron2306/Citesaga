import pygame 
import sys
import os
import random
import asyncio

# The existing interface was laid out on a 2560x1440 design canvas.
# Keep that coordinate system so every existing position, font, card, popup,
# and hitbox stays proportional, then scale the completed frame into a
# 1920x1080 window. This also makes resizing automatic and aspect-safe.
DESIGN_WIDTH = 2560
DESIGN_HEIGHT = 1440
WINDOW_WIDTH = 1920
WINDOW_HEIGHT = 1080

# Existing game code uses SCREEN_WIDTH / SCREEN_HEIGHT for layout. These now
# refer to the logical design canvas rather than the physical display window.
SCREEN_WIDTH = DESIGN_WIDTH
SCREEN_HEIGHT = DESIGN_HEIGHT
FPS = 60

GOLD = (231, 231, 231)
BLACK = (0, 0, 0)
WHITE = (255, 255, 255)
GREY = (50, 50, 50)

TEXT_BOX_BG = (79, 53, 47, 204)
BROWN = (139, 69, 19)
TEXT_COLOR = BROWN

TOKEN_TYPES = ['green', 'red', 'blue', 'yellow', 'purple', 'corruption', 'key']
TOKEN_COLORS = {
    'green': (0, 255, 0),
    'red': (255, 0, 0),
    'blue': (0, 0, 255),
    'yellow': (255, 255, 0),
    'purple': (128, 0, 128),
    'corruption': (128, 0, 0),
    'key': (255, 215, 0)
}

TOKEN_LEVELS = {
    'green': 1,
    'red': 1,
    'blue': 2,
    'yellow': 2,
    'purple': 3
}

MAIN_MENU = 'main_menu'
FADE_IN_ENVIRONMENT_CARDS = 'fade_in_environment_cards'
PLAYER_TURN_FLIP_CITATION_CARDS = 'player_turn_flipping_citation_cards'
PLAYER_TURN_ACTIVE = 'player_turn_active'
PAY_CITATION_CARD = 'pay_citation_card'
BUSTLING_STALLS_CHOICE = 'bustling_stalls_choice'
WIN_CONDITION = 'win_condition'
END_GAME = 'end_game'
PLAYER_TURN_CONCLUSION = 'player_turn_conclusion'
COMPLETE_REFERENCE = 'complete_reference'

CITATION_TOKENS_COLUMN_WIDTH = 350
CITATION_CARDS_COLUMN_WIDTH = 350

class Player:
    def __init__(self, name, image_path):
        self.name = name
        self.image = self.load_image(image_path)
        self.rect = self.image.get_rect()
        self.current_environment_card = None
        self.citation_cards = []
        self.tokens = {token: 0 for token in TOKEN_TYPES}
        self.crystals = 0
        self.last_sound_played = None
        self.phase = "movement"
        self.remaining_moves = 1
        self.cheat_input_buffer = ""
        self.seal_type = None
        self.multiply_turns_remaining = 0

    def load_image(self, name, scale=None):
        path = os.path.join('assets', 'images', name)
        if not os.path.isfile(path):
            placeholder = pygame.Surface((100, 100))
            placeholder.fill(GREY)
            return placeholder
        image = pygame.image.load(path).convert_alpha()
        if scale:
            image = pygame.transform.scale(image, scale)
        return image

class CitationCard:
    def __init__(self, name, image_path, cost, reward=1):
        self.name = name
        self.front_image = self.load_image(image_path)
        self.back_image = self.load_image('citation_card_back.png')
        self.flipped = False
        self.cost = cost
        self.reward = reward
        self.current_alpha = 0
        self.gatekept = False

    def load_image(self, name, scale=None):
        path = os.path.join('assets', 'images', name)
        if not os.path.isfile(path):
            placeholder = pygame.Surface((300, 500))
            placeholder.fill(GREY)
            return placeholder
        image = pygame.image.load(path).convert_alpha()
        
        if scale:
            # Assets are sized in logical design pixels. The complete logical
            # frame is scaled once during presentation, keeping cards, text,
            # effects, and mouse hitboxes perfectly aligned.
            image = pygame.transform.smoothscale(image, scale)
        return image


class EnvironmentCard:
    def __init__(self, name, image_path, token_type, display_name, description, scale=None, hover_sound=None):
        self.name = name
        self.image = self.load_image(image_path, scale)
        self.rect = self.image.get_rect()
        self.occupied_by = None
        self.token = token_type
        self.display_name = display_name
        self.description = description
        self.hover_sound = hover_sound

    def load_image(self, name, scale=None):
        path = os.path.join('assets', 'images', name)
        if not os.path.isfile(path):
            placeholder = pygame.Surface((300, 500))
            placeholder.fill(GREY)
            return placeholder
        image = pygame.image.load(path).convert_alpha()
        if scale:
            image = pygame.transform.scale(image, scale)
        return image

class Game:
    def __init__(self):
        pygame.init()

        global WINDOW_WIDTH, WINDOW_HEIGHT
        if sys.platform == "emscripten":
            import platform
            WINDOW_WIDTH = platform.window.innerWidth
            WINDOW_HEIGHT = platform.window.innerHeight

        # Physical display surface: starts at exactly 1920x1080, but remains
        # resizable. The game itself renders to the larger logical canvas below.
        self.window = pygame.display.set_mode(
            (WINDOW_WIDTH, WINDOW_HEIGHT),
            pygame.RESIZABLE
        )
        pygame.display.set_caption("Citesaga")

        # Logical rendering surface. All existing drawing code continues to use
        # self.screen, so every asset and coordinate is scaled as one scene.
        self.screen = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT)).convert()
        self.render_scale = 1.0
        self.viewport_rect = pygame.Rect(0, 0, WINDOW_WIDTH, WINDOW_HEIGHT)
        self.update_viewport()

        self.clock = pygame.time.Clock()
        self.load_assets()
        self.players = self.create_players()
        self.environment_card_tokens = {
            'boundless_sands.png': 'green',
            'celestial_lakes.png': 'green',
            'inkflow_skyline.png': 'red',
            'the_evergrove.png': 'green',
            'untouched_territories.png': 'red',
            'restless_canopies.png': 'red',
            'bustling_stalls.png': None,
            'serene_environs.png': None,
            'fusty_swamps.png': 'green',
            'the_plainlands.png': 'red',
            'painted_fields.png': 'green',
            'inkwash_backwaters.png': 'red',
            'wooded_pathways.png': 'green',
            'stolen_mires.png': 'red',
            'spiralling_corridors.png': 'green',
            'fireproof_crags.png': 'red',
            'frigid_mountains.png': 'green',
            'palatial_halls.png': 'red'
        }
        self.environment_card_display_names = {
            'boundless_sands.png': "Boundless Sands",
            'celestial_lakes.png': "Celestial Lakes",
            'inkflow_skyline.png': "Inkflow Skyline",
            'the_evergrove.png': "The Evergrove",
            'untouched_territories.png': "Untouched Territories",
            'restless_canopies.png': "Restless Canopies",
            'bustling_stalls.png': "Bustling Stalls",
            'serene_environs.png': "Serene Environs",
            'fusty_swamps.png': "Fusty Swamps",
            'the_plainlands.png': "The Plainlands",
            'painted_fields.png': "Painted Fields",
            'inkwash_backwaters.png': "Inkwash Backwaters",
            'wooded_pathways.png': "Wooded Pathways",
            'stolen_mires.png': "Stolen Mires",
            'spiralling_corridors.png': "Spiralling Corridors",
            'fireproof_crags.png': "Fireproof Crags",
            'frigid_mountains.png': "Frigid Mountains",
            'palatial_halls.png': "Palatial Halls"
        }
        self.environment_card_effect_descriptions = {
            'boundless_sands.png': "Draw two citation tokens from any level you do not have a citation token from.",
            'celestial_lakes.png': "Gain one corruption token",
            'inkflow_skyline.png': "Convert any 2 level 1 tokens of the same color to another level 1 color. Gain one key.",
            'the_evergrove.png': "Draw two level 2 citation tokens.",
            'untouched_territories.png': "Draw one level 2 token.",
            'restless_canopies.png': "Swap one citation card.",
            'bustling_stalls.png': "Choose an action upon landing.",
            'serene_environs.png': "Choose to pay for a citation card or skip your turn.",
            'fusty_swamps.png': "Draw one level 1 citation token.",
            'the_plainlands.png': "Swap one citation card.",
            'painted_fields.png': "Draw one level 2 citation token.",
            'inkwash_backwaters.png': "Swap two citation cards.",
            'wooded_pathways.png': "Draw one level 1 & one level 2 citation token.",
            'stolen_mires.png': "Convert a level 2 citation token into a level 3 citation token.",
            'spiralling_corridors.png': "Swap two citation cards.",
            'fireproof_crags.png': "Convert a level 1 citation token into a level 2 citation token.",
            'frigid_mountains.png': "Pay 2 level 1 citation tokens to upgrade to 1 level 2 token.",
            'palatial_halls.png': "Draw two level 2 citation tokens."
        }
        self.all_environment_card_names = list(self.environment_card_tokens.keys())
        self.environment_cards = self.create_environment_cards()
        self.position_environment_cards()
        self.environment_alphas = [0 for _ in self.environment_cards]
        self.faded_in_cards = []
        self.game_state = MAIN_MENU
        self.env_fade_speed = 5
        self.citation_flip_index = 0
        self.citation_flip_delay = 500
        self.last_flip_time = 0
        self.flipping_citation = False
        self.popup_message = None
        self.popup_start_time = None
        self.popup_display_duration = 2000
        self.popup_fade_duration = 1000
        self.choice = False
        self.win = False
        self.flip_sound = self.load_sound('flip.wav')
        self.move_sound = self.load_sound('move.mp3')
        self.magic_sound = self.load_sound('magic.mp3')
        self.load_music('Neon_Realms.mp3')
        self.current_player = 0
        self.flip_alpha = 0
        self.flip_duration = 1000
        self.flip_start_time = None
        self.current_flip_card_index = 0
        self.flip_in_progress = False
        self.zoomed_card = None
        self.citation_card_y_offsets = [40, 120, 205]
        self.show_turn_image = True
        self.turn_image_display_start = 0
        pygame.mixer.set_num_channels(20)
        self.hover_sound_channel = pygame.mixer.Channel(10)
        self.current_hovered_card = None
        self.execute_card_effect_done = False
        self.conclusion_phase_start_time = None
        self.selected_citation_card = None
        self.reference_input = ''

        base_x, base_y = CITATION_TOKENS_COLUMN_WIDTH + 20, 20
        self.seal_images = {
            'teleport': self.load_image('seal_teleport.png', scale=(200, 200)),
            'multiply': self.load_image('seal_multiply.png', scale=(200, 200)),
            'plagiarise': self.load_image('seal_plagiarise.png', scale=(200, 200)),
            'gatekeep': self.load_image('seal_gatekeep.png', scale=(200, 200)),
            'terraform': self.load_image('seal_terraform.png', scale=(200, 200)),
            'convert': self.load_image('seal_convert.png', scale=(200, 200))
        }
        self.seal_rect = pygame.Rect((base_x, base_y), (100, 100))
        self.lock_image = self.load_image('lock.png', scale=(30, 30))

    def update_viewport(self):
        """Recalculate the aspect-preserving destination rectangle."""
        current_window = pygame.display.get_surface()
        if current_window is not None:
            self.window = current_window

        window_width, window_height = self.window.get_size()
        window_width = max(1, window_width)
        window_height = max(1, window_height)

        self.render_scale = min(
            window_width / SCREEN_WIDTH,
            window_height / SCREEN_HEIGHT
        )

        scaled_width = max(1, round(SCREEN_WIDTH * self.render_scale))
        scaled_height = max(1, round(SCREEN_HEIGHT * self.render_scale))
        offset_x = (window_width - scaled_width) // 2
        offset_y = (window_height - scaled_height) // 2

        self.viewport_rect = pygame.Rect(
            offset_x, offset_y, scaled_width, scaled_height
        )

    def get_mouse_pos(self):
        """Map physical-window mouse coordinates into logical game space."""
        self.update_viewport()
        mouse_x, mouse_y = pygame.mouse.get_pos()

        if not self.viewport_rect.collidepoint(mouse_x, mouse_y):
            # Keep letterbox/pillarbox clicks from activating edge controls.
            return (-10000, -10000)

        logical_x = int(
            (mouse_x - self.viewport_rect.x) / self.render_scale
        )
        logical_y = int(
            (mouse_y - self.viewport_rect.y) / self.render_scale
        )

        return (
            max(0, min(SCREEN_WIDTH - 1, logical_x)),
            max(0, min(SCREEN_HEIGHT - 1, logical_y))
        )

    def present_frame(self):
        """Scale the completed logical frame into the current window."""
        self.update_viewport()
        self.window.fill(BLACK)

        if self.viewport_rect.size == self.screen.get_size():
            scaled_frame = self.screen
        else:
            scaled_frame = pygame.transform.smoothscale(
                self.screen, self.viewport_rect.size
            )

        self.window.blit(scaled_frame, self.viewport_rect.topleft)
        pygame.display.flip()

    def load_image(self, name, scale=None):
        path = os.path.join('assets', 'images', name)
        if not os.path.isfile(path):
            placeholder = pygame.Surface((100, 100))
            placeholder.fill(GREY)
            return placeholder
        image = pygame.image.load(path).convert_alpha()
        if scale:
            image = pygame.transform.scale(image, scale)
        return image

    def load_font(self, name, size):
        path = os.path.join('assets', 'fonts', name)
        if not os.path.isfile(path):
            pygame.quit()
            sys.exit()
        font = pygame.font.Font(path, size)
        return font

    def load_sound(self, name):
        path = os.path.join('assets', 'sounds', name)
        if not os.path.isfile(path):
            silent_sound = pygame.mixer.Sound(buffer=b'\x00' * 44100)
            return silent_sound
        sound = pygame.mixer.Sound(path)
        return sound

    def load_music(self, name):
        path = os.path.join('assets', 'music', name)
        if not os.path.isfile(path):
            return
        pygame.mixer.music.load(path)
        pygame.mixer.music.set_volume(0.3)
        pygame.mixer.music.play(-1)

    def load_assets(self):
        self.title_font = self.load_font('Pirata_One.ttf', 80)
        self.button_font = self.load_font('Pirata_One.ttf', 40)
        self.turn_font = self.load_font('Pirata_One.ttf', 60)
        self.token_font = self.load_font('Grand_Baron.otf', 25)
        self.popup_font = self.load_font('Pirata_One.ttf', 25)
        self.choice_font = self.load_font('Pirata_One.ttf', 30)
        self.column_header_font = self.load_font('Pirata_One.ttf', 40)
        self.background_main = self.load_image('Citesaga.png', scale=(SCREEN_WIDTH, SCREEN_HEIGHT))
        self.background_game = self.load_image('background.png', scale=(SCREEN_WIDTH, SCREEN_HEIGHT))
        self.fade_overlay = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.SRCALPHA)
        self.fade_overlay.set_alpha(150)
        self.fade_overlay.fill(BLACK)
        self.citation_card_back = self.load_image('citation_card_back.png')
        self.crystal_image = self.load_image('crystal.png', scale=(30, 30))
        self.TOKEN_IMAGES = {}
        for token in TOKEN_TYPES:
            image_name = f"{token}.png"
            self.TOKEN_IMAGES[token] = self.load_image(image_name, scale=(30, 30))
        self.character_sounds = {
            'Duskwrit': [
                ('Duskwrit_1.wav', self.load_sound('Duskwrit_1.wav')),
                ('Duskwrit_2.wav', self.load_sound('Duskwrit_2.wav')),
                ('Duskwrit_3.wav', self.load_sound('Duskwrit_3.wav'))
            ],
            'Thistlepage': [
                ('Thistlepage_1.wav', self.load_sound('Thistlepage_1.wav')),
                ('Thistlepage_2.wav', self.load_sound('Thistlepage_2.wav')),
                ('Thistlepage_3.wav', self.load_sound('Thistlepage_3.wav'))
            ],
            'Referella': [
                ('Referella_1.wav', self.load_sound('Referella_1.wav')),
                ('Referella_2.wav', self.load_sound('Referella_2.wav')),
                ('Referella_3.wav', self.load_sound('Referella_3.wav'))
            ],
            'Pendragraph': [
                ('Pendragraph_1.wav', self.load_sound('Pendragraph_1.wav')),
                ('Pendragraph_2.wav', self.load_sound('Pendragraph_2.wav')),
                ('Pendragraph_3.wav', self.load_sound('Pendragraph_3.wav'))
            ],
            'Cite-a-lot': [
                ('citealot_1.wav', self.load_sound('citealot_1.wav')),
                ('citealot_2.wav', self.load_sound('citealot_2.wav')),
                ('citealot_3.wav', self.load_sound('citealot_3.wav'))
            ],
            'Echo Quill': [
                ('echoquill_1.wav', self.load_sound('echoquill_1.wav')),
                ('echoquill_2.wav', self.load_sound('echoquill_2.wav')),
                ('echoquill_3.wav', self.load_sound('echoquill_3.wav'))
            ],
            'Cinder Scroll': [
                ('cinderscroll_1.wav', self.load_sound('cinderscroll_1.wav')),
                ('cinderscroll_2.wav', self.load_sound('cinderscroll_2.wav')),
                ('cinderscroll_3.wav', self.load_sound('cinderscroll_3.wav'))
            ],
            'Tomebough': [
                ('tomebough_1.wav', self.load_sound('tomebough_1.wav')),
                ('tomebough_2.wav', self.load_sound('tomebough_2.wav')),
                ('tomebough_3.wav', self.load_sound('tomebough_3.wav'))
            ]
        }
        self.citesaga_button = self.load_image('citesaga_button.png')
        self.citesaga_glow = self.load_image('citesaga_glow.png')
        self.citation_token_counter = self.load_image('citation_token_counter.png', scale=(CITATION_TOKENS_COLUMN_WIDTH, SCREEN_HEIGHT))
        self.citation_card_counter = self.load_image('citation_card_counter.png', scale=(CITATION_CARDS_COLUMN_WIDTH, SCREEN_HEIGHT))
        self.phase_image = self.load_image('phase.png', scale=(400, 150))
        self.referella_phase_image = self.load_image('referella_phase.png', scale=(100, 100))
        self.duskwrit_phase_image = self.load_image('duskwrit_phase.png', scale=(100, 100))
        self.pendragraph_phase_image = self.load_image('pendragraph_phase.png', scale=(100, 100))
        self.thistlepage_phase_image = self.load_image('thistlepage_phase.png', scale=(100, 100))
        self.citealot_phase_image = self.load_image('citealot_phase.png', scale=(100, 100))
        self.echoquill_phase_image = self.load_image('echoquill_phase.png', scale=(100, 100))
        self.cinderscroll_phase_image = self.load_image('cinderscroll_phase.png', scale=(100, 100))
        self.tomebough_phase_image = self.load_image('tomebough_phase.png', scale=(100, 100))
        self.small_button = self.load_image('citesaga_button.png', scale=(50, 50))

    def create_players(self):
        all_characters = [
            ('Referella', 'Referella.png'),
            ('Pendragraph', 'Pendragraph.png'),
            ('Duskwrit', 'Duskwrit.png'),
            ('Thistlepage', 'Thistlepage.png'),
            ('Cite-a-lot', 'Citealot.png'),
            ('Echo Quill', 'EchoQuill.png'),
            ('Cinder Scroll', 'CinderScroll.png'),
            ('Tomebough', 'Tomebough.png')
        ]
        selected_characters = random.sample(all_characters, 4)
        players = [Player(name, image_file) for name, image_file in selected_characters]
        all_seals = ['teleport', 'multiply', 'plagiarise', 'gatekeep', 'terraform', 'convert']
        for player in players:
            player.seal_type = random.choice(all_seals)
        return players

    def create_environment_cards(self):
        mandatory_cards = [
            'celestial_lakes.png',
            'serene_environs.png',
            'bustling_stalls.png',
            'inkflow_skyline.png'
        ]

        optional_cards = [
            'boundless_sands.png',
            'the_evergrove.png',
            'untouched_territories.png',
            'restless_canopies.png',
            'fusty_swamps.png',
            'the_plainlands.png',
            'painted_fields.png',
            'inkwash_backwaters.png',
            'wooded_pathways.png',
            'stolen_mires.png',
            'spiralling_corridors.png',
            'fireproof_crags.png',
            'frigid_mountains.png',
            'palatial_halls.png'
        ]

        selected_mandatory = mandatory_cards.copy()
        selected_optional = random.sample(optional_cards, 4)
        selected_cards = selected_mandatory + selected_optional

        environment_cards = []
        for name in selected_cards:
            token_type = self.environment_card_tokens.get(name, None)
            display_name = self.environment_card_display_names.get(name, name.replace('_', ' ').replace('.png', '').title())
            description = self.environment_card_effect_descriptions.get(name, "No effect defined.")
            sound_name = name.replace('.png', '.mp3')
            hover_sound = self.load_sound(sound_name)
            card = EnvironmentCard(
                name,
                name,
                token_type,
                display_name,
                description,
                scale=(300, 500),
                hover_sound=hover_sound
            )
            environment_cards.append(card)
        return environment_cards

    def create_environment_card_positions(self):
        top_row_count = 4
        bottom_row_count = 4
        SPACING = 100
        total_width_top = sum(card.rect.width for card in self.environment_cards[:top_row_count]) + SPACING * (top_row_count - 1)
        start_x_top = (SCREEN_WIDTH - total_width_top) // 2
        top_y = SCREEN_HEIGHT // 2 - self.environment_cards[0].rect.height - 80 + 100
        bottom_y = SCREEN_HEIGHT // 2 + 100

        current_x = start_x_top
        for i in range(top_row_count):
            if i >= len(self.environment_cards):
                break
            self.environment_cards[i].rect.topleft = (current_x, top_y)
            current_x += self.environment_cards[i].rect.width + SPACING

        current_x = start_x_top
        for i in range(top_row_count, top_row_count + bottom_row_count):
            if i >= len(self.environment_cards):
                break
            self.environment_cards[i].rect.topleft = (current_x, bottom_y)
            current_x += self.environment_cards[i].rect.width + SPACING

    def position_environment_cards(self):
        self.create_environment_card_positions()

    def assign_citation_cards(self):
        citation_card_names = [
            'alchemists_almanac.png',
            'astral_symposia.png',
            'citehold_conundrum.png',
            'lunar_howls.png',
            'mandates_of_the_hive.png',
            'pixie_parlance.png',
            'sand_and_summit.png',
            'territorial_tenets.png',
            'council_of_the_realms.png',
            'manual_of_ambition.png',
            'the_inkblade_murders.png',
            'the_elders_codex.png',
            'scrolltube.png',
            'arcane_linguistics.png',
            'celestial_footnotes.png',
            'chronicles_of_citealot.png',
            'citehold_chronicles.png',
            'whispers_of_the_shadeleaf.png'
        ]
        for player in self.players:
            player.citation_cards = []
            selected = random.sample(citation_card_names, 3)
            for card_name in selected:
                cost = self.create_citation_card_costs(card_name)
                reward = self.get_citation_card_reward(card_name)
                card = CitationCard(card_name, card_name, cost, reward)
                player.citation_cards.append(card)
        for player in self.players:
            for card in player.citation_cards:
                card.flipped = False
        self.game_state = FADE_IN_ENVIRONMENT_CARDS
        if self.current_hovered_card:
            self.hover_sound_channel.stop()
            self.current_hovered_card = None

    def create_citation_card_costs(self, card_name):
        costs = {
            'alchemists_almanac.png': {'red': 2, 'green': 1, 'yellow': 1},
            'astral_symposia.png': {'red': 2, 'green': 1, 'yellow': 1},
            'citehold_conundrum.png': {'red': 1, 'green': 1, 'yellow': 1},
            'lunar_howls.png': {'red': 2, 'green': 1, 'yellow': 1},
            'mandates_of_the_hive.png': {'red': 1, 'green': 1, 'yellow': 2},
            'pixie_parlance.png': {'red': 1, 'green': 1, 'yellow': 1},
            'sand_and_summit.png': {'red': 1, 'green': 1, 'yellow': 1},
            'territorial_tenets.png': {'red': 1, 'green': 1, 'yellow': 1},
            'council_of_the_realms.png': {'green': 1, 'yellow': 1, 'blue': 1, 'key': 2, 'any': 2},
            'manual_of_ambition.png': {'red': 3, 'green': 1, 'yellow': 1, 'blue': 1, 'corruption': 1},
            'the_inkblade_murders.png': {'red': 3, 'green': 1, 'yellow': 1, 'blue': 1, 'corruption': 1},
            'the_elders_codex.png': {'green': 1, 'yellow': 1, 'blue': 1, 'key': 3, 'any': 1},
            'scrolltube.png': {'red': 3, 'yellow': 1, 'blue': 1, 'any': 1},
            'arcane_linguistics.png': {'red': 2, 'green': 1, 'yellow': 1, 'blue': 1},
            'celestial_footnotes.png': {'red': 3, 'green': 1, 'yellow': 1, 'blue': 1},
            'chronicles_of_citealot.png': {'red': 3, 'green': 1, 'yellow': 1, 'blue': 1, 'any': 1},
            'citehold_chronicles.png': {'green': 1, 'yellow': 1, 'blue': 1, 'key': 2, 'any': 1},
            'whispers_of_the_shadeleaf.png': {'red': 2, 'green': 1, 'yellow': 1, 'blue': 2, 'corruption': 1}
        }
        return costs.get(card_name, {})

    def get_citation_card_reward(self, card_name):
        rewards = {
            'alchemists_almanac.png': 1,
            'astral_symposia.png': 1,
            'citehold_conundrum.png': 1,
            'lunar_howls.png': 1,
            'mandates_of_the_hive.png': 1,
            'pixie_parlance.png': 1,
            'sand_and_summit.png': 1,
            'territorial_tenets.png': 1,
            'council_of_the_realms.png': 3,
            'manual_of_ambition.png': 3,
            'the_inkblade_murders.png': 3,
            'the_elders_codex.png': 3,
            'scrolltube.png': 2,
            'arcane_linguistics.png': 1,
            'celestial_footnotes.png': 2,
            'chronicles_of_citealot.png': 3,
            'citehold_chronicles.png': 2,
            'whispers_of_the_shadeleaf.png': 3
        }
        return rewards.get(card_name, 1)

    async def run(self):
        while True:
            for event in pygame.event.get(pygame.VIDEORESIZE):
                self.window = pygame.display.set_mode((event.w, event.h), pygame.RESIZABLE)
                self.update_viewport()

            if self.game_state == MAIN_MENU:
                self.main_menu()
            elif self.game_state == FADE_IN_ENVIRONMENT_CARDS:
                self.fade_in_environment_cards()
            elif self.game_state == PLAYER_TURN_FLIP_CITATION_CARDS:
                self.player_turn_flipping_citation_cards()
            elif self.game_state == PLAYER_TURN_ACTIVE:
                self.player_turn_active()
            elif self.game_state == PAY_CITATION_CARD:
                self.pay_citation_card()
            elif self.game_state == BUSTLING_STALLS_CHOICE:
                self.bustling_stalls_choice()
            elif self.game_state == WIN_CONDITION:
                self.win_condition_screen()
            elif self.game_state == END_GAME:
                self.end_game()
            elif self.game_state == PLAYER_TURN_CONCLUSION:
                self.player_turn_conclusion()
            elif self.game_state == COMPLETE_REFERENCE:
                self.complete_reference()
            self.present_frame()
            self.clock.tick(FPS)
            await asyncio.sleep(0)

    def main_menu(self):
        mouse_pos = self.get_mouse_pos()
        mouse_clicked = False
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit()
                sys.exit()
            elif event.type == pygame.MOUSEBUTTONDOWN:
                mouse_clicked = True
        self.screen.blit(self.background_main, (0, 0))
        try:
            logo_image = self.load_image('citesage_logo.png', scale=(600, 200))
            logo_rect = logo_image.get_rect(center=(SCREEN_WIDTH // 2, 200))
            self.screen.blit(logo_image, logo_rect.topleft)
        except:
            self.draw_text("Citesaga", self.title_font, TEXT_COLOR, SCREEN_WIDTH // 2, 200)

        start_button_rect = pygame.Rect(
            (SCREEN_WIDTH // 2 - 200, SCREEN_HEIGHT // 2 - 60 + 100),
            (400, 120)
        )
        exit_button_rect = pygame.Rect(
            (SCREEN_WIDTH // 2 - 200, SCREEN_HEIGHT // 2 - 60 + 250),
            (400, 120)
        )
        start_hover = start_button_rect.collidepoint(mouse_pos)
        exit_hover = exit_button_rect.collidepoint(mouse_pos)

        start_button_image = pygame.transform.scale(self.citesaga_button, (400, 120))
        self.screen.blit(start_button_image, start_button_rect.topleft)
        self.draw_text("Start", self.button_font, TEXT_COLOR, start_button_rect.centerx, start_button_rect.centery)

        exit_button_image = pygame.transform.scale(self.citesaga_button, (400, 120))
        self.screen.blit(exit_button_image, exit_button_rect.topleft)
        self.draw_text("Exit", self.button_font, TEXT_COLOR, exit_button_rect.centerx, exit_button_rect.centery)

        if mouse_clicked:
            if start_hover:
                self.assign_citation_cards()
            elif exit_hover:
                pygame.quit()
                sys.exit()

    def fade_in_environment_cards(self):
        mouse_pos = self.get_mouse_pos()
        mouse_clicked = False
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit()
                sys.exit()
            elif event.type == pygame.MOUSEBUTTONDOWN:
                mouse_clicked = True
        self.screen.blit(self.background_game, (0, 0))
        all_faded_in = True
        for idx, card in enumerate(self.environment_cards):
            if self.environment_alphas[idx] < 255:
                all_faded_in = False
                self.environment_alphas[idx] += self.env_fade_speed
                if self.environment_alphas[idx] > 255:
                    self.environment_alphas[idx] = 255
                    if card not in self.faded_in_cards:
                        self.faded_in_cards.append(card)
            card_image = card.image.copy()
            card_image.set_alpha(self.environment_alphas[idx])
            self.draw_card_with_shadow(card_image, card.rect)
            self.draw_card_token_indicator(card)
        for card in self.environment_cards:
            if card.occupied_by is not None:
                self.draw_player_on_card(card.occupied_by, card)
        if all_faded_in:
            self.game_state = PLAYER_TURN_FLIP_CITATION_CARDS
            self.citation_flip_index = 0
            self.flipping_citation = False
            self.flip_alpha = 0
            self.flip_start_time = pygame.time.get_ticks()
            self.current_flip_card_index = 0
            self.flip_in_progress = False
            current_player = self.players[self.current_player]
            for card in current_player.citation_cards:
                card.flipped = False
            self.show_turn_image = True
            self.turn_image_display_start = pygame.time.get_ticks()
            self.flip_sound.play()
        self.handle_environment_card_hover(mouse_pos)

    def player_turn_flipping_citation_cards(self):
        player = self.players[self.current_player]
        current_time = pygame.time.get_ticks()
        mouse_pos = self.get_mouse_pos()
        mouse_clicked = False
        right_clicked = False
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit()
                sys.exit()
            elif event.type == pygame.MOUSEBUTTONDOWN:
                if event.button == 1:
                    mouse_clicked = True
                elif event.button == 3:
                    right_clicked = True
            elif event.type == pygame.KEYDOWN and player.phase == "movement":
                if event.key == pygame.K_BACKSPACE:
                    player.cheat_input_buffer = player.cheat_input_buffer[:-1]
                elif event.key == pygame.K_RETURN:
                    pass
                else:
                    player.cheat_input_buffer += event.unicode.lower()
                cheat_code = "integrity"
                if len(player.cheat_input_buffer) > len(cheat_code):
                    player.cheat_input_buffer = player.cheat_input_buffer[-len(cheat_code):]
                if player.cheat_input_buffer == cheat_code:
                    for token in TOKEN_TYPES:
                        player.tokens[token] += 1
                    player.crystals += 1
                    self.magic_sound.play()
                    self.show_popup_message(f"Cheat Activated! {player.name} gains one of every token, crystal, corruption, and key.", choice=False)
                    player.cheat_input_buffer = ""

        if self.show_turn_image:
            if self.turn_image_display_start == 0:
                self.turn_image_display_start = current_time
            elapsed_since_start = current_time - self.turn_image_display_start
            if elapsed_since_start < 2000:
                self.screen.blit(self.background_game, (0, 0))
                self.screen.blit(self.fade_overlay, (0, 0))
                self.draw_citation_tokens()
                self.draw_citation_cards_column()
                for card in self.environment_cards:
                    card_image = card.image.copy()
                    card_image.set_alpha(255)
                    self.draw_card_with_shadow(card_image, card.rect)
                    self.draw_card_token_indicator(card)
                for card in self.environment_cards:
                    if card.occupied_by is not None:
                        self.draw_player_on_card(card.occupied_by, card)
                button_image = pygame.transform.scale(self.citesaga_button, (600, 200))
                button_rect = button_image.get_rect(center=(SCREEN_WIDTH // 2, SCREEN_HEIGHT // 2))
                self.screen.blit(button_image, button_rect.topleft)
                turn_text = f"{player.name}'s Turn"
                text_surface = self.turn_font.render(turn_text, True, TEXT_COLOR)
                text_rect = text_surface.get_rect(center=button_rect.center)
                self.screen.blit(text_surface, text_rect)
                return
            else:
                self.show_turn_image = False

        if self.current_flip_card_index < len(player.citation_cards) and not self.flip_in_progress:
            self.flip_start_time = current_time
            self.flip_in_progress = True
            self.flip_sound.play()
        if self.current_flip_card_index >= len(player.citation_cards):
            self.game_state = PLAYER_TURN_ACTIVE
            return
        current_card = player.citation_cards[self.current_flip_card_index]
        elapsed_time = current_time - self.flip_start_time
        if elapsed_time < self.flip_duration:
            flip_progress = elapsed_time / self.flip_duration
            current_alpha = int(flip_progress * 255)
            if current_alpha > 255:
                current_alpha = 255
        else:
            current_card.flipped = True
            self.current_flip_card_index += 1
            self.flip_in_progress = False
            return
        self.screen.blit(self.background_game, (0, 0))
        self.screen.blit(self.fade_overlay, (0, 0))
        self.draw_citation_tokens()
        self.draw_citation_cards_column()
        for card in self.environment_cards:
            card_image = card.image.copy()
            card_image.set_alpha(255)
            self.draw_card_with_shadow(card_image, card.rect)
            self.draw_card_token_indicator(card)
        for card in self.environment_cards:
            if card.occupied_by is not None:
                self.draw_player_on_card(card.occupied_by, card)
        self.draw_phase(player)
        self.flip_alpha = current_alpha
        column_x = SCREEN_WIDTH - CITATION_CARDS_COLUMN_WIDTH
        start_y = 150
        for i, citation_card in enumerate(player.citation_cards):
            card_width = 180
            card_height = 270
            if i >= len(self.citation_card_y_offsets):
                offset = 0
            else:
                offset = self.citation_card_y_offsets[i]
            card_x = column_x + (CITATION_CARDS_COLUMN_WIDTH - card_width) // 2
            card_y = start_y + i * (card_height + 40) + offset
            if citation_card.flipped:
                card_image = pygame.transform.scale(citation_card.front_image, (card_width, card_height))
                self.screen.blit(card_image, (card_x, card_y))
            elif i == self.current_flip_card_index and self.flip_in_progress:
                back_image = pygame.transform.scale(citation_card.back_image, (card_width, card_height))
                front_image = pygame.transform.scale(citation_card.front_image, (card_width, card_height))
                front_image.set_alpha(current_alpha)
                self.screen.blit(back_image, (card_x, card_y))
                self.screen.blit(front_image, (card_x, card_y))
            else:
                back_image = pygame.transform.scale(citation_card.back_image, (card_width, card_height))
                self.screen.blit(back_image, (card_x, card_y))
        for i, citation_card in enumerate(player.citation_cards):
            card_width = 180
            card_height = 270
            if i >= len(self.citation_card_y_offsets):
                offset = 0
            else:
                offset = self.citation_card_y_offsets[i]
            card_x = column_x + (CITATION_CARDS_COLUMN_WIDTH - card_width) // 2
            card_y = start_y + i * (card_height + 40) + offset
            card_rect = pygame.Rect(card_x, card_y, card_width, card_height)
            if card_rect.collidepoint(self.get_mouse_pos()) and not self.zoomed_card:
                glow_image = pygame.transform.scale(self.citesaga_glow, (card_width, card_height))
                self.screen.blit(glow_image, (card_x, card_y))
        if right_clicked:
            if self.zoomed_card:
                self.zoomed_card = None
            else:
                for i, citation_card in enumerate(player.citation_cards):
                    card_width = 180
                    card_height = 270
                    if i >= len(self.citation_card_y_offsets):
                        offset = 0
                    else:
                        offset = self.citation_card_y_offsets[i]
                    card_x = SCREEN_WIDTH - CITATION_CARDS_COLUMN_WIDTH + (CITATION_CARDS_COLUMN_WIDTH - card_width) // 2
                    card_y = 150 + i * (card_height + 40) + offset
                    card_rect = pygame.Rect(card_x, card_y, card_width, card_height)
                    if card_rect.collidepoint(mouse_pos):
                        self.zoomed_card = citation_card
                        break
        if self.zoomed_card:
            zoom_image = pygame.transform.scale(
                self.zoomed_card.front_image if self.zoomed_card.flipped else self.zoomed_card.back_image,
                (600, 900)
            )
            zoom_rect = zoom_image.get_rect(center=(SCREEN_WIDTH // 2, SCREEN_HEIGHT // 2))
            self.screen.blit(zoom_image, zoom_rect.topleft)
        self.handle_environment_card_hover(mouse_pos)

    def player_turn_active(self):
        player = self.players[self.current_player]
        mouse_pos = self.get_mouse_pos()
        mouse_clicked = False
        right_clicked = False
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit()
                sys.exit()
            elif event.type == pygame.MOUSEBUTTONDOWN:
                if event.button == 1:
                    mouse_clicked = True
                elif event.button == 3:
                    right_clicked = True
            elif event.type == pygame.KEYDOWN and player.phase == "movement":
                if event.key == pygame.K_BACKSPACE:
                    player.cheat_input_buffer = player.cheat_input_buffer[:-1]
                elif event.key == pygame.K_RETURN:
                    pass
                else:
                    player.cheat_input_buffer += event.unicode.lower()
                cheat_code = "integrity"
                if len(player.cheat_input_buffer) > len(cheat_code):
                    player.cheat_input_buffer = player.cheat_input_buffer[-len(cheat_code):]
                if player.cheat_input_buffer == cheat_code:
                    for token in TOKEN_TYPES:
                        player.tokens[token] += 1
                    player.crystals += 1
                    self.magic_sound.play()
                    self.show_popup_message(f"Cheat Activated! {player.name} gains one of every token, crystal, corruption, and key.", choice=False)
                    player.cheat_input_buffer = ""

        self.screen.blit(self.background_game, (0, 0))
        self.screen.blit(self.fade_overlay, (0, 0))
        self.draw_citation_tokens()
        self.draw_citation_cards_column()
        for card in self.environment_cards:
            card_image = card.image.copy()
            card_image.set_alpha(255)
            self.draw_card_with_shadow(card_image, card.rect)
            self.draw_card_token_indicator(card)
        for card in self.environment_cards:
            if card.occupied_by is not None:
                self.draw_player_on_card(card.occupied_by, card)
        self.draw_phase(player)
        self.handle_environment_card_hover(mouse_pos)
        possible_moves = [card for card in self.environment_cards if card.occupied_by is None]
        self.highlight_environment_cards(possible_moves)
        if self.popup_message and not self.choice:
            self.draw_popup_message()
        seal_type = player.seal_type
        seal_image = self.seal_images[seal_type]
        self.screen.blit(seal_image, self.seal_rect.topleft)
        if mouse_clicked and self.seal_rect.collidepoint(mouse_pos):
            if seal_type == 'teleport':
                if player.crystals >= 1:
                    player.crystals -= 1
                    self.magic_sound.play()
                    activation_message = f"{player.name} has activated the Teleport Seal!\nInstantly move to another environment card not occupied by another player."
                    self.show_popup_message(activation_message, choice=False)
                    player.remaining_moves = 2
            elif seal_type == 'multiply':
                if player.crystals >= 1:
                    player.crystals -= 1
                    self.magic_sound.play()
                    activation_message = f"{player.name} has activated the Multiply Seal!\nAll citation tokens collected will be doubled for the next 2 turns."
                    self.show_popup_message(activation_message, choice=False)
                    player.multiply_turns_remaining = 2
            elif seal_type == 'plagiarise':
                if player.crystals >= 2:
                    player.crystals -= 2
                    self.magic_sound.play()
                    target_player = self.select_random_other_player(player)
                    if target_player:
                        stolen_tokens = {token: amount for token, amount in target_player.tokens.items() if amount > 0}
                        if stolen_tokens:
                            for token, amount in stolen_tokens.items():
                                player.tokens[token] += amount
                                target_player.tokens[token] = 0
                            stolen_details = ", ".join([f"{amount} {token.capitalize()}" for token, amount in stolen_tokens.items()])
                            activation_message = f"{player.name} has activated the Plagiarise Seal!\nStole all tokens from {target_player.name}:\n{stolen_details}."
                        else:
                            activation_message = f"{player.name} has activated the Plagiarise Seal!\nBut {target_player.name} has no tokens to steal."
                    else:
                        activation_message = "No other players to steal from."
                    self.show_popup_message(activation_message, choice=False)
            elif seal_type == 'gatekeep':
                if player.crystals >= 1:
                    player.crystals -= 1
                    self.magic_sound.play()
                    activation_message = f"{player.name} has activated the Gatekeep Seal!"
                    self.show_popup_message(activation_message, choice=False)
                    self.activate_gatekeep(player)
                else:
                    self.show_popup_message("Cannot activate the Gatekeep seal now.", choice=False)
            elif seal_type == 'terraform':
                if player.crystals >= 1:
                    player.crystals -= 1
                    self.magic_sound.play()
                    activation_message = f"{player.name} has activated the Terraform Seal!"
                    self.show_popup_message(activation_message, choice=False)
                    self.activate_terraform(player)
                else:
                    self.show_popup_message("Cannot activate the Terraform seal now.", choice=False)
            elif seal_type == 'convert':
                total_citation_tokens = sum(player.tokens[token] for token in TOKEN_TYPES if token not in ['key', 'corruption'])
                if total_citation_tokens >= 5:
                    tokens_needed = 5
                    for token in TOKEN_TYPES:
                        if token in ['key', 'corruption']:
                            continue
                        tokens_to_deduct = min(player.tokens[token], tokens_needed)
                        player.tokens[token] -= tokens_to_deduct
                        tokens_needed -= tokens_to_deduct
                        if tokens_needed == 0:
                            break
                    player.crystals += 1
                    self.magic_sound.play()
                    activation_message = f"{player.name} has activated the Convert Seal!\nConverted 5 citation tokens into 1 crystal shard."
                    self.show_popup_message(activation_message, choice=False)
                else:
                    self.show_popup_message("Not enough citation tokens to activate the Convert seal.", choice=False)
        if mouse_clicked and not self.popup_message and not self.zoomed_card:
            clicked_card = None
            for card in possible_moves:
                if card.rect.collidepoint(mouse_pos):
                    clicked_card = card
                    break
            if clicked_card:
                if self.current_hovered_card and self.current_hovered_card.hover_sound:
                    self.hover_sound_channel.stop()
                    self.current_hovered_card = None
                if player.current_environment_card is not None:
                    old_card = self.environment_cards[player.current_environment_card]
                    old_card.occupied_by = None
                clicked_card.occupied_by = player
                player.current_environment_card = self.environment_cards.index(clicked_card)
                self.move_sound.play()
                self.play_character_sound(player)
                token_added_message = ""
                if clicked_card.token:
                    self.add_tokens(player, clicked_card.token, 1)
                    token_added_message = f"Added {clicked_card.token.capitalize()} token."
                if clicked_card.name == 'bustling_stalls.png':
                    self.show_popup_message("Choose an action:", choice=True)
                    self.game_state = BUSTLING_STALLS_CHOICE
                elif clicked_card.name == 'serene_environs.png':
                    self.show_popup_message("Choose an action:", choice=True)
                    self.game_state = PAY_CITATION_CARD
                else:
                    if clicked_card.token:
                        effect_msg = f"{player.name} landed on {clicked_card.display_name}.\n{clicked_card.description}"
                    else:
                        effect_msg = f"{player.name} landed on {clicked_card.display_name}.\n{clicked_card.description}"
                    self.show_popup_message(effect_msg)
                player.remaining_moves -= 1
                if player.remaining_moves <= 0:
                    player.phase = "action"
                else:
                    remaining_message = f"{player.remaining_moves} move(s) remaining."
                    self.show_popup_message(remaining_message, choice=False)
        if right_clicked:
            if self.zoomed_card:
                self.zoomed_card = None
            else:
                for i, citation_card in enumerate(player.citation_cards):
                    card_width = 180
                    card_height = 270
                    if i >= len(self.citation_card_y_offsets):
                        offset = 0
                    else:
                        offset = self.citation_card_y_offsets[i]
                    card_x = SCREEN_WIDTH - CITATION_CARDS_COLUMN_WIDTH + (CITATION_CARDS_COLUMN_WIDTH - card_width) // 2
                    card_y = 150 + i * (card_height + 40) + offset
                    card_rect = pygame.Rect(card_x, card_y, card_width, card_height)
                    if card_rect.collidepoint(mouse_pos):
                        self.zoomed_card = citation_card
                        break
        if self.zoomed_card:
            zoom_image = pygame.transform.scale(
                self.zoomed_card.front_image if self.zoomed_card.flipped else self.zoomed_card.back_image,
                (600, 900)
            )
            zoom_rect = zoom_image.get_rect(center=(SCREEN_WIDTH // 2, SCREEN_HEIGHT // 2))
            self.screen.blit(zoom_image, zoom_rect.topleft)
        if player.phase == "action" and self.popup_message is None and not self.choice and not self.zoomed_card:
            player.phase = "conclusion"
            self.game_state = PLAYER_TURN_CONCLUSION

    def play_character_sound(self, player):
        available_sounds = [s for s in self.character_sounds[player.name] if s[1] != player.last_sound_played]
        if not available_sounds:
            available_sounds = self.character_sounds[player.name]
        selected_sound_tuple = random.choice(available_sounds)
        selected_sound_name, selected_sound = selected_sound_tuple
        player.last_sound_played = selected_sound
        selected_sound.play()

    def activate_gatekeep(self, activating_player):
        target_players = [player for player in self.players if player != activating_player]
        if not target_players:
            self.show_popup_message("No other players to target.", choice=False)
            return
        target_player = random.choice(target_players)
        if not target_player.citation_cards:
            self.show_popup_message(f"{target_player.name} has no citation cards to target.", choice=False)
            return
        target_card = random.choice(target_player.citation_cards)
        if 'key' in target_card.cost:
            target_card.cost['key'] += 2
        else:
            target_card.cost['key'] = 2
        target_card.gatekept = True
        self.magic_sound.play()
        self.show_popup_message(f"{activating_player.name} has increased the cost of {target_player.name}'s citation card.", choice=False)

    def activate_terraform(self, player):
        target_cards = [card for card in self.environment_cards if card.name not in ('serene_environs.png', 'bustling_stalls.png')]
        if not target_cards:
            self.show_popup_message("No environment cards can be terraformed.", choice=False)
            return
        target_card = random.choice(target_cards)

        current_card_names = [card.name for card in self.environment_cards]
        unused_environment_card_names = [name for name in self.all_environment_card_names if name not in current_card_names]

        if not unused_environment_card_names:
            self.show_popup_message("No unused environment cards available to terraform.", choice=False)
            return

        new_card_name = random.choice(unused_environment_card_names)

        token_type = self.environment_card_tokens.get(new_card_name, None)
        display_name = self.environment_card_display_names.get(new_card_name, new_card_name.replace('_', ' ').replace('.png', '').title())
        description = self.environment_card_effect_descriptions.get(new_card_name, "No effect defined.")
        sound_name = new_card_name.replace('.png', '.mp3')
        hover_sound = self.load_sound(sound_name)
        new_card = EnvironmentCard(
            new_card_name,
            new_card_name,
            token_type,
            display_name,
            description,
            scale=(300, 500),
            hover_sound=hover_sound
        )

        new_card.rect.topleft = target_card.rect.topleft
        new_card.occupied_by = target_card.occupied_by

        index = self.environment_cards.index(target_card)
        self.environment_cards[index] = new_card
        self.environment_alphas[index] = 255

        self.show_popup_message(f"{player.name} terraformed {target_card.display_name} into {new_card.display_name}.", choice=False)

    def draw_citation_cards_column(self):
        column_width = CITATION_CARDS_COLUMN_WIDTH
        column_x = SCREEN_WIDTH - column_width
        column_surface = self.citation_card_counter
        self.screen.blit(column_surface, (column_x, 0))
        player = self.players[self.current_player]
        card_width = 180
        card_height = 270
        num_card_slots = 3
        total_card_height = card_height * num_card_slots
        start_y = 150
        spacing = 40
        for i in range(num_card_slots):
            if i >= len(player.citation_cards):
                break
            citation_card = player.citation_cards[i]
            card_x = column_x + (CITATION_CARDS_COLUMN_WIDTH - card_width) // 2
            card_y = start_y + i * (card_height + 40) + (self.citation_card_y_offsets[i] if i < len(self.citation_card_y_offsets) else 0)
            scaled_card_image = pygame.transform.scale(
                citation_card.back_image if not citation_card.flipped else citation_card.front_image,
                (card_width, card_height)
            )
            self.draw_card_with_shadow(scaled_card_image, pygame.Rect(card_x, card_y, card_width, card_height))
            card_rect = pygame.Rect(card_x, card_y, card_width, card_height)
            if card_rect.collidepoint(self.get_mouse_pos()) and not self.zoomed_card:
                glow_image = pygame.transform.scale(self.citesaga_glow, (card_width, card_height))
                self.screen.blit(glow_image, (card_x, card_y))
            if citation_card.gatekept:
                lock1_x = card_x + 10
                lock1_y = card_y + 10
                lock2_x = card_x + card_width - self.lock_image.get_width() - 10
                lock2_y = card_y + card_height - self.lock_image.get_height() - 10
                self.screen.blit(self.lock_image, (lock1_x, lock1_y))
                self.screen.blit(self.lock_image, (lock2_x, lock2_y))
        if self.zoomed_card:
            zoom_image = pygame.transform.scale(
                self.zoomed_card.front_image if self.zoomed_card.flipped else self.zoomed_card.back_image,
                (600, 900)
            )
            zoom_rect = zoom_image.get_rect(center=(SCREEN_WIDTH // 2, SCREEN_HEIGHT // 2))
            self.screen.blit(zoom_image, zoom_rect.topleft)

    def draw_card_with_shadow(self, card_image, card_rect):
        shadow_offset = (10, 10)
        shadow_color = (0, 0, 0, 200)
        shadow_surface = pygame.Surface((card_image.get_width() + 10, card_image.get_height() + 10), pygame.SRCALPHA)
        shadow_surface.fill((0, 0, 0, 0))
        pygame.draw.rect(shadow_surface, shadow_color, (5, 5, card_image.get_width(), card_image.get_height()))
        self.screen.blit(shadow_surface, (card_rect.x - 5 + shadow_offset[0], card_rect.y - 5 + shadow_offset[1]))
        self.screen.blit(card_image, (card_rect.x, card_rect.y))

    def player_turn_conclusion(self):
        player = self.players[self.current_player]
        mouse_pos = self.get_mouse_pos()
        mouse_clicked = False
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit()
                sys.exit()
            elif event.type == pygame.MOUSEBUTTONDOWN:
                if event.button == 1:
                    mouse_clicked = True
        self.screen.blit(self.background_game, (0, 0))
        self.screen.blit(self.fade_overlay, (0, 0))
        self.draw_citation_tokens()
        self.draw_citation_cards_column()
        for card in self.environment_cards:
            card_image = card.image.copy()
            card_image.set_alpha(255)
            self.draw_card_with_shadow(card_image, card.rect)
            self.draw_card_token_indicator(card)
        for card in self.environment_cards:
            if card.occupied_by is not None:
                self.draw_player_on_card(card.occupied_by, card)
        self.draw_phase(player)
        self.handle_environment_card_hover(mouse_pos)
        current_time = pygame.time.get_ticks()
        if self.conclusion_phase_start_time is None:
            self.conclusion_phase_start_time = current_time
        if not self.execute_card_effect_done:
            self.execute_card_effect()
            self.execute_card_effect_done = True
        if current_time - self.conclusion_phase_start_time >= 2000:
            self.advance_turn()
            self.conclusion_phase_start_time = None
            self.execute_card_effect_done = False
            self.choice = False

    def complete_reference(self):
        player = self.players[self.current_player]
        mouse_pos = self.get_mouse_pos()
        mouse_clicked = False
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit()
                sys.exit()
            elif event.type == pygame.KEYDOWN:
                if event.key == pygame.K_BACKSPACE:
                    self.reference_input = self.reference_input[:-1]
                elif event.key == pygame.K_RETURN:
                    pass
                else:
                    self.reference_input += event.unicode
            elif event.type == pygame.MOUSEBUTTONDOWN:
                if event.button == 1:
                    mouse_clicked = True
        self.screen.blit(self.background_game, (0, 0))
        self.screen.blit(self.fade_overlay, (0, 0))
        self.draw_citation_tokens()
        self.draw_citation_cards_column()
        for card in self.environment_cards:
            card_image = card.image.copy()
            card_image.set_alpha(255)
            self.draw_card_with_shadow(card_image, card.rect)
            self.draw_card_token_indicator(card)
        for card in self.environment_cards:
            if card.occupied_by is not None:
                self.draw_player_on_card(card.occupied_by, card)
        self.draw_phase(player)
        popup_width = 900
        popup_height = 600
        popup_x = (SCREEN_WIDTH - popup_width) // 2
        popup_y = (SCREEN_HEIGHT - popup_height) // 2
        popup_image = pygame.transform.scale(self.citesaga_button, (popup_width, popup_height))
        self.screen.blit(popup_image, (popup_x, popup_y))
        instruction_text = "Complete the reference for this citation card"
        text_surface = self.choice_font.render(instruction_text, True, TEXT_COLOR)
        text_rect = text_surface.get_rect(center=(SCREEN_WIDTH // 2, popup_y + 130))
        self.screen.blit(text_surface, text_rect)
        input_box_width = popup_width - 100
        input_box_height = 50
        input_box_x = popup_x + 50
        input_box_y = popup_y + 200
        pygame.draw.rect(self.screen, WHITE, (input_box_x, input_box_y, input_box_width, input_box_height))
        pygame.draw.rect(self.screen, BLACK, (input_box_x, input_box_y, input_box_width, input_box_height), 2)
        input_text_surface = self.choice_font.render(self.reference_input, True, BLACK)
        self.screen.blit(input_text_surface, (input_box_x + 10, input_box_y + 10))
        button_width = 200
        button_height = 60
        button_spacing = 50
        total_buttons_width = 2 * button_width + button_spacing
        buttons_x = popup_x + (popup_width - total_buttons_width) // 2
        buttons_y = popup_y + popup_height + 20
        correct_button_rect = pygame.Rect(buttons_x, buttons_y, button_width, button_height)
        incorrect_button_rect = pygame.Rect(buttons_x + button_width + button_spacing, buttons_y, button_width, button_height)
        scaled_button = pygame.transform.scale(self.citesaga_button, (button_width, button_height))
        self.screen.blit(scaled_button, correct_button_rect.topleft)
        self.draw_text("Correct", self.choice_font, TEXT_COLOR, correct_button_rect.centerx, correct_button_rect.centery)
        self.screen.blit(scaled_button, incorrect_button_rect.topleft)
        self.draw_text("Incorrect", self.choice_font, TEXT_COLOR, incorrect_button_rect.centerx, incorrect_button_rect.centery)
        if mouse_clicked:
            if correct_button_rect.collidepoint(mouse_pos):
                self.process_payment()
                self.reference_input = ''
                self.game_state = PLAYER_TURN_CONCLUSION
            elif incorrect_button_rect.collidepoint(mouse_pos):
                self.reference_input = ''
                self.players[self.current_player].phase = "conclusion"
                self.game_state = PLAYER_TURN_CONCLUSION
        if self.zoomed_card:
            zoom_image = pygame.transform.scale(
                self.zoomed_card.front_image if self.zoomed_card.flipped else self.zoomed_card.back_image,
                (600, 900)
            )
            zoom_rect = zoom_image.get_rect(center=(SCREEN_WIDTH // 2, SCREEN_HEIGHT // 2))
            self.screen.blit(zoom_image, zoom_rect.topleft)

    def process_payment(self):
        player = self.players[self.current_player]
        selected_card = self.selected_citation_card
        for token, amount in selected_card.cost.items():
            if token != 'any':
                player.tokens[token] -= amount
        any_needed = selected_card.cost.get('any', 0)
        if any_needed > 0:
            all_tokens = []
            for token, amount in player.tokens.items():
                all_tokens.extend([token] * amount)
            if len(all_tokens) >= any_needed:
                tokens_to_use = random.sample(all_tokens, any_needed)
                for token in tokens_to_use:
                    player.tokens[token] -= 1
            else:
                for token in all_tokens:
                    player.tokens[token] -= 1
        player.crystals += selected_card.reward
        self.magic_sound.play()
        player.citation_cards.remove(selected_card)
        self.show_popup_message(f"Paid for {selected_card.name.replace('_',' ').replace('.png','').title()}.", choice=False)
        if selected_card.gatekept:
            selected_card.gatekept = False
        if player.crystals >= 5:
            self.show_popup_message(f"Player {player.name} has restored the crystal of citation!", win=True)
            self.game_state = WIN_CONDITION
            return
        if not player.citation_cards:
            self.assign_new_citation_cards(player)
        for token, amount in player.tokens.items():
            if player.tokens[token] < 0:
                player.tokens[token] = 0

    def assign_new_citation_cards(self, player):
        citation_card_names = [
            'alchemists_almanac.png',
            'astral_symposia.png',
            'citehold_conundrum.png',
            'lunar_howls.png',
            'mandates_of_the_hive.png',
            'pixie_parlance.png',
            'sand_and_summit.png',
            'territorial_tenets.png',
            'council_of_the_realms.png',
            'manual_of_ambition.png',
            'the_inkblade_murders.png',
            'the_elders_codex.png',
            'scrolltube.png'
        ]
        selected = random.sample(citation_card_names, 3)
        for card_name in selected:
            cost = self.create_citation_card_costs(card_name)
            reward = self.get_citation_card_reward(card_name)
            card = CitationCard(card_name, card_name, cost, reward)
            player.citation_cards.append(card)

    def win_condition_screen(self):
        mouse_pos = self.get_mouse_pos()
        mouse_clicked = False
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit()
                sys.exit()
            elif event.type == pygame.MOUSEBUTTONDOWN:
                if event.button == 1:
                    mouse_clicked = True
        self.screen.blit(self.background_game, (0, 0))
        self.screen.blit(self.fade_overlay, (0, 0))
        message = self.popup_message
        popup_width = 800
        popup_height = 300
        popup_x = (SCREEN_WIDTH - popup_width) // 2
        popup_y = (SCREEN_HEIGHT - popup_height) // 2
        popup_image = pygame.transform.scale(self.citesaga_button, (popup_width, popup_height))
        self.screen.blit(popup_image, (popup_x, popup_y))
        lines = message.split('\n')
        for i, line in enumerate(lines):
            text_surface = self.popup_font.render(line, True, TEXT_COLOR)
            text_rect = text_surface.get_rect(center=(SCREEN_WIDTH // 2, popup_y + 50 + i * 50))
            self.screen.blit(text_surface, text_rect)
        main_menu_button_rect = pygame.Rect(
            (SCREEN_WIDTH // 2 - 100, SCREEN_HEIGHT // 2 + 100),
            (200, 50)
        )
        scaled_button = pygame.transform.scale(self.citesaga_button, (200, 50))
        self.screen.blit(scaled_button, main_menu_button_rect.topleft)
        self.draw_text("Main Menu", self.button_font, TEXT_COLOR, main_menu_button_rect.centerx, main_menu_button_rect.centery)
        if mouse_clicked and main_menu_button_rect.collidepoint(mouse_pos):
            self.reset_game()
            self.game_state = MAIN_MENU
        if self.zoomed_card:
            zoom_image = pygame.transform.scale(
                self.zoomed_card.front_image if self.zoomed_card.flipped else self.zoomed_card.back_image,
                (600, 900)
            )
            zoom_rect = zoom_image.get_rect(center=(SCREEN_WIDTH // 2, SCREEN_HEIGHT // 2))
            self.screen.blit(zoom_image, zoom_rect.topleft)

    def reset_game(self):
        for player in self.players:
            player.tokens = {token: 0 for token in TOKEN_TYPES}
            player.citation_cards = []
            player.crystals = 0
            player.current_environment_card = None
            player.last_sound_played = None
            player.multiply_turns_remaining = 0
        self.assign_citation_cards()
        self.current_player = 0
        if self.current_hovered_card:
            self.hover_sound_channel.stop()
            self.current_hovered_card = None

    def bustling_stalls_choice(self):
        mouse_pos = self.get_mouse_pos()
        mouse_clicked = False
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit()
                sys.exit()
            elif event.type == pygame.MOUSEBUTTONDOWN:
                if event.button == 1:
                    mouse_clicked = True
        self.screen.blit(self.background_game, (0, 0))
        self.screen.blit(self.fade_overlay, (0, 0))
        self.draw_citation_tokens()
        self.draw_citation_cards_column()
        for card in self.environment_cards:
            card_image = card.image.copy()
            card_image.set_alpha(255)
            self.draw_card_with_shadow(card_image, card.rect)
            self.draw_card_token_indicator(card)
        for card in self.environment_cards:
            if card.occupied_by is not None:
                self.draw_player_on_card(card.occupied_by, card)
        self.draw_phase(self.players[self.current_player])
        popup_width = 800
        popup_height = 400
        popup_x = (SCREEN_WIDTH - popup_width) // 2
        popup_y = (SCREEN_HEIGHT - popup_height) // 2
        header_button_width = 300
        header_button_height = 100
        header_button_image = pygame.transform.scale(self.citesaga_button, (header_button_width, header_button_height))
        header_button_x = popup_x + (popup_width - header_button_width) // 2
        header_button_y = popup_y + 20
        self.screen.blit(header_button_image, (header_button_x, header_button_y))
        self.draw_text("Choose an action:", self.choice_font, TEXT_COLOR, SCREEN_WIDTH // 2, header_button_y + header_button_height // 2)
        button_width, button_height = 600, 60
        scaled_button = pygame.transform.scale(self.citesaga_button, (button_width, button_height))
        button_x = popup_x + (popup_width - button_width) // 2
        button_y_start = popup_y + header_button_height + 60
        button_spacing = 80
        convert_lvl1_rect = pygame.Rect(button_x, button_y_start, button_width, button_height)
        convert_lvl2_rect = pygame.Rect(button_x, button_y_start + button_spacing, button_width, button_height)
        swap_card_rect = pygame.Rect(button_x, button_y_start + 2 * button_spacing, button_width, button_height)
        self.screen.blit(scaled_button, convert_lvl1_rect.topleft)
        self.draw_text("Convert 2 level 1 tokens to 1 level 2 token", self.choice_font, TEXT_COLOR, convert_lvl1_rect.centerx, convert_lvl1_rect.centery)
        self.screen.blit(scaled_button, convert_lvl2_rect.topleft)
        self.draw_text("Convert 2 level 2 tokens to 1 level 3 token", self.choice_font, TEXT_COLOR, convert_lvl2_rect.centerx, convert_lvl2_rect.centery)
        self.screen.blit(scaled_button, swap_card_rect.topleft)
        self.draw_text("Swap 1 citation card for another random one", self.choice_font, TEXT_COLOR, swap_card_rect.centerx, swap_card_rect.centery)
        if mouse_clicked:
            player = self.players[self.current_player]
            if convert_lvl1_rect.collidepoint(mouse_pos):
                self.convert_2_level1_to_level2(player)
                self.choice = False
                player.phase = "conclusion"
                self.game_state = PLAYER_TURN_CONCLUSION
                self.execute_card_effect_done = True
            elif convert_lvl2_rect.collidepoint(mouse_pos):
                self.convert_2_level2_to_level3(player)
                self.choice = False
                player.phase = "conclusion"
                self.game_state = PLAYER_TURN_CONCLUSION
                self.execute_card_effect_done = True
            elif swap_card_rect.collidepoint(mouse_pos):
                self.swap_citation_card(player)
                self.choice = False
                player.phase = "conclusion"
                self.game_state = PLAYER_TURN_CONCLUSION
                self.execute_card_effect_done = True
        if self.zoomed_card:
            zoom_image = pygame.transform.scale(
                self.zoomed_card.front_image if self.zoomed_card.flipped else self.zoomed_card.back_image,
                (600, 900)
            )
            zoom_rect = zoom_image.get_rect(center=(SCREEN_WIDTH // 2, SCREEN_HEIGHT // 2))
            self.screen.blit(zoom_image, zoom_rect.topleft)

    def advance_turn(self):
        outgoing_player = self.players[self.current_player]
        if outgoing_player.multiply_turns_remaining > 0:
            outgoing_player.multiply_turns_remaining -= 1
            if outgoing_player.multiply_turns_remaining == 0:
                self.show_popup_message(f"{outgoing_player.name}'s Multiply Seal effect has ended.", choice=False)
        self.current_player = (self.current_player + 1) % len(self.players)
        self.game_state = PLAYER_TURN_FLIP_CITATION_CARDS
        self.execute_card_effect_done = False
        self.citation_flip_index = 0
        self.flipping_citation = False
        self.flip_alpha = 0
        self.flip_start_time = pygame.time.get_ticks()
        self.current_flip_card_index = 0
        self.flip_in_progress = False
        current_player = self.players[self.current_player]
        for card in current_player.citation_cards:
            card.flipped = False
        current_player.phase = "movement"
        current_player.remaining_moves = 1
        self.show_turn_image = True
        self.turn_image_display_start = 0
        self.flip_sound.play()
        if self.current_hovered_card:
            self.hover_sound_channel.stop()
            self.current_hovered_card = None

    def convert_2_level1_to_level2(self, player):
        level1_tokens = [token for token in TOKEN_LEVELS if TOKEN_LEVELS[token] == 1 and player.tokens[token] >= 2]
        if not level1_tokens:
            self.show_popup_message("Not enough level 1 tokens to convert.", choice=False)
            return
        token_to_convert = random.choice(level1_tokens)
        player.tokens[token_to_convert] -= 2
        level2_tokens = [token for token, lvl in TOKEN_LEVELS.items() if lvl == 2]
        new_token = random.choice(level2_tokens)
        self.add_tokens(player, new_token, 1)
        self.show_popup_message(f"Converted 2 {token_to_convert.capitalize()} tokens to 1 {new_token.capitalize()} token.", choice=False)

    def convert_2_level2_to_level3(self, player):
        level2_tokens = [token for token in TOKEN_LEVELS if TOKEN_LEVELS[token] == 2 and player.tokens[token] >= 2]
        if not level2_tokens:
            self.show_popup_message("Not enough level 2 tokens to convert.", choice=False)
            return
        token_to_convert = random.choice(level2_tokens)
        player.tokens[token_to_convert] -= 2
        level3_tokens = [token for token, lvl in TOKEN_LEVELS.items() if lvl == 3]
        new_token = random.choice(level3_tokens)
        self.add_tokens(player, new_token, 1)
        self.show_popup_message(f"Converted 2 {token_to_convert.capitalize()} tokens to 1 {new_token.capitalize()} token.", choice=False)

    def swap_citation_card(self, player):
        if not player.citation_cards:
            self.show_popup_message("No citation cards to swap.", choice=False)
            return
        old_card = random.choice(player.citation_cards)
        player.citation_cards.remove(old_card)
        if old_card.gatekept:
            old_card.gatekept = False
        citation_card_names = [
            'alchemists_almanac.png',
            'astral_symposia.png',
            'citehold_conundrum.png',
            'lunar_howls.png',
            'mandates_of_the_hive.png',
            'pixie_parlance.png',
            'sand_and_summit.png',
            'territorial_tenets.png',
            'council_of_the_realms.png',
            'manual_of_ambition.png',
            'the_inkblade_murders.png',
            'the_elders_codex.png',
            'scrolltube.png'
        ]
        new_card_name = random.choice(citation_card_names)
        cost = self.create_citation_card_costs(new_card_name)
        reward = self.get_citation_card_reward(new_card_name)
        new_card = CitationCard(new_card_name, new_card_name, cost, reward)
        player.citation_cards.append(new_card)
        self.show_popup_message(f"Swapped {old_card.name.replace('_',' ').replace('.png','').title()} for {new_card.name.replace('_',' ').replace('.png','').title()}.", choice=False)

    def add_tokens(self, player, token_type, amount=1):
        if player.multiply_turns_remaining > 0:
            amount *= 2
        player.tokens[token_type] += amount
        self.show_popup_message(f"Added {amount} {token_type.capitalize()} token(s).", choice=False)

    def handle_environment_card_hover(self, mouse_pos):
        hovered_card = None
        for card in self.environment_cards:
            if card.rect.collidepoint(mouse_pos):
                hovered_card = card
                break
        if hovered_card != self.current_hovered_card:
            if self.current_hovered_card and self.current_hovered_card.hover_sound:
                self.hover_sound_channel.stop()
            if hovered_card and hovered_card.hover_sound:
                self.hover_sound_channel.play(hovered_card.hover_sound, loops=-1)
            self.current_hovered_card = hovered_card

    def select_random_other_player(self, current_player):
        other_players = [player for player in self.players if player != current_player]
        if not other_players:
            return None
        return random.choice(other_players)

    def draw_citation_tokens(self):
        column_width = CITATION_TOKENS_COLUMN_WIDTH
        column_surface = self.citation_token_counter
        self.screen.blit(column_surface, (0, 0))
        num_players = len(self.players)
        player_section_height = SCREEN_HEIGHT // num_players
        y_offsets = [120, 65, 10, -45]
        for player_index, player in enumerate(self.players):
            green_red_yellow_x = 65
            blue_purple_crystal_x = column_width // 2 + 5
            start_y = 100 + player_section_height * player_index + y_offsets[player_index]
            spacing = 40
            for i, token in enumerate(['green', 'red', 'yellow', 'corruption']):
                token_image = self.TOKEN_IMAGES[token]
                self.screen.blit(token_image, (green_red_yellow_x, start_y + i * spacing))
                count_text = f"x {player.tokens[token]}"
                self.draw_text(count_text, self.token_font, TEXT_COLOR, green_red_yellow_x + token_image.get_width() + 40, start_y + i * spacing + token_image.get_height() // 2)
            for i, token in enumerate(['blue', 'purple']):
                token_image = self.TOKEN_IMAGES[token]
                self.screen.blit(token_image, (blue_purple_crystal_x, start_y + i * spacing))
                count_text = f"x {player.tokens[token]}"
                self.draw_text(count_text, self.token_font, TEXT_COLOR, blue_purple_crystal_x + token_image.get_width() + 40, start_y + i * spacing + token_image.get_height() // 2)
            self.screen.blit(self.crystal_image, (blue_purple_crystal_x, start_y + 2 * spacing))
            count_text = f"x {player.crystals}"
            self.draw_text(count_text, self.token_font, TEXT_COLOR, blue_purple_crystal_x + self.crystal_image.get_width() + 40, start_y + 2 * spacing + self.crystal_image.get_height() // 2)
            key_y = start_y + 3 * spacing
            key_image = self.TOKEN_IMAGES['key']
            self.screen.blit(key_image, (blue_purple_crystal_x, key_y))
            count_text = f"x {player.tokens['key']}"
            self.draw_text(count_text, self.token_font, TEXT_COLOR, blue_purple_crystal_x + key_image.get_width() + 40, key_y + key_image.get_height() // 2)

    def execute_card_effect(self):
        last_player = self.players[self.current_player]
        if last_player.current_environment_card is None:
            return
        card = self.environment_cards[last_player.current_environment_card]
        if card.name == 'serene_environs.png':
            self.serene_environs_effect(last_player)
        elif card.name == 'bustling_stalls.png':
            self.game_state = BUSTLING_STALLS_CHOICE
        elif card.name == 'boundless_sands.png':
            self.boundless_sands_effect(last_player)
        elif card.name == 'celestial_lakes.png':
            self.celestial_lakes_effect(last_player)
        elif card.name == 'inkflow_skyline.png':
            self.inkflow_skyline_effect(last_player)
        elif card.name == 'the_evergrove.png':
            self.the_evergrove_effect(last_player)
        elif card.name == 'untouched_territories.png':
            self.untouched_territories_effect(last_player)
        elif card.name == 'restless_canopies.png':
            self.restless_canopies_effect(last_player)
        elif card.name == 'fusty_swamps.png':
            self.fusty_swamps_effect(last_player)
        elif card.name == 'the_plainlands.png':
            self.the_plainlands_effect(last_player)
        elif card.name == 'painted_fields.png':
            self.painted_fields_effect(last_player)
        elif card.name == 'inkwash_backwaters.png':
            self.inkwash_backwaters_effect(last_player)
        elif card.name == 'wooded_pathways.png':
            self.wooded_pathways_effect(last_player)
        elif card.name == 'stolen_mires.png':
            self.stolen_mires_effect(last_player)
        elif card.name == 'spiralling_corridors.png':
            self.spiralling_corridors_effect(last_player)
        elif card.name == 'fireproof_crags.png':
            self.fireproof_crags_effect(last_player)
        elif card.name == 'frigid_mountains.png':
            self.frigid_mountains_effect(last_player)
        elif card.name == 'palatial_halls.png':
            self.palatial_halls_effect(last_player)

    def show_popup_message(self, message, choice=False, win=False):
        self.popup_message = message
        self.popup_start_time = pygame.time.get_ticks()
        self.choice = choice
        self.win = win

    def draw_popup_message(self):
        if self.popup_message:
            current_time = pygame.time.get_ticks()
            elapsed_time = current_time - self.popup_start_time
            if elapsed_time < self.popup_display_duration or self.choice or self.win:
                alpha = 255
            elif elapsed_time < self.popup_display_duration + self.popup_fade_duration:
                fade_elapsed = elapsed_time - self.popup_display_duration
                fade_ratio = fade_elapsed / self.popup_fade_duration
                alpha = max(255 - int(255 * fade_ratio), 0)
            else:
                self.popup_message = None
                self.choice = False
                self.win = False
                return
            popup_width = 800
            popup_height = 300
            popup_image = pygame.transform.scale(self.citesaga_button, (popup_width, popup_height))
            popup_image.set_alpha(alpha)
            self.screen.blit(popup_image, ((SCREEN_WIDTH - popup_width) // 2, (SCREEN_HEIGHT - popup_height) // 2))
            lines = self.popup_message.split('\n')
            for i, line in enumerate(lines):
                text_surface = self.popup_font.render(line, True, TEXT_COLOR)
                text_rect = text_surface.get_rect(center=(SCREEN_WIDTH // 2, SCREEN_HEIGHT // 2 - 40 + i * 50))
                self.screen.blit(text_surface, text_rect)
            if self.choice:
                self.draw_popup_buttons()

    def draw_popup_buttons(self):
        popup_width = 800
        popup_height = 300
        popup_x = (SCREEN_WIDTH - popup_width) // 2
        popup_y = (SCREEN_HEIGHT - popup_height) // 2
        button_width = 200
        button_height = 60
        button_spacing = 50
        total_buttons_width = 2 * button_width + button_spacing
        buttons_x = popup_x + (popup_width - total_buttons_width) // 2
        buttons_y = popup_y + popup_height + 20
        correct_button_rect = pygame.Rect(buttons_x, buttons_y, button_width, button_height)
        incorrect_button_rect = pygame.Rect(buttons_x + button_width + button_spacing, buttons_y, button_width, button_height)
        scaled_button = pygame.transform.scale(self.citesaga_button, (button_width, button_height))
        self.screen.blit(scaled_button, correct_button_rect.topleft)
        self.draw_text("Correct", self.choice_font, TEXT_COLOR, correct_button_rect.centerx, correct_button_rect.centery)
        self.screen.blit(scaled_button, incorrect_button_rect.topleft)
        self.draw_text("Incorrect", self.choice_font, TEXT_COLOR, incorrect_button_rect.centerx, incorrect_button_rect.centery)

    def draw_phase(self, player):
        phase_text = ""
        phase_image = {
            "Referella": self.referella_phase_image,
            "Duskwrit": self.duskwrit_phase_image,
            "Pendragraph": self.pendragraph_phase_image,
            "Thistlepage": self.thistlepage_phase_image,
            "Cite-a-lot": self.citealot_phase_image,
            "Echo Quill": self.echoquill_phase_image,
            "Cinder Scroll": self.cinderscroll_phase_image,
            "Tomebough": self.tomebough_phase_image
        }.get(player.name)
        if player.phase == "movement":
            phase_text = "Movement Phase"
        elif player.phase == "action":
            phase_text = "Action Phase"
        elif player.phase == "conclusion":
            phase_text = "Conclusion Phase"
        if phase_image:
            if player.phase == "movement":
                phase_image_rect = phase_image.get_rect(midtop=(SCREEN_WIDTH // 2 - 140, 47))
            elif player.phase == "action":
                phase_image_rect = phase_image.get_rect(midtop=(SCREEN_WIDTH // 2 + 0, 47))
            elif player.phase == "conclusion":
                phase_image_rect = phase_image.get_rect(midtop=(SCREEN_WIDTH // 2 + 140, 47))
            self.screen.blit(phase_image, phase_image_rect.topleft)
        phase_rect = self.phase_image.get_rect(midtop=(SCREEN_WIDTH // 2, 0))
        self.screen.blit(self.phase_image, phase_rect.topleft)
        font = self.load_font('Pirata_One.ttf', 40)
        text_surface = font.render(phase_text, True, TEXT_COLOR)
        text_rect = text_surface.get_rect(midtop=(SCREEN_WIDTH // 2, phase_rect.bottom + 10))
        self.screen.blit(text_surface, text_rect)

    def draw_player_on_card(self, player, card):
        card_width, card_height = card.rect.size
        scaled_width = int(card_width * 0.75)
        scaled_height = int(card_height * 0.75)
        scaled_player_image = pygame.transform.scale(player.image, (scaled_width, scaled_height))
        player_rect = scaled_player_image.get_rect(center=card.rect.center)
        self.screen.blit(scaled_player_image, player_rect.topleft)

    def end_game(self):
        pass

    def draw_button(self, rect, text, font, text_color, bg_color):
        pygame.draw.rect(self.screen, bg_color, rect)
        pygame.draw.rect(self.screen, TEXT_COLOR, rect, 5)
        self.draw_text(text, font, text_color, rect.centerx, rect.centery)

    def draw_text(self, text, font, color, x, y):
        textobj = font.render(text, True, color)
        text_rect = textobj.get_rect(center=(x, y))
        self.screen.blit(textobj, text_rect)

    def serene_environs_effect(self, player):
        self.show_popup_message("Choose to pay for a citation card or skip your turn.", choice=True)

    def boundless_sands_effect(self, player):
        available_levels = [level for level in [1, 2, 3] if not any(
            TOKEN_LEVELS.get(token) == level and player.tokens[token] > 0 for token in player.tokens
        )]
        if not available_levels:
            self.show_popup_message("No available levels to draw tokens from.", choice=False)
            return
        tokens_drawn = []
        for _ in range(2):
            if available_levels:
                level = random.choice(available_levels)
                token_types = [token for token, lvl in TOKEN_LEVELS.items() if lvl == level]
                token = random.choice(token_types)
                self.add_tokens(player, token, 1)
                tokens_drawn.append(token.capitalize())
        self.show_popup_message(f"Drawn tokens: {', '.join(tokens_drawn)}.", choice=False)

    def celestial_lakes_effect(self, player):
        self.add_tokens(player, 'corruption', 1)
        self.show_popup_message("Gained one Corruption token.", choice=False)

    def inkwash_backwaters_effect(self, player):
        self.swap_citation_card(player)
        self.swap_citation_card(player)
        self.show_popup_message("Swapped two citation cards.", choice=False)

    def the_evergrove_effect(self, player):
        level2_tokens = [token for token, lvl in TOKEN_LEVELS.items() if lvl == 2]
        tokens_drawn = []
        for _ in range(2):
            token = random.choice(level2_tokens)
            self.add_tokens(player, token, 1)
            tokens_drawn.append(token.capitalize())
        self.show_popup_message(f"Drawn tokens: {', '.join(tokens_drawn)}.", choice=False)

    def untouched_territories_effect(self, player):
        level2_tokens = [token for token in TOKEN_LEVELS if TOKEN_LEVELS[token] == 2]
        token = random.choice(level2_tokens)
        self.add_tokens(player, token, 1)
        self.show_popup_message(f"Drawn token: {token.capitalize()}.", choice=False)

    def restless_canopies_effect(self, player):
        self.swap_citation_card(player)
        self.show_popup_message("Swapped one citation card.", choice=False)

    def fusty_swamps_effect(self, player):
        self.add_tokens(player, 'green', 1)
        self.show_popup_message("Drawn token: Green.", choice=False)

    def the_plainlands_effect(self, player):
        self.swap_citation_card(player)
        self.show_popup_message("Swapped one citation card.", choice=False)

    def painted_fields_effect(self, player):
        self.add_tokens(player, 'green', 1)
        self.add_tokens(player, 'blue', 1)
        self.show_popup_message("Drawn tokens: Green & Blue.", choice=False)

    def inkflow_skyline_effect(self, player):
        level1_tokens = [token for token in TOKEN_LEVELS if TOKEN_LEVELS[token] == 1 and player.tokens[token] >= 2]
        if not level1_tokens:
            self.show_popup_message("Not enough level 1 tokens to convert.", choice=False)
            return
        token_to_convert = random.choice(level1_tokens)
        player.tokens[token_to_convert] -= 2
        possible_conversion_tokens = [token for token in TOKEN_LEVELS if TOKEN_LEVELS[token] == 1 and token != token_to_convert]
        if not possible_conversion_tokens:
            player.tokens[token_to_convert] += 2
            self.show_popup_message("No available tokens to convert to.", choice=False)
            return
        new_token = random.choice(possible_conversion_tokens)
        self.add_tokens(player, new_token, 2)
        self.add_tokens(player, 'key', 1)
        self.show_popup_message(
            f"Converted 2 {token_to_convert.capitalize()} tokens to 2 {new_token.capitalize()} tokens.\nGained 1 Key token.",
            choice=False
        )

    def wooded_pathways_effect(self, player):
        self.add_tokens(player, 'green', 1)
        self.add_tokens(player, 'blue', 1)
        self.show_popup_message("Drawn tokens: Green & Blue.", choice=False)

    def stolen_mires_effect(self, player):
        if player.tokens['blue'] >= 1:
            player.tokens['blue'] -= 1
            self.add_tokens(player, 'purple', 1)
            self.show_popup_message("Converted one Blue token to one Purple token.", choice=False)
        else:
            self.show_popup_message("Not enough Blue tokens to convert.", choice=False)

    def spiralling_corridors_effect(self, player):
        self.swap_citation_card(player)
        self.swap_citation_card(player)
        self.show_popup_message("Swapped two citation cards.", choice=False)

    def fireproof_crags_effect(self, player):
        if player.tokens['green'] >= 1:
            player.tokens['green'] -= 1
            self.add_tokens(player, 'blue', 1)
            self.show_popup_message("Converted one Green token to one Blue token.", choice=False)
        else:
            self.show_popup_message("Not enough Green tokens to convert.", choice=False)

    def frigid_mountains_effect(self, player):
        if player.tokens['green'] >= 2:
            player.tokens['green'] -= 2
            self.add_tokens(player, 'blue', 1)
            self.show_popup_message("Upgraded two Green tokens to one Blue token.", choice=False)
        else:
            self.show_popup_message("Not enough Green tokens to upgrade.", choice=False)

    def palatial_halls_effect(self, player):
        self.add_tokens(player, 'blue', 2)
        self.show_popup_message("Drawn tokens: Two Blue.", choice=False)

    def pay_citation_card(self):
        mouse_pos = self.get_mouse_pos()
        mouse_clicked = False
        right_clicked = False
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit()
                sys.exit()
            elif event.type == pygame.MOUSEBUTTONDOWN:
                if event.button == 1:
                    mouse_clicked = True
                elif event.button == 3:
                    right_clicked = True
        self.screen.blit(self.background_game, (0, 0))
        self.screen.blit(self.fade_overlay, (0, 0))
        self.draw_citation_tokens()
        self.draw_citation_cards_column()
        for card in self.environment_cards:
            card_image = card.image.copy()
            card_image.set_alpha(255)
            self.draw_card_with_shadow(card_image, card.rect)
            self.draw_card_token_indicator(card)
        for card in self.environment_cards:
            if card.occupied_by is not None:
                self.draw_player_on_card(card.occupied_by, card)
        self.draw_phase(self.players[self.current_player])
        self.handle_environment_card_hover(mouse_pos)
        popup_width = 800
        popup_height = 400
        popup_x = (SCREEN_WIDTH - popup_width) // 2
        popup_y = (SCREEN_HEIGHT - popup_height) // 2
        header_button_width = 300
        header_button_height = 100
        header_button_image = pygame.transform.scale(self.citesaga_button, (header_button_width, header_button_height))
        header_button_x = popup_x + (popup_width - header_button_width) // 2
        header_button_y = popup_y + 20
        self.screen.blit(header_button_image, (header_button_x, header_button_y))
        self.draw_text("Choose an action:", self.choice_font, TEXT_COLOR, SCREEN_WIDTH // 2, header_button_y + header_button_height // 2)
        button_width, button_height = 600, 60
        scaled_button = pygame.transform.scale(self.citesaga_button, (button_width, button_height))
        button_x = popup_x + (popup_width - button_width) // 2
        button_y_start = popup_y + header_button_height + 60
        button_spacing = 80
        pay_button_rect = pygame.Rect(button_x, button_y_start, button_width, button_height)
        skip_button_rect = pygame.Rect(button_x, button_y_start + button_spacing, button_width, button_height)
        self.screen.blit(scaled_button, pay_button_rect.topleft)
        self.draw_text("Pay", self.choice_font, TEXT_COLOR, pay_button_rect.centerx, pay_button_rect.centery)
        self.screen.blit(scaled_button, skip_button_rect.topleft)
        self.draw_text("Skip Turn", self.choice_font, TEXT_COLOR, skip_button_rect.centerx, skip_button_rect.centery)
        if mouse_clicked:
            if pay_button_rect.collidepoint(mouse_pos):
                player = self.players[self.current_player]
                affordable_cards = []
                for card in player.citation_cards:
                    required_tokens = card.cost.copy()
                    player_tokens = player.tokens.copy()
                    any_needed = required_tokens.pop('any', 0)
                    can_pay = True
                    for token, amount in required_tokens.items():
                        if player_tokens.get(token, 0) < amount:
                            can_pay = False
                            break
                        player_tokens[token] -= amount
                    if can_pay and any_needed > 0:
                        total_available_tokens = sum(player_tokens.values())
                        if total_available_tokens < any_needed:
                            can_pay = False
                    if can_pay:
                        affordable_cards.append(card)
                if affordable_cards:
                    self.selected_citation_card = affordable_cards[0]
                    self.reference_input = ''
                    self.game_state = COMPLETE_REFERENCE
                else:
                    self.show_popup_message("No affordable citation cards.", choice=False)
                    self.choice = False
                    self.players[self.current_player].phase = "conclusion"
                    self.game_state = PLAYER_TURN_CONCLUSION
            elif skip_button_rect.collidepoint(mouse_pos):
                self.show_popup_message("Turn skipped.", choice=False)
                self.choice = False
                self.players[self.current_player].phase = "conclusion"
                self.game_state = PLAYER_TURN_CONCLUSION
        if right_clicked:
            if self.zoomed_card:
                self.zoomed_card = None
            else:
                for i, citation_card in enumerate(self.players[self.current_player].citation_cards):
                    card_width = 180
                    card_height = 270
                    if i >= len(self.citation_card_y_offsets):
                        offset = 0
                    else:
                        offset = self.citation_card_y_offsets[i]
                    card_x = SCREEN_WIDTH - CITATION_CARDS_COLUMN_WIDTH + (CITATION_CARDS_COLUMN_WIDTH - card_width) // 2
                    card_y = 150 + i * (card_height + 40) + offset
                    card_rect = pygame.Rect(card_x, card_y, card_width, card_height)
                    if card_rect.collidepoint(mouse_pos):
                        self.zoomed_card = citation_card
                        break
        if self.zoomed_card:
            zoom_image = pygame.transform.scale(
                self.zoomed_card.front_image if self.zoomed_card.flipped else self.zoomed_card.back_image,
                (600, 900)
            )
            zoom_rect = zoom_image.get_rect(center=(SCREEN_WIDTH // 2, SCREEN_HEIGHT // 2))
            self.screen.blit(zoom_image, zoom_rect.topleft)

    def draw_card_token_indicator(self, card):
        if card.token:
            INDICATOR_SIZE = 30
            PADDING = 10
            if card.token in self.TOKEN_IMAGES:
                token_image = self.TOKEN_IMAGES[card.token]
                token_image = pygame.transform.scale(token_image, (INDICATOR_SIZE, INDICATOR_SIZE))
                self.screen.blit(token_image, (card.rect.left + PADDING, card.rect.top + PADDING))
            else:
                pygame.draw.rect(self.screen, TOKEN_COLORS[card.token], (card.rect.left + PADDING, card.rect.top + PADDING, INDICATOR_SIZE, INDICATOR_SIZE))

    def highlight_environment_cards(self, possible_moves):
        for card in self.environment_cards:
            if card in possible_moves:
                pygame.draw.rect(self.screen, (0, 255, 0), card.rect, 5)
            else:
                pygame.draw.rect(self.screen, (255, 0, 0), card.rect, 5)

    def swap_citation_card(self, player):
        if not player.citation_cards:
            self.show_popup_message("No citation cards to swap.", choice=False)
            return
        old_card = random.choice(player.citation_cards)
        player.citation_cards.remove(old_card)
        if old_card.gatekept:
            old_card.gatekept = False
        citation_card_names = [
            'alchemists_almanac.png',
            'astral_symposia.png',
            'citehold_conundrum.png',
            'lunar_howls.png',
            'mandates_of_the_hive.png',
            'pixie_parlance.png',
            'sand_and_summit.png',
            'territorial_tenets.png',
            'council_of_the_realms.png',
            'manual_of_ambition.png',
            'the_inkblade_murders.png',
            'the_elders_codex.png',
            'scrolltube.png'
        ]
        new_card_name = random.choice(citation_card_names)
        cost = self.create_citation_card_costs(new_card_name)
        reward = self.get_citation_card_reward(new_card_name)
        new_card = CitationCard(new_card_name, new_card_name, cost, reward)
        player.citation_cards.append(new_card)
        self.show_popup_message(f"Swapped {old_card.name.replace('_',' ').replace('.png','').title()} for {new_card.name.replace('_',' ').replace('.png','').title()}.", choice=False)

    def draw_environment_card_hover_effects(self, card, mouse_pos):
        if card.rect.collidepoint(mouse_pos):
            glow_image = pygame.transform.scale(self.citesaga_glow, (card.rect.width, card.rect.height))
            self.screen.blit(glow_image, card.rect.topleft)

    def draw_environment_cards(self):
        for card in self.environment_cards:
            card_image = card.image.copy()
            card_image.set_alpha(255)
            self.draw_card_with_shadow(card_image, card.rect)
            self.draw_card_token_indicator(card)
            if card.occupied_by is not None:
                self.draw_player_on_card(card.occupied_by, card)
            if card.rect.collidepoint(self.get_mouse_pos()):
                glow_image = pygame.transform.scale(self.citesaga_glow, (card.rect.width, card.rect.height))
                self.screen.blit(glow_image, card.rect.topleft)

async def main():
    if sys.platform == "emscripten":
        import platform
        platform.document.documentElement.style.height = "100%"
        platform.document.body.style.height = "100%"
        platform.document.body.style.margin = "0"
        platform.document.body.style.padding = "0"
        platform.document.body.style.overflow = "hidden"
        platform.document.body.style.background = "#000000"
        platform.window.canvas.style.width = "100%"
        platform.window.canvas.style.height = "100%"

    game = Game()
    await game.run()

if __name__ == "__main__":
    asyncio.run(main())
