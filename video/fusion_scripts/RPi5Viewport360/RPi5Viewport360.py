# 360° turntable captured from the Fusion viewport, so the photo texture of the scan is visible
# (Fusion's ray-traced renderer does not use it). It starts with the bare scan, then the shell, the bezel and
# the stand are added while the camera turns. Four series are captured, each with a different set of visible
# parts, and video/tools/blend_states.py fades from one series to the next:
#   s0 = scan only    s1 = + bezel    s2 = + shell    s3 = + stand
# Only the frames needed by the fades are captured.

import adsk.core, adsk.fusion, math, os, time, traceback

FRAMES = 144
WIDTH, HEIGHT = 2560, 1440      # captured at 2x and reduced to 1280x720 by slowmo.py (supersampling)
FRAMES_DIR = r'C:\Workspace\homeassistant_rpi5\video\frames\viewport'

CENTER_CM = (2.16, 1.82, 2.0)   # centre of the case (x, y, z) in cm
UP = (0.0, 1.0, 0.0)            # the case's vertical axis
ELEVATION_DEG = 16.0
AZIMUTH0_DEG = -35.0            # 0 = looking straight at the back of the case
DIST_CM = 46.0

# Fade windows, in order of appearance: first part, second part, third part
FIRST_IN = (0.06, 0.30)
SECOND_IN = (0.32, 0.56)
THIRD_IN = (0.58, 0.82)
ALL_OUT = (0.88, 0.99)

PART_NAMES = ['Bezel', 'Shell', 'Stand']   # order in which the parts appear
SCAN_NAME = 'scan texture'
MATERIAL = 'PETG white'
MATERIAL_BASE = 'Plastic - Glossy (White)'

LOG = os.path.join(FRAMES_DIR, 'run.log')


def log(msg):
    try:
        os.makedirs(FRAMES_DIR, exist_ok=True)
        with open(LOG, 'a', encoding='utf-8') as f:
            f.write('%s %s\n' % (time.strftime('%H:%M:%S'), msg))
    except Exception:
        pass


def needed(state, t):
    if state == 0: return t <= FIRST_IN[1] or t >= ALL_OUT[0]
    if state == 1: return FIRST_IN[0] <= t <= SECOND_IN[1]
    if state == 2: return SECOND_IN[0] <= t <= THIRD_IN[1]
    return THIRD_IN[0] <= t <= ALL_OUT[1]


def set_toggle(ui, cmd_id, value):
    cd = ui.commandDefinitions.itemById(cmd_id)
    if cd and hasattr(cd.controlDefinition, 'isChecked') and cd.controlDefinition.isChecked != value:
        cd.controlDefinition.isChecked = value


def hide_planes(root):
    """Hide every plane, axis, point and sketch so only the model is in the frames."""
    comps = [root] + [o.component for o in root.allOccurrences]
    seen = set()
    for c in comps:
        if c.entityToken in seen:
            continue
        seen.add(c.entityToken)
        for name in ('xYConstructionPlane', 'xZConstructionPlane', 'yZConstructionPlane',
                     'xConstructionAxis', 'yConstructionAxis', 'zConstructionAxis', 'originConstructionPoint'):
            e = getattr(c, name, None)
            if e is not None:
                e.isLightBulbOn = False
        for coll in (c.constructionPlanes, c.constructionAxes, c.constructionPoints):
            for e in coll:
                e.isLightBulbOn = False
        for sk in c.sketches:
            sk.isLightBulbOn = False


def run(context):
    app = adsk.core.Application.get()
    ui = app.userInterface
    design = adsk.fusion.Design.cast(app.activeProduct)
    root = design.rootComponent
    log('run() started')
    try:
        # Capture from the Design workspace, where the photo texture of the scan is shown. Before running, turn
        # off by hand the layout grid, the origin/axes and the ground plane (View > Display Settings): the
        # commands that toggle them cannot be read back from a script.
        if ui.activeWorkspace.id != 'FusionSolidEnvironment':
            ui.workspaces.itemById('FusionSolidEnvironment').activate()
        material = design.appearances.itemByName(MATERIAL)
        if material is None:
            lib = app.materialLibraries.itemByName('Fusion Appearance Library')
            material = design.appearances.addByCopy(lib.appearances.itemByName(MATERIAL_BASE), MATERIAL)
        parts = {}
        for occ in root.allOccurrences:
            if occ.component.name in PART_NAMES:
                parts[occ.component.name] = occ
                for body in occ.component.bRepBodies:
                    body.appearance = material
        scan = None
        for m in root.meshBodies:
            if m.name == SCAN_NAME: scan = m
            else: m.isLightBulbOn = False
        scan.isLightBulbOn = True
        hide_planes(root)

        v = app.activeViewport
        v.visualStyle = adsk.core.VisualStyles.ShadedVisualStyle
        center = adsk.core.Point3D.create(*CENTER_CM)
        el = math.radians(ELEVATION_DEG)

        def place(i):
            az = math.radians(AZIMUTH0_DEG) + 2 * math.pi * i / FRAMES
            cam = v.camera
            cam.isSmoothTransition = False
            cam.cameraType = adsk.core.CameraTypes.PerspectiveCameraType
            cam.isFitView = False
            cam.target = center
            cam.eye = adsk.core.Point3D.create(
                center.x + DIST_CM * math.cos(el) * math.sin(az),
                center.y + DIST_CM * math.sin(el),
                center.z + DIST_CM * math.cos(el) * math.cos(az))
            cam.upVector = adsk.core.Vector3D.create(*UP)
            v.camera = cam
            adsk.doEvents()
            v.refresh()

        total = 0
        for state in range(4):
            for n in PART_NAMES:
                parts[n].isLightBulbOn = state >= PART_NAMES.index(n) + 1
            out_dir = os.path.join(FRAMES_DIR, 's%d' % state)
            os.makedirs(out_dir, exist_ok=True)
            for i in range(FRAMES):
                t = i / FRAMES
                if not (needed(state, t) or needed(state, (i - 1) / FRAMES) or needed(state, (i + 1) / FRAMES)):
                    continue
                place(i)
                if v.saveAsImageFile(os.path.join(out_dir, 'frame_%04d.png' % i), WIDTH, HEIGHT):
                    total += 1
            log('series s%d captured' % state)
        for n in PART_NAMES:
            parts[n].isLightBulbOn = True
        log('total captured: %d' % total)
        return total
    except Exception:
        log(traceback.format_exc())
        raise
