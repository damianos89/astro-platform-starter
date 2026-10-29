package de.reelcut.app.data

import android.content.ContentValues
import android.content.Context
import android.net.Uri
import android.os.Build
import android.os.Environment
import android.provider.MediaStore
import android.provider.OpenableColumns
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.withContext
import java.io.File
import java.io.IOException

/** Moves video bytes around: content Uri -> cache file (for upload) and downloaded file -> gallery. */
class VideoRepository(private val context: Context) {

    /**
     * Copies a picked/shared video into the app cache. Shared content URIs are only readable while the
     * sharing grant lives, so this has to happen right away, before the background worker runs.
     */
    suspend fun importToCache(uri: Uri): File = withContext(Dispatchers.IO) {
        val name = displayName(uri) ?: "video.mp4"
        val ext = name.substringAfterLast('.', "mp4").lowercase().take(5)
        val dir = File(context.cacheDir, "uploads").apply { mkdirs() }
        val target = File(dir, "upload_${System.currentTimeMillis()}.$ext")
        context.contentResolver.openInputStream(uri)?.use { input ->
            target.outputStream().use { output -> input.copyTo(output, bufferSize = 1 shl 20) }
        } ?: throw IOException("Video konnte nicht gelesen werden: $uri")
        target
    }

    fun displayName(uri: Uri): String? {
        if (uri.scheme == "file") return uri.lastPathSegment
        context.contentResolver.query(uri, arrayOf(OpenableColumns.DISPLAY_NAME), null, null, null)?.use { c ->
            if (c.moveToFirst()) {
                val idx = c.getColumnIndex(OpenableColumns.DISPLAY_NAME)
                if (idx >= 0) return c.getString(idx)
            }
        }
        return null
    }

    /** Saves a rendered mp4 into Movies/ReelCut so TikTok/Instagram can pick it up; returns its content Uri. */
    suspend fun saveToGallery(file: File, displayName: String): Uri = withContext(Dispatchers.IO) {
        val resolver = context.contentResolver
        val values = ContentValues().apply {
            put(MediaStore.Video.Media.DISPLAY_NAME, displayName)
            put(MediaStore.Video.Media.MIME_TYPE, "video/mp4")
            if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.Q) {
                put(MediaStore.Video.Media.RELATIVE_PATH, Environment.DIRECTORY_MOVIES + "/ReelCut")
                put(MediaStore.Video.Media.IS_PENDING, 1)
            } else {
                @Suppress("DEPRECATION")
                val dir = File(Environment.getExternalStoragePublicDirectory(Environment.DIRECTORY_MOVIES), "ReelCut").apply { mkdirs() }
                @Suppress("DEPRECATION")
                put(MediaStore.Video.Media.DATA, File(dir, displayName).absolutePath)
            }
        }
        val collection = if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.Q) {
            MediaStore.Video.Media.getContentUri(MediaStore.VOLUME_EXTERNAL_PRIMARY)
        } else {
            @Suppress("DEPRECATION")
            MediaStore.Video.Media.EXTERNAL_CONTENT_URI
        }
        val uri = resolver.insert(collection, values) ?: throw IOException("MediaStore insert failed")
        try {
            resolver.openOutputStream(uri)?.use { out -> file.inputStream().use { it.copyTo(out, 1 shl 20) } }
                ?: throw IOException("could not open $uri for writing")
            if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.Q) {
                resolver.update(uri, ContentValues().apply { put(MediaStore.Video.Media.IS_PENDING, 0) }, null, null)
            }
        } catch (e: Exception) {
            resolver.delete(uri, null, null)
            throw e
        }
        uri
    }

    fun cleanupUploads(olderThanMs: Long = 24 * 60 * 60 * 1000L) {
        val cutoff = System.currentTimeMillis() - olderThanMs
        File(context.cacheDir, "uploads").listFiles()?.filter { it.lastModified() < cutoff }?.forEach { it.delete() }
        File(context.cacheDir, "results").listFiles()?.filter { it.lastModified() < cutoff }?.forEach { it.delete() }
    }
}
