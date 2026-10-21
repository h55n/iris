package `in`.iris.app

import org.json.JSONArray
import org.json.JSONObject
import java.io.File
import java.net.HttpURLConnection
import java.net.URL

/** Talks to the user's own machines only:
 *  - relay (sync_server.py): pull meeting bundles (ciphertext when encrypted)
 *  - laptop (ingest_server.py): POST a recording for transcription */
object SyncClient {

    data class Meeting(val id: String, val ts: Double)

    private fun req(url: String, token: String, body: ByteArray? = null,
                    contentType: String = "application/json", extraHeaders: Map<String, String> = emptyMap()): Pair<Int, ByteArray> {
        val c = URL(url).openConnection() as HttpURLConnection
        c.connectTimeout = 15000; c.readTimeout = 60000
        c.setRequestProperty("X-Convo-Token", token)
        extraHeaders.forEach { (k, v) -> c.setRequestProperty(k, v) }
        if (body != null) {
            c.requestMethod = "POST"
            c.doOutput = true
            c.setRequestProperty("Content-Type", contentType)
            c.outputStream.use { it.write(body) }
        }
        val code = c.responseCode
        val stream = if (code in 200..299) c.inputStream else c.errorStream
        val bytes = stream?.readBytes() ?: ByteArray(0)
        c.disconnect()
        return code to bytes
    }

    fun listMeetings(relay: String, token: String, since: Double = 0.0): List<Meeting> {
        val (code, bytes) = req("$relay/list?since=$since", token)
        if (code != 200) throw Exception("list failed: $code")
        val arr: JSONArray = JSONObject(String(bytes)).getJSONArray("meetings")
        return (0 until arr.length()).map {
            val o = arr.getJSONObject(it); Meeting(o.getString("id"), o.getDouble("ts"))
        }
    }

    fun pullBundle(relay: String, token: String, id: String): JSONObject {
        val (code, bytes) = req("$relay/pull/$id", token)
        if (code != 200) throw Exception("pull failed: $code")
        return JSONObject(String(bytes))
    }

    /** Upload a recording to the user's laptop over LAN for transcription.
     *  Retries twice with backoff: phones drop off Wi-Fi mid-upload often. */
    fun uploadForIngest(laptop: String, token: String, wav: File, title: String,
                        retries: Int = 2): JSONObject {
        val payload = wav.readBytes()
        var lastErr: Exception? = null
        for (attempt in 0..retries) {
            try {
                val (code, bytes) = req("$laptop/ingest", token, payload,
                    contentType = "audio/wav", extraHeaders = mapOf("X-Iris-Title" to title))
                if (code == 200) return JSONObject(String(bytes))
                lastErr = Exception("ingest failed: $code ${String(bytes)}")
            } catch (e: Exception) {
                lastErr = e
            }
            if (attempt < retries) Thread.sleep(1500L * (attempt + 1))
        }
        throw lastErr ?: Exception("ingest failed")
    }
}
