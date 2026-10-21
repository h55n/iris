package `in`.convo.app

import android.os.Build
import java.math.BigInteger
import java.security.KeyFactory
import java.security.spec.NamedParameterSpec
import java.security.spec.XECPrivateKeySpec
import java.security.spec.XECPublicKeySpec
import javax.crypto.Cipher
import javax.crypto.KeyAgreement
import javax.crypto.spec.IvParameterSpec
import javax.crypto.spec.SecretKeySpec

/** Decrypts age v1 files (X25519 recipient stanza, STREAM payload), the exact
 *  format the desktop side writes with `age -a`. Needs Android 13+ (API 33)
 *  for X25519 in the platform crypto provider; the app checks Build.VERSION
 *  before offering decryption. Header-MAC verification is skipped: any
 *  tampering fails at the AEAD layer instead. (Honest note in TESTED.md.) */
object AgeDecrypt {

    class AgeException(msg: String) : Exception(msg)

    fun supported() = Build.VERSION.SDK_INT >= 33

    // ---------- bech32 (age secret keys are bech32, HRP "age-secret-key-") ----------
    private val CHARSET = "qpzry9x8gf2tvdw0s3jn54khce6mua7l"
    private fun bech32Polymod(values: IntArray): Int {
        val gen = intArrayOf(0x3b6a57b2, 0x26508e6d, 0x1ea119fa, 0x3d4233dd, 0x2a1462b3)
        var chk = 1
        for (v in values) {
            val top = chk ushr 25
            chk = (chk and 0x1ffffff) shl 5 xor v
            for (i in 0..4) if ((top ushr i) and 1 == 1) chk = chk xor gen[i]
        }
        return chk
    }
    fun bech32Decode(bech: String): ByteArray {
        val s = bech.trim().lowercase()
        val pos = s.lastIndexOf('1')
        if (pos < 1) throw AgeException("not a bech32 string")
        val hrp = s.substring(0, pos)
        val data = s.substring(pos + 1).map {
            val i = CHARSET.indexOf(it)
            if (i < 0) throw AgeException("bad bech32 char: $it")
            i
        }
        val hrpExpand = hrp.map { it.code shr 5 } + listOf(0) + hrp.map { it.code and 31 }
        val check = bech32Polymod((hrpExpand + data).toIntArray())
        if (check != 1) throw AgeException("bech32 checksum failed")
        val payload = data.dropLast(6)
        // convert 5-bit groups to 8-bit
        var acc = 0; var bits = 0
        val out = ArrayList<Byte>()
        for (v in payload) {
            acc = (acc shl 5) or v; bits += 5
            if (bits >= 8) { bits -= 8; out.add(((acc shr bits) and 0xff).toByte()) }
        }
        return out.toByteArray()
    }

    // ---------- HKDF-SHA256 ----------
    private fun hmac(key: ByteArray, data: ByteArray): ByteArray {
        val m = javax.crypto.Mac.getInstance("HmacSHA256")
        m.init(SecretKeySpec(if (key.isEmpty()) ByteArray(32) else key, "HmacSHA256"))
        return m.doFinal(data)
    }
    private fun hkdf(salt: ByteArray, ikm: ByteArray, info: String, len: Int = 32): ByteArray {
        val prk = hmac(salt, ikm)
        val t1 = hmac(prk, info.toByteArray() + byteArrayOf(1))
        return t1.copyOf(len)
    }

    private fun chacha(key: ByteArray, nonce: ByteArray, data: ByteArray): ByteArray {
        val c = Cipher.getInstance("ChaCha20-Poly1305")
        c.init(Cipher.DECRYPT_MODE, SecretKeySpec(key, "ChaCha20"), IvParameterSpec(nonce))
        return c.doFinal(data)
    }

    private fun x25519(secret: ByteArray, publicU: ByteArray): ByteArray {
        if (!supported()) throw AgeException("needs Android 13+")
        val kf = KeyFactory.getInstance("XDH")
        val params = NamedParameterSpec("X25519")
        val priv = kf.generatePrivate(XECPrivateKeySpec(params, secret))
        val u = BigInteger(1, publicU.reversedArray())
        val pub = kf.generatePublic(XECPublicKeySpec(params, u))
        val ka = KeyAgreement.getInstance("XDH")
        ka.init(priv); ka.doPhase(pub, true)
        return ka.generateSecret()
    }

    private val B64 = java.util.Base64.getMimeDecoder()

    /** Decrypt an age-armored file with an AGE-SECRET-KEY-1... string. */
    fun decrypt(armored: String, secretKeyBech32: String): ByteArray {
        val b64 = armored.lines().filter { it.isNotBlank() && !it.startsWith("-----") }.joinToString("")
        val raw = B64.decode(b64)
        val text = String(raw, Charsets.ISO_8859_1)  // payload is binary; header is ASCII
        if (!text.startsWith("age-encryption.org/v1\n")) throw AgeException("bad header")
        val headerEnd = text.indexOf("\n--- ")
        if (headerEnd < 0) throw AgeException("no header end")
        val headerLines = text.substring(0, headerEnd).split("\n")
        var ephemeral: ByteArray? = null
        var wrapped: ByteArray? = null
        var i = 1
        while (i < headerLines.size) {
            val line = headerLines[i]
            if (line.startsWith("-> X25519 ")) {
                ephemeral = B64.decode(line.removePrefix("-> X25519 ").trim())
                // stanza body lines (short: one line, 32 bytes wrapped => b64)
                wrapped = B64.decode(headerLines[i + 1].trim())
                i += 2
            } else i++   // unknown stanza (e.g. scrypt): skip with its body lines conservatively
        }
        if (ephemeral == null || wrapped == null) throw AgeException("no X25519 stanza")
        val secret = bech32Decode(secretKeyBech32)
        // recipient public key = X25519(secret, basepoint)
        val basepoint = ByteArray(32).also { it[0] = 9 }
        val recipientPub = x25519(secret, basepoint)
        val wrapKey = hkdf(ephemeral + recipientPub, x25519(secret, ephemeral), "age-encryption.org/v1/X25519")
        val fileKey = try {
            chacha(wrapKey, ByteArray(12), wrapped)
        } catch (e: Exception) { throw AgeException("unwrap failed (wrong key?)") }
        // payload starts after "--- <mac>\n"
        val macLineEnd = text.indexOf('\n', headerEnd + 1)
        val payloadOffset = macLineEnd + 1
        val payload = raw.copyOfRange(payloadOffset, raw.size)
        val nonce = payload.copyOfRange(0, 16)
        val streamKey = hkdf(nonce, fileKey, "payload")
        val body = payload.copyOfRange(16, payload.size)
        val chunkSize = 64 * 1024
        val out = java.io.ByteArrayOutputStream()
        var off = 0; var counter = 0L
        while (off < body.size) {
            val remaining = body.size - off
            val encLen = if (remaining > chunkSize + 16) chunkSize + 16 else remaining
            val isLast = off + encLen == body.size
            val n = ByteArray(12)
            for (j in 0..10) n[10 - j] = (counter shr (8 * j)).toByte()
            n[11] = if (isLast) 1 else 0
            out.write(chacha(streamKey, n, body.copyOfRange(off, off + encLen)))
            off += encLen; counter++
        }
        return out.toByteArray()
    }
}
