package `in`.iris.app

import android.Manifest
import android.app.Activity
import android.content.Intent
import android.content.pm.PackageManager
import android.graphics.Color
import android.os.Bundle
import android.view.Gravity
import android.view.View
import android.widget.*
import java.io.File
import kotlin.concurrent.thread

class MainActivity : Activity() {
    private lateinit var status: TextView
    private lateinit var list: TextView
    private lateinit var recordBtn: Button
    private var recording = false

    private val prefs by lazy { getSharedPreferences("iris", MODE_PRIVATE) }

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        requestPermissions(arrayOf(Manifest.permission.RECORD_AUDIO, Manifest.permission.POST_NOTIFICATIONS), 1)

        val root = LinearLayout(this).apply {
            orientation = LinearLayout.VERTICAL
            setPadding(48, 64, 48, 48)
        }
        fun label(t: String) = TextView(this).apply { text = t; textSize = 13f; setTextColor(Color.GRAY) }
        fun field(hint: String, key: String) = EditText(this).apply {
            setHint(hint); setText(prefs.getString(key, "")); textSize = 13f
            setOnFocusChangeListener { _, _ -> prefs.edit().putString(key, text.toString()).apply() }
        }

        status = TextView(this).apply { text = "Iris - private meeting notes"; textSize = 18f; gravity = Gravity.CENTER }
        recordBtn = Button(this).apply {
            text = "Start recording"
            setOnClickListener { toggleRecording() }
        }
        root.addView(status); root.addView(recordBtn)

        root.addView(label("Laptop ingest URL (same Wi-Fi, e.g. http://192.168.1.5:8472)"))
        root.addView(field("http://...:8472", "laptop"))
        root.addView(Button(this).apply {
            text = "Send last recording to laptop"
            setOnClickListener { sendToLaptop() }
        })

        root.addView(label("Sync relay URL + token"))
        root.addView(field("http://...:8471", "relay"))
        root.addView(field("sync token", "token"))
        root.addView(Button(this).apply {
            text = "Sync notes now"
            setOnClickListener { syncNow() }
        })

        root.addView(label("age secret key (AGE-SECRET-KEY-1...) - stays on this phone"))
        root.addView(field("AGE-SECRET-KEY-1...", "agekey"))

        root.addView(Button(this).apply {
            text = "Enable meeting nudges (Zoom/Meet/Teams)"
            setOnClickListener { enableNudges() }
        })

        list = TextView(this).apply { textSize = 12f; setPadding(0, 24, 0, 0) }
        val scroll = ScrollView(this).apply { addView(list) }
        root.addView(scroll, LinearLayout.LayoutParams(LinearLayout.LayoutParams.MATCH_PARENT, 0, 1f))
        setContentView(root)
    }

    private fun toast(msg: String) = runOnUiThread { Toast.makeText(this, msg, Toast.LENGTH_LONG).show() }

    private fun toggleRecording() {
        if (recording) {
            startService(Intent(this, RecorderService::class.java).setAction(RecorderService.ACTION_STOP))
            recording = false; recordBtn.text = "Start recording"; status.text = "saving..."
        } else {
            if (checkSelfPermission(Manifest.permission.RECORD_AUDIO) != PackageManager.PERMISSION_GRANTED) {
                toast("mic permission needed"); return
            }
            startForegroundService(Intent(this, RecorderService::class.java).setAction(RecorderService.ACTION_START))
            recording = true; recordBtn.text = "Stop recording"; status.text = "recording (local only)"
        }
    }

    private fun sendToLaptop() {
        val laptop = prefs.getString("laptop", "") ?: ""
        val token = prefs.getString("token", "") ?: ""
        val f = RecorderService.lastFile ?: run { toast("no recording yet"); return }
        if (laptop.isBlank() || token.isBlank()) { toast("set laptop URL + token first"); return }
        status.text = "uploading to your laptop..."
        thread {
            try {
                val res = SyncClient.uploadForIngest(laptop, token, f, f.nameWithoutExtension)
                val integ = res.optJSONObject("integrity")
                toast("transcribed: ${res.getString("meeting")} (${integ?.optInt("passed")}/${integ?.optInt("checked")} claims verified)")
                runOnUiThread { status.text = "sent ${f.name} -> ${res.getString("meeting")}" }
            } catch (e: Exception) { toast("failed: ${e.message}"); runOnUiThread { status.text = "upload failed" } }
        }
    }

    private fun syncNow() {
        val relay = prefs.getString("relay", "") ?: ""
        val token = prefs.getString("token", "") ?: ""
        val key = prefs.getString("agekey", "") ?: ""
        if (relay.isBlank() || token.isBlank()) { toast("set relay URL + token first"); return }
        status.text = "syncing..."
        thread {
            try {
                val meetings = SyncClient.listMeetings(relay, token)
                val sb = StringBuilder()
                for (m in meetings.takeLast(20).reversed()) {
                    val b = SyncClient.pullBundle(relay, token, m.id)
                    val title = b.optJSONObject("meta")?.optString("title") ?: m.id
                    sb.append("== $title\n")
                    when {
                        b.has("notes_age") -> {
                            if (key.isBlank()) sb.append("(encrypted - import your age key to read)\n")
                            else if (!AgeDecrypt.supported()) sb.append("(encrypted - needs Android 13+ to read)\n")
                            else try {
                                sb.append(String(AgeDecrypt.decrypt(b.getString("notes_age"), key)))
                            } catch (e: Exception) { sb.append("(decrypt failed: ${e.message})\n") }
                        }
                        b.has("notes") -> sb.append(b.getString("notes"))
                        else -> sb.append("(no notes)\n")
                    }
                    sb.append("\n")
                }
                runOnUiThread { list.text = sb.toString(); status.text = "synced ${meetings.size} meetings" }
            } catch (e: Exception) { toast("sync failed: ${e.message}"); runOnUiThread { status.text = "sync failed" } }
        }
    }

    private fun enableNudges() {
        if (!MeetingNudge.hasUsageAccess(this)) {
            toast("grant Usage Access for Iris, then come back")
            startActivity(MeetingNudge.usageAccessIntent())
            return
        }
        MeetingNudge.start(this)
        toast("nudges on: I'll notice when Zoom/Meet/Teams is in front")
    }
}
