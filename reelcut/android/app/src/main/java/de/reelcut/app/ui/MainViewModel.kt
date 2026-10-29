package de.reelcut.app.ui

import android.app.Application
import android.net.Uri
import androidx.lifecycle.AndroidViewModel
import androidx.lifecycle.viewModelScope
import androidx.work.Constraints
import androidx.work.ExistingWorkPolicy
import androidx.work.NetworkType
import androidx.work.OneTimeWorkRequestBuilder
import androidx.work.OutOfQuotaPolicy
import androidx.work.WorkInfo
import androidx.work.WorkManager
import androidx.work.workDataOf
import de.reelcut.app.data.ApiClient
import de.reelcut.app.data.AppSettings
import de.reelcut.app.data.Health
import de.reelcut.app.data.JobOptions
import de.reelcut.app.data.ProcessedVideo
import de.reelcut.app.data.SettingsRepository
import de.reelcut.app.data.VideoRepository
import de.reelcut.app.work.ProcessVideoWorker
import kotlinx.coroutines.Job
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.first
import kotlinx.coroutines.flow.update
import kotlinx.coroutines.launch
import java.io.File
import java.util.UUID

enum class Screen { HOME, PROCESSING, RESULT, SETTINGS }

data class ProcessingState(val stage: String = "queued", val progress: Float = 0f, val message: String = "")

data class UiState(
    val screen: Screen = Screen.HOME,
    val settings: AppSettings = AppSettings(),
    val settingsLoaded: Boolean = false,
    val videoFile: File? = null,
    val videoName: String? = null,
    val importing: Boolean = false,
    val options: JobOptions = JobOptions(),
    val processing: ProcessingState = ProcessingState(),
    val result: ProcessedVideo? = null,
    val error: String? = null,
    val connectionTest: String? = null,
)

class MainViewModel(app: Application) : AndroidViewModel(app) {

    private val settingsRepo = SettingsRepository(app)
    private val videoRepo = VideoRepository(app)
    private val workManager = WorkManager.getInstance(app)

    private val _state = MutableStateFlow(UiState())
    val state: StateFlow<UiState> = _state

    private var workObserver: Job? = null
    private var pendingSharedUri: Uri? = null

    init {
        viewModelScope.launch {
            val initial = settingsRepo.settings.first()
            _state.update { it.copy(settings = initial, options = initial.defaultOptions, settingsLoaded = true) }
            initial.lastWorkId?.let { observeWork(UUID.fromString(it), resume = true) }
            pendingSharedUri?.let { uri -> pendingSharedUri = null; onVideoShared(uri) }
            settingsRepo.settings.collect { s -> _state.update { it.copy(settings = s) } }
        }
    }

    // ------------------------------------------------------------------ video selection

    fun onVideoPicked(uri: Uri) {
        importVideo(uri, autoStart = false)
    }

    /** Entry point for the share-sheet intent. Honours the "start immediately" setting. */
    fun onVideoShared(uri: Uri) {
        if (!_state.value.settingsLoaded) {
            pendingSharedUri = uri
            return
        }
        importVideo(uri, autoStart = _state.value.settings.autoStartOnShare)
    }

    private fun importVideo(uri: Uri, autoStart: Boolean) {
        viewModelScope.launch {
            _state.update { it.copy(importing = true, error = null, screen = Screen.HOME) }
            runCatching { videoRepo.importToCache(uri) }
                .onSuccess { file ->
                    _state.update { it.copy(videoFile = file, videoName = videoRepo.displayName(uri) ?: file.name, importing = false) }
                    if (autoStart) startProcessing()
                }
                .onFailure { e -> _state.update { it.copy(importing = false, error = e.message ?: "Import fehlgeschlagen") } }
        }
    }

    fun updateOptions(transform: (JobOptions) -> JobOptions) {
        _state.update { it.copy(options = transform(it.options)) }
    }

    // ------------------------------------------------------------------ processing

    fun startProcessing() {
        val file = _state.value.videoFile ?: return
        val options = _state.value.options
        viewModelScope.launch { settingsRepo.saveDefaultOptions(options) }

        val request = OneTimeWorkRequestBuilder<ProcessVideoWorker>()
            .setInputData(
                workDataOf(
                    ProcessVideoWorker.KEY_FILE to file.absolutePath,
                    ProcessVideoWorker.KEY_PRESET to options.preset.wireName,
                    ProcessVideoWorker.KEY_TARGET_DURATION to options.targetDuration,
                    ProcessVideoWorker.KEY_INSTRUCTIONS to options.instructions,
                    ProcessVideoWorker.KEY_HOOK_TITLE to options.addHookTitle,
                ),
            )
            .setConstraints(Constraints.Builder().setRequiredNetworkType(NetworkType.CONNECTED).build())
            .setExpedited(OutOfQuotaPolicy.RUN_AS_NON_EXPEDITED_WORK_REQUEST)
            .build()
        workManager.enqueueUniqueWork(UNIQUE_WORK, ExistingWorkPolicy.REPLACE, request)
        viewModelScope.launch { settingsRepo.saveLastWorkId(request.id.toString()) }
        _state.update { it.copy(screen = Screen.PROCESSING, processing = ProcessingState(), error = null, result = null) }
        observeWork(request.id, resume = false)
    }

    private fun observeWork(id: UUID, resume: Boolean) {
        workObserver?.cancel()
        workObserver = viewModelScope.launch {
            workManager.getWorkInfoByIdFlow(id).collect { info ->
                if (info == null) {
                    if (resume) settingsRepo.saveLastWorkId(null)
                    return@collect
                }
                when (info.state) {
                    WorkInfo.State.ENQUEUED, WorkInfo.State.BLOCKED -> _state.update {
                        it.copy(screen = Screen.PROCESSING, processing = ProcessingState("queued", 0f, ""))
                    }
                    WorkInfo.State.RUNNING -> {
                        val p = info.progress
                        _state.update {
                            it.copy(
                                screen = Screen.PROCESSING,
                                processing = ProcessingState(
                                    stage = p.getString(ProcessVideoWorker.KEY_STAGE) ?: "queued",
                                    progress = p.getFloat(ProcessVideoWorker.KEY_PROGRESS, 0f),
                                    message = p.getString(ProcessVideoWorker.KEY_MESSAGE) ?: "",
                                ),
                            )
                        }
                    }
                    WorkInfo.State.SUCCEEDED -> {
                        val out = info.outputData
                        val result = ProcessedVideo(
                            outputUri = out.getString(ProcessVideoWorker.KEY_OUTPUT_URI) ?: "",
                            title = out.getString(ProcessVideoWorker.KEY_OUT_TITLE) ?: "",
                            summary = out.getString(ProcessVideoWorker.KEY_OUT_SUMMARY) ?: "",
                            suggestedCaption = out.getString(ProcessVideoWorker.KEY_OUT_CAPTION) ?: "",
                            durationSeconds = out.getDouble(ProcessVideoWorker.KEY_OUT_DURATION, 0.0),
                        )
                        settingsRepo.saveLastWorkId(null)
                        _state.update { it.copy(screen = Screen.RESULT, result = result, videoFile = null, videoName = null) }
                    }
                    WorkInfo.State.FAILED -> {
                        settingsRepo.saveLastWorkId(null)
                        val msg = info.outputData.getString(ProcessVideoWorker.KEY_ERROR) ?: "Unbekannter Fehler"
                        _state.update { it.copy(screen = Screen.HOME, error = msg) }
                    }
                    WorkInfo.State.CANCELLED -> {
                        settingsRepo.saveLastWorkId(null)
                        _state.update { it.copy(screen = Screen.HOME) }
                    }
                }
            }
        }
    }

    fun cancelProcessing() {
        workManager.cancelUniqueWork(UNIQUE_WORK)
        _state.update { it.copy(screen = Screen.HOME, processing = ProcessingState()) }
    }

    fun reset() {
        _state.update { it.copy(screen = Screen.HOME, result = null, error = null, videoFile = null, videoName = null) }
    }

    fun dismissError() = _state.update { it.copy(error = null) }

    // ------------------------------------------------------------------ settings

    fun openSettings() = _state.update { it.copy(screen = Screen.SETTINGS, connectionTest = null) }

    fun closeSettings() = _state.update { it.copy(screen = if (it.result != null) Screen.RESULT else Screen.HOME) }

    fun saveServer(baseUrl: String, token: String) {
        viewModelScope.launch { settingsRepo.saveServer(baseUrl, token) }
    }

    fun saveAutoStart(enabled: Boolean) {
        viewModelScope.launch { settingsRepo.saveAutoStart(enabled) }
    }

    fun testConnection(baseUrl: String, token: String, onResult: (Result<Health>) -> Unit) {
        viewModelScope.launch {
            val result = runCatching { ApiClient.create(baseUrl, token).health() }
            onResult(result)
        }
    }

    companion object {
        private const val UNIQUE_WORK = "reelcut-process"
    }
}
