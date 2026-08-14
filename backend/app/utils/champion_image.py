"""
Utility: lấy URL ảnh champion từ Riot Data Dragon
Thay thế static files local bằng CDN của Riot
"""
import json
from pathlib import Path
from functools import lru_cache

PATCH_VERSION = "16.13.1"
BACKEND_DIR = Path(__file__).resolve().parents[2]
KEYS_PATH = BACKEND_DIR / "data" / "riot_champion_keys.json"


@lru_cache(maxsize=1)
def _load_keys() -> dict:
    with open(KEYS_PATH, encoding="utf-8") as f:
        return json.load(f)


def get_champion_image_url(champion_name: str) -> str:
    """
    Trả về URL ảnh champion từ Riot Data Dragon.
    Fallback về placeholder nếu không tìm được key.
    
    Ví dụ:
        "Azir" → https://ddragon.../Azir.png
        "Rek'Sai" → https://ddragon.../RekSai.png
    """
    keys = _load_keys()
    riot_key = keys.get(champion_name)
    if not riot_key:
        # Thử normalize: bỏ space, apostrophe, &
        normalized = (champion_name
                      .replace("'", "")
                      .replace(" ", "")
                      .replace("&", "")
                      .replace(".", ""))
        riot_key = normalized or champion_name
    
    return (
        f"https://ddragon.leagueoflegends.com/cdn/"
        f"{PATCH_VERSION}/img/champion/{riot_key}.png"
    )