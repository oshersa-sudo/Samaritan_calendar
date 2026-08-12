package net.thesamaritans.samcalendar

import android.app.PendingIntent
import android.content.Intent
import androidx.wear.watchface.complications.data.ComplicationData
import androidx.wear.watchface.complications.data.ComplicationText
import androidx.wear.watchface.complications.data.ComplicationType
import androidx.wear.watchface.complications.data.LongTextComplicationData
import androidx.wear.watchface.complications.data.PlainComplicationText
import androidx.wear.watchface.complications.data.ShortTextComplicationData
import androidx.wear.watchface.complications.datasource.ComplicationDataSourceService
import androidx.wear.watchface.complications.datasource.ComplicationRequest

/**
 * Puts the Samaritan date on the watch face itself. SHORT_TEXT is the day
 * number alone — a complication slot is a few characters wide — and LONG_TEXT
 * adds the month, or today's festival when there is one.
 */
class TodayComplicationService : ComplicationDataSourceService() {

    private fun plain(s: String): ComplicationText =
        PlainComplicationText.Builder(s).build()

    private fun tapIntent(): PendingIntent = PendingIntent.getActivity(
        this, 0,
        Intent(this, MainActivity::class.java).addFlags(Intent.FLAG_ACTIVITY_NEW_TASK),
        PendingIntent.FLAG_IMMUTABLE
    )

    private fun build(type: ComplicationType, short: String, long: String): ComplicationData? =
        when (type) {
            ComplicationType.SHORT_TEXT ->
                ShortTextComplicationData.Builder(plain(short), plain(long))
                    .setTapAction(tapIntent())
                    .build()

            ComplicationType.LONG_TEXT ->
                LongTextComplicationData.Builder(plain(long), plain(long))
                    .setTapAction(tapIntent())
                    .build()

            else -> null
        }

    override fun getPreviewData(type: ComplicationType): ComplicationData? =
        build(type, "ל", "ל · החדש הרביעי")

    override fun onComplicationRequest(
        request: ComplicationRequest,
        listener: ComplicationDataSourceService.ComplicationRequestListener
    ) {
        val today = SamCalendar.todayIso()
        val day = SamCalendar.findDay(this, today)

        if (day == null) {
            listener.onComplicationData(null)
            return
        }

        val short = day.hebDay.toString()
        val festivals = day.notable.joinToString(" · ") { it.name }
        val long = if (festivals.isNotEmpty()) "${day.hebDay} · $festivals"
        else "${day.hebDay} · ${day.monthName}"

        listener.onComplicationData(build(request.complicationType, short, long))
    }
}
