package `in`.iris.app

import android.app.NotificationChannel
import android.app.NotificationManager
import android.app.PendingIntent
import android.app.usage.UsageStatsManager
import android.content.Context
import android.content.Intent
import kotlin.concurrent.thread

/** Meeting nudge: the ONLY detection Android allows a normal app.
 *  Polls UsageStatsManager for the foreground app; if it's a known meeting
 *  app, posts a "meeting? tap to record" notification. Requires the user to
 *  grant Usage Access in system settings. Cannot see the mic or audio of
 *  other apps (OS-level, since Play policy May 2022) - documented in TESTED.md. */
object MeetingNudge {
    internal val MEETING_APPS = mapOf(
        "us.zoom.videomeetings" to "Zoom",
        "com.google.android.apps.meetings" to "Google Meet",
        "com.google.android.apps.tachyon" to "Google Meet (Duo)",
        "com.microsoft.teams" to "Microsoft Teams",
        "com.webex.meetings" to "Webex",
        "com.cisco.webex.meetings" to "Webex",
        "com.slack" to "Slack (huddle?)"
    )
    /** Display name for a foreground package, or null if it isn't a known meeting app. */
    fun meetingAppName(pkg: String): String? = MEETING_APPS[pkg]

    @Volatile private var running = false

    fun start(ctx: Context) {
        if (running) return
        running = true
        val nm = ctx.getSystemService(Context.NOTIFICATION_SERVICE) as NotificationManager
        nm.createNotificationChannel(NotificationChannel("nudge", "Meeting nudges", NotificationManager.IMPORTANCE_DEFAULT))
        thread {
            var nudgedFor: String? = null
            while (running) {
                val fg = foregroundApp(ctx)
                val app = fg?.let { meetingAppName(it) }
                if (app != null && nudgedFor != fg) {
                    nudgedFor = fg
                    val tap = PendingIntent.getActivity(ctx, 2, Intent(ctx, MainActivity::class.java), PendingIntent.FLAG_IMMUTABLE)
                    nm.notify(2, android.app.Notification.Builder(ctx, "nudge")
                        .setContentTitle("$app is open")
                        .setContentText("In a meeting? Tap to start recording.")
                        .setSmallIcon(android.R.drawable.ic_btn_speak_now)
                        .setContentIntent(tap).setAutoCancel(true).build())
                } else if (app == null) {
                    nudgedFor = null
                }
                Thread.sleep(20_000)
            }
        }
    }

    fun stop() { running = false }

    fun foregroundApp(ctx: Context): String? {
        val usm = ctx.getSystemService(Context.USAGE_STATS_SERVICE) as UsageStatsManager
        val now = System.currentTimeMillis()
        val stats = usm.queryUsageStats(UsageStatsManager.INTERVAL_DAILY, now - 60_000, now) ?: return null
        return stats.filter { it.lastTimeUsed > 0 }.maxByOrNull { it.lastTimeUsed }?.packageName
    }

    fun hasUsageAccess(ctx: Context): Boolean {
        val usm = ctx.getSystemService(Context.USAGE_STATS_SERVICE) as UsageStatsManager
        val now = System.currentTimeMillis()
        return !usm.queryUsageStats(UsageStatsManager.INTERVAL_DAILY, now - 60_000, now).isNullOrEmpty()
    }

    fun usageAccessIntent() = Intent(android.provider.Settings.ACTION_USAGE_ACCESS_SETTINGS)
}
