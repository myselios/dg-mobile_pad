import java.util.List;
import local.trackpad.Hid;

/** Run with java -ea (build.sh does). */
public class HidTest {
    static void check(boolean ok, String what) { if (!ok) throw new AssertionError(what); }

    public static void main(String[] a) {
        List<byte[]> r = Hid.move(0, 300, -200, 0);
        int sx = 0, sy = 0;
        for (byte[] b : r) {
            check(b.length == 4, "4-byte report");
            check(b[1] >= -127 && b[2] >= -127, "never -128 (outside the descriptor's logical min)");
            sx += b[1]; sy += b[2];
        }
        check(sx == 300 && sy == -200, "large move is split, not clipped: " + sx + "," + sy);
        check(r.size() == 3, "300 needs 3 steps of <=127");
        for (byte[] b : r) check(b[0] == 0, "buttons kept on every split report");

        List<byte[]> click = Hid.move(1, 0, 0, 0);
        check(click.size() == 1 && click.get(0)[0] == 1 && click.get(0)[1] == 0, "button-only change still sends one report");

        List<byte[]> held = Hid.move(1, 130, 0, 0);
        for (byte[] b : held) check(b[0] == 1, "drag keeps the button down across split reports");

        System.out.println("HidTest OK");
    }
}
