package `in`.iris.app

import org.junit.Assert.assertEquals
import org.junit.Assert.assertFalse
import org.junit.Test

class SyncClientIngestHeadersTest {
    @Test fun englishSendsNoLanguageHeaders() {
        // matches the laptop's pre-header default exactly: old servers see no change
        val h = SyncClient.ingestHeaders("meeting-1", "en", false)
        assertEquals("meeting-1", h["X-Iris-Title"])
        assertFalse(h.containsKey("X-Iris-Language"))
        assertFalse(h.containsKey("X-Iris-Multilingual"))
        assertFalse(h.containsKey("X-Iris-Careful"))
    }

    @Test fun hindiSendsForcedLanguage() {
        val h = SyncClient.ingestHeaders("t", "hi", false)
        assertEquals("hi", h["X-Iris-Language"])
        assertFalse(h.containsKey("X-Iris-Multilingual"))
    }

    @Test fun hinglishSendsMultilingualNotLanguage() {
        // mixed audio needs per-segment detection; a forced single language drops speech
        val h = SyncClient.ingestHeaders("t", "multi", false)
        assertEquals("1", h["X-Iris-Multilingual"])
        assertFalse(h.containsKey("X-Iris-Language"))
    }

    @Test fun carefulSendsFlagOnlyWhenOn() {
        assertEquals("1", SyncClient.ingestHeaders("t", "hi", true)["X-Iris-Careful"])
        assertFalse(SyncClient.ingestHeaders("t", "hi", false).containsKey("X-Iris-Careful"))
    }
}
