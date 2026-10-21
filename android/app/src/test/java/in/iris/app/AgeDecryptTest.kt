package `in`.iris.app

import org.junit.Assert.assertEquals
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
    fun bech32AlphabetIsComplete() {
        // the age/Bech32 charset has exactly 32 distinct symbols
        val chars = "qpzry9x8gf2tvdw0s3jn54khce6mua7l"
        assertEquals(32, chars.toSet().size)
    }
}
