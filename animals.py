# ===============================================
# ANIMALS.PY - Enemy definitions by region
# Difficulty tiers: Camp (Easy), Forest (Medium),
# Highlands (Hard), Jungle (Very Hard), City (Boss)
# ===============================================

# ==== CAMP (Easy) ====
camp_animals = [
    {"name": "Rabbit",      "hp": 8,  "attack": 1, "xp_reward": 8,  "loot": {"Fur": 1, "Meat": 1}, "loot_chance": 0.2},
    {"name": "Sparrow",     "hp": 6,  "attack": 2, "xp_reward": 6,  "loot": {},                  "loot_chance": 0.0},
    {"name": "Field Mouse", "hp": 7,  "attack": 2, "xp_reward": 7,  "loot": {"Fur": 1},          "loot_chance": 0.2},
    {"name": "Frog",        "hp": 8,  "attack": 3, "xp_reward": 10, "loot": {"Meat": 1},         "loot_chance": 0.2}
]

# ==== FOREST (Medium) ====
forest_animals = [
    {"name": "Wild Boar", "hp": 20, "attack": 6, "xp_reward": 20, "loot": {"Meat": 2}, "loot_chance": 0.3},
    {"name": "Wolf",      "hp": 25, "attack": 5, "xp_reward": 20, "loot": {"Fur": 1},  "loot_chance": 0.2},
    {"name": "Hawk",      "hp": 30, "attack": 3, "xp_reward": 16, "loot": {"Bone": 1}, "loot_chance": 0.2},
    {"name": "Viper",     "hp": 18, "attack": 5, "xp_reward": 16, "loot": {"Scale": 1},"loot_chance": 0.2}
]

# ==== HIGHLANDS (Hard) ====
highlands_animals = [
    {"name": "Mountain Goat",     "hp": 30, "attack": 7, "xp_reward": 18, "loot": {"Fur": 1, "Meat": 1}, "loot_chance": 0.2},
    {"name": "Highland Viper",    "hp": 35, "attack": 8, "xp_reward": 22, "loot": {"Scale": 1},         "loot_chance": 0.2},
    {"name": "Eagle",             "hp": 35, "attack": 5, "xp_reward": 24, "loot": {"Bone": 1},          "loot_chance": 0.2},
    {"name": "Wild Ape",          "hp": 38, "attack": 9, "xp_reward": 28, "loot": {"Bone": 1, "Meat": 1},"loot_chance": 0.2}
]

# ==== JUNGLE (Very Hard) ====
jungle_animals = [
    {"name": "Panther",       "hp": 45, "attack": 10, "xp_reward": 32, "loot": {"Fur": 1, "Meat": 1},  "loot_chance": 0.2},
    {"name": "Giant Snake",   "hp": 50, "attack": 11, "xp_reward": 35, "loot": {"Scale": 1},           "loot_chance": 0.2},
    {"name": "Wild Ape",  "hp": 55, "attack": 12, "xp_reward": 40, "loot": {"Meat": 1, "Bone": 1}, "loot_chance": 0.2},
    {"name": "Crocodile",     "hp": 60, "attack": 12, "xp_reward": 50, "loot": {"Scale": 2},           "loot_chance": 0.25}
]

# ==== CITY (Boss) ====
boss = {"name": "The Ruined Titan", "hp": 200, "attack": 25}
