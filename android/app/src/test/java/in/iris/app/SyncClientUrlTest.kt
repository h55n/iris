package `in`.iris.app

import org.junit.Assert.assertFalse
import org.junit.Assert.assertTrue
import org.junit.Test

class SyncClientUrlTest {
    @Test fun httpsIsAllowedAnywhere() {
        assertTrue(SyncClient.validUrl("https://iris-cloud-one.vercel.app/sync"))
        assertFalse(SyncClient.validUrl("https://"))
    }

    @Test fun plainHttpOnlyOnYourOwnNetwork() {
        assertTrue(SyncClient.validUrl("http://192.168.1.5:8472"))
        assertTrue(SyncClient.validUrl("http://10.0.0.7:8471"))
        assertTrue(SyncClient.validUrl("http://172.20.1.1:8471"))
        assertTrue(SyncClient.validUrl("http://my-laptop.local:8472"))
        assertTrue(SyncClient.validUrl("http://localhost:8471"))
        assertFalse(SyncClient.validUrl("http://example.com"))
        assertFalse(SyncClient.validUrl("http://172.32.1.1"))
        assertFalse(SyncClient.validUrl("http://8.8.8.8:8471"))
        assertFalse(SyncClient.validUrl("http://192.168.1.5.evil.com"))
        assertFalse(SyncClient.validUrl("http://evil.com@192.168.1.5.evil.com/"))
    }

    @Test fun otherSchemesAreRejected() {
        assertFalse(SyncClient.validUrl("ftp://192.168.1.5"))
        assertFalse(SyncClient.validUrl("javascript:alert(1)"))
        assertFalse(SyncClient.validUrl(""))
    }
}
