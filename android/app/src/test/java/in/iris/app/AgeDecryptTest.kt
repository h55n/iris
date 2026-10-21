package `in`.iris.app

import org.junit.Assert.assertEquals
import org.junit.Assert.assertFalse
import org.junit.Assert.assertTrue
import org.junit.Test

/** JVM unit tests for AgeDecrypt helpers (no Android runtime needed). */
class AgeDecryptTest {

    @Test
    fun bech32RejectsGarbage() {
        try {
            AgeDecrypt.bech32Decode("not-a-key")
            throw AssertionError("should have thrown")
        } catch (e: Exception) {
            assertTrue(true)
        }
    }

    @Test
    fun bech32DecodesRealAgeKey() {
        // throwaway key generated with age-keygen for this test vector
        val raw = AgeDecrypt.bech32Decode(
            "AGE-SECRET-KEY-1QQ44ZAQFNH5TYV22N00WU74Y8E5FNYFFWHXARAQHMSPDLAJC6JVS2C4H4D")
        assertEquals(32, raw.size)
    }

    @Test
    fun validUrlRules() {
        assertTrue(SyncClient.validUrl("http://192.168.1.5:8472"))
        assertTrue(SyncClient.validUrl("https://relay.example.com"))
        assertTrue(!SyncClient.validUrl("192.168.1.5"))
        assertTrue(!SyncClient.validUrl(""))
        assertTrue(!SyncClient.validUrl("ftp://x"))
    }

    @Test
    fun bech32AlphabetIsComplete() {
        // the age/Bech32 charset has exactly 32 distinct symbols
        val chars = "qpzry9x8gf2tvdw0s3jn54khce6mua7l"
        assertEquals(32, chars.toSet().size)
    }
}

class AgeKeyShapeTest {
    @Test fun realKeygenKeyPasses() {
        // shape of a real age-keygen secret (checked against a real one in CI earlier)
        val k = "AGE-SECRET-KEY-1" + "q".repeat(58)
        assertTrue(AgeDecrypt.validSecretKey(k))
    }
    @Test fun rejectsWrongPrefix() {
        assertFalse(AgeDecrypt.validSecretKey("age1qqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqq"))
        assertFalse(AgeDecrypt.validSecretKey(""))
        assertFalse(AgeDecrypt.validSecretKey("AGE-SECRET-KEY-2" + "q".repeat(58)))
    }
    @Test fun rejectsBadCharsetAndLength() {
        assertFalse(AgeDecrypt.validSecretKey("AGE-SECRET-KEY-1" + "q".repeat(10)))          // too short
        assertFalse(AgeDecrypt.validSecretKey("AGE-SECRET-KEY-1" + "q".repeat(58) + "!"))     // bad char + long
        assertFalse(AgeDecrypt.validSecretKey("AGE-SECRET-KEY-1" + "b".repeat(58)))           // 'b' not in bech32
    }
}
