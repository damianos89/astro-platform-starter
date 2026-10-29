package de.reelcut.app.data

import kotlinx.serialization.SerialName
import kotlinx.serialization.Serializable

/** Mirrors backend/reelcut/schemas.py (only the fields the app needs; unknown keys are ignored). */

enum class StylePreset(val wireName: String) {
    FREESTYLE_MIX("freestyle_mix"),
    BOLD_POP("bold_pop"),
    CLEAN("clean"),
    KARAOKE("karaoke");

    companion object {
        fun fromWire(name: String?): StylePreset = entries.firstOrNull { it.wireName == name } ?: FREESTYLE_MIX
    }
}

@Serializable
data class JobStatus(
    val id: String,
    val stage: String,
    val progress: Float = 0f,
    val message: String = "",
    val error: String? = null,
    val plan: EditPlan? = null,
    @SerialName("result_url") val resultUrl: String? = null,
    @SerialName("output_duration") val outputDuration: Double? = null,
) {
    val isDone get() = stage == "done"
    val isFailed get() = stage == "failed"
}

@Serializable
data class EditPlan(
    val title: String = "",
    val summary: String = "",
    @SerialName("keep_segments") val keepSegments: List<Segment> = emptyList(),
    val captions: List<Caption> = emptyList(),
    @SerialName("suggested_caption") val suggestedCaption: String = "",
)

@Serializable
data class Segment(val start: Double, val end: Double, val reason: String = "")

@Serializable
data class Caption(val start: Double, val end: Double, val text: String)

@Serializable
data class Health(
    val ok: Boolean,
    val planner: String = "",
    val transcriber: String = "",
    val model: String = "",
)

/** What the user configures before starting a job. */
data class JobOptions(
    val preset: StylePreset = StylePreset.FREESTYLE_MIX,
    /** seconds, 0 = let Claude decide */
    val targetDuration: Int = 0,
    val instructions: String = "",
    val addHookTitle: Boolean = true,
)

/** Final result shown on the result screen. */
data class ProcessedVideo(
    val outputUri: String,
    val title: String,
    val summary: String,
    val suggestedCaption: String,
    val durationSeconds: Double,
)
