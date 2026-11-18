package local.trackpad;

import java.util.ArrayList;
import java.util.List;

/** Bluetooth HID mouse: report descriptor and report encoding. Pure Java so it is unit-tested in the build. */
public final class Hid {
    public static final int MOUSE_ID = 1;

    // Mouse with report ID 1: 3 buttons, relative X, Y, wheel as int8 (-127..127).
    public static final byte[] DESCRIPTOR = bytes(
        0x05, 0x01, 0x09, 0x02, 0xA1, 0x01, 0x85, MOUSE_ID,
        0x09, 0x01, 0xA1, 0x00,
        0x05, 0x09, 0x19, 0x01, 0x29, 0x03, 0x15, 0x00, 0x25, 0x01, 0x95, 0x03, 0x75, 0x01, 0x81, 0x02,
        0x95, 0x01, 0x75, 0x05, 0x81, 0x03,
        0x05, 0x01, 0x09, 0x30, 0x09, 0x31, 0x09, 0x38, 0x15, 0x81, 0x25, 0x7F, 0x75, 0x08, 0x95, 0x03, 0x81, 0x06,
        0xC0, 0xC0);

    /** Reports for one move: split into steps of at most 127 so big moves are not clipped. Always at least one. */
    public static List<byte[]> move(int buttons, int dx, int dy, int wheel) {
        List<byte[]> out = new ArrayList<>();
        do {
            int sx = clamp(dx), sy = clamp(dy), sw = clamp(wheel);
            out.add(new byte[] {(byte) buttons, (byte) sx, (byte) sy, (byte) sw});
            dx -= sx; dy -= sy; wheel -= sw;
        } while (dx != 0 || dy != 0 || wheel != 0);
        return out;
    }

    /** Two-finger scroll: finger travel (dp) to wheel steps, keeping the remainder so slow drags still scroll. */
    public static final class Wheel {
        private final float stepDp;
        private float acc;

        public Wheel(float stepDp) { this.stepDp = stepDp; }

        public int add(float dyDp) {
            acc += dyDp;
            int n = (int) (acc / stepDp);
            acc -= n * stepDp;
            return n;
        }

        public void reset() { acc = 0; }
    }

    private static int clamp(int v) { return Math.max(-127, Math.min(127, v)); }

    private static byte[] bytes(int... v) {
        byte[] b = new byte[v.length];
        for (int i = 0; i < v.length; i++) b[i] = (byte) v[i];
        return b;
    }
}
