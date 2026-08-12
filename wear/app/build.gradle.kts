// Imported rather than fully qualified: inside a Kotlin DSL build script the
// name `java` resolves to the project's java extension, so `java.time.Year`
// does not reference the package at all.
import java.time.Year
import java.time.ZoneId

plugins {
    id("com.android.application")
    id("org.jetbrains.kotlin.android")
}

// The repository root, two levels up — the web build and the calendar archive
// live there and are the single source of truth for both the app and the site.
val siteRoot = rootProject.projectDir.parentFile

// Years the watch page can actually reach (it probes y-1 … y+1). Bundling only
// these keeps the APK at a few hundred KB instead of shipping the 103 MB archive.
val currentYear = Year.now(ZoneId.of("Asia/Jerusalem")).value
val bundledYears = listOf(currentYear - 1, currentYear, currentYear + 1)

// Copy the web build into assets so the app opens instantly and works with no
// network at all on first launch. MainActivity later prefers fresher copies
// downloaded into internal storage, so the data is not frozen at build time.
val webAssets by tasks.registering(Copy::class) {
    into(layout.buildDirectory.dir("generated/webAssets"))
    from(siteRoot.resolve("watch")) { into("watch") }
    from(siteRoot.resolve("Sam_font.ttf"))
    from(siteRoot.resolve("cal")) {
        into("cal")
        include(bundledYears.map { year -> "$year.dat" })
    }
    doFirst {
        val missing = bundledYears.filter { year -> !siteRoot.resolve("cal/$year.dat").isFile }
        if (missing.isNotEmpty()) {
            logger.warn(
                "wear: calendar years ${missing.joinToString()} are not in cal/ — " +
                    "the app will fall back to downloading them"
            )
        }
    }
}

android {
    namespace = "net.thesamaritans.samcalendar"
    compileSdk = 35

    defaultConfig {
        applicationId = "net.thesamaritans.samcalendar"
        minSdk = 30                    // Wear OS 3+ (Galaxy Watch 4 and later, Pixel Watch)
        targetSdk = 35
        versionCode = 1
        versionName = "1.0"
    }

    sourceSets["main"].assets.srcDir(layout.buildDirectory.dir("generated/webAssets"))

    buildTypes {
        release {
            isMinifyEnabled = false
            proguardFiles(getDefaultProguardFile("proguard-android-optimize.txt"), "proguard-rules.pro")
        }
    }
    compileOptions {
        sourceCompatibility = JavaVersion.VERSION_17
        targetCompatibility = JavaVersion.VERSION_17
    }
    kotlinOptions { jvmTarget = "17" }
}

tasks.named("preBuild") { dependsOn(webAssets) }

dependencies {
    implementation("androidx.core:core-ktx:1.15.0")
    implementation("androidx.activity:activity:1.9.3")
    implementation("androidx.webkit:webkit:1.12.1")

    // Tile (swipe from the watch face) and complication (text on the face itself)
    implementation("androidx.wear.tiles:tiles:1.4.1")
    implementation("androidx.wear.protolayout:protolayout:1.2.1")
    implementation("androidx.wear.watchface:watchface-complications-data-source:1.2.1")
    implementation("com.google.guava:guava:33.3.1-android")
}
