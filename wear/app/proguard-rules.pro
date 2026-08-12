# Minification is off for release builds; keep this file so proguardFiles resolves.
# The tile and complication services are entered by the system, never by our code.
-keep class net.thesamaritans.samcalendar.TodayTileService { *; }
-keep class net.thesamaritans.samcalendar.TodayComplicationService { *; }
