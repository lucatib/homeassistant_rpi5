# The scan

`scan/3DModel.obj` is the textured scan of the display with the Pi mounted behind it (metres, Y up).

**Fusion does not save the photo texture of an imported mesh in the document.** The photos are visible while the document stays open,
but after every reopen (or Fusion restart) the mesh comes back without them. Insert `scan/3DModel_fusion_square.obj` again (mm, already
in model coordinates) to get them back. Assigning any appearance to the mesh also hides the photos.

The model is built on the scan, so it is first brought into the model's coordinates and tidied. The three scripts in `tools/scan/`
(plain Python, no packages) do it:

1. `icp.py scan/3DModel.obj nodes.txt` finds the exact rotation and translation that map the OBJ onto the mesh already in the Fusion document
   (`nodes.txt` is the list of mesh nodes in mm, one `x y z` per line). The result is a rotation of 90° about X, a small rotation about Z and a shift of about 21.3 mm.
2. `cutcap.py` cuts the scan at the front plane of the display (z = 3.418 mm) and closes it with a flat cap that is exactly 164.9 × 102 mm,
   so the front of the module is flat and the mesh is watertight.
3. `square.py` straightens the walls of the display module, up to the back of the module (about 12.4 mm), to the same rectangle.
   Above that the effect fades out, so the Pi and the speakers are not touched.

`scan/3DModel_fusion_square.obj` is the result, already in model coordinates (mm, Z along the depth of the case, front at z = 0).
It uses the same `3DModel.mtl` and textures in `scan/3DModel/`.
