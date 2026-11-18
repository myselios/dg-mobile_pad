package local.trackpad;

import java.util.ArrayList;
import java.util.List;

/** Bluetooth HID mouse: report descriptor and report encoding. Pure Java so it is unit-tested in the build. */
public final class Hid {
    public static final int MOUSE_ID = 1, KEYBOARD_ID = 2, CONSUMER_ID = 3;
    public static final int MOD_GUI = 0x08;                         // left Command (macOS)
    public static final int KEY_LEFT_BRACKET = 0x2F, KEY_RIGHT_BRACKET = 0x30;
    public static final int AC_BACK = 0x224, AC_FORWARD = 0x225;    // consumer page: Android back/forward

    // Mouse with report ID 1: 3 buttons, relative X, Y, wheel as int8 (-127..127).
    public static final byte[] DESCRIPTOR = bytes(
        0x05, 0x01, 0x09, 0x02, 0xA1, 0x01, 0x85, MOUSE_ID,
        0x09, 0x01, 0xA1, 0x00,
        0x05, 0x09, 0x19, 0x01, 0x29, 0x03, 0x15, 0x00, 0x25, 0x01, 0x95, 0x03, 0x75, 0x01, 0x81, 0x02,
        0x95, 0x01, 0x75, 0x05, 0x81, 0x03,
        0x05, 0x01, 0x09, 0x30, 0x09, 0x31, 0x09, 0x38, 0x15, 0x81, 0x25, 0x7F, 0x75, 0x08, 0x95, 0x03, 0x81, 0x06,
        0xC0, 0xC0,
        // Keyboard, report ID 2: modifiers, reserved, 6 key codes
        0x05, 0x01, 0x09, 0x06, 0xA1, 0x01, 0x85, KEYBOARD_ID,
        0x05, 0x07, 0x19, 0xE0, 0x29, 0xE7, 0x15, 0x00, 0x25, 0x01, 0x75, 0x01, 0x95, 0x08, 0x81, 0x02,
        0x95, 0x01, 0x75, 0x08, 0x81, 0x01,
        0x95, 0x06, 0x75, 0x08, 0x15, 0x00, 0x25, 0x65, 0x05, 0x07, 0x19, 0x00, 0x29, 0x65, 0x81, 0x00,
        0xC0,
        // Consumer control, report ID 3: one 16-bit usage
        0x05, 0x0C, 0x09, 0x01, 0xA1, 0x01, 0x85, CONSUMER_ID,
        0x15, 0x00, 0x26, 0xFF, 0x03, 0x19, 0x00, 0x2A, 0xFF, 0x03, 0x75, 0x10, 0x95, 0x01, 0x81, 0x00,
        0xC0);

    /** Keyboard report (8 bytes). key(0, 0) is "all keys up". */
    public static byte[] key(int modifiers, int usage) {
        return new byte[] {(byte) modifiers, 0, (byte) usage, 0, 0, 0, 0, 0};
    }

    /** Consumer report (16-bit little-endian usage). consumer(0) is "released". */
    public static byte[] consumer(int usage) {
        return new byte[] {(byte) usage, (byte) (usage >> 8)};
    }

    public static int reportSize(int id) { return id == KEYBOARD_ID ? 8 : id == CONSUMER_ID ? 2 : 4; }

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
