package local.trackpad;

import android.Manifest;
import android.app.Activity;
import android.bluetooth.BluetoothAdapter;
import android.bluetooth.BluetoothDevice;
import android.bluetooth.BluetoothHidDevice;
import android.bluetooth.BluetoothHidDeviceAppSdpSettings;
import android.bluetooth.BluetoothManager;
import android.bluetooth.BluetoothProfile;
import android.content.Intent;
import android.content.pm.PackageManager;
import android.graphics.Color;
import android.os.Build;
import android.os.Bundle;
import android.util.Log;
import android.view.Gravity;
import android.view.MotionEvent;
import android.view.View;
import android.view.WindowManager;
import android.widget.Button;
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
    private TextView status;
    private LinearLayout hosts;
    private float density, lastX, lastY, fracX, fracY, moved;
    private long downT;

    @Override protected void onCreate(Bundle b) {
        super.onCreate(b);
        getWindow().addFlags(WindowManager.LayoutParams.FLAG_KEEP_SCREEN_ON);
        density = getResources().getDisplayMetrics().density;
        bt = getSystemService(BluetoothManager.class).getAdapter();

        LinearLayout root = new LinearLayout(this);
        root.setOrientation(LinearLayout.VERTICAL);
        root.setBackgroundColor(0xFF111111);
        int p = (int) (16 * density);
        root.setPadding(p, p, p, p);

        status = new TextView(this);
        status.setTextColor(Color.WHITE);
        status.setTextSize(16);
        root.addView(status);

        Button visible = new Button(this);
        visible.setText("다른 기기에서 이 폰 보이게 하기 (2분)");
        visible.setOnClickListener(v -> startActivity(new Intent(BluetoothAdapter.ACTION_REQUEST_DISCOVERABLE)
                .putExtra(BluetoothAdapter.EXTRA_DISCOVERABLE_DURATION, 120)));
        root.addView(visible);

        hosts = new LinearLayout(this);
        hosts.setOrientation(LinearLayout.VERTICAL);
        ScrollView hostScroll = new ScrollView(this);  // many paired devices must not push the pad off screen
        hostScroll.addView(hosts);
        root.addView(hostScroll, new LinearLayout.LayoutParams(LinearLayout.LayoutParams.MATCH_PARENT, (int) (160 * density)));

        TextView pad = new TextView(this);
        pad.setText("한 손가락: 커서 이동\n탭: 클릭");
        pad.setGravity(Gravity.CENTER);
        pad.setTextColor(0xFF555555);
        pad.setBackgroundColor(0xFF1C1C1E);
        pad.setOnTouchListener(this::onPad);
        root.addView(pad, new LinearLayout.LayoutParams(LinearLayout.LayoutParams.MATCH_PARENT, 0, 1f));
        setContentView(root);

        if (Build.VERSION.SDK_INT >= 31 && checkSelfPermission(Manifest.permission.BLUETOOTH_CONNECT)
                != PackageManager.PERMISSION_GRANTED) {
            requestPermissions(new String[] {Manifest.permission.BLUETOOTH_CONNECT,
                    Manifest.permission.BLUETOOTH_ADVERTISE}, 1);
        } else {
            start();
        }
    }

    @Override public void onRequestPermissionsResult(int code, String[] perms, int[] res) {
        if (res.length > 0 && res[0] == PackageManager.PERMISSION_GRANTED) start();
        else say("블루투스 권한이 필요합니다. 앱을 다시 열어 허용해 주세요.");
    }

    private int sent, failed;

    private void say(String s) { Log.i("Trackpad", s); runOnUiThread(() -> status.setText(s)); }

    private void start() {
        if (bt == null || !bt.isEnabled()) { say("블루투스를 켜고 앱을 다시 열어 주세요."); return; }
        say("블루투스 마우스 기능 준비 중…");
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
            if (registered) { say("준비됨. 아래에서 연결할 기기를 누르세요.\n(목록에 없으면 먼저 폰 블루투스 설정에서 맥과 페어링)"); runOnUiThread(MainActivity.this::listHosts); }
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
            if (state == BluetoothProfile.STATE_CONNECTED) { host = d; say("연결됨: " + name(d)); }
            else if (state == BluetoothProfile.STATE_DISCONNECTED && d.equals(host)) { host = null; say("연결 끊김: " + name(d)); }
            else if (state == BluetoothProfile.STATE_CONNECTING) say("연결 중: " + name(d));
        }
    };

    private String name(BluetoothDevice d) {
        try { return d.getName(); } catch (SecurityException e) { return d.getAddress(); }
    }

    private void listHosts() {
        hosts.removeAllViews();
        try {
            for (BluetoothDevice d : bt.getBondedDevices()) {
                Button btn = new Button(this);
                btn.setText("연결: " + name(d));
                btn.setOnClickListener(v -> {
                    if (d.equals(host)) { say("이미 연결됨: " + name(d)); return; }
                    if (hid != null && !hid.connect(d)) say("연결 요청 실패: " + name(d));
                });
                hosts.addView(btn);
            }
        } catch (SecurityException e) { say("권한 오류: " + e.getMessage()); }
    }

    private void send(int buttons, int dx, int dy) {
        if (hid == null || host == null) return;
        try {
            for (byte[] r : Hid.move(buttons, dx, dy, 0)) {
                if (hid.sendReport(host, Hid.MOUSE_ID, r)) sent++; else failed++;
            }
            if ((sent + failed) % 50 == 1) say("연결됨: " + name(host) + "\n보낸 신호 " + sent + " / 실패 " + failed);
        } catch (SecurityException e) { say("권한 오류: " + e.getMessage()); }
    }

    private boolean onPad(View v, MotionEvent e) {
        switch (e.getActionMasked()) {
            case MotionEvent.ACTION_DOWN:
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
                if (e.getEventTime() - downT < TAP_MS && moved < TAP_DP) { send(1, 0, 0); send(0, 0, 0); }
                return true;
            case MotionEvent.ACTION_CANCEL:
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
