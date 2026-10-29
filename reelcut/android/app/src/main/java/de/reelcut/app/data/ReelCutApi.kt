package de.reelcut.app.data

import kotlinx.serialization.json.Json
import okhttp3.MediaType.Companion.toMediaType
import okhttp3.MultipartBody
import okhttp3.OkHttpClient
import okhttp3.RequestBody
import okhttp3.ResponseBody
import okhttp3.logging.HttpLoggingInterceptor
import retrofit2.Retrofit
import retrofit2.converter.kotlinx.serialization.asConverterFactory
import retrofit2.http.GET
import retrofit2.http.Multipart
import retrofit2.http.POST
import retrofit2.http.Part
import retrofit2.http.Path
import retrofit2.http.Streaming
import java.util.concurrent.TimeUnit

interface ReelCutApi {

    @GET("healthz")
    suspend fun health(): Health

    @Multipart
    @POST("v1/jobs")
    suspend fun createJob(
        @Part file: MultipartBody.Part,
        @Part("preset") preset: RequestBody,
        @Part("target_duration") targetDuration: RequestBody,
        @Part("instructions") instructions: RequestBody,
        @Part("language") language: RequestBody,
        @Part("add_hook_title") addHookTitle: RequestBody,
    ): JobStatus

    @GET("v1/jobs/{id}")
    suspend fun getJob(@Path("id") id: String): JobStatus

    @Streaming
    @GET("v1/jobs/{id}/result")
    suspend fun downloadResult(@Path("id") id: String): ResponseBody
}

object ApiClient {

    val json = Json {
        ignoreUnknownKeys = true
        coerceInputValues = true
        isLenient = true
    }

    fun normalizeBaseUrl(raw: String): String {
        var url = raw.trim()
        if (url.isEmpty()) return url
        if (!url.startsWith("http://") && !url.startsWith("https://")) url = "http://$url"
        if (!url.endsWith("/")) url += "/"
        return url
    }

    fun create(baseUrl: String, token: String, debugLogging: Boolean = false): ReelCutApi {
        val clientBuilder = OkHttpClient.Builder()
            .connectTimeout(30, TimeUnit.SECONDS)
            .readTimeout(10, TimeUnit.MINUTES) // downloads of long renders
            .writeTimeout(30, TimeUnit.MINUTES) // uploads over mobile data
            .addInterceptor { chain ->
                val request = chain.request().newBuilder().apply {
                    if (token.isNotBlank()) header("Authorization", "Bearer $token")
                }.build()
                chain.proceed(request)
            }
        if (debugLogging) {
            clientBuilder.addInterceptor(HttpLoggingInterceptor().apply { level = HttpLoggingInterceptor.Level.BASIC })
        }
        return Retrofit.Builder()
            .baseUrl(normalizeBaseUrl(baseUrl))
            .client(clientBuilder.build())
            .addConverterFactory(json.asConverterFactory("application/json".toMediaType()))
            .build()
            .create(ReelCutApi::class.java)
    }
}
