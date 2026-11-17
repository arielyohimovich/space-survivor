<div align="center">

# 🚀 Space Survivor

![Space Survivor](space.png)

**How long can you survive?**

An endless space survival shooter built with Python and pygame.
The monsters keep multiplying, and a new boss arrives every 30 seconds. Stay alive as long as you can.

[![Play on itch.io](https://img.shields.io/badge/▶_PLAY_NOW-itch.io-FA5C5C?style=for-the-badge&logo=itchdotio&logoColor=white)](https://ariel93.itch.io/space-survivor)

![Python](https://img.shields.io/badge/Python-3.10+-3776AB?logo=python&logoColor=white)
![pygame-ce](https://img.shields.io/badge/pygame--ce-2.x-6BBE45)
![Platform](https://img.shields.io/badge/platform-Web%20%7C%20Windows%20%7C%20macOS%20%7C%20Linux-lightgrey)

### 🎮 [Play it in your browser: ariel93.itch.io/space-survivor](https://ariel93.itch.io/space-survivor)
*Nothing to install. It runs right in your browser.*

</div>

---

## 📖 Table of Contents
- [About the Game](#-about-the-game)
- [Controls](#-controls)
- [Gameplay](#-gameplay)
  - [Power-up Drops](#-power-up-drops)
  - [Weapons](#-weapons)
  - [Monsters](#-monsters)
  - [Bosses](#-bosses)
- [Run Locally](#-run-locally)
- [Build for the Web](#-build-for-the-web)
- [Configuration](#️-configuration)
- [Technical Highlights](#-technical-highlights)
- [Project Structure](#-project-structure)
- [Credits](#-credits)

---

## 🌌 About the Game

You are an astronaut stranded in deep space. Wave after wave of alien monsters closes in on you, and **every 10 seconds their number doubles**. Your lasers fire automatically at the nearest enemy, so your job is to **move, dodge and grab power-ups**.

There is no finish line. The clock keeps counting, and your score is **how long you survive**.

**Features**
- ⏱️ Endless survival mode with a live clock and a saved best time
- 👨‍🚀 Astronaut hero in a space suit that turns **red** when you pick up speed
- 🔫 4 laser weapons in 4 colors: **Blue → Green → Yellow → Red**
- 🛡️ Cyan energy shield that blinks during its last 3 seconds
- 👾 6 monster types, plus a boss every 30 seconds in a new color
- 📊 Live side panel with kills per monster type, weapon level and power-up timers
- 💥 Particles, screen shake, damage numbers and sound effects generated in code

---

## 🕹 Controls

| Action | Keys |
|---|---|
| Move | `W` `A` `S` `D` / Arrow keys / Hold left mouse button |
| Shoot | Automatic, aims at the nearest monster |
| Pause | `P` or `Esc` |
| Start / Restart | `Space` / `Enter` / Click |
| Switch hero face (menu) | `F` |

---

## 🎯 Gameplay

### Difficulty curve
| Every... | What happens |
|---|---|
| **10 seconds** | The number of monsters **doubles** (5 → 10 → 20 → 40 …) and they get **6% faster** |
| **30 seconds** | A **boss** arrives with a ring of monsters surrounding you |
| Over time | Monsters get more health, and new monster types join the fight |

### 🎁 Power-up Drops
Each monster you kill rolls once for a drop. Drops blink and disappear after 12 seconds if you don't collect them.

| Drop | Chance | Effect |
|---|---|---|
| ➕ **Health** | 3% | Restores 25 HP |
| ⚡ **Speed** | 5% | 1.6× movement speed for 8 seconds. Your suit turns **red** |
| 🔫 **Weapon** | 4% | Upgrades your laser to the next color (+5% damage once maxed, up to +50%) |
| 🛡️ **Shield** | 2% | **Invulnerable for 10 seconds**. Blinks during the last 3 seconds and blocks bullets |

### 🔫 Weapons
| Level | Weapon | Beams | Damage | Fire rate | Pierces |
|---|---|---|---|---|---|
| 1 | 🔵 **Blue Laser** | 1 | 14 | 0.36s | 1 enemy |
| 2 | 🟢 **Green Twin** | 2 parallel | 12 | 0.36s | 1 enemy |
| 3 | 🟡 **Yellow Spread** | 3 spread | 15 | 0.32s | 2 enemies |
| 4 | 🔴 **Red Destroyer** | 5 spread | 22 | 0.22s | 3 enemies |

Every hit has a **10% chance to crit** for double damage.

### 👾 Monsters
| Monster | Shape | HP | Speed | Appears | Special |
|---|---|---|---|---|---|
| 🟥 **Crawler** | Red square | 14 | 80 | 0:00 | The basic chaser |
| 🟡 **Zipper** | Yellow circle | 8 | 150 | 0:10 | Very fast, very fragile |
| 🟣 **Brute** | Purple hexagon | 80 | 48 | 0:20 | Slow tank that hits hard |
| 🔶 **Spitter** | Orange triangle | 24 | 72 | 0:30 | Keeps its distance and **shoots** at you |
| 🟢 **Splitter** | Green diamond | 34 | 64 | 0:40 | Splits into 2 Spawnlings when killed |
| 🟢 **Spawnling** | Small green circle | 7 | 125 | from Splitters | Small and quick |

### 👑 Bosses
A new boss arrives **every 30 seconds**. Each boss is **stronger than the previous one** (×1.75 HP, bigger, faster, more bullets) and comes in a **new color**:
🟠 Orange → 🟢 Green → 🔵 Cyan → 🟣 Purple → 🟡 Yellow → 🩷 Pink → 🔴 Red → 🔷 Blue → ⚪ White → random colors

Boss attacks:
- 🎯 **Aimed shots**, fired straight at you
- 🌀 **Spiral barrage** of rotating bullets
- 💨 **Charge**: shakes in place, then dashes at you
- 👥 **Summon**: calls fast minions around itself

Defeating a boss drops one random power-up.

---

## 💻 Run Locally

**Requirements:** Python 3.10 or newer

```bash
# 1. Clone the repository
git clone https://github.com/arielyohimovich/space-survivor.git
cd space-survivor

# 2. Install pygame (pygame-ce is the actively maintained version)
python -m pip install pygame-ce

# 3. Play!
python main.py
```

> 💡 The original `pygame` package also works: `pip install pygame`

---

## 🌐 Build for the Web

The browser version is built with [pygbag](https://github.com/pygame-web/pygbag), which compiles pygame games to WebAssembly.

```bash
python -m pip install pygbag

# Test locally at http://localhost:8000
python -m pygbag space-survivor

# Create the upload package -> build/web.zip
python -m pygbag --archive space-survivor
```

Upload `build/web.zip` to [itch.io](https://itch.io) as an **HTML** project and tick **"This file will be played in the browser"**. Viewport size: **1100 × 620**.

---

## ⚙️ Configuration

All the balance settings are constants at the top of [`main.py`](main.py):

| Constant | Default | Description |
|---|---|---|
| `DROP_TABLE` | 3% / 5% / 4% / 2% | Drop chance for health / speed / weapon / shield |
| `START_MONSTERS` | `5` | Monsters on the field at the start |
| `DOUBLE_EVERY` | `10` | Seconds between monster doublings |
| `SPEEDUP` | `0.06` | Monster speed increase per doubling |
| `BOSS_EVERY` | `30` | Seconds between bosses |
| `SHIELD_TIME` | `10` | Shield duration (seconds) |
| `SHIELD_BLINK` | `3` | Shield starts blinking this many seconds before it ends |
| `SPEED_TIME` | `8` | Speed boost duration (seconds) |
| `SPEED_MULT` | `1.6` | Speed boost multiplier |
| `MAX_ENEMIES` | `340` | Cap on monsters on screen (keeps the game smooth) |
| `WEAPONS` | — | Color, beams, damage and fire rate of each laser |

---

## 🔧 Technical Highlights

- **Spatial hash grid**: the world is split into 64px cells, so collisions are only checked against nearby objects. This keeps hundreds of monsters and lasers at 60 FPS, even in the browser.
- **Async game loop** (`asyncio`), which lets the same code run on desktop and in the browser through pygbag.
- **Procedural graphics**: everything is drawn with `pygame.draw` (neon glow, the astronaut and the monsters), and the sprites are pre-rendered and cached.
- **Generated sound effects**: built from raw waveforms in code, so the game ships with no audio files.
- **Persistent best time**: stored in `localStorage` in the browser and in `save.json` on desktop.

---

## 📁 Project Structure

```
space-survivor/
├── main.py              # The whole game
├── face.png             # Hero face shown inside the helmet (optional)
├── space.png            # Cover art
├── screenshot_boss.png  # Gameplay screenshot
├── README.md
└── .gitignore
```

> 🧑‍🚀 **Make it yours:** replace `face.png` with any square photo to put your own face in the helmet. Delete it and the game uses a drawn cartoon face.

---

## 📸 Screenshot

![Gameplay: a boss fight](screenshot_boss.png)

---

## 🙌 Credits

- **Game design & development:** [Ariel93](https://ariel93.itch.io)
- Built with [pygame-ce](https://pyga.me) and [pygbag](https://github.com/pygame-web/pygbag)
- Developed with the help of AI (Claude)

<div align="center">

### ⭐ If you enjoyed the game, give the repo a star and [play it on itch.io](https://ariel93.itch.io/space-survivor)!

</div>
