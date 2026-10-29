package de.reelcut.app.ui

import androidx.compose.animation.AnimatedContent
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.material3.Surface
import androidx.compose.runtime.Composable
import androidx.compose.runtime.getValue
import androidx.compose.ui.Modifier
import androidx.lifecycle.compose.collectAsStateWithLifecycle
import de.reelcut.app.ui.screens.HomeScreen
import de.reelcut.app.ui.screens.ProcessingScreen
import de.reelcut.app.ui.screens.ResultScreen
import de.reelcut.app.ui.screens.SettingsScreen

@Composable
fun ReelCutRoot(viewModel: MainViewModel) {
    val state by viewModel.state.collectAsStateWithLifecycle()
    Surface(modifier = Modifier.fillMaxSize()) {
        AnimatedContent(targetState = state.screen, label = "screen") { screen ->
            when (screen) {
                Screen.HOME -> HomeScreen(state = state, viewModel = viewModel)
                Screen.PROCESSING -> ProcessingScreen(state = state.processing, onCancel = viewModel::cancelProcessing)
                Screen.RESULT -> state.result?.let { result ->
                    ResultScreen(result = result, onNewVideo = viewModel::reset, onSettings = viewModel::openSettings)
                } ?: HomeScreen(state = state, viewModel = viewModel)
                Screen.SETTINGS -> SettingsScreen(
                    settings = state.settings,
                    onSaveServer = viewModel::saveServer,
                    onAutoStartChange = viewModel::saveAutoStart,
                    onTest = viewModel::testConnection,
                    onBack = viewModel::closeSettings,
                )
            }
        }
    }
}
