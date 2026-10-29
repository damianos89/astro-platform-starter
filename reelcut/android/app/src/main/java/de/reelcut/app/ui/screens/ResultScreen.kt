package de.reelcut.app.ui.screens

import android.net.Uri
import android.widget.Toast
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.aspectRatio
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.safeDrawingPadding
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.foundation.verticalScroll
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.ContentCopy
import androidx.compose.material.icons.filled.Settings
import androidx.compose.material3.Button
import androidx.compose.material3.Card
import androidx.compose.material3.Icon
import androidx.compose.material3.IconButton
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.OutlinedButton
import androidx.compose.material3.Text
import androidx.compose.material3.TextButton
import androidx.compose.runtime.Composable
import androidx.compose.runtime.DisposableEffect
import androidx.compose.runtime.remember
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.res.stringResource
import androidx.compose.ui.unit.dp
import androidx.compose.ui.viewinterop.AndroidView
import androidx.media3.common.MediaItem
import androidx.media3.common.Player
import androidx.media3.exoplayer.ExoPlayer
import androidx.media3.ui.PlayerView
import de.reelcut.app.R
import de.reelcut.app.data.ProcessedVideo
import de.reelcut.app.share.ShareHelper

@Composable
fun ResultScreen(result: ProcessedVideo, onNewVideo: () -> Unit, onSettings: () -> Unit) {
    val context = LocalContext.current
    val videoUri = remember(result.outputUri) { Uri.parse(result.outputUri) }
    val copiedText = stringResource(R.string.caption_copied)

    Column(
        modifier = Modifier
            .fillMaxSize()
            .safeDrawingPadding()
            .verticalScroll(rememberScrollState())
            .padding(horizontal = 20.dp, vertical = 12.dp),
        verticalArrangement = Arrangement.spacedBy(16.dp),
    ) {
        Row(verticalAlignment = Alignment.CenterVertically) {
            Column(Modifier.weight(1f)) {
                Text(stringResource(R.string.result_title), style = MaterialTheme.typography.headlineSmall)
                Text(stringResource(R.string.result_saved), style = MaterialTheme.typography.bodySmall)
                if (result.durationSeconds > 0) {
                    Text(stringResource(R.string.result_duration, formatDuration(result.durationSeconds)), style = MaterialTheme.typography.bodySmall)
                }
            }
            IconButton(onClick = onSettings) { Icon(Icons.Default.Settings, contentDescription = stringResource(R.string.settings)) }
        }

        VideoPreview(uri = videoUri, modifier = Modifier.fillMaxWidth().aspectRatio(9f / 16f).clip(RoundedCornerShape(16.dp)))

        if (result.title.isNotBlank() || result.summary.isNotBlank()) {
            Card(Modifier.fillMaxWidth()) {
                Column(Modifier.padding(16.dp), verticalArrangement = Arrangement.spacedBy(4.dp)) {
                    if (result.title.isNotBlank()) Text(result.title, style = MaterialTheme.typography.titleMedium)
                    if (result.summary.isNotBlank()) Text(result.summary, style = MaterialTheme.typography.bodySmall)
                }
            }
        }

        if (result.suggestedCaption.isNotBlank()) {
            Card(Modifier.fillMaxWidth()) {
                Column(Modifier.padding(16.dp), verticalArrangement = Arrangement.spacedBy(8.dp)) {
                    Row(verticalAlignment = Alignment.CenterVertically) {
                        Text(stringResource(R.string.suggested_caption_label), style = MaterialTheme.typography.titleSmall, modifier = Modifier.weight(1f))
                        TextButton(onClick = {
                            ShareHelper.copyCaption(context, result.suggestedCaption)
                            Toast.makeText(context, copiedText, Toast.LENGTH_SHORT).show()
                        }) {
                            Icon(Icons.Default.ContentCopy, contentDescription = null)
                            Text(" " + stringResource(R.string.copy))
                        }
                    }
                    Text(result.suggestedCaption, style = MaterialTheme.typography.bodyMedium)
                }
            }
        }

        Row(horizontalArrangement = Arrangement.spacedBy(12.dp), modifier = Modifier.fillMaxWidth()) {
            Button(onClick = { ShareHelper.shareToTikTok(context, videoUri, result.suggestedCaption) }, modifier = Modifier.weight(1f).height(52.dp)) {
                Text(stringResource(R.string.share_tiktok))
            }
            Button(onClick = { ShareHelper.shareToInstagram(context, videoUri, result.suggestedCaption) }, modifier = Modifier.weight(1f).height(52.dp)) {
                Text(stringResource(R.string.share_instagram))
            }
        }
        Row(horizontalArrangement = Arrangement.spacedBy(12.dp), modifier = Modifier.fillMaxWidth()) {
            OutlinedButton(onClick = { ShareHelper.shareGeneric(context, videoUri, result.suggestedCaption) }, modifier = Modifier.weight(1f)) {
                Text(stringResource(R.string.share_other))
            }
            OutlinedButton(onClick = onNewVideo, modifier = Modifier.weight(1f)) { Text(stringResource(R.string.new_video)) }
        }
        Spacer(Modifier.height(24.dp))
    }
}

@Composable
private fun VideoPreview(uri: Uri, modifier: Modifier = Modifier) {
    val context = LocalContext.current
    val player = remember(uri) {
        ExoPlayer.Builder(context).build().apply {
            setMediaItem(MediaItem.fromUri(uri))
            repeatMode = Player.REPEAT_MODE_ONE
            prepare()
            playWhenReady = true
        }
    }
    DisposableEffect(player) { onDispose { player.release() } }
    AndroidView(
        modifier = modifier,
        factory = { ctx -> PlayerView(ctx).apply { useController = true; this.player = player } },
        update = { view -> view.player = player },
    )
}

private fun formatDuration(seconds: Double): String {
    val total = seconds.toInt()
    return "%d:%02d".format(total / 60, total % 60)
}
