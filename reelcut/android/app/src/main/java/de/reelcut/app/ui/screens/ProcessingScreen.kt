package de.reelcut.app.ui.screens

import androidx.compose.animation.core.animateFloatAsState
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.safeDrawingPadding
import androidx.compose.material3.LinearProgressIndicator
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.OutlinedButton
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.getValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.res.stringResource
import androidx.compose.ui.text.style.TextAlign
import androidx.compose.ui.unit.dp
import de.reelcut.app.R
import de.reelcut.app.ui.ProcessingState
import de.reelcut.app.work.ProcessVideoWorker

@Composable
fun ProcessingScreen(state: ProcessingState, onCancel: () -> Unit) {
    val progress by animateFloatAsState(targetValue = state.progress.coerceIn(0f, 1f), label = "progress")
    val stageLabel = stageLabel(state.stage, state.message)

    Column(
        modifier = Modifier
            .fillMaxSize()
            .safeDrawingPadding()
            .padding(32.dp),
        horizontalAlignment = Alignment.CenterHorizontally,
        verticalArrangement = Arrangement.Center,
    ) {
        Text(stringResource(R.string.processing_title), style = MaterialTheme.typography.headlineSmall)
        Spacer(Modifier.height(32.dp))
        LinearProgressIndicator(progress = { progress }, modifier = Modifier.fillMaxWidth().height(10.dp))
        Spacer(Modifier.height(16.dp))
        Text("${(progress * 100).toInt()} %", style = MaterialTheme.typography.titleLarge)
        Spacer(Modifier.height(8.dp))
        Text(stageLabel, style = MaterialTheme.typography.bodyLarge, textAlign = TextAlign.Center)
        Spacer(Modifier.height(32.dp))
        Text(
            stringResource(R.string.processing_hint),
            style = MaterialTheme.typography.bodySmall,
            textAlign = TextAlign.Center,
            color = MaterialTheme.colorScheme.onSurfaceVariant,
        )
        Spacer(Modifier.height(32.dp))
        OutlinedButton(onClick = onCancel) { Text(stringResource(R.string.cancel)) }
    }
}

@Composable
private fun stageLabel(stage: String, message: String): String = when (stage) {
    ProcessVideoWorker.STAGE_UPLOADING -> stringResource(R.string.stage_uploading)
    "queued" -> stringResource(R.string.stage_queued)
    "probing" -> stringResource(R.string.stage_probing)
    "transcribing" -> stringResource(R.string.stage_transcribing)
    "planning" -> stringResource(R.string.stage_planning)
    "rendering" -> stringResource(R.string.stage_rendering)
    ProcessVideoWorker.STAGE_DOWNLOADING -> stringResource(R.string.stage_downloading)
    ProcessVideoWorker.STAGE_SAVING -> stringResource(R.string.stage_saving)
    else -> message.ifBlank { stage }
}
