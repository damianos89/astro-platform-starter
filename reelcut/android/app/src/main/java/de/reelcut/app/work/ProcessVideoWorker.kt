package de.reelcut.app.work

import android.app.Notification
import android.app.PendingIntent
import android.content.Context
import android.content.Intent
import android.content.pm.ServiceInfo
import android.os.Build
import androidx.core.app.NotificationCompat
import androidx.core.app.NotificationManagerCompat
import androidx.work.CoroutineWorker
import androidx.work.ForegroundInfo
import androidx.work.WorkerParameters
import androidx.work.workDataOf
import de.reelcut.app.MainActivity
import de.reelcut.app.R
import de.reelcut.app.ReelCutApp
import de.reelcut.app.data.ApiClient
import de.reelcut.app.data.JobStatus
import de.reelcut.app.data.SettingsRepository
import de.reelcut.app.data.VideoRepository
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.delay
import kotlinx.coroutines.flow.first
import kotlinx.coroutines.withContext
import okhttp3.MediaType.Companion.toMediaType
import okhttp3.MultipartBody
import okhttp3.RequestBody.Companion.asRequestBody
import okhttp3.RequestBody.Companion.toRequestBody
import java.io.File
import java.text.SimpleDateFormat
import java.util.Date
import java.util.Locale

/**
 * Upload -> poll -> download -> save to gallery, all in the background so the user can close the app.
 * Progress is published via [setProgress]; the final [androidx.work.WorkInfo] carries the output data.
 */
class ProcessVideoWorker(appContext: Context, params: WorkerParameters) : CoroutineWorker(appContext, params) {

    private val settingsRepo = SettingsRepository(appContext)
    private val videoRepo = VideoRepository(appContext)

    override suspend fun getForegroundInfo(): ForegroundInfo = foregroundInfo(applicationContext.getString(R.string.stage_uploading), 0)

    override suspend fun doWork(): Result {
        val filePath = inputData.getString(KEY_FILE) ?: return failure("no input file")
        val file = File(filePath)
        if (!file.exists()) return failure("input file vanished")

        val settings = settingsRepo.settings.first()
        if (settings.baseUrl.isBlank()) return failure("Server-URL fehlt (Einstellungen)")
        val api = ApiClient.create(settings.baseUrl, settings.token)

        try {
            runCatching { setForeground(getForegroundInfo()) } // may be refused on Android 12+ while in background; progress still works
            publish(STAGE_UPLOADING, 0.02f, applicationContext.getString(R.string.stage_uploading))

            val text = "text/plain".toMediaType()
            val part = MultipartBody.Part.createFormData("file", file.name, file.asRequestBody("video/mp4".toMediaType()))
            var status = api.createJob(
                file = part,
                preset = (inputData.getString(KEY_PRESET) ?: "freestyle_mix").toRequestBody(text),
                targetDuration = inputData.getInt(KEY_TARGET_DURATION, 0).toString().toRequestBody(text),
                instructions = (inputData.getString(KEY_INSTRUCTIONS) ?: "").toRequestBody(text),
                language = "".toRequestBody(text),
                addHookTitle = inputData.getBoolean(KEY_HOOK_TITLE, true).toString().toRequestBody(text),
            )
            val jobId = status.id

            val deadline = System.currentTimeMillis() + MAX_WAIT_MS
            while (!status.isDone && !status.isFailed) {
                if (isStopped) return Result.failure()
                if (System.currentTimeMillis() > deadline) return failure("Zeitüberschreitung beim Warten auf den Server")
                publish(status.stage, 0.05f + 0.75f * status.progress, status.message)
                delay(POLL_INTERVAL_MS)
                status = api.getJob(jobId)
            }
            if (status.isFailed) return failure(status.error ?: "Server meldet Fehler")

            publish(STAGE_DOWNLOADING, 0.82f, applicationContext.getString(R.string.stage_downloading))
            val resultsDir = File(applicationContext.cacheDir, "results").apply { mkdirs() }
            val downloaded = File(resultsDir, "reelcut-$jobId.mp4")
            withContext(Dispatchers.IO) {
                api.downloadResult(jobId).use { body ->
                    body.byteStream().use { input -> downloaded.outputStream().use { input.copyTo(it, 1 shl 20) } }
                }
            }

            publish(STAGE_SAVING, 0.95f, applicationContext.getString(R.string.stage_saving))
            val stamp = SimpleDateFormat("yyyyMMdd_HHmmss", Locale.US).format(Date())
            val galleryUri = videoRepo.saveToGallery(downloaded, "ReelCut_$stamp.mp4")
            downloaded.delete()
            file.delete()
            videoRepo.cleanupUploads()

            val plan = status.plan
            notifyDone()
            return Result.success(
                workDataOf(
                    KEY_OUTPUT_URI to galleryUri.toString(),
                    KEY_OUT_TITLE to (plan?.title ?: ""),
                    KEY_OUT_SUMMARY to (plan?.summary ?: ""),
                    KEY_OUT_CAPTION to (plan?.suggestedCaption ?: ""),
                    KEY_OUT_DURATION to (status.outputDuration ?: 0.0),
                ),
            )
        } catch (e: Exception) {
            if (isStopped) return Result.failure()
            notifyFailed(e.message ?: e.javaClass.simpleName)
            return failure(e.message ?: e.javaClass.simpleName)
        }
    }

    private suspend fun publish(stage: String, progress: Float, message: String) {
        setProgress(workDataOf(KEY_STAGE to stage, KEY_PROGRESS to progress, KEY_MESSAGE to message))
        runCatching { setForeground(foregroundInfo(message, (progress * 100).toInt())) }
    }

    private fun failure(message: String): Result = Result.failure(workDataOf(KEY_ERROR to message))

    // ------------------------------------------------------------------ notifications

    private fun contentIntent(): PendingIntent {
        val intent = Intent(applicationContext, MainActivity::class.java).apply {
            flags = Intent.FLAG_ACTIVITY_SINGLE_TOP or Intent.FLAG_ACTIVITY_CLEAR_TOP
            putExtra(MainActivity.EXTRA_WORK_ID, id.toString())
        }
        return PendingIntent.getActivity(applicationContext, 0, intent, PendingIntent.FLAG_UPDATE_CURRENT or PendingIntent.FLAG_IMMUTABLE)
    }

    private fun foregroundInfo(text: String, percent: Int): ForegroundInfo {
        val notification: Notification = NotificationCompat.Builder(applicationContext, ReelCutApp.CHANNEL_PROCESSING)
            .setSmallIcon(R.drawable.ic_launcher_foreground)
            .setContentTitle(applicationContext.getString(R.string.notification_processing_title))
            .setContentText(text)
            .setProgress(100, percent, percent == 0)
            .setOngoing(true)
            .setOnlyAlertOnce(true)
            .setContentIntent(contentIntent())
            .build()
        return if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.Q) {
            ForegroundInfo(NOTIFICATION_ID, notification, ServiceInfo.FOREGROUND_SERVICE_TYPE_DATA_SYNC)
        } else {
            ForegroundInfo(NOTIFICATION_ID, notification)
        }
    }

    private fun notifyDone() = notify(
        applicationContext.getString(R.string.notification_done_title),
        applicationContext.getString(R.string.notification_done_text),
    )

    private fun notifyFailed(reason: String) = notify(applicationContext.getString(R.string.notification_failed_title), reason)

    private fun notify(title: String, text: String) {
        val notification = NotificationCompat.Builder(applicationContext, ReelCutApp.CHANNEL_PROCESSING)
            .setSmallIcon(R.drawable.ic_launcher_foreground)
            .setContentTitle(title)
            .setContentText(text)
            .setAutoCancel(true)
            .setContentIntent(contentIntent())
            .build()
        runCatching { NotificationManagerCompat.from(applicationContext).notify(NOTIFICATION_ID + 1, notification) }
    }

    companion object {
        const val KEY_FILE = "file"
        const val KEY_PRESET = "preset"
        const val KEY_TARGET_DURATION = "target_duration"
        const val KEY_INSTRUCTIONS = "instructions"
        const val KEY_HOOK_TITLE = "hook_title"

        const val KEY_STAGE = "stage"
        const val KEY_PROGRESS = "progress"
        const val KEY_MESSAGE = "message"
        const val KEY_ERROR = "error"

        const val KEY_OUTPUT_URI = "output_uri"
        const val KEY_OUT_TITLE = "out_title"
        const val KEY_OUT_SUMMARY = "out_summary"
        const val KEY_OUT_CAPTION = "out_caption"
        const val KEY_OUT_DURATION = "out_duration"

        const val STAGE_UPLOADING = "uploading"
        const val STAGE_DOWNLOADING = "downloading"
        const val STAGE_SAVING = "saving"

        private const val NOTIFICATION_ID = 4711
        private const val POLL_INTERVAL_MS = 3_000L
        private const val MAX_WAIT_MS = 45 * 60 * 1000L
    }
}
