<p align="center">
  <img src="logo.png" alt="Python Game Box Logo" width="256">
</p>

<h1 align="center">Python Game Box (PGB) | Flash Revival</h1>

<p align="center">
  <strong>A collection of classic Flash games rebuilt with pure Python</strong>
</p>

<p align="center">
  <a href="https://x.com/HAKORAdev">
    <img alt="Twitter Follow" src="https://img.shields.io/badge/Contact-@HAKORAdev-blue?style=for-the-badge&logo=x">
  </a>
  <a href="https://github.com/HAKORADev/Python_Game_Box_PGB">
    <img alt="GitHub" src="https://img.shields.io/badge/Repo-Python_Game_Box-181717?style=for-the-badge&logo=github">
  </a>
</p>

---

## About

Python Game Box (PGB) is a nostalgic tribute to the golden age of Flash games. It features a curated collection of classic mini-games, all written in **100% pure Python code**. No game engines, no frameworks — just Python.

### Key Features

- **Pure Python**: All games are built from scratch using only Python and standard libraries
- **Lightweight**: Simple, fast, and easy to run
- **Nostalgic**: Brings back the fun of classic Flash-era mini-games
- **Cross-Platform**: Source code runs on Windows, Linux, and macOS
- **Extensible**: Add new language ports under src/ (e.g. src/cpp/, src/web/)

---

## Repository Structure

```
PGB/
├── docs/                    # Documentation
│   ├── changelog.txt        # Full version history
│   ├── Controls.txt         # Game controls reference
│   ├── about.txt            # Project overview
│   ├── v1.3.5_readme.txt    # v1.3.5 release notes
│   └── v1.3.8_readme.txt    # v1.3.8 release notes
├── src/
│   └── python/              # Python source code
│       ├── v1.3.5/          # 13 games
│       └── v1.3.8/          # 14 games (Pop TD added)
├── assets/                  # Game screenshots (all versions)
├── logo.png                 # Project logo
├── showcase.md              # Screenshot gallery
├── requirements.txt         # Python dependencies
├── LICENSE
└── README.md
```

The `src/` directory is organized by language/platform. Drop any new source code into `src/<language>/<version>/`. For example, to add C++ ports: `src/cpp/v1.3.8/`. This structure makes it easy to:
- Add new language ports under `src/`
- Track which games exist in each version
- Keep source code separated by platform

---

## Game Collection (v1.3.8 — 14 Games)

> 📸 **[View all screenshots →](showcase.md)** — Every game across every version

| Game | Type | Description |
|------|------|-------------|
| **2048** | Puzzle | Classic number puzzle with single player and VS mode |
| **Cosmic Spud** | Shooter | Survival shooter with auto-fire, 10 enemy types, upgrade system |
| **Dario** | Platformer | Platformer with coins, enemies, and power-ups |
| **Escape The Maze** | Puzzle | Navigate procedurally generated mazes |
| **Fruit Slasher** | Arcade | Slice fruits with mouse swipes, avoid bombs |
| **Geometry Flash** | Arcade | Switch lanes to avoid obstacles |
| **Hen Invaders** | Arcade | Space invaders with power-ups and 2-player mode |
| **Keyboard Singer** | Music | 10 instruments, multiple play modes |
| **Matcher** | Puzzle | Match-3 gem puzzle with special powers |
| **Pop TD** | Strategy | Tower defense — 6 tower types, 15 waves, upgrade paths *(v1.3.8+)* |
| **Pong** | Arcade | Classic ping pong with AI and multiplayer |
| **Snake** | Arcade | Classic snake with AI mode and 2-player support |
| **Snowy Tower** | Platformer | Jump between platforms to climb higher |
| **XO** | Puzzle | Tic Tac Toe with 4 AI difficulties |

---

## Downloads

### Legacy Windows Executables (v1.0–v1.1.1)

| Version | Download | Description |
|---------|----------|-------------|
| **v1.1.1** | [MediaFire](https://www.mediafire.com/file/dpj5sopetnzvv86/Python_Game_Box_V1.1.1.zip/file) | Bug squash patch |
| **v1.1** | [MediaFire](https://www.mediafire.com/file/pur1laddvdj073a/Python_Game_Box_V1.1.exe/file) | Game Box Update (Matcher added) |
| **v1.0** | [MediaFire](https://www.mediafire.com/file/8gdnugakadw978c/Python_Game_Box.exe/file) | Initial release (10 games) |

> **Note**: These are pre-compiled Windows executables. The itch.io page is no longer available. Source code for v1.3.5+ is available in this repository.

### Running from Source

1. Install Python 3.x
2. Install dependencies: `pip install -r requirements.txt`
3. Run any game: `python src/python/v1.3.8/<game>.py`

---

## Version History

| Version | Date | Games | Highlights |
|---------|------|-------|------------|
| **v1.3.8** | May 2026 | 14 | Pop TD added (tower defense) |
| **v1.3.5** | Mar 2026 | 13 | Cosmic Spud + Fruit Slasher, major improvements |
| **v1.1.1** | Apr 2025 | 11 | Bug fixes across 8 games |
| **v1.1** | Apr 2025 | 11 | Matcher added, 2-player modes, visual upgrades |
| **v1.0** | Apr 2025 | 10 | Initial release |

See [docs/changelog.txt](docs/changelog.txt) for the full detailed changelog.

---

## Technical Details

- **Language**: 100% Pure Python
- **Libraries**: PyQt5, Pygame, Pymunk, Pyganim, NumPy, SciPy
- **Optional**: PyOpenGL (GPU rendering in Pop TD)
- **Platform**: Windows, Linux (source), macOS (source)
- **FPS**: Consistent 60 FPS across all games
- **Audio**: Procedurally generated (no external audio files)

---

## Why Pure Python?

Every game in this collection is written entirely in Python without using game engines like Unity or Godot. This demonstrates what's possible with standard Python libraries and serves as a testament to the language's versatility.

---

## License

This software is provided for personal, non-commercial use. See the included LICENSE file for more details.

---

## Contact

- **X/Twitter**: [@HAKORAdev](https://x.com/HAKORAdev)
- **GitHub**: [HAKORADev](https://github.com/HAKORADev)

---

## Acknowledgments

- The Flash game community for inspiring generations of web games
- Python Software Foundation for an amazing programming language
- Everyone who enjoys nostalgic gaming experiences!
