package de.reelcut.app.ui.screens

import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.safeDrawingPadding
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.text.KeyboardOptions
import androidx.compose.foundation.verticalScroll
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.automirrored.filled.ArrowBack
import androidx.compose.material3.Button
import androidx.compose.material3.Icon
import androidx.compose.material3.IconButton
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.OutlinedButton
import androidx.compose.material3.OutlinedTextField
import androidx.compose.material3.Switch
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.saveable.rememberSaveable
import androidx.compose.runtime.setValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.res.stringResource
import androidx.compose.ui.text.input.KeyboardType
import androidx.compose.ui.text.input.PasswordVisualTransformation
import androidx.compose.ui.unit.dp
import de.reelcut.app.R
import de.reelcut.app.data.AppSettings
import de.reelcut.app.data.Health

@Composable
fun SettingsScreen(
    settings: AppSettings,
    onSaveServer: (String, String) -> Unit,
    onAutoStartChange: (Boolean) -> Unit,
    onTest: (String, String, (Result<Health>) -> Unit) -> Unit,
    onBack: () -> Unit,
) {
    var baseUrl by rememberSaveable { mutableStateOf(settings.baseUrl) }
    var token by rememberSaveable { mutableStateOf(settings.token) }
    var testResult by rememberSaveable { mutableStateOf<String?>(null) }
    var testing by rememberSaveable { mutableStateOf(false) }
    LaunchedEffect(settings.baseUrl, settings.token) {
        if (baseUrl.isBlank()) baseUrl = settings.baseUrl
        if (token.isBlank()) token = settings.token
    }
    val context = LocalContext.current

    Column(
        modifier = Modifier
            .fillMaxSize()
            .safeDrawingPadding()
            .verticalScroll(rememberScrollState())
            .padding(horizontal = 20.dp, vertical = 12.dp),
        verticalArrangement = Arrangement.spacedBy(16.dp),
    ) {
        Row(verticalAlignment = Alignment.CenterVertically) {
            IconButton(onClick = onBack) { Icon(Icons.AutoMirrored.Filled.ArrowBack, contentDescription = stringResource(R.string.back)) }
            Text(stringResource(R.string.settings_title), style = MaterialTheme.typography.headlineSmall)
        }

        OutlinedTextField(
            value = baseUrl,
            onValueChange = { baseUrl = it },
            label = { Text(stringResource(R.string.settings_server_url)) },
            placeholder = { Text(stringResource(R.string.settings_server_hint)) },
            singleLine = true,
            keyboardOptions = KeyboardOptions(keyboardType = KeyboardType.Uri),
            modifier = Modifier.fillMaxWidth(),
        )
        OutlinedTextField(
            value = token,
            onValueChange = { token = it },
            label = { Text(stringResource(R.string.settings_token)) },
            singleLine = true,
            visualTransformation = PasswordVisualTransformation(),
            keyboardOptions = KeyboardOptions(keyboardType = KeyboardType.Password),
            modifier = Modifier.fillMaxWidth(),
        )
        Row(horizontalArrangement = Arrangement.spacedBy(12.dp)) {
            OutlinedButton(
                enabled = !testing && baseUrl.isNotBlank(),
                onClick = {
                    testing = true
                    testResult = null
                    onTest(baseUrl, token) { r ->
                        testing = false
                        testResult = r.fold(
                            onSuccess = { context.getString(R.string.settings_connection_ok, it.planner, it.model) },
                            onFailure = { context.getString(R.string.settings_connection_failed, it.message ?: it.javaClass.simpleName) },
                        )
                    }
                },
                modifier = Modifier.weight(1f),
            ) { Text(stringResource(R.string.settings_test_connection)) }
            Button(onClick = { onSaveServer(baseUrl, token); onBack() }, modifier = Modifier.weight(1f)) {
                Text(stringResource(R.string.save))
            }
        }
        testResult?.let { Text(it, style = MaterialTheme.typography.bodySmall) }

        Spacer(Modifier.height(8.dp))
        Row(verticalAlignment = Alignment.CenterVertically) {
            Column(Modifier.weight(1f)) {
                Text(stringResource(R.string.settings_auto_start), style = MaterialTheme.typography.titleSmall)
                Text(stringResource(R.string.settings_auto_start_desc), style = MaterialTheme.typography.bodySmall)
            }
            Switch(checked = settings.autoStartOnShare, onCheckedChange = onAutoStartChange)
        }
    }
}
