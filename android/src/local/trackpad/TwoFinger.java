package local.trackpad;

/**
 * Two-finger gesture: the first direction the fingers move decides it.
 * Vertical = scroll (wheel steps in {@link #scroll}); horizontal = one BACK/FORWARD per gesture.
 * Pure Java so it is unit-tested in the build.
 */
public final class TwoFinger {
    public static final int NONE = 0, BACK = 1, FORWARD = 2;

    private final float lockDp, swipeDp;
    private final Hid.Wheel wheel;
    private float tx, ty;
    private int axis;  // 0 = undecided, 1 = vertical, 2 = horizontal
    private boolean fired;
    /** Wheel steps produced by the last {@link #feed}. */
    public int scroll;

    public TwoFinger(float lockDp, float swipeDp, float stepDp) {
        this.lockDp = lockDp;
        this.swipeDp = swipeDp;
        this.wheel = new Hid.Wheel(stepDp);
    }

    public void reset() { tx = ty = 0; axis = 0; fired = false; scroll = 0; wheel.reset(); }

    public int feed(float dxDp, float dyDp) {
        scroll = 0;
        tx += dxDp;
        ty += dyDp;
        if (axis == 0) {
            if (Math.abs(tx) + Math.abs(ty) < lockDp) return NONE;
            axis = Math.abs(tx) > Math.abs(ty) ? 2 : 1;
            if (axis == 1) dyDp = ty;  // the travel before the lock counts too
        }
        if (axis == 1) { scroll = wheel.add(dyDp); return NONE; }
        if (!fired && Math.abs(tx) >= swipeDp) { fired = true; return tx < 0 ? BACK : FORWARD; }
        return NONE;
    }
}
