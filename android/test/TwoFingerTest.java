import local.trackpad.TwoFinger;

/** Run with java -ea (build.sh does). */
public class TwoFingerTest {
    static void check(boolean ok, String what) { if (!ok) throw new AssertionError(what); }

    public static void main(String[] a) {
        TwoFinger t = new TwoFinger(12, 60, 8);  // lock after 12dp, swipe at 60dp, 8dp per wheel step

        // vertical: nothing until the axis locks, then the travel so far scrolls
        check(t.feed(0, 5) == TwoFinger.NONE && t.scroll == 0, "below lock distance: nothing");
        check(t.feed(1, 10) == TwoFinger.NONE && t.scroll == 1, "locks vertical, 15dp so far = 1 step");
        t.feed(30, 0);
        check(t.scroll == 0, "once vertical, sideways drift never fires or scrolls");
        t.feed(0, 16);
        check(t.scroll == 2, "vertical keeps scrolling (7 left + 16 = 23 -> 2)");

        // horizontal left -> BACK, once per gesture, never scrolls
        t.reset();
        check(t.feed(-10, 1) == TwoFinger.NONE, "below lock");
        check(t.feed(-30, 2) == TwoFinger.NONE && t.scroll == 0, "locked horizontal, not far enough, no scroll");
        check(t.feed(-30, 0) == TwoFinger.BACK, "left swipe past 60dp = back");
        check(t.feed(-40, 0) == TwoFinger.NONE, "fires only once per gesture");
        check(t.feed(0, 50) == TwoFinger.NONE && t.scroll == 0, "horizontal gesture never scrolls");

        t.reset();
        t.feed(20, 0);
        check(t.feed(45, 3) == TwoFinger.FORWARD, "right swipe = forward");

        System.out.println("TwoFingerTest OK");
    }
}
