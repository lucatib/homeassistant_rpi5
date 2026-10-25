# 360° turntable of the case: it starts with the bare scan (with its photo texture), then the shell, the bezel
# and the stand are added while the camera turns.
# Fusion's renderer ignores opacity, so four series are rendered, each with a different set of visible parts,
# and video/tools/blend_states.py fades from one series to the next:
#   s0 = scan only    s1 = + shell    s2 = + bezel    s3 = + stand
# Only the frames needed by the fades are rendered. Frames that already exist are skipped.

import adsk.core, adsk.fusion, math, os, time, traceback

FRAMES = 144            # 144 frames = 6 seconds at 24 fps (then taken to 48 fps by video/tools/slowmo.py)
QUALITY = 40            # 25-100: 75 = 'Final'
RESOLUTION = adsk.fusion.RenderResolutions.Video1280x720RenderResolution
FRAMES_DIR = r'C:\Workspace\homeassistant_rpi5\video\frames'

# Deterministic camera: it orbits around the vertical axis of the case (Y) through its centre.
CENTER_CM = (2.16, 1.82, 2.0)   # centre of the case (x, y, z) in cm
UP = (0.0, 1.0, 0.0)
ELEVATION_DEG = 16.0
AZIMUTH0_DEG = -35.0            # 0 = looking straight at the back of the case
RADIUS_CM = 14.5                # radius of the scene around the axis (reaches the LAN cable of the scan)
FIT = 1.10                      # >1 = smaller model in the frame

# Fade windows, as a fraction of the turn
FIRST_IN = (0.10, 0.28)    # bezel
SECOND_IN = (0.34, 0.52)   # shell
THIRD_IN = (0.58, 0.76)    # stand
ALL_OUT = (0.88, 0.98)          # everything fades out and only the scan is left: the video loops

PART_NAMES = ['Bezel', 'Shell', 'Stand']   # order in which the parts appear
SCAN_NAME = 'scan texture'
OLD_SCAN_NAME = 'submesh'
MATERIAL = 'PETG white'
MATERIAL_BASE = 'Plastic - Glossy (White)'
SHOW_DIALOGS = False

# For tests, JOB = {'frames': [(state, index), ...], 'dir': folder} can be passed with runpy.run_path(init_globals=...)
JOB = globals().get('JOB')

LOG = os.path.join(os.path.dirname(os.path.abspath(__file__)) if '__file__' in globals() else FRAMES_DIR, 'run.log')


def log(msg):
    try:
        with open(LOG, 'a', encoding='utf-8') as f:
            f.write('%s %s\n' % (time.strftime('%H:%M:%S'), msg))
    except Exception:
        pass


def rotate(v, k, theta):
    c, s = math.cos(theta), math.sin(theta)
    cross = k.crossProduct(v)
    dot = k.dotProduct(v)
    return adsk.core.Vector3D.create(
        v.x * c + cross.x * s + k.x * dot * (1 - c),
        v.y * c + cross.y * s + k.y * dot * (1 - c),
        v.z * c + cross.z * s + k.z * dot * (1 - c))


def needed(state, t):
    """True if the frame at fraction t of the turn is needed by series 'state'."""
    if state == 0: return t <= FIRST_IN[1] or t >= ALL_OUT[0]
    if state == 1: return FIRST_IN[0] <= t <= SECOND_IN[1]
    if state == 2: return SECOND_IN[0] <= t <= THIRD_IN[1]
    return THIRD_IN[0] <= t <= ALL_OUT[1]


def prepare(design, app):
    """White PETG on the three parts; the old scan without photos stays hidden."""
    root = design.rootComponent
    existing = design.appearances.itemByName(MATERIAL)
    if existing is None:
        lib = app.materialLibraries.itemByName('Fusion Appearance Library')
        existing = design.appearances.addByCopy(lib.appearances.itemByName(MATERIAL_BASE), MATERIAL)
    parts = {}
    for occ in root.allOccurrences:
        if occ.component.name in PART_NAMES:
            parts[occ.component.name] = occ
            for body in occ.component.bRepBodies:
                body.appearance = existing
    scan = None
    for m in root.meshBodies:
        if m.name == OLD_SCAN_NAME:
            m.isLightBulbOn = False
        elif m.name == SCAN_NAME:
            scan = m
    missing = [n for n in PART_NAMES if n not in parts] + ([] if scan else [SCAN_NAME])
    if missing:
        raise RuntimeError('Parts not found: ' + ', '.join(missing))
    return parts, scan


def set_state(state, parts, scan):
    scan.isLightBulbOn = True
    for i, n in enumerate(PART_NAMES):
        parts[n].isLightBulbOn = state >= i + 1
    adsk.doEvents()


def run(context):
    log('run() started')
    app = adsk.core.Application.get()
    ui = app.userInterface
    saved_cam = None
    vis = {}
    parts = {}
    try:
        design = adsk.fusion.Design.cast(app.activeProduct)
        if not design:
            raise RuntimeError('Open the case design before running the script.')
        parts, scan = prepare(design, app)
        vis = {n: parts[n].isLightBulbOn for n in parts}
        if not design.renderManager.isRenderWorkspaceActive:
            design.renderManager.activateRenderWorkspace()

        center = adsk.core.Point3D.create(*CENTER_CM)
        up = adsk.core.Vector3D.create(*UP)
        cur = app.activeViewport.camera
        saved_cam = cur
        fov = cur.perspectiveAngle if cur.cameraType == adsk.core.CameraTypes.PerspectiveCameraType else 0.6
        dist = FIT * RADIUS_CM / math.tan(fov / 2) / 1.6
        el = math.radians(ELEVATION_DEG)
        h = rotate(adsk.core.Vector3D.create(0, 0, 1), up, math.radians(AZIMUTH0_DEG))
        offset = adsk.core.Vector3D.create(
            dist * (math.cos(el) * h.x + math.sin(el) * up.x),
            dist * (math.cos(el) * h.y + math.sin(el) * up.y),
            dist * (math.cos(el) * h.z + math.sin(el) * up.z))
        log('camera: dist=%.2f fov=%.3f el=%.0f' % (dist, fov, ELEVATION_DEG))

        rendering = design.renderManager.rendering
        rendering.resolution = RESOLUTION
        rendering.renderQuality = QUALITY
        rendering.isBackgroundTransparent = False

        def queue(state, indices, out_dir):
            os.makedirs(out_dir, exist_ok=True)
            set_state(state, parts, scan)
            n = 0
            for i in indices:
                path = os.path.join(out_dir, 'frame_%04d.png' % i)
                if os.path.exists(path):
                    continue
                cam = app.activeViewport.camera
                eye = center.copy()
                eye.translateBy(rotate(offset, up, 2 * math.pi * i / FRAMES))
                cam.eye = eye
                cam.target = center
                cam.upVector = up
                app.activeViewport.camera = cam
                adsk.doEvents()
                if rendering.startLocalRender(path, cam):
                    n += 1
                else:
                    log('startLocalRender failed: state %d frame %d' % (state, i))
                adsk.doEvents()
            return n

        total = 0
        if JOB:
            by_state = {}
            for state, i in JOB['frames']:
                by_state.setdefault(state, []).append(i)
            for state in sorted(by_state):
                total += queue(state, by_state[state], JOB['dir'])
        else:
            for state in range(4):
                idx = [i for i in range(FRAMES) if needed(state, i / FRAMES)
                       or needed(state, (i - 1) / FRAMES) or needed(state, (i + 1) / FRAMES)]
                n = queue(state, idx, os.path.join(FRAMES_DIR, 's%d' % state))
                log('series s%d queued: %d' % (state, n))
                total += n
        log('total queued: %d' % total)
        if SHOW_DIALOGS:
            ui.messageBox('%d renders queued. Leave Fusion open until they finish.' % total)
        return total
    except Exception:
        log(traceback.format_exc())
        if SHOW_DIALOGS:
            ui.messageBox('Error:\n{}'.format(traceback.format_exc()))
        raise
    finally:
        try:
            for n, v in vis.items():
                parts[n].isLightBulbOn = v
        except Exception:
            pass
        try:
            if saved_cam:
                app.activeViewport.camera = saved_cam
        except Exception:
            pass
