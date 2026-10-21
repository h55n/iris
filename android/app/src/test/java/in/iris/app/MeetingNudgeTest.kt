package `in`.iris.app

import org.junit.Assert.*
import org.junit.Test

class MeetingNudgeTest {
    @Test fun knownMeetingAppsResolve() {
        assertEquals("Zoom", MeetingNudge.meetingAppName("us.zoom.videomeetings"))
        assertEquals("Google Meet", MeetingNudge.meetingAppName("com.google.android.apps.meetings"))
        assertEquals("Microsoft Teams", MeetingNudge.meetingAppName("com.microsoft.teams"))
        assertTrue(MeetingNudge.meetingAppName("com.slack")!!.contains("Slack"))
    }
    @Test fun nonMeetingAppsAreNull() {
        assertNull(MeetingNudge.meetingAppName("com.whatsapp"))
        assertNull(MeetingNudge.meetingAppName(""))
    }
    @Test fun wherebDesktopPackagePresent() {
        // Whereby's desktop detection lives in the Chrome extension; on Android
        // Whereby runs inside Chrome, which is intentionally NOT flagged.
        assertNull(MeetingNudge.meetingAppName("com.android.chrome"))
    }
}
