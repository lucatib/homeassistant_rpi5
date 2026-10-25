"""Smooth slow motion: blended frames (video/frames/blended) -> video/rpi5_case_360.mp4.

144 real frames at 24 fps (6 s) taken to 48 fps with 2x motion-compensated interpolation.
Requires ffmpeg (winget install Gyan.FFmpeg).
"""
import os, subprocess

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC = os.path.join(ROOT, "frames", "blended", "frame_%04d.png")
OUT = os.path.join(ROOT, "rpi5_case_360.mp4")

subprocess.run([
    "ffmpeg", "-y", "-loglevel", "error", "-framerate", "24", "-i", SRC,
    "-vf", "scale=1280:720:flags=lanczos,setsar=1,minterpolate=fps=48:mi_mode=mci:mc_mode=aobmc:me_mode=bidir:vsbmc=1:scd=none",
    "-r", "48", "-c:v", "libx264", "-pix_fmt", "yuv420p", "-crf", "15", "-movflags", "+faststart", OUT,
], check=True)
print("Created", OUT)
