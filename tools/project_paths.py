"""Locations for optional development tools; override through environment variables."""
import os
from pathlib import Path
GAME_DIR = Path(os.environ.get('DIVA_GAME_DIR', r'C:\Program Files (x86)\Steam\steamapps\common\Hatsune Miku Project DIVA Mega Mix Plus'))
MOD_DIR = Path(os.environ.get('DIVA_MOD_DIR', str(GAME_DIR / 'mods/Diva Room')))
MIKUMIKUMODEL_DIR = Path(os.environ.get('MIKUMIKUMODEL_DIR', str(Path.home() / 'Downloads/MikuMikuModel')))
ROOM_SOURCE_DIR = Path(os.environ.get('DIVA_ROOM_SOURCE_DIR', str(MOD_DIR / '3dmodels/divaroom')))
