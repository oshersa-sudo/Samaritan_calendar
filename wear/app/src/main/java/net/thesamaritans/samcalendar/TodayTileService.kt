package net.thesamaritans.samcalendar

import androidx.wear.protolayout.ActionBuilders
import androidx.wear.protolayout.ColorBuilders.argb
import androidx.wear.protolayout.DimensionBuilders.dp
import androidx.wear.protolayout.DimensionBuilders.expand
import androidx.wear.protolayout.DimensionBuilders.sp
import androidx.wear.protolayout.LayoutElementBuilders
import androidx.wear.protolayout.ModifiersBuilders
import androidx.wear.protolayout.ResourceBuilders
import androidx.wear.protolayout.TimelineBuilders
import androidx.wear.tiles.RequestBuilders
import androidx.wear.tiles.TileBuilders
import androidx.wear.tiles.TileService
import com.google.common.util.concurrent.Futures
import com.google.common.util.concurrent.ListenableFuture

/**
 * The glanceable surface: swipe from the watch face and today's Samaritan date
 * is there without opening anything. Text is modern Hebrew — protolayout cannot
 * embed the Samaritan font, and the script toggle belongs in the app.
 */
class TodayTileService : TileService() {

    private companion object {
        const val RES_VERSION = "1"
        const val GOLD = 0xFFC9A35F.toInt()
        const val INK = 0xFFF2ECE0.toInt()
        const val MUTED = 0xFF8F8676.toInt()
        const val REFRESH_MS = 30L * 60L * 1000L
    }

    override fun onTileRequest(
        requestParams: RequestBuilders.TileRequest
    ): ListenableFuture<TileBuilders.Tile> {
        val tile = TileBuilders.Tile.Builder()
            .setResourcesVersion(RES_VERSION)
            .setFreshnessIntervalMillis(REFRESH_MS)
            .setTileTimeline(
                TimelineBuilders.Timeline.Builder()
                    .addTimelineEntry(
                        TimelineBuilders.TimelineEntry.Builder()
                            .setLayout(
                                LayoutElementBuilders.Layout.Builder()
                                    .setRoot(root())
                                    .build()
                            )
                            .build()
                    )
                    .build()
            )
            .build()
        return Futures.immediateFuture(tile)
    }

    override fun onTileResourcesRequest(
        requestParams: RequestBuilders.ResourcesRequest
    ): ListenableFuture<ResourceBuilders.Resources> =
        Futures.immediateFuture(
            ResourceBuilders.Resources.Builder().setVersion(RES_VERSION).build()
        )

    // ---------------- layout ----------------

    private fun text(
        value: String,
        sizeSp: Float,
        color: Int,
        bold: Boolean = false,
        maxLines: Int = 2
    ): LayoutElementBuilders.Text =
        LayoutElementBuilders.Text.Builder()
            .setText(value)
            .setMaxLines(maxLines)
            .setFontStyle(
                LayoutElementBuilders.FontStyle.Builder()
                    .setSize(sp(sizeSp))
                    .setColor(argb(color))
                    .setWeight(
                        if (bold) LayoutElementBuilders.FONT_WEIGHT_BOLD
                        else LayoutElementBuilders.FONT_WEIGHT_NORMAL
                    )
                    .build()
            )
            .build()

    private fun spacer(height: Float): LayoutElementBuilders.Spacer =
        LayoutElementBuilders.Spacer.Builder().setHeight(dp(height)).build()

    private fun root(): LayoutElementBuilders.LayoutElement {
        val today = SamCalendar.todayIso()
        val day = SamCalendar.findDay(this, today)

        val column = LayoutElementBuilders.Column.Builder()
            .setWidth(expand())
            .setHorizontalAlignment(LayoutElementBuilders.HORIZONTAL_ALIGN_CENTER)

        if (day == null) {
            column.addContent(text(getString(R.string.tile_no_data), 14f, MUTED))
        } else {
            column.addContent(
                text(SamCalendar.WEEKDAYS[SamCalendar.weekdayIndex(today)], 13f, GOLD, maxLines = 1)
            )
            column.addContent(spacer(2f))
            column.addContent(text(day.hebDay.toString(), 34f, INK, bold = true, maxLines = 1))
            column.addContent(text(day.monthName, 13f, GOLD))
            column.addContent(spacer(4f))
            column.addContent(
                text("${SamCalendar.gregLabel(today)}  ·  ☾ ${day.sunset}", 12f, MUTED, maxLines = 1)
            )

            // Whatever is worth knowing next: today's own festivals, else the countdown.
            val line = day.notable.takeIf { it.isNotEmpty() }
                ?.joinToString(" · ") { it.name }
                ?: SamCalendar.nextFestival(this, today)?.let { next ->
                    val n = SamCalendar.daysBetween(today, next.greg)
                    val name = next.notable.first().name
                    if (n == 1) getString(R.string.tile_tomorrow, name)
                    else getString(R.string.tile_in_days, name, n)
                }
            if (line != null) {
                column.addContent(spacer(4f))
                column.addContent(text(line, 12f, INK))
            }
        }

        return LayoutElementBuilders.Box.Builder()
            .setWidth(expand())
            .setHeight(expand())
            .setModifiers(
                ModifiersBuilders.Modifiers.Builder()
                    .setPadding(
                        ModifiersBuilders.Padding.Builder().setAll(dp(14f)).build()
                    )
                    .setClickable(
                        ModifiersBuilders.Clickable.Builder()
                            .setId("open")
                            .setOnClick(
                                ActionBuilders.LaunchAction.Builder()
                                    .setAndroidActivity(
                                        ActionBuilders.AndroidActivity.Builder()
                                            .setPackageName(packageName)
                                            .setClassName(MainActivity::class.java.name)
                                            .build()
                                    )
                                    .build()
                            )
                            .build()
                    )
                    .build()
            )
            .addContent(column.build())
            .build()
    }
}
