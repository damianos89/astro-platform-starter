package de.reelcut.app.data

import android.content.Context
import androidx.datastore.core.DataStore
import androidx.datastore.preferences.core.Preferences
import androidx.datastore.preferences.core.booleanPreferencesKey
import androidx.datastore.preferences.core.edit
import androidx.datastore.preferences.core.intPreferencesKey
import androidx.datastore.preferences.core.stringPreferencesKey
import androidx.datastore.preferences.preferencesDataStore
import kotlinx.coroutines.flow.Flow
import kotlinx.coroutines.flow.map

private val Context.dataStore: DataStore<Preferences> by preferencesDataStore(name = "reelcut_settings")

data class AppSettings(
    val baseUrl: String = "http://192.168.0.10:8000/",
    val token: String = "",
    val autoStartOnShare: Boolean = true,
    val defaultOptions: JobOptions = JobOptions(),
    /** WorkManager id of the last job so the UI can re-attach after the app was killed. */
    val lastWorkId: String? = null,
)

class SettingsRepository(private val context: Context) {

    private object Keys {
        val BASE_URL = stringPreferencesKey("base_url")
        val TOKEN = stringPreferencesKey("token")
        val AUTO_START = booleanPreferencesKey("auto_start_on_share")
        val PRESET = stringPreferencesKey("preset")
        val TARGET_DURATION = intPreferencesKey("target_duration")
        val INSTRUCTIONS = stringPreferencesKey("instructions")
        val HOOK_TITLE = booleanPreferencesKey("add_hook_title")
        val LAST_WORK_ID = stringPreferencesKey("last_work_id")
    }

    val settings: Flow<AppSettings> = context.dataStore.data.map { p ->
        val defaults = AppSettings()
        AppSettings(
            baseUrl = p[Keys.BASE_URL] ?: defaults.baseUrl,
            token = p[Keys.TOKEN] ?: defaults.token,
            autoStartOnShare = p[Keys.AUTO_START] ?: defaults.autoStartOnShare,
            defaultOptions = JobOptions(
                preset = StylePreset.fromWire(p[Keys.PRESET]),
                targetDuration = p[Keys.TARGET_DURATION] ?: 0,
                instructions = p[Keys.INSTRUCTIONS] ?: "",
                addHookTitle = p[Keys.HOOK_TITLE] ?: true,
            ),
            lastWorkId = p[Keys.LAST_WORK_ID],
        )
    }

    suspend fun saveServer(baseUrl: String, token: String) {
        context.dataStore.edit {
            it[Keys.BASE_URL] = ApiClient.normalizeBaseUrl(baseUrl)
            it[Keys.TOKEN] = token.trim()
        }
    }

    suspend fun saveAutoStart(enabled: Boolean) {
        context.dataStore.edit { it[Keys.AUTO_START] = enabled }
    }

    suspend fun saveDefaultOptions(options: JobOptions) {
        context.dataStore.edit {
            it[Keys.PRESET] = options.preset.wireName
            it[Keys.TARGET_DURATION] = options.targetDuration
            it[Keys.INSTRUCTIONS] = options.instructions
            it[Keys.HOOK_TITLE] = options.addHookTitle
        }
    }

    suspend fun saveLastWorkId(id: String?) {
        context.dataStore.edit {
            if (id == null) it.remove(Keys.LAST_WORK_ID) else it[Keys.LAST_WORK_ID] = id
        }
    }
}
