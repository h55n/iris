package `in`.iris.app

import android.Manifest
import android.animation.ValueAnimator
import android.app.Activity
import android.content.BroadcastReceiver
import android.content.Context
import android.content.Intent
import android.content.IntentFilter
import android.content.pm.PackageManager
import android.content.res.ColorStateList
import android.graphics.Color
import android.graphics.Typeface
import android.graphics.drawable.GradientDrawable
import android.graphics.drawable.RippleDrawable
import android.os.Bundle
import android.text.InputType
import android.view.Gravity
import android.view.View
import android.widget.*
import kotlin.concurrent.thread

class MainActivity : Activity() {

    // Iris palette: warm paper + plant accents (coral, lavender, orange, blue)
    private val bg = Color.parseColor("#FAF8F4")
    private val ink = Color.parseColor("#2B2926")
    private val gray = Color.parseColor("#8A857C")
    private val border = Color.parseColor("#E7E1D8")
    private val softBtn = Color.parseColor("#F1EDE7")
    private val coral = Color.parseColor("#DD6B4F")
    private val coralDark = Color.parseColor("#B94E38")
    private val coralTint = Color.parseColor("#F9E8E2")
    private val lavender = Color.parseColor("#8F7FC4")
    private val lavenderTint = Color.parseColor("#EFEBF8")
    private val blue = Color.parseColor("#6E97C4")
    private val blueTint = Color.parseColor("#E7EFF7")

    private lateinit var status: TextView
    private lateinit var statusCard: LinearLayout
    private lateinit var statusDot: View
    private lateinit var recordBtn: Button
    private lateinit var recList: LinearLayout
    private lateinit var notesCard: LinearLayout
    private lateinit var notesOut: TextView
    private var recording = false
    private var pulse: ValueAnimator? = null

    private val prefs by lazy { getSharedPreferences("iris", MODE_PRIVATE) }

    companion object { private const val REQ_RECORD = 1 }

    private fun dp(v: Int) = (v * resources.displayMetrics.density).toInt()
    private fun dpF(v: Float) = v * resources.displayMetrics.density

    private val recordingDone = object : BroadcastReceiver() {
        override fun onReceive(c: Context?, i: Intent?) {
            val f = RecorderService.lastFile
            stopPulse()
            setStatus(if (f != null) "saved ${f.name} (${f.length() / 1024} KB)" else "saved", blueTint, blue)
            refreshRecordings()
        }
    }

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        window.statusBarColor = bg
        window.navigationBarColor = bg
        window.decorView.systemUiVisibility =
            View.SYSTEM_UI_FLAG_LIGHT_STATUS_BAR or View.SYSTEM_UI_FLAG_LIGHT_NAVIGATION_BAR

        val content = LinearLayout(this).apply {
            orientation = LinearLayout.VERTICAL
            setPadding(dp(20), dp(24), dp(20), dp(24))
            setBackgroundColor(bg)
        }
        val scroll = ScrollView(this).apply {
            addView(content)
            setBackgroundColor(bg)
        }

        // header: sprout + wordmark
        val header = LinearLayout(this).apply {
            orientation = LinearLayout.HORIZONTAL
            gravity = Gravity.CENTER_VERTICAL
        }
        header.addView(ImageView(this).apply {
            setImageResource(R.drawable.ic_sprout)
            contentDescription = null
        }, LinearLayout.LayoutParams(dp(44), dp(44)))
        val titles = LinearLayout(this).apply {
            orientation = LinearLayout.VERTICAL
            setPadding(dp(12), 0, 0, 0)
        }
        titles.addView(TextView(this).apply {
            text = "Iris"; textSize = 26f; setTextColor(ink); typeface = Typeface.DEFAULT_BOLD
        })
        titles.addView(TextView(this).apply {
            text = "Private meeting notes"; textSize = 13f; setTextColor(gray)
        })
        header.addView(titles)
        content.addView(header)

        // status card
        statusCard = LinearLayout(this).apply {
            orientation = LinearLayout.HORIZONTAL
            gravity = Gravity.CENTER_VERTICAL
            setPadding(dp(14), dp(12), dp(14), dp(12))
            background = rounded(lavenderTint, 14f)
        }
        statusDot = View(this).apply { background = rounded(lavender, 5f) }
        statusCard.addView(statusDot, LinearLayout.LayoutParams(dp(10), dp(10)).apply { rightMargin = dp(10) })
        status = TextView(this).apply {
            textSize = 15f
            setTextColor(ink)
            accessibilityLiveRegion = View.ACCESSIBILITY_LIVE_REGION_POLITE
        }
        statusCard.addView(status, LinearLayout.LayoutParams(0, LinearLayout.LayoutParams.WRAP_CONTENT, 1f))
        content.addBlock(statusCard, 16)
        setStatus("Ready - your meetings stay on this phone", lavenderTint, lavender)

        // record button
        recordBtn = Button(this).apply {
            text = "Start recording"
            setAllCaps(false)
            setTextColor(Color.WHITE)
            textSize = 16f
            typeface = Typeface.DEFAULT_BOLD
            minHeight = dp(56)
            background = RippleDrawable(ColorStateList.valueOf(0x33000000), rounded(coral, 28f), null)
            contentDescription = "Start recording"
            setOnClickListener { toggleRecording() }
        }
        content.addBlock(recordBtn, 14)

        // recordings
        content.addBlock(sectionLabel("On this phone (newest first):"), 24)
        val recCard = LinearLayout(this).apply {
            orientation = LinearLayout.VERTICAL
            background = rounded(Color.WHITE, 16f, border)
            setPadding(dp(14), dp(4), dp(14), dp(4))
        }
        recList = LinearLayout(this).apply { orientation = LinearLayout.VERTICAL }
        recCard.addView(recList)
        content.addBlock(recCard, 8)

        // settings
        content.addBlock(sectionLabel("Settings"), 24)
        val syncPanel = LinearLayout(this).apply {
            orientation = LinearLayout.VERTICAL
            visibility = View.GONE
            background = rounded(Color.WHITE, 16f, border)
            setPadding(dp(14), dp(14), dp(14), dp(14))
        }
        content.addBlock(settingRow("Sync setup", "Optional - laptop, relay, encryption key") {
            syncPanel.visibility = if (syncPanel.visibility == View.GONE) View.VISIBLE else View.GONE
        }, 8)
        content.addBlock(syncPanel, 8)

        syncPanel.addView(fieldLabel("Laptop ingest URL (same Wi-Fi)"))
        syncPanel.addView(field("http://192.168.1.5:8472", "laptop"))
        syncPanel.addBlock(secondaryButton("Send last recording to laptop") { sendToLaptop() }, 10)

        syncPanel.addView(fieldLabel("Sync relay URL + token", 16))
        syncPanel.addView(field("http://...:8471", "relay"))
        syncPanel.addView(field("sync token", "token", secret = true))
        syncPanel.addBlock(secondaryButton("Sync notes now") { syncNow() }, 10)

        syncPanel.addView(fieldLabel("age secret key - stays on this phone", 16))
        syncPanel.addView(field("AGE-SECRET-KEY-1...", "agekey", secret = true))

        notesCard = LinearLayout(this).apply {
            orientation = LinearLayout.VERTICAL
            visibility = View.GONE
        }
        notesCard.addView(fieldLabel("Synced notes", 16))
        notesOut = TextView(this).apply {
            textSize = 12f
            typeface = Typeface.MONOSPACE
            setTextColor(ink)
            setTextIsSelectable(true)
            setPadding(dp(12), dp(10), dp(12), dp(10))
            background = rounded(bg, 10f, border)
        }
        notesCard.addView(notesOut)
        syncPanel.addView(notesCard)

        content.addBlock(settingRow("Meeting nudges", "Notice when Zoom/Meet/Teams opens") { enableNudges() }, 8)

        setContentView(scroll)
        refreshRecordings()
        registerReceiver(recordingDone, IntentFilter("in.iris.app.RECORDING_DONE"), RECEIVER_NOT_EXPORTED)
    }

    override fun onDestroy() {
        stopPulse()
        unregisterReceiver(recordingDone)
        super.onDestroy()
    }

    // ---- view helpers ----

    private fun LinearLayout.addBlock(v: View, top: Int) {
        addView(v, LinearLayout.LayoutParams(LinearLayout.LayoutParams.MATCH_PARENT,
            LinearLayout.LayoutParams.WRAP_CONTENT).apply { topMargin = dp(top) })
    }

    private fun rounded(color: Int, radiusDp: Float, strokeColor: Int? = null): GradientDrawable =
        GradientDrawable().apply {
            setColor(color)
            cornerRadius = dpF(radiusDp)
            if (strokeColor != null) setStroke(dp(1), strokeColor)
        }

    private fun sectionLabel(t: String) = TextView(this).apply {
        text = t
        textSize = 13f
        setTextColor(gray)
        typeface = Typeface.DEFAULT_BOLD
        letterSpacing = 0.06f
    }

    private fun fieldLabel(t: String, top: Int = 0) = TextView(this).apply {
        text = t
        textSize = 12f
        setTextColor(gray)
        setPadding(0, dp(top), 0, dp(6))
    }

    private fun field(hint: String, key: String, secret: Boolean = false) = EditText(this).apply {
        setHint(hint)
        setHintTextColor(gray)
        setText(prefs.getString(key, ""))
        setTextColor(ink)
        textSize = 14f
        setSingleLine()
        minHeight = dp(48)
        setPadding(dp(12), 0, dp(12), 0)
        background = rounded(Color.WHITE, 10f, border)
        inputType = if (secret)
            InputType.TYPE_CLASS_TEXT or InputType.TYPE_TEXT_VARIATION_PASSWORD
        else
            InputType.TYPE_CLASS_TEXT or InputType.TYPE_TEXT_VARIATION_URI
        setOnFocusChangeListener { _, _ -> prefs.edit().putString(key, text.toString()).apply() }
    }

    private fun secondaryButton(label: String, onClick: () -> Unit) = Button(this).apply {
        text = label
        setAllCaps(false)
        setTextColor(ink)
        textSize = 14f
        minHeight = dp(48)
        background = RippleDrawable(ColorStateList.valueOf(0x33000000), rounded(softBtn, 12f), null)
        setOnClickListener { onClick() }
    }

    private fun settingRow(title: String, sub: String, onClick: () -> Unit): LinearLayout {
        val row = LinearLayout(this).apply {
            orientation = LinearLayout.HORIZONTAL
            gravity = Gravity.CENTER_VERTICAL
            minimumHeight = dp(56)
            setPadding(dp(14), dp(8), dp(14), dp(8))
            background = RippleDrawable(ColorStateList.valueOf(0x14000000), rounded(Color.WHITE, 16f, border), null)
            isClickable = true
            isFocusable = true
        }
        val col = LinearLayout(this).apply { orientation = LinearLayout.VERTICAL }
        col.addView(TextView(this).apply { text = title; textSize = 15f; setTextColor(ink) })
        col.addView(TextView(this).apply { text = sub; textSize = 12f; setTextColor(gray) })
        row.addView(col, LinearLayout.LayoutParams(0, LinearLayout.LayoutParams.WRAP_CONTENT, 1f))
        row.addView(TextView(this).apply { text = "›"; textSize = 22f; setTextColor(gray) })
        row.setOnClickListener { onClick() }
        return row
    }

    private fun setStatus(text: String, tint: Int, dotColor: Int) {
        status.text = text
        statusCard.background = rounded(tint, 14f)
        statusDot.background = rounded(dotColor, 5f)
    }

    private fun startPulse() {
        stopPulse()
        pulse = ValueAnimator.ofFloat(0.35f, 1f).apply {
            duration = 900
            repeatCount = ValueAnimator.INFINITE
            repeatMode = ValueAnimator.REVERSE
            addUpdateListener { statusDot.alpha = it.animatedValue as Float }
            start()
        }
    }

    private fun stopPulse() {
        pulse?.cancel()
        pulse = null
        if (::statusDot.isInitialized) statusDot.alpha = 1f
    }

    // ---- recordings list ----

    private fun refreshRecordings() {
        recList.removeAllViews()
        val wavs = (filesDir.listFiles { f -> f.name.matches(Regex("meeting-\\d{8}-\\d{6}\\.wav")) }
            ?: emptyArray()).sortedByDescending { it.name }
        if (wavs.isEmpty()) {
            recList.addView(TextView(this).apply {
                text = "No recordings on this phone yet.\nRecord something and it stays here, on this device."
                textSize = 14f
                setTextColor(gray)
                gravity = Gravity.CENTER
                setPadding(0, dp(18), 0, dp(18))
            })
            return
        }
        val df = java.text.SimpleDateFormat("yyyyMMdd-HHmmss", java.util.Locale.US)
        val out = java.text.SimpleDateFormat("d MMM, HH:mm", java.util.Locale.US)
        val shown = wavs.take(20)
        shown.forEachIndexed { i, f ->
            val when_ = try { out.format(df.parse(f.name.removePrefix("meeting-").removeSuffix(".wav"))!!) } catch (e: Exception) { f.name }
            val row = LinearLayout(this).apply {
                orientation = LinearLayout.HORIZONTAL
                gravity = Gravity.CENTER_VERTICAL
                setPadding(0, dp(10), 0, dp(10))
            }
            row.addView(TextView(this).apply { text = when_; textSize = 15f; setTextColor(ink) },
                LinearLayout.LayoutParams(0, LinearLayout.LayoutParams.WRAP_CONTENT, 1f))
            row.addView(TextView(this).apply { text = "${f.length() / 1024} KB"; textSize = 13f; setTextColor(gray) })
            recList.addView(row)
            if (i < shown.size - 1) {
                recList.addView(View(this).apply { setBackgroundColor(border) },
                    LinearLayout.LayoutParams(LinearLayout.LayoutParams.MATCH_PARENT, dp(1)))
            }
        }
    }

    private fun toast(msg: String) = runOnUiThread { Toast.makeText(this, msg, Toast.LENGTH_LONG).show() }

    // ---- recording ----

    private fun toggleRecording() {
        if (recording) {
            startService(Intent(this, RecorderService::class.java).setAction(RecorderService.ACTION_STOP))
            recording = false
            recordBtn.text = "Start recording"
            recordBtn.contentDescription = "Start recording"
            recordBtn.background = RippleDrawable(ColorStateList.valueOf(0x33000000), rounded(coral, 28f), null)
            setStatus("saving...", coralTint, coral)
        } else {
            if (checkSelfPermission(Manifest.permission.RECORD_AUDIO) != PackageManager.PERMISSION_GRANTED) {
                setStatus("Iris needs the microphone to record your meeting", lavenderTint, lavender)
                requestPermissions(arrayOf(Manifest.permission.RECORD_AUDIO, Manifest.permission.POST_NOTIFICATIONS), REQ_RECORD)
                return
            }
            startRecording()
        }
    }

    private fun startRecording() {
        startForegroundService(Intent(this, RecorderService::class.java).setAction(RecorderService.ACTION_START))
        recording = true
        recordBtn.text = "Stop recording"
        recordBtn.contentDescription = "Stop recording"
        recordBtn.background = RippleDrawable(ColorStateList.valueOf(0x33FFFFFF), rounded(coralDark, 28f), null)
        setStatus("recording (local only)", coralTint, coral)
        startPulse()
    }

    override fun onRequestPermissionsResult(requestCode: Int, permissions: Array<out String>, grantResults: IntArray) {
        super.onRequestPermissionsResult(requestCode, permissions, grantResults)
        if (requestCode != REQ_RECORD) return
        val mic = permissions.indexOf(Manifest.permission.RECORD_AUDIO)
        if (mic >= 0 && grantResults.getOrNull(mic) == PackageManager.PERMISSION_GRANTED) {
            startRecording()
        } else {
            if (shouldShowRequestPermissionRationale(Manifest.permission.RECORD_AUDIO))
                setStatus("mic access is needed to record - tap Start recording to try again", coralTint, coralDark)
            else
                setStatus("mic access is off - enable it in Android Settings > Apps > Iris > Permissions", coralTint, coralDark)
        }
    }

    // ---- sync / laptop / nudges ----

    private fun sendToLaptop() {
        val laptop = prefs.getString("laptop", "") ?: ""
        val token = prefs.getString("token", "") ?: ""
        val f = RecorderService.lastFile ?: run { toast("no recording yet"); return }
        if (laptop.isBlank() || token.isBlank()) { toast("set laptop URL + token first"); return }
        if (!SyncClient.validUrl(laptop)) { toast("laptop URL must be https, or http on your own network"); return }
        setStatus("uploading to your laptop...", coralTint, coral)
        thread {
            try {
                val res = SyncClient.uploadForIngest(laptop, token, f, f.nameWithoutExtension)
                val integ = res.optJSONObject("integrity")
                toast("transcribed: ${res.getString("meeting")} (${integ?.optInt("passed")}/${integ?.optInt("checked")} claims verified)")
                runOnUiThread { setStatus("sent ${f.name} (${f.length() / 1024} KB) -> ${res.getString("meeting")}", blueTint, blue) }
            } catch (e: Exception) { toast("failed: ${e.message}"); runOnUiThread { setStatus("upload failed", coralTint, coralDark) } }
        }
    }

    private fun syncNow() {
        val relay = prefs.getString("relay", "") ?: ""
        val token = prefs.getString("token", "") ?: ""
        val key = prefs.getString("agekey", "") ?: ""
        if (relay.isBlank() || token.isBlank()) { toast("set relay URL + token first"); return }
        if (!SyncClient.validUrl(relay)) { toast("relay URL must be https, or http on your own network"); return }
        if (key.isNotBlank() && !AgeDecrypt.validSecretKey(key)) { toast("age key doesn't look right - paste the AGE-SECRET-KEY-1... line"); return }
        setStatus("syncing...", coralTint, coral)
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
                runOnUiThread {
                    notesOut.text = sb.toString()
                    notesCard.visibility = View.VISIBLE
                    setStatus("synced ${meetings.size} meetings", blueTint, blue)
                }
            } catch (e: Exception) { toast("sync failed: ${e.message}"); runOnUiThread { setStatus("sync failed", coralTint, coralDark) } }
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
