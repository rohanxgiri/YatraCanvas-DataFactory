"""Optional local artwork authoring; no APIs, no authentic place depictions.

Creates procedural category illustrations released under CC0 by the project.
Runtime only consumes the reviewed/check-in asset manifest.
"""
import hashlib
from pathlib import Path
from PIL import Image, ImageDraw
from datafactory.utils.atomic import atomic_json

ROOT = Path(__file__).resolve().parents[1] / "assets" / "fallbacks"
CATEGORIES = ["temple", "mosque", "church", "monastery", "ghat", "fort", "palace", "museum", "lake", "beach",
              "waterfall", "mountain", "viewpoint", "wildlife", "garden", "market", "sweets", "cafe", "restaurant",
              "shopping", "park", "nature", "heritage", "culture", "experience", "hotel", "transport"]


def draw_scene(category, variant):
    image = Image.new("RGB", (960, 600), (245-variant*2, 237-variant*3, 219+variant*2))
    d = ImageDraw.Draw(image)
    ink, accent = (37+variant*4, 77+variant*3, 82+variant*5), (192-variant*5, 114+variant*7, 66+variant*5)
    shift = variant * 12
    d.ellipse((730-shift, 70, 820-shift, 160), fill=accent)
    d.rounded_rectangle((70, 485, 890, 510), radius=12, fill=ink)
    if category in {"cafe", "restaurant", "sweets"}:
        if category == "cafe":
            d.rounded_rectangle((300+shift, 250, 590+shift, 465), 32, fill=ink)
            d.arc((510+shift, 255, 690+shift, 440), 260, 100, fill=ink, width=25)
            for x in (365, 435, 505):
                d.arc((x, 155, x+40, 230), 70+variant*10, 270, fill=accent, width=8)
        elif category == "restaurant":
            d.ellipse((275, 195, 665, 480), fill=ink)
            d.ellipse((305, 220, 635, 455), fill=accent)
            for x in (180, 740):
                d.line((x, 245, x, 455), fill=ink, width=14)
            for x in (160, 180, 200):
                d.line((x, 200, x, 280), fill=ink, width=7)
        else:
            for y in range(3):
                for x in range(4-y):
                    cx = 310+x*85+y*42+shift//2
                    d.ellipse((cx, 390-y*70, cx+70, 460-y*70), fill=accent if (x+y)%2 else ink)
    elif category in {"market", "shopping"}:
        d.rectangle((210+shift, 250, 685+shift, 470), fill=accent)
        d.polygon([(180+shift,250),(240+shift,170),(655+shift,170),(715+shift,250)], fill=ink)
        for x in range(250, 650, 90):
            d.rectangle((x+shift, 275, x+65+shift, 395), fill=ink)
    elif category in {"lake", "beach", "waterfall", "ghat"}:
        for y in range(310, 480, 35):
            d.arc((160-shift, y-80, 760+shift, y+80), 10, 170, fill=ink, width=12)
        if category == "waterfall":
            d.rectangle((390+shift, 160, 570+shift, 390), fill=accent)
        elif category == "ghat":
            for y in range(4):
                d.rectangle((170+y*40, 170+y*35, 500+y*40, 195+y*35), fill=accent)
        else:
            d.polygon([(100,300),(300+shift,160),(470,300)], fill=accent)
    elif category in {"mountain", "viewpoint", "nature", "park", "garden", "wildlife", "experience"}:
        if category in {"mountain", "viewpoint", "nature", "experience"}:
            d.polygon([(170,475),(425+shift,170),(670,475)], fill=ink)
            d.polygon([(445,475),(650-shift,250),(825,475)], fill=accent)
            d.polygon([(365+shift,240),(425+shift,170),(480+shift,240)], fill=(245,237,219))
        else:
            for x in (280, 450+shift, 660):
                d.rectangle((x,280,x+15,480),fill=ink)
                d.ellipse((x-65,170,x+85,345),fill=accent)
            if category == "wildlife":
                d.ellipse((350,385,590,465),fill=ink)
                d.ellipse((550,355,650,435),fill=ink)
    elif category == "transport":
        d.rounded_rectangle((235+shift, 225, 695+shift, 440), 30, fill=ink)
        for x in (285, 390, 495, 600):
            d.rectangle((x+shift, 260, x+60+shift, 325), fill=accent)
        for x in (310, 610):
            d.ellipse((x+shift,410,x+65+shift,475),fill=accent)
    else:
        d.rectangle((260+shift,285,685+shift,475),fill=ink)
        for x in (310,420,530,640):
            d.rounded_rectangle((x+shift,330,x+35+shift,470),12,fill=accent)
        if category == "temple":
            d.polygon([(350+shift,285),(465+shift,120),(580+shift,285)],fill=accent)
        elif category in {"mosque", "palace"}:
            d.pieslice((345+shift,135,600+shift,380),180,360,fill=accent)
        elif category in {"fort", "heritage"}:
            for x in range(260,686,80):
                d.rectangle((x+shift,240,x+40+shift,300),fill=accent)
        elif category == "church":
            d.rectangle((425+shift,145,500+shift,290),fill=accent)
            d.line((460+shift,115,460+shift,195),fill=ink,width=12)
            d.line((430+shift,145,490+shift,145),fill=ink,width=12)
        else:
            d.polygon([(220+shift,280),(475+shift,140),(725+shift,280)],fill=accent)
    return image


def main():
    assets = []
    for category in CATEGORIES:
        for variant in range(8):
            relative = f"{category}/{variant:02}.webp"
            path = ROOT / relative
            path.parent.mkdir(parents=True, exist_ok=True)
            draw_scene(category, variant).save(path, "WEBP", quality=88)
            assets.append({"id": f"contextual-{category}-{variant:02}", "category": category, "path": relative,
                "image_type": "fallback", "creator": "YatraCanvas contributors", "license": "CC0",
                "license_url": "https://creativecommons.org/publicdomain/zero/1.0/",
                "source_url": "https://creativecommons.org/publicdomain/zero/1.0/",
                "attribution": "YatraCanvas contextual illustration; generic artwork, not a photograph of this place",
                "sha256": hashlib.sha256(path.read_bytes()).hexdigest()})
    atomic_json(ROOT / "manifest.json", {"version": 1, "artwork_method": "local procedural illustration", "assets": assets})
    print(f"Authored {len(assets)} CC0 contextual illustrations in {len(CATEGORIES)} categories")


if __name__ == "__main__":
    main()
