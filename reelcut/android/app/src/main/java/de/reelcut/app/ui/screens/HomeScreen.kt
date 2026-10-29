package de.reelcut.app.ui.screens

import androidx.activity.compose.rememberLauncherForActivityResult
import androidx.activity.result.PickVisualMediaRequest
import androidx.activity.result.contract.ActivityResultContracts
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.safeDrawingPadding
import androidx.compose.foundation.layout.width
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.verticalScroll
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.Settings
import androidx.compose.material.icons.filled.VideoLibrary
import androidx.compose.material3.AssistChip
import androidx.compose.material3.Button
import androidx.compose.material3.Card
import androidx.compose.material3.CircularProgressIndicator
import androidx.compose.material3.ExperimentalMaterial3Api
import androidx.compose.material3.FilterChip
import androidx.compose.material3.Icon
import androidx.compose.material3.IconButton
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.OutlinedButton
import androidx.compose.material3.OutlinedTextField
import androidx.compose.material3.Slider
import androidx.compose.material3.Switch
import androidx.compose.material3.Text
import androidx.compose.material3.TextButton
import androidx.compose.runtime.Composable
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.res.stringResource
import androidx.compose.ui.unit.dp
import de.reelcut.app.R
import de.reelcut.app.data.StylePreset
import de.reelcut.app.ui.MainViewModel
import de.reelcut.app.ui.UiState

@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun HomeScreen(state: UiState, viewModel: MainViewModel) {
    val picker = rememberLauncherForActivityResult(ActivityResultContracts.PickVisualMedia()) { uri ->
        uri?.let(viewModel::onVideoPicked)
    }
    val options = state.options

    Column(
        modifier = Modifier
            .fillMaxSize()
            .safeDrawingPadding()
            .verticalScroll(rememberScrollState())
            .padding(horizontal = 20.dp, vertical = 12.dp),
        verticalArrangement = Arrangement.spacedBy(16.dp),
    ) {
        Row(verticalAlignment = Alignment.CenterVertically) {
            Text(stringResource(R.string.home_title), style = MaterialTheme.typography.headlineSmall, modifier = Modifier.weight(1f))
            IconButton(onClick = viewModel::openSettings) {
                Icon(Icons.Default.Settings, contentDescription = stringResource(R.string.settings))
            }
        }
        Text(stringResource(R.string.home_subtitle), style = MaterialTheme.typography.bodyMedium)

        // ------------------------------------------------------------------ video
        Card(modifier = Modifier.fillMaxWidth()) {
            Column(modifier = Modifier.padding(16.dp), verticalArrangement = Arrangement.spacedBy(12.dp)) {
                when {
                    state.importing -> Row(verticalAlignment = Alignment.CenterVertically) {
                        CircularProgressIndicator(modifier = Modifier.width(24.dp).height(24.dp))
                        Spacer(Modifier.width(12.dp))
                        Text("Video wird übernommen …")
                    }
                    state.videoFile != null -> {
                        Row(verticalAlignment = Alignment.CenterVertically) {
                            Icon(Icons.Default.VideoLibrary, contentDescription = null)
                            Spacer(Modifier.width(12.dp))
                            Column(Modifier.weight(1f)) {
                                Text(state.videoName ?: state.videoFile.name, style = MaterialTheme.typography.titleMedium)
                                Text("%.1f MB".format(state.videoFile.length() / 1e6), style = MaterialTheme.typography.bodySmall)
                            }
                        }
                        TextButton(onClick = { picker.launch(PickVisualMediaRequest(ActivityResultContracts.PickVisualMedia.VideoOnly)) }) {
                            Text(stringResource(R.string.change_video))
                        }
                    }
                    else -> {
                        Text(stringResource(R.string.no_video_selected), style = MaterialTheme.typography.bodyMedium)
                        Button(
                            onClick = { picker.launch(PickVisualMediaRequest(ActivityResultContracts.PickVisualMedia.VideoOnly)) },
                            modifier = Modifier.fillMaxWidth(),
                        ) { Text(stringResource(R.string.pick_video)) }
                    }
                }
            }
        }

        // ------------------------------------------------------------------ options
        Text(stringResource(R.string.preset_label), style = MaterialTheme.typography.titleSmall)
        Row(horizontalArrangement = Arrangement.spacedBy(8.dp), modifier = Modifier.fillMaxWidth()) {
            PresetChip(StylePreset.FREESTYLE_MIX, R.string.preset_freestyle_mix, options.preset) { p -> viewModel.updateOptions { it.copy(preset = p) } }
            PresetChip(StylePreset.BOLD_POP, R.string.preset_bold_pop, options.preset) { p -> viewModel.updateOptions { it.copy(preset = p) } }
        }
        Row(horizontalArrangement = Arrangement.spacedBy(8.dp), modifier = Modifier.fillMaxWidth()) {
            PresetChip(StylePreset.CLEAN, R.string.preset_clean, options.preset) { p -> viewModel.updateOptions { it.copy(preset = p) } }
            PresetChip(StylePreset.KARAOKE, R.string.preset_karaoke, options.preset) { p -> viewModel.updateOptions { it.copy(preset = p) } }
        }

        Row(verticalAlignment = Alignment.CenterVertically) {
            Text(stringResource(R.string.target_duration_label), style = MaterialTheme.typography.titleSmall, modifier = Modifier.weight(1f))
            AssistChip(
                onClick = {},
                label = {
                    Text(
                        if (options.targetDuration == 0) stringResource(R.string.target_duration_auto)
                        else stringResource(R.string.target_duration_seconds, options.targetDuration),
                    )
                },
            )
        }
        Slider(
            value = options.targetDuration.toFloat(),
            onValueChange = { v -> viewModel.updateOptions { it.copy(targetDuration = (v / 5).toInt() * 5) } },
            valueRange = 0f..90f,
            steps = 17,
        )

        OutlinedTextField(
            value = options.instructions,
            onValueChange = { v -> viewModel.updateOptions { it.copy(instructions = v) } },
            label = { Text(stringResource(R.string.instructions_label)) },
            placeholder = { Text(stringResource(R.string.instructions_hint)) },
            minLines = 2,
            modifier = Modifier.fillMaxWidth(),
        )

        Row(verticalAlignment = Alignment.CenterVertically) {
            Text(stringResource(R.string.hook_title_label), modifier = Modifier.weight(1f))
            Switch(checked = options.addHookTitle, onCheckedChange = { c -> viewModel.updateOptions { it.copy(addHookTitle = c) } })
        }

        state.error?.let { err ->
            Card(modifier = Modifier.fillMaxWidth()) {
                Column(Modifier.padding(16.dp)) {
                    Text(stringResource(R.string.error_title), style = MaterialTheme.typography.titleSmall, color = MaterialTheme.colorScheme.error)
                    Text(stringResource(R.string.error_generic, err), style = MaterialTheme.typography.bodySmall)
                    Row(horizontalArrangement = Arrangement.End, modifier = Modifier.fillMaxWidth()) {
                        TextButton(onClick = viewModel::dismissError) { Text("OK") }
                        if (state.videoFile != null) OutlinedButton(onClick = viewModel::startProcessing) { Text(stringResource(R.string.retry)) }
                    }
                }
            }
        }

        Button(
            onClick = viewModel::startProcessing,
            enabled = state.videoFile != null && !state.importing,
            modifier = Modifier.fillMaxWidth().height(56.dp),
        ) { Text(stringResource(R.string.start_processing), style = MaterialTheme.typography.titleMedium) }
        Spacer(Modifier.height(24.dp))
    }
}

@Composable
private fun PresetChip(preset: StylePreset, labelRes: Int, selected: StylePreset, onSelect: (StylePreset) -> Unit) {
    FilterChip(selected = preset == selected, onClick = { onSelect(preset) }, label = { Text(stringResource(labelRes)) })
}
