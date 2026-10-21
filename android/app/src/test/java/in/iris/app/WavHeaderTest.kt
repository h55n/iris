package `in`.iris.app

import org.junit.Assert.*
import org.junit.Test
import java.io.File
import java.io.RandomAccessFile
import java.nio.ByteBuffer
import java.nio.ByteOrder

class WavHeaderTest {
    private fun header(dataLen: Long, rate: Int): ByteArray {
        val f = File.createTempFile("wav", ".hdr"); f.deleteOnExit()
        RandomAccessFile(f, "rw").use { raf ->
            raf.setLength(44 + dataLen.coerceAtMost(0))
            WavHeader.write(raf, dataLen, rate)
        }
        return f.readBytes().copyOf(44)
    }

    @Test fun riffMagicAndFormat() {
        val h = header(1000, 16000)
        assertEquals("RIFF", String(h, 0, 4))
        assertEquals("WAVE", String(h, 8, 4))
        assertEquals("fmt ", String(h, 12, 4))
        assertEquals("data", String(h, 36, 4))
    }

    @Test fun lengthsAreLittleEndian() {
        val h = header(32000, 16000)
        val bb = ByteBuffer.wrap(h).order(ByteOrder.LITTLE_ENDIAN)
        assertEquals(36 + 32000, bb.getInt(4))   // RIFF chunk size
        assertEquals(16000, bb.getInt(24))       // sample rate
        assertEquals(32000, bb.getInt(28))       // byte rate = rate * 2 (16-bit mono)
        assertEquals(32000, bb.getInt(40))       // data length
    }

    @Test fun pcmFields() {
        val h = header(0, 44100)
        val bb = ByteBuffer.wrap(h).order(ByteOrder.LITTLE_ENDIAN)
        assertEquals(1, bb.getShort(22).toInt())  // mono
        assertEquals(16, bb.getShort(34).toInt()) // bits per sample
        assertEquals(44100, bb.getInt(24))
    }
}
