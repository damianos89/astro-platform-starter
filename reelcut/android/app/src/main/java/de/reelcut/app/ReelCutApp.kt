package de.reelcut.app

import android.app.Application
import android.app.NotificationChannel
import android.app.NotificationManager
import android.content.Context

class ReelCutApp : Application() {

    override fun onCreate() {
        super.onCreate()
        createNotificationChannel()
    }

    private fun createNotificationChannel() {
        val manager = getSystemService(Context.NOTIFICATION_SERVICE) as NotificationManager
        val channel = NotificationChannel(
            CHANNEL_PROCESSING,
            getString(R.string.notification_channel_name),
            NotificationManager.IMPORTANCE_LOW,
        ).apply { description = getString(R.string.notification_channel_desc) }
        manager.createNotificationChannel(channel)
    }

    companion object {
        const val CHANNEL_PROCESSING = "processing"
    }
}
