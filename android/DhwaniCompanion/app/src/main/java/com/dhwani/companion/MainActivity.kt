package com.dhwani.companion

import android.Manifest
import android.content.pm.PackageManager
import android.media.MediaRecorder
import android.os.Bundle
import androidx.activity.ComponentActivity
import androidx.activity.compose.setContent
import androidx.activity.result.contract.ActivityResultContracts
import androidx.compose.foundation.background
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material3.Button
import androidx.compose.material3.ButtonDefaults
import androidx.compose.material3.Card
import androidx.compose.material3.CardDefaults
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Surface
import androidx.compose.material3.Text
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.setValue
import androidx.compose.runtime.*
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import java.io.File

class MainActivity : ComponentActivity() {

    private var recorder: MediaRecorder? = null
    private var audioFile: File? = null

    private var recording by mutableStateOf(false)
    private var status by mutableStateOf("READY")
    private var risk by mutableStateOf("--")

    private val permissionLauncher =
        registerForActivityResult(
            ActivityResultContracts.RequestPermission()
        ) { granted ->
            if (granted) {
                startRecording()
            } else {
                status = "MICROPHONE PERMISSION DENIED"
            }
        }

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)

        setContent {
            DhwaniScreen(
                recording = recording,
                status = status,
                risk = risk,
                onRecord = {
                    if (recording) {
                        stopRecording()
                    } else {
                        checkPermissionAndRecord()
                    }
                }
            )
        }
    }

    private fun checkPermissionAndRecord() {
        if (
            checkSelfPermission(Manifest.permission.RECORD_AUDIO)
            != PackageManager.PERMISSION_GRANTED
        ) {
            permissionLauncher.launch(Manifest.permission.RECORD_AUDIO)
        } else {
            startRecording()
        }
    }

    private fun startRecording() {
        try {
            audioFile = File(
                externalCacheDir,
                "dhwani_${System.currentTimeMillis()}.m4a"
            )

            recorder = MediaRecorder(this).apply {
                setAudioSource(MediaRecorder.AudioSource.VOICE_COMMUNICATION)
                setOutputFormat(MediaRecorder.OutputFormat.MPEG_4)
                setAudioEncoder(MediaRecorder.AudioEncoder.AAC)
                setAudioEncodingBitRate(128000)
                setAudioSamplingRate(16000)
                setOutputFile(audioFile!!.absolutePath)

                prepare()
                start()
            }

            recording = true
            status = "RECORDING"
            risk = "--"

        } catch (e: Exception) {
            status = "RECORDING ERROR"
            recorder?.release()
            recorder = null
        }
    }

    private fun stopRecording() {
        try {
            recorder?.stop()
        } catch (_: Exception) {
        }

        recorder?.release()
        recorder = null

        recording = false
        status = "RECORDED"

        audioFile?.let {
            uploadAudio(it)
        }
    }

    private fun uploadAudio(file: File) {
        Thread {
            try {
                val url = java.net.URL(
                    "http://172.21.1.0:8000/analyze"
                )
                val connection =
                    url.openConnection() as java.net.HttpURLConnection

                connection.requestMethod = "POST"
                connection.doOutput = true
                connection.setRequestProperty(
                    "Content-Type",
                    "audio/mp4"
                )

                file.inputStream().use { input ->
                    connection.outputStream.use { output ->
                        input.copyTo(output)
                    }
                }

                val responseCode = connection.responseCode

                runOnUiThread {
                    if (responseCode in 200..299) {
                        status = "ANALYSIS COMPLETE"
                        risk = "RESULT RECEIVED"
                    } else {
                        status = "SERVER ERROR"
                    }
                }

                connection.disconnect()

            } catch (e: Exception) {
                runOnUiThread {
                    status = "SERVER OFFLINE"
                }
            }
        }.start()
    }
}

@Composable
fun DhwaniScreen(
    recording: Boolean,
    status: String,
    risk: String,
    onRecord: () -> Unit
) {
    Surface(
        modifier = Modifier.fillMaxSize(),
        color = Color(0xFF071111)
    ) {
        Column(
            modifier = Modifier
                .fillMaxSize()
                .padding(24.dp),
            horizontalAlignment = Alignment.CenterHorizontally
        ) {

            Text(
                text = "ECHOSHIELD",
                fontSize = 28.sp,
                fontWeight = FontWeight.Bold,
                color = Color.White
            )

            Text(
                text = "AI VOICE PROTECTION",
                fontSize = 12.sp,
                color = Color(0xFF8FAAAA)
            )

            Spacer(modifier = Modifier.height(30.dp))

            Card(
                modifier = Modifier.fillMaxWidth(),
                shape = RoundedCornerShape(20.dp),
                colors = CardDefaults.cardColors(
                    containerColor = Color(0xFF102020)
                )
            ) {
                Column(
                    modifier = Modifier.padding(24.dp)
                ) {

                    Text(
                        text = "● ${if (recording) "LIVE ANALYSIS" else "READY"}",
                        color = if (recording)
                            Color(0xFFFF5252)
                        else
                            Color(0xFF4CAF50),
                        fontSize = 18.sp,
                        fontWeight = FontWeight.Bold
                    )

                    Spacer(modifier = Modifier.height(20.dp))

                    Text(
                        text = "RISK SCORE",
                        color = Color(0xFF8FAAAA),
                        fontSize = 13.sp
                    )

                    Text(
                        text = risk,
                        color = Color.White,
                        fontSize = 42.sp,
                        fontWeight = FontWeight.Bold
                    )

                    Spacer(modifier = Modifier.height(12.dp))

                    Text(
                        text = status,
                        color = Color.White,
                        fontSize = 16.sp
                    )
                }
            }

            Spacer(modifier = Modifier.height(24.dp))

            Row(
                modifier = Modifier.fillMaxWidth(),
                horizontalArrangement = Arrangement.spacedBy(12.dp)
            ) {

                Button(
                    onClick = onRecord,
                    modifier = Modifier
                        .weight(1f)
                        .height(58.dp),
                    shape = RoundedCornerShape(16.dp),
                    colors = ButtonDefaults.buttonColors(
                        containerColor =
                            if (recording)
                                Color(0xFFB71C1C)
                            else
                                Color(0xFF176B87)
                    )
                ) {
                    Text(
                        if (recording)
                            "STOP"
                        else
                            "RECORD CALL"
                    )
                }
            }

            Spacer(modifier = Modifier.height(28.dp))

            Text(
                text = "WHY?",
                modifier = Modifier.fillMaxWidth(),
                color = Color.White,
                fontSize = 18.sp,
                fontWeight = FontWeight.Bold
            )

            Spacer(modifier = Modifier.height(10.dp))

            Text(
                text = "✓ Speech detection\n" +
                        "✓ Audio analysis\n" +
                        "⚠ Anti-spoofing analysis\n" +
                        "⚠ Verification recommended",
                modifier = Modifier.fillMaxWidth(),
                color = Color(0xFFB8C8C8),
                fontSize = 15.sp,
                lineHeight = 27.sp
            )

            Spacer(modifier = Modifier.weight(1f))

            Text(
                text = "Dhwani • Voice Authenticity Protection",
                color = Color(0xFF607070),
                fontSize = 11.sp
            )
        }
    }
}