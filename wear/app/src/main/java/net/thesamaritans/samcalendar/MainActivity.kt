package net.thesamaritans.samcalendar

import android.annotation.SuppressLint
import android.app.Activity
import android.os.Bundle
import android.view.InputDevice
import android.view.MotionEvent
import android.view.ViewGroup
import android.webkit.WebResourceRequest
import android.webkit.WebResourceResponse
import android.webkit.WebView
import android.webkit.WebViewClient
import androidx.webkit.WebViewAssetLoader
import java.io.File
import java.io.FileInputStream
import java.net.HttpURLConnection
import java.net.URL
import java.util.Calendar
import kotlin.math.abs

/**
 * Wraps the watch web build in a WebView. The page is served from assets through
 * WebViewAssetLoader, so it lives on a real https origin (localStorage and the
 * service worker behave normally) and opens instantly with no network at all.
 *
 * Two things the page cannot work out for itself are passed in on the URL:
 * the physical case shape, which Android reports and the CSS Round Display
 * media query does not expose inside a plain WebView, and tap navigation,
 * because Wear reserves the horizontal swipe for its own dismiss gesture.
 */
class MainActivity : Activity() {

    private companion object {
        const val ORIGIN = "https://appassets.androidplatform.net"
        const val PAGE = "$ORIGIN/assets/watch/index.html"
        const val SITE = "https://sam-calendar.the-samaritans.net"
        val CAL_PATH = Regex("^/assets/cal/(\\d{4})\\.dat$")
    }

    private lateinit var web: WebView

    @SuppressLint("SetJavaScriptEnabled")
    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)

        val loader = WebViewAssetLoader.Builder()
            .setDomain("appassets.androidplatform.net")
            .addPathHandler("/assets/", WebViewAssetLoader.AssetsPathHandler(this))
            .build()

        web = WebView(this)
        web.layoutParams = ViewGroup.LayoutParams(
            ViewGroup.LayoutParams.MATCH_PARENT, ViewGroup.LayoutParams.MATCH_PARENT
        )
        setContentView(web)

        web.settings.apply {
            javaScriptEnabled = true
            domStorageEnabled = true
            builtInZoomControls = false
            displayZoomControls = false
            textZoom = 100                 // ignore the system font scale; the layout is in vmin
        }
        web.setBackgroundColor(0xFF000000.toInt())
        web.isVerticalScrollBarEnabled = false
        web.isHorizontalScrollBarEnabled = false

        web.webViewClient = object : WebViewClient() {
            override fun shouldInterceptRequest(
                view: WebView, request: WebResourceRequest
            ): WebResourceResponse? {
                // Prefer a year file refreshed from the live site over the bundled one.
                val path = request.url.path
                if (path != null) {
                    CAL_PATH.find(path)?.let { m ->
                        val f = File(filesDir, "cal/${m.groupValues[1]}.dat")
                        if (f.isFile && f.length() > 1000) {
                            try {
                                return WebResourceResponse("text/plain", "utf-8", FileInputStream(f))
                            } catch (e: Exception) {
                                // fall through to the bundled asset
                            }
                        }
                    }
                }
                return loader.shouldInterceptRequest(request.url)
            }
        }

        web.loadUrl("$PAGE?shape=${detectShape()}&nav=tap")

        // The rotary bezel/crown does not reach the page as a wheel event, so
        // translate it here into the page's own panel navigation.
        web.isFocusableInTouchMode = true
        web.requestFocus()
        web.setOnGenericMotionListener { _, ev ->
            if (ev.action == MotionEvent.ACTION_SCROLL &&
                ev.isFromSource(InputDevice.SOURCE_ROTARY_ENCODER)
            ) {
                val delta = ev.getAxisValue(MotionEvent.AXIS_SCROLL)
                val step = if (delta < 0) 1 else -1
                web.evaluateJavascript("show(page + ($step))", null)
                true
            } else {
                false
            }
        }

        refreshCalendarData()
    }

    /** Round is reported by the platform; square vs rectangular from the ratio. */
    private fun detectShape(): String {
        if (resources.configuration.isScreenRound) return "round"
        val m = resources.displayMetrics
        val ratio = m.widthPixels.toFloat() / m.heightPixels.toFloat()
        return if (abs(1f - ratio) < 0.12f) "square" else "rect"
    }

    /**
     * Pull the reachable year files into internal storage in the background, so
     * the app does not stay frozen on whatever was bundled at build time. The
     * running page has already loaded its data; the new copy is picked up next
     * launch, which keeps a session internally consistent.
     */
    private fun refreshCalendarData() {
        Thread {
            val year = Calendar.getInstance(SamCalendar.ISRAEL).get(Calendar.YEAR)
            val dir = File(filesDir, "cal").apply { mkdirs() }
            for (gy in (year - 1)..(year + 1)) {
                var conn: HttpURLConnection? = null
                try {
                    conn = (URL("$SITE/cal/$gy.dat").openConnection() as HttpURLConnection).apply {
                        connectTimeout = 8_000
                        readTimeout = 20_000
                    }
                    if (conn.responseCode == 200) {
                        val bytes = conn.inputStream.use { it.readBytes() }
                        if (bytes.size > 1000) {                 // never overwrite with a stub
                            val tmp = File(dir, "$gy.dat.part")
                            tmp.writeBytes(bytes)
                            if (!tmp.renameTo(File(dir, "$gy.dat"))) tmp.delete()
                        }
                    }
                } catch (e: Exception) {
                    // A watch is offline most of the time; the bundled copy covers it.
                } finally {
                    conn?.disconnect()
                }
            }
            SamCalendar.invalidate()
        }.apply { isDaemon = true }.start()
    }

    override fun onDestroy() {
        web.destroy()
        super.onDestroy()
    }
}
