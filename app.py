# ============================
# APP.PY - The Backwoods
# ============================

import sys
import time
import random
import os
import json

SAVE_DIR = "saves"

# ==== Imports: Areas & Animals ====
from map import areas
from animals import (
    camp_animals,
    forest_animals,
    highlands_animals,
    jungle_animals,
    boss,
)

# ==== Constants & Gameplay Flags ====
FLYING_ENEMIES = {"Sparrow", "Hawk", "Eagle"}  # used by Bow special
BOW_ENEMY_ATK_REDUCTION = 1

# ==== Player State (INIT BEFORE ANY FUNCTION USES THEM) ====
xp = 0
upgrade_amt = 110
hp = 60
max_hp = 60
att = 6
lv = 1
alive = True

# ==== Upgrade Path Tracking ====
strength_level = 0
endurance_level = 0
survival_level = 0
crit_chance = 0  # percent

# ==== World State ====
current_area_index = 0  # starts at Camp
current_weapon = "Fists"
adrenaline_active = False

# ==== DEV MODE FLAG ====
devmode_active = False

# ==== Inventory (Weapons / Items / Resources) ====
weapons_inventory = {"Fists": {"name": "Fists", "bonus": 0}}  # name → {name, bonus}
bag = {}  # name → count (Items + Resources; UI splits them)

# Categories used for Inventory UI
ITEM_NAMES = {"Fruit", "Food", "Medkit", "Bandage", "Adrenaline Shot"}
RESOURCE_NAMES = {"Wood", "Stone", "Rope", "Fur", "Bones", "Scales", "Meat"}

# ==== Weapons: Craftable & Findable (stats & availability) ====
# Craftable basics:
CRAFT_WEAPONS_BASIC = [
    {"name": "Wooden Sword", "bonus": 2, "cost": {"Wood": 3}},
    {"name": "Spear",        "bonus": 3, "cost": {"Wood": 2, "Bones": 1}},
]
# Requires Workbench to appear in crafting:
CRAFT_WEAPONS_ADV = [
    {"name": "Bone Spear",   "bonus": 4, "cost": {"Bones": 2, "Rope": 1, "Wood": 2}},
]
# Armor (Workbench unlocks these in crafting under Weapons section)
CRAFT_ARMOR_ADV = [
    {"name": "Scale Armor",  "hp_bonus": 10, "cost": {"Scales": 2, "Rope": 2}},
    {"name": "Fur Cloak",    "hp_bonus": 5,  "cost": {"Fur": 3, "Rope": 1}},
]
# Find-only weapons by area:
FINDABLE_WEAPONS = {
    "Dagger":      {"bonus": 3, "areas": {"Camp", "Forest", "Highlands", "Jungle"}},
    "Rusty Sword": {"bonus": 4, "areas": {"Forest", "Highlands", "Jungle"}},
    "Bow":         {"bonus": 3, "areas": {"Forest", "Highlands", "Jungle"}},  # -1 enemy atk vs non-flying
    "Axe":         {"bonus": 5, "areas": {"Jungle"}},  # Jungle-only
}

# ==== Buildings & Trap Logic ====
buildings = {}  # e.g., {"Campfire": 1, "Trap": 2, "Advanced Trap": 1, "Workbench": 1}
MAX_TRAPS_TOTAL = 4        # normal + advanced combined
NTCC = 0.20                # Normal Trap Catch Chance
ATCC = 0.35                # Advanced Trap Catch Chance

# ==== Resource Distribution (by Area) ====
RESOURCE_TABLE = {
    "Camp": [
        ("Wood",   0.35),
        ("Stone",  0.20),
        ("Rope",   0.15),
        ("Bones",  0.00),
        ("Scales", 0.00),
        ("Fruit",  0.25),
        ("Nothing",0.05),
    ],
    "Forest": [
        ("Wood",   0.40),
        ("Stone",  0.20),
        ("Rope",   0.25),
        ("Bones",  0.15),
        ("Scales", 0.00),
        ("Fruit",  0.20),
        ("Nothing",0.05),
    ],
    "Highlands": [
        ("Wood",   0.30),
        ("Stone",  0.35),
        ("Rope",   0.25),
        ("Bones",  0.05),
        ("Scales", 0.20),
        ("Fruit",  0.15),
        ("Nothing",0.05),
    ],
    "Jungle": [
        ("Wood",   0.40),
        ("Stone",  0.20),
        ("Rope",   0.20),
        ("Bones",  0.35),
        ("Scales", 0.35),
        ("Fruit",  0.10),
        ("Nothing",0.05),
    ],
}

# ===============================================
#                    Helpers
# ===============================================
def add_to_bag(name: str, count: int = 1):
    """Add items/resources to the bag."""
    bag[name] = bag.get(name, 0) + max(1, count)

def remove_from_bag(req: dict):
    """Consume a dict of resources from the bag."""
    for k, v in req.items():
        if k in bag:
            bag[k] -= v
            if bag[k] <= 0:
                del bag[k]

def have_in_bag(req: dict) -> bool:
    """Check if the bag contains at least 'req' amounts for each resource."""
    return all(bag.get(k, 0) >= v for k, v in req.items())

def total_attack():
    """Player base attack plus current weapon bonus."""
    return att + weapons_inventory[current_weapon]["bonus"]

def get_current_area_name():
    return areas[current_area_index]["name"]

def weighted_choice(pairs):
    """Choose one key based on weights; pairs = [(key, weight), ...]. Works with any total sum."""
    total = sum(w for _, w in pairs)
    if total <= 0:
        return pairs[-1][0]
    r = random.random() * total
    acc = 0.0
    for key, w in pairs:
        acc += w
        if r < acc:
            return key
    return pairs[-1][0]  # fallback

def is_trap_cap_reached():
    return buildings.get("Trap", 0) + buildings.get("Advanced Trap", 0) >= MAX_TRAPS_TOTAL

def normalize_resource_name(name: str) -> str:
    """Normalize singular names from animals into our bag naming."""
    if name == "Bone":  return "Bones"
    if name == "Scale": return "Scales"
    return name

def show_missing_materials(cost):
    """Print a clear 'you need/have' breakdown for crafting."""
    print("Required:")
    for k, v in cost.items():
        have = bag.get(k, 0)
        print(f" - {k}: {have}/{v}")

def type_text(line, char_delay=0.15, end="\n"):
    """Types text one character at a time."""
    for ch in line:
        print(ch, end="", flush=True)
        time.sleep(char_delay)
    print(end, end="", flush=True)

def boss_cinematic():
    cinematic_lines = [
        "The ground trembles beneath your feet...",
        "Somewhere in the darkness, gears begin to turn.",
        "A low drone builds, pulsing like the heartbeat of a sleeping giant...",
        "The iron doors shudder.",
        "A presence stirs beyond the gate—older than memory, forged of metal and will...",
    ]

    for line in cinematic_lines:
        type_text(line)
        if "..." in line:
            time.sleep(0.5)
        else:
            time.sleep(0.3)

    # Boss name reveal slowly on one line
    boss_name = "THE RUINED TITAN"
    print("\n", end="")
    for ch in boss_name:
        print(ch, end="", flush=True)
        time.sleep(0.3)
    print("\n")

    time.sleep(1)
    print("\n" * 20)
    print("...", flush=True)
    time.sleep(1)

def get_strong_animal(area_name):
    """Strong animal used by Search (no XP)."""
    if area_name == "Camp":
        return {"name": "Wolf", "hp": 25, "attack": 5, "xp_reward": 0}
    elif area_name == "Forest":
        return {"name": "Wild Ape", "hp": 50, "attack": 9, "xp_reward": 0}
    elif area_name == "Highlands":
        return {"name": "Crocodile", "hp": 60, "attack": 12, "xp_reward": 0}
    elif area_name == "Jungle":
        return {"name": "Crocodile", "hp": 60, "attack": 12, "xp_reward": 0}
    else:
        return {"name": "Wolf", "hp": 25, "attack": 5, "xp_reward": 0}

def game_end_sequence(enemy_name):
    print("\n===================================")
    time.sleep(0.5)
    print(f"🏆 {enemy_name} collapses in a storm of fire and shrapnel...")
    time.sleep(1)
    print("The earth falls silent. The mechanical threat has been destroyed.")
    time.sleep(1)
    print("You have survived The Backwoods.")
    time.sleep(1.5)
    print("\n*** CONGRATULATIONS! YOU BEAT THE GAME ***\n")
    time.sleep(1)

    while True:
        choice = input("[1] Return to Main Menu\n[2] Quit Game\n> ").strip()
        if choice == "1":
            start_menu()
            return
        elif choice == "2":
            print("Thank you for playing The Backwoods!")
            sys.exit(0)
        else:
            print("Invalid input. Please choose 1 or 2.")


# ===============================================
# UI: Stats, Map, Inventory (Weapons / Items / Resources)
# ===============================================
def stats():
    print("==== Your Stats ====")
    print(f"HP: {hp}/{max_hp}")
    print(f"XP: {xp}/{int(upgrade_amt)}")
    print(f"Attack: {total_attack()}")
    print(f"Weapon: {current_weapon}")
    print(f"Level: {lv}")
    print(f"Current Area: {get_current_area_name()}")
    print("====================")

def show_map():
    print("\n===== MAP =====")
    for i, area in enumerate(areas):
        marker = "<== You are here" if i == current_area_index else ""
        print(f"{area['name']} {marker}")
        if i < len(areas) - 1:
            print("  |")
    print("================\n")

def show_inventory():
    """Inventory UI split into Weapons, Items, Resources."""
    global current_weapon

    print("\n===== INVENTORY =====")

    # Weapons
    print("\n-- Weapons --")
    wlist = list(weapons_inventory.values())
    for idx, w in enumerate(wlist, start=1):
        t_atk = att + w["bonus"]
        mark = " (Equipped)" if w["name"] == current_weapon else ""
        print(f"[{idx}] {w['name']} - Attack: {t_atk}{mark}")

    # Items
    print("\n-- Items --")
    any_items = False
    for name in sorted(ITEM_NAMES):
        if bag.get(name, 0) > 0:
            any_items = True
            print(f"{name} x{bag[name]}")
    if not any_items:
        print("No items.")

    # Resources
    print("\n-- Resources --")
    any_res = False
    for name in sorted(RESOURCE_NAMES):
        if bag.get(name, 0) > 0:
            any_res = True
            print(f"{name} x{bag[name]}")
    if not any_res:
        print("No resources.")

    print("=====================")

    # Equip or use prompt
    choice = input("Select a weapon number to equip, type 'use' to use an item, or press Enter to go back:\n> ").strip().lower()
    # Dev commands usable here
    if dev_command_handler(choice):
        return

    if choice == "":
        return
    if choice == "use":
        use_item()
        return
    if choice.isdigit():
        num = int(choice)
        if 1 <= num <= len(wlist):
            selected = wlist[num - 1]["name"]
            if selected == current_weapon:
                print(f"{selected} is already equipped.")
            else:
                current_weapon = selected
                print(f"You equipped the {current_weapon}.")
        else:
            print("Invalid choice.")
    else:
        print("Invalid input.")

# ===============================================
# Items: Healing & Buffs
# ===============================================
def use_item():
    """Use a healing/buff item from Items section."""
    global hp, adrenaline_active

    owned = [name for name in ITEM_NAMES if bag.get(name, 0) > 0]
    if not owned:
        print("You have no items to use.")
        return

    print("\n-- Usable Items --")
    for i, nm in enumerate(owned, start=1):
        print(f"[{i}] {nm}")
    sel = input("> ").strip()

    # Dev commands usable here
    if dev_command_handler(sel):
        return

    if not sel.isdigit() or not (1 <= int(sel) <= len(owned)):
        print("Invalid choice.")
        return

    item_name = owned[int(sel) - 1]

    if item_name == "Fruit":
        healed = min(max_hp - hp, 10)
        hp += healed
        print(f"You eat Fruit and heal {healed} HP.")
    elif item_name == "Food":
        healed = min(max_hp - hp, 15)
        hp += healed
        print(f"You eat Food and heal {healed} HP.")
    elif item_name == "Medkit":
        healed = min(max_hp - hp, 25)
        hp += healed
        print(f"You use a Medkit and heal {healed} HP.")
    elif item_name == "Bandage":
        healed = min(max_hp - hp, 10)
        hp += healed
        print(f"You use a Bandage and heal {healed} HP.")
    elif item_name == "Adrenaline Shot":
        adrenaline_active = True
        print("You used an Adrenaline Shot! You feel stronger for your next fight.")
    else:
        print("That item cannot be used.")
        return

    bag[item_name] -= 1
    if bag[item_name] <= 0:
        del bag[item_name]

# ===============================================
# Save/Load Helpers
# ===============================================
def ensure_save_dir():
    if not os.path.isdir(SAVE_DIR):
        os.makedirs(SAVE_DIR, exist_ok=True)

def serialize_state():
    """Return a JSON-serializable snapshot of the full game state."""
    return {
        "xp": xp,
        "upgrade_amt": upgrade_amt,
        "hp": hp,
        "max_hp": max_hp,
        "att": att,
        "lv": lv,
        "alive": alive,
        "current_area_index": current_area_index,
        "current_weapon": current_weapon,
        "adrenaline_active": adrenaline_active,
        "weapons_inventory": weapons_inventory,
        "bag": bag,
        "buildings": buildings,
    }

def apply_state(state):
    """Load a snapshot back into globals."""
    global xp, upgrade_amt, hp, max_hp, att, lv, alive
    global current_area_index, current_weapon, adrenaline_active
    global weapons_inventory, bag, buildings

    xp = state.get("xp", 0)
    upgrade_amt = state.get("upgrade_amt", 110)
    hp = state.get("hp", 60)
    max_hp = state.get("max_hp", 60)
    att = state.get("att", 6)
    lv = state.get("lv", 1)
    alive = state.get("alive", True)
    current_area_index = state.get("current_area_index", 0)
    current_weapon = state.get("current_weapon", "Fists")
    adrenaline_active = state.get("adrenaline_active", False)
    weapons_inventory = state.get("weapons_inventory", {"Fists": {"name": "Fists", "bonus": 0}})
    bag = state.get("bag", {})
    buildings = state.get("buildings", {})

def list_saves():
    """Return a sorted list of save filenames (without .json)."""
    ensure_save_dir()
    files = []
    for fn in os.listdir(SAVE_DIR):
        if fn.lower().endswith(".json"):
            files.append(fn[:-5])
    return sorted(files, key=str.lower)

def save_game():
    """Manual save. Player can overwrite existing saves or create a new one."""
    if devmode_active:
        print("❌ Cannot save in Developer Mode.")
        return

    ensure_save_dir()
    saves = list_saves()

    print("\n===== SAVE GAME =====")
    if saves:
        print("Select a save to overwrite, or choose a new slot:")
        for i, name in enumerate(saves, start=1):
            print(f"[{i}] Overwrite '{name}'")
        print("[0] Create New Save")
    else:
        print("No existing saves. Create your first save:")
        print("[0] New Save Only")

    choice = input("> ").strip()
    if choice == "0":
        name = input("Enter new save name:\n> ").strip()
        if not name:
            print("Save cancelled.")
            return
        safe = "".join(ch for ch in name if ch.isalnum() or ch in "-_")
        if not safe:
            print("Invalid name. Must use letters, numbers, '-' or '_'.")
            return
        path = os.path.join(SAVE_DIR, f"{safe}.json")

        if os.path.exists(path):
            confirm = input(f"A save named '{safe}' already exists. Overwrite? (y/n)\n> ").strip().lower()
            if confirm != "y":
                print("Save cancelled.")
                return

        try:
            with open(path, "w", encoding="utf-8") as f:
                json.dump(serialize_state(), f, indent=2)
            print(f"✅ Game saved successfully as '{safe}.json'.")
        except Exception as e:
            print(f"❌ Failed to save: {e}")
        return

    if choice.isdigit() and 1 <= int(choice) <= len(saves):
        selected = saves[int(choice) - 1]
        path = os.path.join(SAVE_DIR, f"{selected}.json")
        confirm = input(f"Overwrite existing save '{selected}'? (y/n)\n> ").strip().lower()
        if confirm != "y":
            print("Save cancelled.")
            return
        try:
            with open(path, "w", encoding="utf-8") as f:
                json.dump(serialize_state(), f, indent=2)
            print(f"✅ Game saved successfully as '{selected}.json'.")
        except Exception as e:
            print(f"❌ Failed to save: {e}")
    else:
        print("Invalid choice.")

def load_game_from_slot():
    """Allows player to pick a save file to load."""
    saves = list_saves()
    if not saves:
        print("No save files found.")
        return False

    print("\n===== LOAD GAME =====")
    for i, name in enumerate(saves, start=1):
        print(f"[{i}] {name}")
    print("[0] Back")

    choice = input("> ").strip()
    if choice == "0":
        return False
    if not choice.isdigit() or not (1 <= int(choice) <= len(saves)):
        print("Invalid choice.")
        return False

    selected = saves[int(choice) - 1]
    path = os.path.join(SAVE_DIR, f"{selected}.json")

    try:
        with open(path, "r", encoding="utf-8") as f:
            state = json.load(f)
        apply_state(state)
        print(f"✅ Loaded save '{selected}'.")
        return True
    except Exception as e:
        print(f"❌ Failed to load save: {e}")
        return False

def delete_save_slot():
    """Allows the player to delete an existing save file."""
    saves = list_saves()
    if not saves:
        print("No save files to delete.")
        return

    print("\n===== DELETE SAVE =====")
    for i, name in enumerate(saves, start=1):
        print(f"[{i}] {name}")
    print("[0] Back")

    choice = input("> ").strip()
    if choice == "0":
        return
    if not choice.isdigit() or not (1 <= int(choice) <= len(saves)):
        print("Invalid choice.")
        return

    selected = saves[int(choice) - 1]
    path = os.path.join(SAVE_DIR, f"{selected}.json")

    confirm = input(f"Are you sure you want to delete '{selected}'? (y/n)\n> ").strip().lower()
    if confirm == "y":
        try:
            os.remove(path)
            print(f"✅ Save '{selected}' deleted.")
        except Exception as e:
            print(f"❌ Failed to delete save: {e}")
    else:
        print("Delete cancelled.")

# ===============================================
# Dev Command Handler (usable at ANY prompt while devmode_active)
# ===============================================
def dev_command_handler(user_input):
    """
    Intercepts developer commands when devmode_active == True.
    Returns True if a dev command was handled (so caller should skip normal flow),
    False otherwise (caller should continue normal handling).
    """
    global hp, max_hp, att, xp, lv, crit_chance
    global current_area_index, strength_level, endurance_level, survival_level
    global devmode_active, bag, weapons_inventory, alive

    # Normalize
    if not isinstance(user_input, str):
        return False
    cmd = user_input.strip().lower()
    if cmd == "":
        return False

    # Allow showing the command list even if devmode is OFF (so you know how to enable it)
    if cmd in ("cmnd", "help", "commands"):
        print("""
Available Dev Commands:
hp <value>                   - Set player health
xp <value>                   - Set player XP
area <name>                  - Teleport to area (camp, forest, highlands, jungle, city)
give.resource <name> <amt>   - Add resource to inventory (e.g., give.resource wood 20)
give.weapon <name>           - Add weapon to inventory (e.g., give.weapon dagger)
strength <1-3>               - Set Strength upgrade path level
endurance <1-3>              - Set Endurance upgrade path level
survival <1-3>               - Set Survival upgrade path level
boss                         - Trigger final boss encounter (city_boss_encounter)
godmode on/off               - Toggle invincibility (hp/max_hp 9999 or reset)
exit                         - Exit developer mode and return to main menu
cmnd                         - Show this list of developer commands
""")
        if not devmode_active:
            print("⚠ Dev mode is OFF. From the MAIN MENU, type:  devmode kyusuf1001")
        return True

    # All other commands require devmode ON
    if not devmode_active:
        return False

    # Special: leave devmode
    if cmd == "exit":
        print("\nExiting Developer Mode... Returning to Main Menu.")
        devmode_active = False
        start_menu()
        return True

    # Quick single-word commands
    if cmd == "boss":
        print("⚠ [DEV] Spawning Boss NOW")
        city_boss_encounter()
        return True
    if cmd in ("godmode on", "godmode 1"):
        alive = True
        hp = 9999
        max_hp = 9999
        print("[DEV] Godmode ON (HP set to 9999).")
        return True
    if cmd in ("godmode off", "godmode 0"):
        alive = True
        hp = 60
        max_hp = 60
        print("[DEV] Godmode OFF (HP reset to 60).")
        return True

    # Tokenize generic forms like "hp 200", "give.resource wood 20"
    parts = cmd.replace("=", " ").replace(".", " ").split()
    if not parts:
        return False

    try:
        key = parts[0]

        # hp <value>
        if key == "hp" and len(parts) >= 2:
            val = int(parts[1])
            hp = val
            if hp > max_hp:
                max_hp = hp
            print(f"[DEV] HP set to {hp}/{max_hp}")
            return True

        # xp <value>
        if key == "xp" and len(parts) >= 2:
            val = int(parts[1])
            xp = val
            print(f"[DEV] XP set to {xp}")
            return True

        # area <name>
        if key == "area" and len(parts) >= 2:
            area_name = parts[1]
            # match against areas list by lowercase
            for i, a in enumerate(areas):
                if a["name"].lower() == area_name.lower():
                    current_area_index = i
                    print(f"[DEV] Teleported to area: {a['name']}")
                    return True
            print("[DEV] Invalid area name. Try: camp, forest, highlands, jungle, city.")
            return True

        # give.resource <name> <amt>
        if key == "give" and len(parts) >= 3 and parts[1] == "resource":
            if len(parts) < 4:
                print("[DEV] Usage: give.resource <name> <amt>")
                return True
            item = parts[2].capitalize()
            amt = int(parts[3])
            bag[item] = bag.get(item, 0) + amt
            print(f"[DEV] Gave resource: {item} x{amt}")
            return True

        # give.weapon <name>
        if key == "give" and len(parts) >= 3 and parts[1] == "weapon":
            # Accept multi-word weapon names too (e.g., rusty sword)
            wname = " ".join(parts[2:]).title()
            # Default bonus if not in FINDABLE_WEAPONS
            default_bonus = 3
            bonus = FINDABLE_WEAPONS.get(wname, {}).get("bonus", default_bonus)
            weapons_inventory[wname] = {"name": wname, "bonus": bonus}
            print(f"[DEV] Weapon unlocked: {wname} (+{bonus} Attack)")
            return True

        # strength|endurance|survival <1-3>
        if key in ("strength", "endurance", "survival") and len(parts) >= 2:
            lvl_value = max(1, min(3, int(parts[1])))
            if key == "strength":
                # remove previous stat deltas then apply fresh (simple approach: just add)
                globals()["strength_level"] = lvl_value
                globals()["crit_chance"] = [0, 10, 15, 20][lvl_value]
                # ensure attack reflects tier (each level +2)
                # We won't subtract old bonuses; this is a dev shortcut. If needed, track base_att.
                att_bonus = 2  # per tier
                # Optionally you can normalize ATT to base first; for now, just add up to level once:
                # a simple guard: if att seems too low for level, bump it:
                min_expected_att = 6 + (2 * lvl_value)
                if att < min_expected_att:
                    att = min_expected_att
                print(f"[DEV] Strength set to {lvl_value} (crit {crit_chance}%). ATT now {att}")
            elif key == "endurance":
                globals()["endurance_level"] = lvl_value
                # normalize HP to a reasonable baseline for dev
                base_hp = 60
                bonus = 6 if lvl_value == 1 else 14 if lvl_value == 2 else 26  # 6 / (6+8) / (6+8+12)
                max_hp = base_hp + bonus
                hp = max_hp
                if lvl_value == 3:
                    bag["Medkit"] = bag.get("Medkit", 0) + 2
                print(f"[DEV] Endurance set to {lvl_value} (Max HP {max_hp}).")
            elif key == "survival":
                globals()["survival_level"] = lvl_value
                print(f"[DEV] Survival set to {lvl_value}.")
            return True

    except Exception as e:
        print(f"[DEV ERROR] {e}")
        return True  # handled (with error message)

    # Not a dev command
    return False


# ===============================================
# Trap Logic (manual & passive)
# ===============================================
def check_traps_now():
    global bag

    if buildings.get("Trap", 0) == 0 and buildings.get("Advanced Trap", 0) == 0:
        print("You have no traps to check.")
        return

    print("\n=== Checking Traps ===")
    normal_traps = buildings.get("Trap", 0)
    adv_traps = buildings.get("Advanced Trap", 0)

    # Effective trap catch chances (Survival III bonus)
    eff_NTCC = NTCC + (0.10 if survival_level >= 3 else 0.0)
    eff_ATCC = ATCC + (0.10 if survival_level >= 3 else 0.0)

    caught_anything = False

    # Normal Traps: Meat 1–2 and Fur 1–2
    for _ in range(normal_traps):
        if random.random() < eff_NTCC:
            caught_anything = True
            meat_qty = random.randint(1, 2)
            fur_qty = random.randint(1, 2)
            add_to_bag("Meat", meat_qty)
            add_to_bag("Fur", fur_qty)
            print(f"Normal Trap caught something! +Meat x{meat_qty}, +Fur x{fur_qty}")
        else:
            print("Normal Trap was empty.")

    # Advanced Traps: pick 3 distinct among Meat/Fur/Bones/Scales, each 1–2
    for _ in range(adv_traps):
        if random.random() < eff_ATCC:
            caught_anything = True
            possible = ["Meat", "Fur", "Bones", "Scales"]
            chosen = random.sample(possible, 3)
            for item in chosen:
                qty = random.randint(1, 2)
                add_to_bag(item, qty)
                print(f"🧩 Advanced Trap captured {item} x{qty}")
        else:
            print("Advanced Trap was empty.")

    if not caught_anything:
        print("\nYour traps caught nothing this time.")
    else:
        print("\n✅ Trap check complete. Resources added to your inventory.")

def passive_trap_catches():
    """Called after explore() — silent background catches with small prints."""
    global bag

    normal_traps = buildings.get("Trap", 0)
    adv_traps = buildings.get("Advanced Trap", 0)

    if normal_traps == 0 and adv_traps == 0:
        return

    eff_NTCC = NTCC + (0.10 if survival_level >= 3 else 0.0)
    eff_ATCC = ATCC + (0.10 if survival_level >= 3 else 0.0)

    # Normal traps
    for _ in range(normal_traps):
        if random.random() < eff_NTCC:
            meat_qty = random.randint(1, 2)
            fur_qty = random.randint(1, 2)
            add_to_bag("Meat", meat_qty)
            add_to_bag("Fur", fur_qty)
            print(f"🔔 (Passive Trap) Gained Meat x{meat_qty}, Fur x{fur_qty}")

    # Advanced traps
    for _ in range(adv_traps):
        if random.random() < eff_ATCC:
            possible = ["Meat", "Fur", "Bones", "Scales"]
            chosen = random.sample(possible, 3)
            for item in chosen:
                qty = random.randint(1, 2)
                add_to_bag(item, qty)
                print(f"⚙️ (Passive Adv Trap) Gained {item} x{qty}")

# ===============================================
# Crafting System
# ===============================================
def craft():
    """Crafting menu. Workbench unlocks advanced recipes automatically."""
    while True:
        print('''
===== CRAFT =====
[1] Weapons
[2] Traps
[3] Campfire
[4] Workbench
[5] Back
''')
        c = input("Choose an option:\n> ").strip()

        # Dev commands allowed from here if devmode_active:
        if dev_command_handler(c):
            continue

        if c == "1":
            craft_weapons_and_armor()
        elif c == "2":
            craft_traps()
        elif c == "3":
            craft_campfire()
        elif c == "4":
            craft_workbench()
        elif c == "5":
            return
        else:
            print("Invalid option.")

def craft_weapons_and_armor():
    """Weapons (basic + advanced if Workbench) and Armor (if Workbench)."""
    have_workbench = buildings.get("Workbench", 0) > 0

    entries = []
    # Basic weapons always available
    for r in CRAFT_WEAPONS_BASIC:
        entries.append(("weapon", r))
    # Advanced appear if Workbench present, plus armor
    if have_workbench:
        for r in CRAFT_WEAPONS_ADV:
            entries.append(("weapon", r))
        for r in CRAFT_ARMOR_ADV:
            entries.append(("armor", r))

    print("\n-- Craft: Weapons" + (" & Armor" if have_workbench else "") + " --")
    for idx, (kind, rec) in enumerate(entries, start=1):
        label = f"{rec['name']} (+{rec['bonus']} Attack)" if kind == "weapon" else f"{rec['name']} (+{rec['hp_bonus']} Max HP)"
        cost_str = ", ".join([f"{k} x{v}" for k, v in rec["cost"].items()])
        print(f"[{idx}] {label}  |  Cost: {cost_str}")
    print("[0] Back")

    sel = input("> ").strip()
    if dev_command_handler(sel):
        return
    if sel == "0":
        return
    if not sel.isdigit() or not (1 <= int(sel) <= len(entries)):
        print("Invalid choice.")
        return

    kind, rec = entries[int(sel) - 1]
    if not have_in_bag(rec["cost"]):
        print("❌ You do not have enough materials.")
        show_missing_materials(rec["cost"])
        return

    remove_from_bag(rec["cost"])

    if kind == "weapon":
        if rec["name"] in weapons_inventory:
            print("You already own that weapon.")
            return
        weapons_inventory[rec["name"]] = {"name": rec["name"], "bonus": rec["bonus"]}
        print(f"✅ You crafted {rec['name']}.")
    else:
        global max_hp, hp
        max_hp += rec["hp_bonus"]
        hp = max_hp
        print(f"✅ You crafted {rec['name']}. Max HP increased by {rec['hp_bonus']}.")

def craft_traps():
    """Craft normal or advanced traps. Enforces global max 4, with auto-replace rule."""
    have_workbench = buildings.get("Workbench", 0) > 0
    print("\n-- Craft: Traps --")
    print("[1] Trap            | Cost: Wood x2, Rope x1")
    if have_workbench:
        print("[2] Advanced Trap   | Cost: Wood x3, Rope x2, Bones x1")
    print("[0] Back")
    sel = input("> ").strip()

    if dev_command_handler(sel):
        return

    if sel == "0":
        return
    if sel == "1":
        craft_trap_normal()
    elif sel == "2" and have_workbench:
        craft_trap_advanced()
    else:
        print("Invalid choice.")

def craft_trap_normal():
    cost = {"Wood": 2, "Rope": 1}
    if is_trap_cap_reached():
        print("You cannot build more traps (limit reached).")
        return
    if not have_in_bag(cost):
        print("❌ You do not have enough materials.")
        show_missing_materials(cost)
        return
    remove_from_bag(cost)
    buildings["Trap"] = buildings.get("Trap", 0) + 1
    print("✅ You built a Trap.")

def craft_trap_advanced():
    """Advanced Trap: if cap is full and a normal trap exists, replace one normal."""
    cost = {"Wood": 3, "Rope": 2, "Bones": 1}
    total = buildings.get("Trap", 0) + buildings.get("Advanced Trap", 0)

    if not have_in_bag(cost):
        print("❌ You do not have enough materials.")
        show_missing_materials(cost)
        return

    if total < MAX_TRAPS_TOTAL:
        remove_from_bag(cost)
        buildings["Advanced Trap"] = buildings.get("Advanced Trap", 0) + 1
        print("✅ You built an Advanced Trap.")
        return

    if buildings.get("Trap", 0) > 0:
        remove_from_bag(cost)
        buildings["Trap"] -= 1
        if buildings["Trap"] <= 0:
            del buildings["Trap"]
        buildings["Advanced Trap"] = buildings.get("Advanced Trap", 0) + 1
        print("✅ You built an Advanced Trap. One normal trap was replaced.")
    else:
        print("All your traps are already advanced. You cannot build more.")

def craft_campfire():
    cost = {"Wood": 3, "Stone": 1}
    print("\n=== Craft Campfire ===")
    print("Cost:", ", ".join([f"{k} x{v}" for k, v in cost.items()]))
    confirm = input("Craft Campfire? (y/n)\n> ").strip().lower()
    if confirm != "y":
        print("Cancelled.")
        return
    if not have_in_bag(cost):
        print("❌ You do not have enough materials.")
        show_missing_materials(cost)
        return
    remove_from_bag(cost)
    buildings["Campfire"] = buildings.get("Campfire", 0) + 1
    print("✅ You built a Campfire. You can cook 5 Meat → 1 Food in Buildings.")

def craft_workbench():
    cost = {"Wood": 4, "Stone": 2, "Rope": 2}
    print("\n=== Craft Workbench ===")
    print("Cost:", ", ".join([f"{k} x{v}" for k, v in cost.items()]))
    confirm = input("Craft Workbench? (y/n)\n> ").strip().lower()
    if confirm != "y":
        print("Cancelled.")
        return
    if buildings.get("Workbench", 0) > 0:
        print("You already have a Workbench.")
        return
    if not have_in_bag(cost):
        print("❌ You do not have enough materials.")
        show_missing_materials(cost)
        return
    remove_from_bag(cost)
    buildings["Workbench"] = 1
    print("✅ You built a Workbench. Advanced crafting is now available.")

def use_campfire():
    if buildings.get("Campfire", 0) <= 0:
        print("You don't have a Campfire.")
        return
    if bag.get("Meat", 0) >= 5:
        bag["Meat"] -= 5
        if bag["Meat"] == 0:
            del bag["Meat"]
        add_to_bag("Food", 1)
        print("You cooked 5 Meat into 1 Food.")
    else:
        print("Not enough Meat to cook (need 5).")

# ===============================================
# Findable Weapons
# ===============================================
def get_allowed_findable_weapons(area_name: str):
    allowed = []
    for wname, data in FINDABLE_WEAPONS.items():
        if area_name in data["areas"]:
            allowed.append(wname)
    return allowed

def maybe_find_weapon(area_name: str):
    """25% branch: try to find a weapon appropriate for this area."""
    allowed = get_allowed_findable_weapons(area_name)
    if not allowed:
        print("You find some old debris, but no usable weapons.")
        return

    # Weight rarities (Axe rare)
    weights = []
    for name in allowed:
        if name == "Axe":
            weights.append(1)
        elif name in {"Rusty Sword", "Bow"}:
            weights.append(3)
        else:  # Dagger common
            weights.append(5)

    total = sum(weights)
    r = random.randint(1, total)
    upto = 0
    pick = allowed[0]
    for name, w in zip(allowed, weights):
        upto += w
        if r <= upto:
            pick = name
            break

    if pick not in weapons_inventory:
        bonus = FINDABLE_WEAPONS[pick]["bonus"]
        weapons_inventory[pick] = {"name": pick, "bonus": bonus}
        print(f"\n🗡️ You found a {pick}! Added to your weapons.")
    else:
        print(f"\nYou spot a {pick}, but you already own one.")

# ===============================================
# Resource Gathering
# ===============================================
def gather_resource(area_name):
    """Gather one resource using the area table. Base qty 1–3; Survival II adds +1."""
    outcome = weighted_choice(RESOURCE_TABLE[area_name])

    if outcome == "Nothing":
        print("You find no useful resources.")
        return

    qty = random.randint(1, 3)
    if survival_level >= 2:
        qty += 1

    add_to_bag(outcome, qty)
    icon = (
        "🪵" if outcome == "Wood" else
        "🪨" if outcome == "Stone" else
        "🧵" if outcome == "Rope" else
        "🍎" if outcome == "Fruit" else
        "💀" if outcome == "Bones" else
        "🐍" if outcome == "Scales" else
        "🎒"
    )
    print(f"{icon} You collected {outcome} x{qty}.")

# ===============================================
# Combat
# ===============================================
def maybe_crit(dmg: int) -> (int, bool):
    """Apply Strength path crits. Returns (final_damage, is_crit)."""
    if crit_chance > 0 and random.randint(1, 100) <= crit_chance:
        return dmg * 2, True
    return dmg, False

def fight(enemy, allow_run=True):
    global hp, alive, xp, adrenaline_active
    player_attack = total_attack()
    if adrenaline_active:
        player_attack += 2
        adrenaline_active = False
    enemy_hp = enemy["hp"]
    enemy_name = enemy["name"]

    print(f"\n⚔️ You engage the {enemy_name} in battle!")

    while enemy_hp > 0 and hp > 0:
        print(f"\nYour HP: {hp}/{max_hp}")
        print(f"{enemy_name} HP: {enemy_hp}")

        if allow_run:
            action = input("Do you ATTACK, USE ITEM, or RUN?\n> ").strip().lower()
        else:
            action = input("Do you ATTACK or USE ITEM?\n> ").strip().lower()

        # Dev commands usable during fight
        if dev_command_handler(action):
            continue

        if action == "attack":
            base = random.randint(max(1, player_attack - 2), player_attack + 2)
            dmg, was_crit = maybe_crit(base)
            enemy_hp -= dmg
            print(f"You hit the {enemy_name} for {dmg} damage!" + (" [CRIT!]" if was_crit else ""))
        elif action in ("use", "use item", "item"):
            use_item()
            continue
        elif action == "run":
            if not allow_run:
                print("You cannot run from this foe!")
                continue
            print("You run away and escape safely, but gain no XP.")
            return
        else:
            print("You hesitate and lose your turn!")

        if enemy_hp > 0:
            enemy_dmg = random.randint(enemy["attack"] - 1, enemy["attack"] + 1)
            # Bow effect: -1 atk vs non-flying
            if current_weapon == "Bow" and enemy_name not in FLYING_ENEMIES:
                enemy_dmg = max(0, enemy_dmg - BOW_ENEMY_ATK_REDUCTION)
            hp -= enemy_dmg
            print(f"The {enemy_name} hits you for {enemy_dmg} damage!")

    if hp <= 0:
        handle_death(enemy_name)
    else:
        if enemy.get("xp_reward", 0) > 0:
            print(f"\n🏆 You defeated the {enemy_name} and gained {enemy['xp_reward']} XP!")
            globals()["xp"] += enemy["xp_reward"]

def fight_boss(enemy):
    global hp, xp, adrenaline_active, current_weapon, devmode_active

    enemy_name = enemy["name"]
    enemy_hp = enemy["hp"]

    # Burn effect tracker
    burn_turns = 0

    print(f"\n⚔️ FINAL BATTLE: {enemy_name} has awakened!")
    print("There is no escape...")

    while enemy_hp > 0 and hp > 0:
        # Apply burn effect
        if burn_turns > 0:
            hp -= 2
            burn_turns -= 1
            print(f"[Burning -2 HP] Your HP is now {hp}/{max_hp}")
            if hp <= 0:
                handle_death(enemy_name)
                return

        # Player's turn
        player_attack = total_attack()
        if adrenaline_active:
            player_attack += 2
            adrenaline_active = False

        print(f"\nYour HP: {hp}/{max_hp}")
        print(f"{enemy_name} HP: {enemy_hp}")

        action = input("Do you ATTACK or USE ITEM?\n> ").strip().lower()

        # --- 🔧 DEV COMMAND SUPPORT ---
        if devmode_active and dev_command_handler(action):
            continue

        if action.startswith("use"):  # Accept "use", "use item", "item"
            use_item()
            continue
        elif action == "attack":
            base = random.randint(max(1, player_attack - 2), player_attack + 2)
            dmg, was_crit = maybe_crit(base)
            enemy_hp -= dmg
            if was_crit:
                print(f"You strike the {enemy_name} for {dmg} damage! [CRITICAL HIT!]")
            else:
                print(f"You strike the {enemy_name} for {dmg} damage!")
        else:
            print("You hesitate and lose your attack!")

        # Boss defeated check
        if enemy_hp <= 0:
            game_end_sequence(enemy_name)
            return

        # Boss's turn
        boss_attack_choice = random.choice(["plasma", "thermal"])
        if boss_attack_choice == "plasma":
            dmg = random.randint(10, 13)
            hp -= dmg
            print(f"⚡ {enemy_name} fires a *Plasma Beam*! You take {dmg} damage!")
        else:
            dmg = random.randint(8, 10)
            hp -= dmg
            burn_turns = 3
            print(f"🔥 {enemy_name} unleashes a *Thermal Surge*! You take {dmg} damage and are now burning!")
            print("[Burning -2 HP for 3 turns]")

        if hp <= 0:
            handle_death(enemy_name)
            return

# ===============================================
# Death & Restart Flow
# ===============================================
def handle_death(enemy_name: str):
    print(f"\n💀 The {enemy_name} has defeated you!")
    print(f"You reached the {get_current_area_name()} at Level {lv}.")
    print("Restarting game", end="", flush=True)
    for _ in range(3):
        time.sleep(1)
        print(".", end="", flush=True)
    print()
    time.sleep(1)
    restart_game(forced=True)

# ===============================================
# Explore & Search
# ===============================================
def explore():
    """Explore the current area: fights, finds, traps, and discovering new areas."""
    global current_area_index

    area_name = get_current_area_name()
    print(f"\nYou explore the {area_name}...")

    if area_name == "City":
        city_boss_encounter()
        return

    if area_name == "Camp":
        pool = camp_animals
    elif area_name == "Forest":
        pool = forest_animals
    elif area_name == "Highlands":
        pool = highlands_animals
    elif area_name == "Jungle":
        pool = jungle_animals
    else:
        pool = []

    # 80% chance to encounter a random-area animal
    if pool and random.random() < 0.80:
        enemy = random.choice(pool)
        print(f"You encounter a {enemy['name']}!")
        fight(enemy)
    else:
        # No animal: 25% chance to find a weapon, otherwise gather resources
        if random.random() < 0.25:
            maybe_find_weapon(area_name)
        else:
            gather_resource(area_name)

    # Passive traps tick
    passive_trap_catches()

    # Discover next area: 10%
    if random.random() < 0.10 and current_area_index < len(areas) - 1:
        next_area = areas[current_area_index + 1]
        print(f"\n🌿 You discover a path to the {next_area['name']}!")
        print(next_area['description'])
        choice = input("Do you want to continue into this area? It looks more dangerous. (y/n)\n> ").strip().lower()

        if dev_command_handler(choice):
            return

        if choice == "y":
            current_area_index += 1
            print(f"\nYou push forward... now entering the {next_area['name']}!")
        else:
            print("You decide to stay and prepare a bit longer.")

    # Endurance II passive regen after exploration loop
    if hp > 0 and endurance_level >= 2:
        healed = min(2, max_hp - hp)
        if healed > 0:
            globals()["hp"] += healed
            print(f"[Regen +{healed} HP]")

def search_area():
    """Your specified search system:
       50% strong animal (no XP, no running)
       30% resource
       20% nothing
       City: always boss
    """
    area_name = get_current_area_name()
    print(f"\n=== Searching the {area_name} ===")
    time.sleep(0.3)

    if area_name == "City":
        print("You step deeper into the ruins...")
        time.sleep(0.3)
        city_boss_encounter()
        return

    roll = random.random()

    if roll < 0.50:
        enemy = get_strong_animal(area_name)
        print("You sense a powerful presence nearby...")
        time.sleep(0.3)
        fight(enemy, allow_run=False)
        return
    elif roll < 0.80:
        print("You search the area for resources...")
        time.sleep(0.3)
        gather_resource(area_name)
        return
    else:
        print("You find nothing of value.")
        time.sleep(0.3)
        return

# ===============================================
# City Boss Encounter
# ===============================================
def city_boss_encounter():
    boss_cinematic()
    enemy = {"name": boss["name"], "hp": boss["hp"], "attack": boss["attack"], "xp_reward": 0}
    print("A towering figure of steel and vengeance stands before you.")
    print("Its core glows with unstable power.")
    time.sleep(0.3)
    fight_boss(enemy)

# ===============================================
# Upgrades
# ===============================================
def upgrade():
    global hp, max_hp, att, xp, lv, upgrade_amt
    global strength_level, endurance_level, survival_level, crit_chance
    global bag

    print("\n=== LEVEL UP! ===")
    choices = {}

    if strength_level < 3:
        next_level = strength_level + 1
        desc = "(+2 ATK, Crit 10%)" if next_level == 1 else "(+2 ATK, Crit 15%)" if next_level == 2 else "(+2 ATK, Crit 20%)"
        choices["1"] = ("Strength", next_level, desc)

    if endurance_level < 3:
        next_level = endurance_level + 1
        desc = "(+6 Max HP)" if next_level == 1 else "(+8 Max HP, +2 Regen/Explore)" if next_level == 2 else "(+12 Max HP, +2 Medkits)"
        choices["2"] = ("Endurance", next_level, desc)

    if survival_level < 3:
        next_level = survival_level + 1
        desc = "(+10% Gather Chance)" if next_level == 1 else "(+20% Gather Yield)" if next_level == 2 else "(+30% Yield, +10% Trap Success)"
        choices["3"] = ("Survival", next_level, desc)

    for key, (name, lvl, desc) in choices.items():
        print(f"[{key}] {name} {lvl} {desc}")

    while True:
        choice = input("> ").strip()
        if dev_command_handler(choice):
            return

        if choice in choices:
            path, tier, _ = choices[choice]

            if path == "Strength":
                strength_level = tier
                att += 2
                crit_chance = 10 if tier == 1 else 15 if tier == 2 else 20

            elif path == "Endurance":
                endurance_level = tier
                if tier == 1:
                    max_hp += 6
                elif tier == 2:
                    max_hp += 8
                elif tier == 3:
                    max_hp += 12
                    bag["Medkit"] = bag.get("Medkit", 0) + 2
                hp = max_hp

            elif path == "Survival":
                survival_level = tier

            lv += 1
            xp = 0
            upgrade_amt = int(upgrade_amt * 1.3)
            print(f"You chose {path} Level {tier}!")
            return
        else:
            print("Invalid choice.")

# ===============================================
# Settings / Restart / Quit
# ===============================================
def quit_game():
    confirm = input("Are you sure you want to quit? (y/n)\n> ").strip().lower()
    if dev_command_handler(confirm):
        return
    if confirm == "y":
        print("Goodbye, thanks for playing!")
        sys.exit()
    else:
        print("Quit cancelled.")

def restart_game(forced=False, autostart=True):
    """Forced restart (death) preserves bag/buildings; manual restart wipes."""
    global xp, upgrade_amt, hp, max_hp, att, lv, alive, current_area_index
    global current_weapon, adrenaline_active, weapons_inventory, bag, buildings
    global strength_level, endurance_level, survival_level, crit_chance

    if not forced:
        confirm = input("Are you sure you want to restart? (y/n)\n> ").strip().lower()
        if dev_command_handler(confirm):
            return
        if confirm != "y":
            print("Restart cancelled.")
            return

    print("Restarting game...")
    xp = 0
    upgrade_amt = 110
    hp = 60
    max_hp = 60
    att = 6
    lv = 1
    alive = True
    current_area_index = 0
    current_weapon = "Fists"
    adrenaline_active = False
    strength_level = 0
    endurance_level = 0
    survival_level = 0
    crit_chance = 0

    if forced:
        weapons_inventory = {"Fists": {"name": "Fists", "bonus": 0}}
        # keep bag & buildings
    else:
        weapons_inventory = {"Fists": {"name": "Fists", "bonus": 0}}
        bag = {}
        buildings = {}

    if autostart:
        print("----- Welcome To The Backwoods -----")
        main()

def settings():
    while True:
        print('''
[1] Quit
[2] Restart
[3] Save Game
[4] Main Menu
[5] Back
''')
        choice = input("Choose an option (1-5)\n> ").strip()
        if dev_command_handler(choice):
            continue

        if choice == "1":
            quit_game()
        elif choice == "2":
            restart_game()
        elif choice == "3":
            save_game()
        elif choice == "4":
            print("Returning to main menu... (game will reset)")
            restart_game(forced=False, autostart=False)
            start_menu()
            return
        elif choice == "5":
            return
        else:
            print("Invalid option, please choose again.")

def buildings_menu():
    """Shows built structures and lets you interact with Campfire/Traps."""
    while True:
        print("\n===== BUILDINGS =====")
        have_campfire = buildings.get("Campfire", 0) > 0
        have_traps = buildings.get("Trap", 0) + buildings.get("Advanced Trap", 0) > 0
        have_any = any([have_campfire, have_traps])

        if not have_any:
            print("You have no buildings.")
            print("[0] Back")
            choice = input("> ").strip()
            if choice == "0":
                return
            else:
                print("Invalid option.")
                continue

        if have_campfire:
            print(f"Campfire x{buildings.get('Campfire', 0)}")
        if have_traps:
            total_traps = buildings.get("Trap", 0) + buildings.get("Advanced Trap", 0)
            print(f"Traps x{total_traps}")

        print("\nOptions:")
        idx = 1
        actions = {}

        if have_campfire:
            print(f"[{idx}] Use Campfire (cook 5 Meat -> 1 Food)")
            actions[str(idx)] = "campfire"
            idx += 1
        if have_traps:
            print(f"[{idx}] Check Traps")
            actions[str(idx)] = "traps"
            idx += 1

        print("[0] Back")
        c = input("> ").strip()

        if c == "0":
            return
        elif c in actions:
            if actions[c] == "campfire":
                use_campfire()
            elif actions[c] == "traps":
                check_traps_now()
        else:
            print("Invalid option.")

# ===============================================
# Main Loop & Start Menu
# ===============================================
def main():
    global xp, upgrade_amt
    while True:
        print(f"""
[1] Stats
[2] Inventory
[3] Explore
[4] Search {areas[current_area_index]['name']}
[5] Craft
[6] Buildings
[7] Map
[8] Settings
""")
        choice = input("> ").strip()

        # Dev commands are ONLY active if devmode_active True (Option A)
        if dev_command_handler(choice):
            continue

        if choice == "1":
            stats()
        elif choice == "2":
            show_inventory()
        elif choice == "3":
            explore()
        elif choice == "4":
            search_area()
        elif choice == "5":
            craft()
        elif choice == "6":
            buildings_menu()
        elif choice == "7":
            show_map()
        elif choice == "8":
            settings()
        else:
            print("This is not a valid input, please choose 1-8.")

        if xp >= upgrade_amt:
            upgrade()

def start_menu():
    global devmode_active
    while True:
        print("\n===== THE BACKWOODS =====")
        print("[1] New Game")
        print("[2] Load Game")
        print("[3] Delete Save")
        print("[4] Quit")
        choice = input("> ").strip().lower()

        # Secret Dev Mode activation from main menu ONLY
        if choice == "devmode kyusuf1001":
            print("\n🔧 DEVELOPER MODE ACTIVATED: SANDBOX MODE ENABLED")
            print("(Saving Disabled - all progress will be lost on exit)")
            devmode_active = True
            restart_game(forced=False, autostart=True)
            main()
            devmode_active = False
            return

        if choice == "1":
            devmode_active = False
            restart_game(forced=False, autostart=True)
            main()
            return
        elif choice == "2":
            if devmode_active:
                print("❌ Cannot load game in Developer Mode.")
                continue
            if load_game_from_slot():
                print("Loading saved game...")
                main()
                return
        elif choice == "3":
            delete_save_slot()
        elif choice == "4":
            print("Goodbye.")
            sys.exit(0)
        else:
            print("Invalid choice.")

# ===============================================
# Entry
# ===============================================
if __name__ == "__main__":
    ensure_save_dir()
    start_menu()
