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

        Hid.Wheel w = new Hid.Wheel(10);
        check(w.add(4) == 0, "below one step: nothing yet");
        check(w.add(7) == 1, "remainder carries over: 4+7 = one step");
        check(w.add(-12) == -1, "reverse direction steps negative");
        check(w.add(31) == 3, "big move gives several steps (-1 left over + 31 = 30)");
        w.reset();
        check(w.add(9) == 0, "reset drops the remainder");

        List<byte[]> scroll = Hid.move(0, 0, 0, -3);
        check(scroll.size() == 1 && scroll.get(0)[3] == -3, "wheel goes in byte 3");

        System.out.println("HidTest OK");
    }
}
