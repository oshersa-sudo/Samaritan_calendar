package net.thesamaritans.samcalendar

import android.content.Context
import android.util.Base64
import org.json.JSONObject
import java.io.File
import java.text.SimpleDateFormat
import java.util.Calendar
import java.util.Date
import java.util.Locale
import java.util.TimeZone

/**
 * Reads the calendar straight from the same .dat files the web build uses:
 * base64, XOR'd with a fixed key, then JSON. Kept deliberately identical to
 * decodeDat() in watch/index.html so the tile, the complication and the page
 * can never disagree about what day it is.
 *
 * A year is looked up in internal storage first (refreshed from the live site
 * by MainActivity) and falls back to the copy bundled in assets.
 */
object SamCalendar {

    private const val KEY = "shomron-luach-5786"
    val ISRAEL: TimeZone = TimeZone.getTimeZone("Asia/Jerusalem")

    /** Holidays worth surfacing on a watch face — the weekly portion is not one. */
    private val NOTABLE = setOf("sam", "moed", "rosh", "community", "jew", "national")

    data class Fest(val kind: String, val name: String)

    data class Day(
        val greg: String,
        val hebDay: Int,
        val hebLabel: String,
        val monthName: String,
        val weekday: String,
        val sunrise: String,
        val sunset: String,
        val festivals: List<Fest>
    ) {
        val notable: List<Fest> get() = festivals.filter { it.kind in NOTABLE }
    }

    private val cache = HashMap<Int, JSONObject?>()

    // ---------------- dates (always Israel local, wherever the watch is) ----------------

    private fun fmt() = SimpleDateFormat("yyyy-MM-dd", Locale.US).apply { timeZone = ISRAEL }

    fun todayIso(): String = fmt().format(Date())

    fun addDays(iso: String, n: Int): String {
        val f = fmt()
        val c = Calendar.getInstance(ISRAEL)
        c.time = f.parse(iso) ?: return iso
        c.add(Calendar.DAY_OF_MONTH, n)
        return f.format(c.time)
    }

    fun daysBetween(from: String, to: String): Int {
        val f = fmt()
        val a = f.parse(from) ?: return 0
        val b = f.parse(to) ?: return 0
        return Math.round((b.time - a.time) / 86_400_000.0).toInt()
    }

    /** 0 = Sunday … 6 = Saturday, for the given ISO date. */
    fun weekdayIndex(iso: String): Int {
        val c = Calendar.getInstance(ISRAEL)
        c.time = fmt().parse(iso) ?: return 0
        return c.get(Calendar.DAY_OF_WEEK) - 1
    }

    val WEEKDAYS = listOf("ראשון", "שני", "שלישי", "רביעי", "חמישי", "שישי", "שבת")
    val MONTHS_HE = listOf(
        "", "ינואר", "פברואר", "מרץ", "אפריל", "מאי", "יוני",
        "יולי", "אוגוסט", "ספטמבר", "אוקטובר", "נובמבר", "דצמבר"
    )

    fun gregLabel(iso: String): String =
        "${iso.substring(8, 10).toInt()} ${MONTHS_HE[iso.substring(5, 7).toInt()]}"

    // ---------------- data ----------------

    private fun decode(b64: String): String {
        val raw = Base64.decode(b64, Base64.DEFAULT)
        for (i in raw.indices) raw[i] = (raw[i].toInt() xor KEY[i % KEY.length].code).toByte()
        return String(raw, Charsets.UTF_8)
    }

    /** Fresher downloaded copy if we have one, otherwise the bundled asset. */
    fun datSource(ctx: Context, gy: Int): (() -> String)? {
        val f = File(ctx.filesDir, "cal/$gy.dat")
        if (f.isFile && f.length() > 1000) return { f.readText() }
        return try {
            ctx.assets.open("cal/$gy.dat").close()
            { ctx.assets.open("cal/$gy.dat").bufferedReader().use { it.readText() } }
        } catch (e: Exception) {
            null
        }
    }

    private fun year(ctx: Context, gy: Int): JSONObject? {
        cache[gy]?.let { return it }
        if (cache.containsKey(gy)) return null
        val parsed = try {
            datSource(ctx, gy)?.let { JSONObject(decode(it())) }
        } catch (e: Exception) {
            null
        }
        cache[gy] = parsed
        return parsed
    }

    /** Drop cached years so a refreshed download is picked up. */
    fun invalidate() = cache.clear()

    private fun toDay(d: JSONObject, monthName: String): Day {
        val fests = ArrayList<Fest>()
        d.optJSONArray("festivals")?.let { arr ->
            for (i in 0 until arr.length()) {
                val f = arr.getJSONObject(i)
                fests.add(Fest(f.optString("kind"), f.optString("name")))
            }
        }
        return Day(
            greg = d.optString("greg"),
            hebDay = d.optInt("heb_day"),
            hebLabel = d.optString("heb_label"),
            monthName = monthName,
            weekday = d.optString("weekday"),
            sunrise = d.optString("sunrise"),
            sunset = d.optString("sunset"),
            festivals = fests
        )
    }

    /**
     * A Samaritan year file starts in Nisan (≈April), so an ISO date in Jan–Mar
     * lives in the previous greg_year file — probe both, newest first.
     */
    fun findDay(ctx: Context, iso: String): Day? {
        val y = iso.substring(0, 4).toIntOrNull() ?: return null
        for (gy in intArrayOf(y, y - 1)) {
            val yc = year(ctx, gy) ?: continue
            val months = yc.optJSONArray("months") ?: continue
            for (mi in 0 until months.length()) {
                val mo = months.getJSONObject(mi)
                val days = mo.optJSONArray("days") ?: continue
                for (di in 0 until days.length()) {
                    val d = days.getJSONObject(di)
                    if (d.optString("greg") == iso) return toDay(d, mo.optString("name"))
                }
            }
        }
        return null
    }

    /** The soonest notable festival strictly after [fromIso], across year files. */
    fun nextFestival(ctx: Context, fromIso: String): Day? {
        val y = fromIso.substring(0, 4).toIntOrNull() ?: return null
        var best: Day? = null
        for (gy in intArrayOf(y - 1, y, y + 1)) {
            val yc = year(ctx, gy) ?: continue
            val months = yc.optJSONArray("months") ?: continue
            for (mi in 0 until months.length()) {
                val mo = months.getJSONObject(mi)
                val days = mo.optJSONArray("days") ?: continue
                for (di in 0 until days.length()) {
                    val raw = days.getJSONObject(di)
                    val iso = raw.optString("greg")
                    if (iso <= fromIso) continue
                    if (best != null && iso >= best.greg) continue
                    val day = toDay(raw, mo.optString("name"))
                    if (day.notable.isNotEmpty()) best = day
                }
            }
        }
        return best
    }

    /**
     * Shabbat runs sunset to sunset: entry is Friday's sunset, exit is
     * Saturday's. On Saturday itself this still describes the current Shabbat.
     */
    fun shabbat(ctx: Context, iso: String): Pair<Day, Day?>? {
        val dow = weekdayIndex(iso)
        val friday = if (dow == 6) addDays(iso, -1) else addDays(iso, (5 - dow + 7) % 7)
        val fri = findDay(ctx, friday) ?: return null
        return fri to findDay(ctx, addDays(friday, 1))
    }
}
