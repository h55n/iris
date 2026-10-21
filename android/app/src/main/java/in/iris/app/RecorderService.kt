package `in`.iris.app

import android.app.*
import android.content.Context
import android.content.Intent
import android.media.AudioFormat
import android.media.AudioRecord
import android.media.MediaRecorder
import android.os.IBinder
import java.io.File
import java.io.RandomAccessFile
import java.text.SimpleDateFormat
import java.util.*
import kotlin.concurrent.thread

/** Records 16 kHz mono PCM to a WAV file in the app's private storage.
 *  Foreground service with a persistent notification: recording is always
 *  visible, never in the background without the user's knowledge. */
class RecorderService : Service() {
    private var recording = false
    private var outFile: File? = null

    companion object {
        const val ACTION_START = "in.iris.app.START"
        const val ACTION_STOP = "in.iris.app.STOP"
        const val EXTRA_OUT = "out"
        const val CH = "rec"
        var lastFile: File? = null
            private set
    }

    override fun onBind(intent: Intent?): IBinder? = null

    override fun onStartCommand(intent: Intent?, flags: Int, startId: Int): Int {
        when (intent?.action) {
            ACTION_STOP -> { recording = false; stopSelf(); return START_NOT_STICKY }
            ACTION_START -> startRecording()
        }
        return START_STICKY
    }

    private fun startRecording() {
        val nm = getSystemService(Context.NOTIFICATION_SERVICE) as NotificationManager
        nm.createNotificationChannel(NotificationChannel(CH, "Recording", NotificationManager.IMPORTANCE_LOW))
        val notif = Notification.Builder(this, CH)
            .setContentTitle("Iris is recording")
            .setContentText("Local only. Tap to stop.")
            .setSmallIcon(android.R.drawable.ic_btn_speak_now)
            .addAction(Notification.Action.Builder(null, "Stop",
                PendingIntent.getService(this, 1,
                    Intent(this, RecorderService::class.java).setAction(ACTION_STOP),
                    PendingIntent.FLAG_IMMUTABLE)).build())
            .build()
        startForeground(1, notif)

        val stamp = SimpleDateFormat("yyyyMMdd-HHmmss", Locale.US).format(Date())
        val f = File(filesDir, "meeting-$stamp.wav")
        outFile = f
        recording = true
        thread {
            val rate = 16000
            val min = AudioRecord.getMinBufferSize(rate, AudioFormat.CHANNEL_IN_MONO, AudioFormat.ENCODING_PCM_16BIT)
            val rec = AudioRecord(MediaRecorder.AudioSource.MIC, rate,
                AudioFormat.CHANNEL_IN_MONO, AudioFormat.ENCODING_PCM_16BIT, min * 2)
            rec.startRecording()
            RandomAccessFile(f, "rw").use { raf ->
                raf.write(ByteArray(44))  // header placeholder
                val buf = ByteArray(min)
                var total = 0L
                while (recording) {
                    val n = rec.read(buf, 0, buf.size)
                    if (n > 0) { raf.write(buf, 0, n); total += n }
                }
                rec.stop(); rec.release()
                writeWavHeader(raf, total, rate)
            }
            lastFile = f
            sendBroadcast(Intent("in.iris.app.RECORDING_DONE").setPackage(packageName))
            stopSelf()
        }
    }

    private fun writeWavHeader(raf: RandomAccessFile, dataLen: Long, rate: Int) {
        val byteRate = rate * 2L
        raf.seek(0)
        raf.writeBytes("RIFF")
        raf.writeIntLE((36 + dataLen).toInt())
        raf.writeBytes("WAVEfmt ")
        raf.writeIntLE(16); raf.writeShortLE(1); raf.writeShortLE(1)
        raf.writeIntLE(rate); raf.writeIntLE(byteRate.toInt())
        raf.writeShortLE(2); raf.writeShortLE(16)
        raf.writeBytes("data")
        raf.writeIntLE(dataLen.toInt())
    }

    private fun RandomAccessFile.writeIntLE(v: Int) = write(byteArrayOf(
        (v and 0xff).toByte(), (v shr 8 and 0xff).toByte(), (v shr 16 and 0xff).toByte(), (v shr 24 and 0xff).toByte()))
    private fun RandomAccessFile.writeShortLE(v: Int) = write(byteArrayOf((v and 0xff).toByte(), (v shr 8 and 0xff).toByte()))
}
