package de.reelcut.app.ui.theme

import android.os.Build
import androidx.compose.foundation.isSystemInDarkTheme
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.darkColorScheme
import androidx.compose.material3.dynamicDarkColorScheme
import androidx.compose.material3.dynamicLightColorScheme
import androidx.compose.material3.lightColorScheme
import androidx.compose.runtime.Composable
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.platform.LocalContext

private val Yellow = Color(0xFFFFD400)
private val Pink = Color(0xFFFF2D55)
private val Ink = Color(0xFF0F0F14)

private val DarkColors = darkColorScheme(
    primary = Yellow,
    onPrimary = Ink,
    secondary = Pink,
    onSecondary = Color.White,
    background = Ink,
    surface = Color(0xFF17171F),
    onBackground = Color(0xFFF4F4F8),
    onSurface = Color(0xFFF4F4F8),
)

private val LightColors = lightColorScheme(
    primary = Color(0xFF8A6D00),
    secondary = Pink,
    background = Color(0xFFFCFBF7),
    surface = Color.White,
)

@Composable
fun ReelCutTheme(darkTheme: Boolean = isSystemInDarkTheme(), content: @Composable () -> Unit) {
    val context = LocalContext.current
    val colors = when {
        Build.VERSION.SDK_INT >= Build.VERSION_CODES.S ->
            if (darkTheme) dynamicDarkColorScheme(context) else dynamicLightColorScheme(context)
        darkTheme -> DarkColors
        else -> LightColors
    }
    MaterialTheme(colorScheme = colors, content = content)
}
