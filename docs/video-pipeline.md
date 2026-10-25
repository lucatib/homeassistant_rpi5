# 360° turntable video

Final file: `video/rpi5_case_360.mp4` — 1280×720, 48 fps, about 6 s, looping.
The camera circles the case. It starts as the bezel begins to appear over the bare 3D scan of the display and the Raspberry Pi,
then the shell and the stand are added one after the other; at the end everything fades back to the scan, so the video loops without a jump.

## What you need
| File | Role |
|---|---|
| `video/fusion_scripts/RPi5Viewport360` | Fusion script: captures the four series of frames from the viewport |
| `video/tools/blend_states.py` | Fades from one series to the next |
| `video/tools/slowmo.py` | Reduces the frames to 1280×720 and interpolates to 48 fps (ffmpeg) → final mp4 |
| ffmpeg | `winget install Gyan.FFmpeg` |

The PNG frames (`video/frames/`) are not in the repository: rebuild them with the steps below.

## Rebuilding the video
1. **Open the model and bring the photos back.** Fusion does not keep the photo texture of the scan in the saved document
   ([docs/scan.md](scan.md)): insert `scan/3DModel_fusion_square.obj` again so the mesh body is called `scan texture`.
2. **Clean viewport.** In the Design workspace, turn off by hand the layout grid, the origin/axes and the ground plane
   (View → Display Settings). These toggles cannot be read from a script, so the script does not touch them.
3. **Capture.** Copy `video/fusion_scripts/RPi5Viewport360` to `%APPDATA%\Autodesk\Autodesk Fusion 360\API\Scripts\`, then
   Shift+S → **RPi5Viewport360** → **Run**. It takes a few minutes and writes `video/frames/viewport/s0 … s3`:
   `s0` scan only, `s1` + bezel, `s2` + shell, `s3` + stand. Only the frames needed by the fades are captured, at 2560×1440.
   The script puts a white PETG appearance on the three printed parts and hides the construction planes, axes and sketches.
4. **Fade.** `python video/tools/blend_states.py viewport` → `video/frames/blended/`
   (bezel 6–30 % of the turn, shell 32–56 %, stand 58–82 %, back to the scan 88–99 %). The sequence is rotated so it starts
   where the bezel begins to appear.
5. **Video.** `python video/tools/slowmo.py` → the final video. The 2560×1440 frames are reduced with a Lanczos filter
   (supersampling), then taken from 24 to 48 fps with motion-compensated interpolation.

## Notes
- **Ray-traced alternative.** `video/fusion_scripts/RPi5Render` renders the same sequence with Fusion's local ray tracing.
  It looks better, but the ray tracer does not use the photo texture of the scan, so the scan comes out as plain metal.
  Run it with `python video/tools/blend_states.py` (no argument) on its `video/frames/s0 … s3`.
- Fusion renders queued from a script cannot be cancelled from the Rendering Gallery: only restarting Fusion stops them.
