package local.trackpad;

import android.Manifest;
import android.app.Activity;
import android.bluetooth.BluetoothAdapter;
import android.bluetooth.BluetoothClass;
import android.bluetooth.BluetoothDevice;
import android.bluetooth.BluetoothHidDevice;
import android.bluetooth.BluetoothHidDeviceAppSdpSettings;
import android.bluetooth.BluetoothManager;
import android.bluetooth.BluetoothProfile;
import android.content.Intent;
import android.content.pm.PackageManager;
import android.content.res.ColorStateList;
import android.graphics.Typeface;
import android.graphics.drawable.GradientDrawable;
import android.graphics.drawable.RippleDrawable;
import android.os.Build;
import android.os.Bundle;
import android.util.Log;
import android.view.Gravity;
import android.view.MotionEvent;
import android.view.View;
import android.view.WindowManager;
import android.widget.FrameLayout;
import android.widget.LinearLayout;
import android.widget.ScrollView;
import android.widget.TextView;

/** Stage 1 (feasibility): register as a BT mouse, connect to a paired host, one-finger move, tap to click. */
public class MainActivity extends Activity {
    private static final float SPEED = 2.0f;   // mouse counts per dp of finger travel (host adds its own acceleration)
    private static final long TAP_MS = 220;
    private static final float TAP_DP = 10;

    private BluetoothAdapter bt;
    private BluetoothHidDevice hid;
    private BluetoothDevice host;
    private LinearLayout hosts;
    private float density, lastX, lastY, fracX, fracY, moved;
    private long downT;

    // Material 3 dark color roles. On Android 12+ they follow the wallpaper (dynamic color).
    private int cPrimary = 0xFFD0BCFF, cOnPrimaryContainer = 0xFFEADDFF, cPrimaryContainer = 0xFF4F378B;
    private int cSurface = 0xFF141218, cSurfaceContainer = 0xFF211F26, cSurfaceHigh = 0xFF2B2930;
    private int cOnSurface = 0xFFE6E0E9, cOnSurfaceVariant = 0xFFCAC4D0, cOutline = 0xFF49454F;
    private static final int OK = 0xFF7FD99A, WAIT = 0xFFFFC26B, ERR = 0xFFF2B8B5;

    private TextView statusText, padHint;
    private View statusDot, pad;
    private ScrollView hostScroll;
    private BluetoothDevice connecting;

    private int dp(float v) { return Math.round(v * density); }

    private GradientDrawable shape(int color, float radiusDp, int strokeColor) {
        GradientDrawable g = new GradientDrawable();
        g.setColor(color);
        g.setCornerRadius(dp(radiusDp));
        if (strokeColor != 0) g.setStroke(dp(1), strokeColor);
        return g;
    }

    private RippleDrawable ripple(GradientDrawable content) {
        return new RippleDrawable(ColorStateList.valueOf(0x22FFFFFF), content, null);
    }

    private TextView text(String s, float sp, int color, boolean bold) {
        TextView t = new TextView(this);
        t.setText(s);
        t.setTextSize(sp);
        t.setTextColor(color);
        if (bold) t.setTypeface(Typeface.create("sans-serif-medium", Typeface.NORMAL));
        return t;
    }

    private void loadDynamicColors() {
        if (Build.VERSION.SDK_INT < 31) return;
        cPrimary = getColor(android.R.color.system_accent1_200);
        cPrimaryContainer = getColor(android.R.color.system_accent1_700);
        cOnPrimaryContainer = getColor(android.R.color.system_accent1_100);
        cSurface = getColor(android.R.color.system_neutral1_900);
        cSurfaceContainer = getColor(android.R.color.system_neutral1_800);
        cSurfaceHigh = getColor(android.R.color.system_neutral2_800);
        cOnSurface = getColor(android.R.color.system_neutral1_100);
        cOnSurfaceVariant = getColor(android.R.color.system_neutral2_200);
        cOutline = getColor(android.R.color.system_neutral2_700);
    }

    @Override protected void onCreate(Bundle b) {
        super.onCreate(b);
        getWindow().addFlags(WindowManager.LayoutParams.FLAG_KEEP_SCREEN_ON);
        density = getResources().getDisplayMetrics().density;
        bt = getSystemService(BluetoothManager.class).getAdapter();
        loadDynamicColors();
        getWindow().setStatusBarColor(cSurface);
        getWindow().setNavigationBarColor(cSurface);

        LinearLayout root = new LinearLayout(this);
        root.setOrientation(LinearLayout.VERTICAL);
        root.setBackgroundColor(cSurface);
        root.setPadding(dp(16), dp(20), dp(16), dp(16));

        // Header: title + "add device" tonal icon button
        LinearLayout header = new LinearLayout(this);
        header.setGravity(Gravity.CENTER_VERTICAL);
        header.addView(text("트랙패드", 24, cOnSurface, false), new LinearLayout.LayoutParams(0, -2, 1f));
        TextView add = text("＋", 22, cOnPrimaryContainer, false);
        add.setGravity(Gravity.CENTER);
        add.setBackground(ripple(shape(cPrimaryContainer, 24, 0)));
        add.setContentDescription("새 기기 추가: 다른 기기에서 이 폰이 보이게 하기");
        add.setOnClickListener(v -> startActivity(new Intent(BluetoothAdapter.ACTION_REQUEST_DISCOVERABLE)
                .putExtra(BluetoothAdapter.EXTRA_DISCOVERABLE_DURATION, 120)));
        header.addView(add, new LinearLayout.LayoutParams(dp(48), dp(48)));
        root.addView(header);

        // Status chip: colored dot + text
        LinearLayout chip = new LinearLayout(this);
        chip.setGravity(Gravity.CENTER_VERTICAL);
        chip.setPadding(dp(12), dp(8), dp(14), dp(8));
        chip.setBackground(shape(cSurfaceHigh, 999, 0));
        statusDot = new View(this);
        statusDot.setBackground(shape(WAIT, 999, 0));
        chip.addView(statusDot, new LinearLayout.LayoutParams(dp(8), dp(8)));
        statusText = text("준비 중…", 14, cOnSurface, false);
        statusText.setPadding(dp(8), 0, 0, 0);
        chip.addView(statusText);
        LinearLayout.LayoutParams chipLp = new LinearLayout.LayoutParams(-2, -2);
        chipLp.topMargin = dp(8);
        root.addView(chip, chipLp);

        TextView label = text("기기", 14, cOnSurfaceVariant, true);
        label.setPadding(dp(4), dp(20), 0, dp(8));
        root.addView(label);

        hosts = new LinearLayout(this);
        hosts.setOrientation(LinearLayout.VERTICAL);
        hostScroll = new ScrollView(this);  // many paired devices must not push the pad off screen
        hostScroll.setVerticalScrollBarEnabled(false);
        hostScroll.addView(hosts);
        root.addView(hostScroll, new LinearLayout.LayoutParams(-1, -2));

        // Touch pad
        FrameLayout padBox = new FrameLayout(this);
        padBox.setBackground(shape(cSurfaceContainer, 28, cOutline));
        padHint = text("", 15, cOnSurfaceVariant, false);
        padHint.setGravity(Gravity.CENTER);
        padHint.setLineSpacing(dp(4), 1f);
        padBox.addView(padHint, new FrameLayout.LayoutParams(-1, -1));
        padBox.setContentDescription("트랙패드 영역");
        padBox.setOnTouchListener(this::onPad);
        pad = padBox;
        LinearLayout.LayoutParams padLp = new LinearLayout.LayoutParams(-1, 0, 1f);
        padLp.topMargin = dp(16);
        root.addView(padBox, padLp);
        setContentView(root);
        renderPad();

        if (Build.VERSION.SDK_INT >= 31 && checkSelfPermission(Manifest.permission.BLUETOOTH_CONNECT)
                != PackageManager.PERMISSION_GRANTED) {
            requestPermissions(new String[] {Manifest.permission.BLUETOOTH_CONNECT,
                    Manifest.permission.BLUETOOTH_ADVERTISE}, 1);
        } else {
            start();
        }
    }

    private void renderPad() {
        boolean on = host != null;
        padHint.setText(on ? "한 손가락으로 움직이기\n탭하면 클릭" : "위에서 연결할 기기를 고르세요");
        padHint.setAlpha(on ? 0.7f : 0.5f);
    }

    @Override public void onRequestPermissionsResult(int code, String[] perms, int[] res) {
        if (res.length > 0 && res[0] == PackageManager.PERMISSION_GRANTED) start();
        else say("블루투스 권한이 필요합니다. 앱을 다시 열어 허용해 주세요.");
    }

    private int sent, failed;

    private void say(String s) { status(s, ERR); }

    private void status(String s, int dot) {
        Log.i("Trackpad", s);
        runOnUiThread(() -> { statusText.setText(s); ((GradientDrawable) statusDot.getBackground()).setColor(dot); });
    }

    private void start() {
        if (bt == null || !bt.isEnabled()) { say("블루투스를 켜고 앱을 다시 열어 주세요."); return; }
        status("블루투스 마우스 기능 준비 중…", WAIT);
        if (!bt.getProfileProxy(this, new BluetoothProfile.ServiceListener() {
            @Override public void onServiceConnected(int profile, BluetoothProfile proxy) {
                hid = (BluetoothHidDevice) proxy;
                BluetoothHidDeviceAppSdpSettings sdp = new BluetoothHidDeviceAppSdpSettings(
                        "트랙패드", "Phone trackpad", "local", BluetoothHidDevice.SUBCLASS1_MOUSE, Hid.DESCRIPTOR);
                try {
                    if (!hid.registerApp(sdp, null, null, getMainExecutor(), callback))
                        say("등록 실패: 이 폰이 블루투스 마우스 기능을 막아둔 것 같습니다.");
                } catch (SecurityException e) { say("권한 오류: " + e.getMessage()); }
            }
            @Override public void onServiceDisconnected(int profile) { hid = null; host = null; say("블루투스 서비스가 끊겼습니다."); }
        }, BluetoothProfile.HID_DEVICE)) {
            say("이 폰은 블루투스 마우스 기능(HID Device)을 지원하지 않습니다.");
        }
    }

    private final BluetoothHidDevice.Callback callback = new BluetoothHidDevice.Callback() {
        @Override public void onAppStatusChanged(BluetoothDevice d, boolean registered) {
            if (registered) { if (host == null) status("연결할 기기를 고르세요", WAIT); runOnUiThread(MainActivity.this::listHosts); }
            else { host = null; say("마우스 기능 등록이 해제되었습니다."); }
        }
        @Override public void onSetProtocol(BluetoothDevice d, byte protocol) { Log.i("Trackpad", "host set protocol " + protocol); }
        @Override public void onGetReport(BluetoothDevice d, byte type, byte id, int size) {
            Log.i("Trackpad", "host get report type " + type + " id " + id);
            try { hid.replyReport(d, type, id, new byte[4]); } catch (SecurityException ignored) { }
        }
        @Override public void onSetReport(BluetoothDevice d, byte type, byte id, byte[] data) {
            Log.i("Trackpad", "host set report type " + type + " id " + id);
            try { hid.reportError(d, BluetoothHidDevice.ERROR_RSP_SUCCESS); } catch (SecurityException ignored) { }
        }
        @Override public void onConnectionStateChanged(BluetoothDevice d, int state) {
            Log.i("Trackpad", "state " + state + " " + d.getAddress());
            if (state == BluetoothProfile.STATE_CONNECTED) { host = d; connecting = null; status(name(d) + "에 연결됨", OK); }
            else if (state == BluetoothProfile.STATE_DISCONNECTED && d.equals(host)) { host = null; status(name(d) + " 연결 끊김", ERR); }
            else if (state == BluetoothProfile.STATE_DISCONNECTED && d.equals(connecting)) { connecting = null; status(name(d) + " 연결 실패", ERR); }
            else if (state == BluetoothProfile.STATE_CONNECTING) { connecting = d; status(name(d) + " 연결 중…", WAIT); }
            runOnUiThread(() -> { listHosts(); renderPad(); });
        }
    };

    private String name(BluetoothDevice d) {
        try { return d.getName(); } catch (SecurityException e) { return d.getAddress(); }
    }

    /** Only hosts that can use a mouse: computers, phones/tablets (hide headphones, cars, watches, mice). */
    private static boolean isHostType(BluetoothDevice d) {
        if (d.getType() == BluetoothDevice.DEVICE_TYPE_LE) return false;  // BLE-only: can't host a classic HID mouse
        BluetoothClass c = d.getBluetoothClass();
        if (c == null) return true;
        int m = c.getMajorDeviceClass();
        return m == BluetoothClass.Device.Major.COMPUTER || m == BluetoothClass.Device.Major.PHONE
                || m == BluetoothClass.Device.Major.UNCATEGORIZED;
    }

    private void listHosts() {
        hosts.removeAllViews();
        int shown = 0;
        try {
            for (BluetoothDevice d : bt.getBondedDevices()) {
                if (!isHostType(d)) continue;
                hosts.addView(hostCard(d));
                shown++;
            }
        } catch (SecurityException e) { say("권한 오류: " + e.getMessage()); }
        if (shown == 0) {
            TextView none = text("페어링된 컴퓨터·태블릿이 없습니다.\n오른쪽 위 ＋ 를 눌러 기기에서 이 폰을 추가하세요.", 14, cOnSurfaceVariant, false);
            none.setPadding(dp(4), 0, 0, 0);
            hosts.addView(none);
        }
        // at most ~3 cards tall, the rest scrolls
        hostScroll.getLayoutParams().height = shown > 3 ? dp(3 * 80) : -2;
        hostScroll.requestLayout();
    }

    private View hostCard(BluetoothDevice d) {
        boolean on = d.equals(host), wait = d.equals(connecting);
        boolean computer = d.getBluetoothClass() != null
                && d.getBluetoothClass().getMajorDeviceClass() == BluetoothClass.Device.Major.COMPUTER;

        LinearLayout card = new LinearLayout(this);
        card.setGravity(Gravity.CENTER_VERTICAL);
        card.setPadding(dp(16), dp(12), dp(16), dp(12));
        card.setMinimumHeight(dp(72));
        card.setBackground(ripple(shape(on ? cPrimaryContainer : cSurfaceContainer, 16, 0)));

        TextView icon = text(computer ? "💻" : "📱", 20, cOnSurface, false);
        icon.setGravity(Gravity.CENTER);
        icon.setBackground(shape(on ? cPrimary : cSurfaceHigh, 999, 0));
        card.addView(icon, new LinearLayout.LayoutParams(dp(44), dp(44)));

        LinearLayout col = new LinearLayout(this);
        col.setOrientation(LinearLayout.VERTICAL);
        col.setPadding(dp(16), 0, 0, 0);
        col.addView(text(name(d), 16, on ? cOnPrimaryContainer : cOnSurface, true));
        col.addView(text(on ? "연결됨 · 탭하면 연결 해제" : wait ? "연결 중…" : "탭해서 연결", 13,
                on ? cOnPrimaryContainer : cOnSurfaceVariant, false));
        card.addView(col, new LinearLayout.LayoutParams(0, -2, 1f));

        card.setContentDescription(name(d) + (on ? ", 연결됨" : ", 연결 안 됨"));
        card.setOnClickListener(v -> {
            if (hid == null) return;
            try {
                if (on) { hid.disconnect(d); return; }
                if (host != null) hid.disconnect(host);  // one host at a time
                if (!hid.connect(d)) say(name(d) + " 연결 요청 실패");
            } catch (SecurityException e) { say("권한 오류: " + e.getMessage()); }
        });
        LinearLayout.LayoutParams lp = new LinearLayout.LayoutParams(-1, -2);
        lp.bottomMargin = dp(8);
        card.setLayoutParams(lp);
        return card;
    }

    private void send(int buttons, int dx, int dy) {
        if (hid == null || host == null) return;
        try {
            for (byte[] r : Hid.move(buttons, dx, dy, 0)) {
                if (hid.sendReport(host, Hid.MOUSE_ID, r)) sent++; else failed++;
            }
            if ((sent + failed) % 200 == 1) Log.i("Trackpad", "reports sent " + sent + " failed " + failed);
        } catch (SecurityException e) { say("권한 오류: " + e.getMessage()); }
    }

    private boolean onPad(View v, MotionEvent e) {
        switch (e.getActionMasked()) {
            case MotionEvent.ACTION_DOWN:
                pad.setAlpha(0.85f);
                lastX = e.getX(); lastY = e.getY(); fracX = fracY = 0; moved = 0; downT = e.getEventTime();
                return true;
            case MotionEvent.ACTION_MOVE: {
                float dx = (e.getX() - lastX) / density, dy = (e.getY() - lastY) / density;
                lastX = e.getX(); lastY = e.getY();
                moved += Math.abs(dx) + Math.abs(dy);
                fracX += dx * SPEED; fracY += dy * SPEED;
                int ix = (int) fracX, iy = (int) fracY;  // keep the remainder so slow moves still add up
                fracX -= ix; fracY -= iy;
                if (ix != 0 || iy != 0) send(0, ix, iy);
                return true;
            }
            case MotionEvent.ACTION_UP:
                pad.setAlpha(1f);
                if (e.getEventTime() - downT < TAP_MS && moved < TAP_DP) { send(1, 0, 0); send(0, 0, 0); }
                return true;
            case MotionEvent.ACTION_CANCEL:
                pad.setAlpha(1f);
                send(0, 0, 0);  // never leave a button down
                return true;
        }
        return false;
    }

    @Override protected void onDestroy() {
        if (hid != null) {
            try { hid.unregisterApp(); } catch (SecurityException ignored) { }
            bt.closeProfileProxy(BluetoothProfile.HID_DEVICE, hid);
        }
        super.onDestroy();
    }
}
