package de.reelcut.app.share

import android.content.ClipData
import android.content.ClipboardManager
import android.content.Context
import android.content.Intent
import android.net.Uri
import android.widget.Toast
import de.reelcut.app.R

/**
 * Hands the finished video to TikTok / Instagram via the system share sheet.
 *
 * Neither platform offers a public "post this video" API for personal accounts (TikTok's Content Posting
 * API and Instagram's Graph API need app review / business accounts), so the last tap stays with the user:
 * ReelCut pre-fills everything, copies the suggested caption to the clipboard and opens the target app.
 */
object ShareHelper {

    private val TIKTOK_PACKAGES = listOf("com.zhiliaoapp.musically", "com.ss.android.ugc.trill")
    private const val INSTAGRAM_PACKAGE = "com.instagram.android"

    fun shareToTikTok(context: Context, video: Uri, caption: String) = shareTo(context, video, caption, TIKTOK_PACKAGES, "TikTok")

    fun shareToInstagram(context: Context, video: Uri, caption: String) = shareTo(context, video, caption, listOf(INSTAGRAM_PACKAGE), "Instagram")

    fun shareGeneric(context: Context, video: Uri, caption: String) {
        copyCaption(context, caption)
        context.startActivity(Intent.createChooser(baseIntent(video, caption), null))
    }

    private fun shareTo(context: Context, video: Uri, caption: String, packages: List<String>, label: String) {
        copyCaption(context, caption)
        val intent = baseIntent(video, caption)
        val installed = packages.firstOrNull { isInstalled(context, it) }
        if (installed != null) {
            intent.setPackage(installed)
            runCatching { context.startActivity(intent) }.onSuccess { return }
        }
        Toast.makeText(context, context.getString(R.string.app_not_installed, label), Toast.LENGTH_SHORT).show()
        context.startActivity(Intent.createChooser(baseIntent(video, caption), null))
    }

    private fun baseIntent(video: Uri, caption: String) = Intent(Intent.ACTION_SEND).apply {
        type = "video/mp4"
        putExtra(Intent.EXTRA_STREAM, video)
        if (caption.isNotBlank()) putExtra(Intent.EXTRA_TEXT, caption)
        addFlags(Intent.FLAG_GRANT_READ_URI_PERMISSION or Intent.FLAG_ACTIVITY_NEW_TASK)
        clipData = ClipData.newRawUri("video", video)
    }

    private fun isInstalled(context: Context, packageName: String): Boolean =
        runCatching { context.packageManager.getPackageInfo(packageName, 0) }.isSuccess

    fun copyCaption(context: Context, caption: String) {
        if (caption.isBlank()) return
        val clipboard = context.getSystemService(Context.CLIPBOARD_SERVICE) as ClipboardManager
        clipboard.setPrimaryClip(ClipData.newPlainText("ReelCut caption", caption))
    }
}
