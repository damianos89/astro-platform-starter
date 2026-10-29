package de.reelcut.app

import android.Manifest
import android.content.Intent
import android.net.Uri
import android.os.Build
import android.os.Bundle
import androidx.activity.ComponentActivity
import androidx.activity.compose.setContent
import androidx.activity.enableEdgeToEdge
import androidx.activity.result.contract.ActivityResultContracts
import androidx.activity.viewModels
import androidx.core.content.IntentCompat
import de.reelcut.app.ui.MainViewModel
import de.reelcut.app.ui.ReelCutRoot
import de.reelcut.app.ui.theme.ReelCutTheme

class MainActivity : ComponentActivity() {

    private val viewModel: MainViewModel by viewModels()

    private val notificationPermission =
        registerForActivityResult(ActivityResultContracts.RequestPermission()) { /* optional, nice to have */ }

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        enableEdgeToEdge()
        requestNotificationPermissionIfNeeded()
        handleIntent(intent)
        setContent {
            ReelCutTheme {
                ReelCutRoot(viewModel = viewModel)
            }
        }
    }

    override fun onNewIntent(intent: Intent) {
        super.onNewIntent(intent)
        setIntent(intent)
        handleIntent(intent)
    }

    /** A video shared from the gallery / camera / another app lands here. */
    private fun handleIntent(intent: Intent?) {
        if (intent?.action != Intent.ACTION_SEND || intent.type?.startsWith("video/") != true) return
        val uri: Uri = IntentCompat.getParcelableExtra(intent, Intent.EXTRA_STREAM, Uri::class.java) ?: return
        viewModel.onVideoShared(uri)
        // consume it so a configuration change doesn't start the job twice
        intent.action = Intent.ACTION_MAIN
        intent.removeExtra(Intent.EXTRA_STREAM)
    }

    private fun requestNotificationPermissionIfNeeded() {
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.TIRAMISU) {
            notificationPermission.launch(Manifest.permission.POST_NOTIFICATIONS)
        }
    }

    companion object {
        const val EXTRA_WORK_ID = "work_id"
    }
}
