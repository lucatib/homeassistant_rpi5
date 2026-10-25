# homeassistant_rpi5

A 3D-printed case for a **7" touch display with a Raspberry Pi 5 mounted behind it**, to run Home Assistant on a wall or on a desk.
The model is built in Autodesk Fusion around a **3D scan of the real hardware**, so every opening lines up with the actual connectors.
Printed in **white PETG**.

## What is in the case
- **Display:** Elecrow 7" HDMI Display-H, 1024×600, USB touch, with two built-in speakers. The module is 164.9 × 102 mm.
- **Computer:** Raspberry Pi 5 with an Armor Lite V5 fan heatsink, behind the display.
- **Ethernet** on the left side and **USB-C power** on the top edge (straight connector).
- Access to the display's **brightness/volume wheel** on one short side.

## The three printed parts
| Part | File | What it does |
|---|---|---|
| Shell | `step/Shell.step` | Holds the display and the Pi. Vents over the fan and heatsink, speaker grilles, keyhole slots for the wall, and a threaded post for the stand. |
| Bezel | `step/Bezel.step` | Front frame with rounded corners. It **snaps on from the front** with 8 hooks once the shell is closed: no screws. |
| Stand | `step/Stand.step` | Optional desk stand that hangs on the two keyhole slots and tilts the case **20° backwards**. One screw locks it. |

Outer size 173.6 × 110.2 mm with 6.8 mm corners; about 40 mm deep (20 mm along the lower strip).

## Screws
| Where | Screw |
|---|---|
| Display to shell, top corners | 2 × M2.5 × 10 |
| Display to shell, bottom corners | 2 × M2.5 × 6 |
| Stand to shell | 1 × M3 × 12 |

The bezel needs no screws. Parts list with links: [docs/components.md](docs/components.md).

## Design notes
- The back is flat on purpose, so the case sits firmly on the wall and does not move when you touch the screen. Only the vent and speaker areas are recessed by 1.5 mm, and those recesses open to the edges so air and sound can get out even against a wall.
- A 1.5 mm interlocking band runs all around the shell, with matching rounded corners on the bezel.
- The display window of the bezel was corrected after the first print, from a photo of the assembled case: it is higher and a little wider on one side, because the active area is not centred on the module. **This corrected bezel has not been printed yet.**

## Contents
| Folder | What |
|---|---|
| `models/` | The Fusion archive (`.f3d`, about 51 MB, includes the textured scan) |
| `step/` | Shell, Bezel and Stand as STEP, for printing |
| `scan/` | The 3D scan (OBJ + textures) and its version aligned and squared to the model |
| `tools/scan/` | Scripts that align the scan to the model, cut it and square it ([docs/scan.md](docs/scan.md)) |
| `video/` | The 360° turntable video (`rpi5_case_360.mp4`), with the Fusion scripts and tools that make it ([docs/video-pipeline.md](docs/video-pipeline.md)) |
| `docs/` | Documentation |

## Opening the model
In Fusion: **File → Open → Open from my computer**, or drag `models/RPi5 Display Case.f3d` into the window.
